import logging
import re
import itertools

from Acquisition import aq_base
from plone.app.workflow.browser.sharing import merge_search_results
from zope.component import adapts
from zope.component.hooks import getSite
from zope.interface import implements
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin
from Products.PluggableAuthService.interfaces import plugins as PAS
from Products.PlonePAS.tools.membership import default_portrait
from Products.PlonePAS.interfaces.plugins import IUserManagement
from Products.PlonePAS.utils import cleanId, getGroupsForPrincipal
from Products.statusmessages.interfaces import IStatusMessage

from collective.teamwork.interfaces import APP_LOG
from collective.teamwork.utils import request_for
from interfaces import ISiteMembers, IGroups


MAILCONF = ('smtp_host', 'email_from_address')


def enumeration_plugins(acl_users):
    """All enumeration plugins minus known duplicative ones"""
    plugins = acl_users.plugins.listPlugins(PAS.IUserEnumerationPlugin)
    result = dict((name, enumerator) for name, enumerator in plugins)
    if 'source_users' in result and 'mutable_properties' in result:
        # we don't need both, will have same keys
        del(result['mutable_properties'])
    return result.values()


def management_plugins(acl_users):
    """All user-management plugins"""
    return acl_users.plugins.listPlugins(IUserManagement)


def list_users(plugin, keyonly=False):
    """
    Returns a list of userid, username (login) tuples for each user.
    If keyonly is True, returns a list of user id keys only.
    """
    if not PAS.IUserEnumerationPlugin.providedBy(plugin):
        raise ValueError('Plugin does not provide IUserEnumerationPlugin')
    direct_methods = ('getLoginForUserId', 'listUserIds')
    direct_listing = all(hasattr(plugin, n) for n in direct_methods)
    if direct_listing:
        # duck-typed capabilities of ZODBUserManager:
        userids = plugin.listUserIds()
        if keyonly:
            return userids  # optimal for __len__()
        pair = lambda userid: (userid, plugin.getLoginForUserId(userid))
        return map(pair, plugin.listUserIds())
    fn = lambda u: (u.get('id'), u.get('login'))
    if keyonly:
        fn = lambda u: u.get('id')
    return map(fn, plugin.enumerateUsers())


class SiteMembers(object):
    """
    Adapter of site presents an iterable mapping of user name (loging
    name) keys to IPropertiedUser user objects.

    Ideally constructed once per request by callers, may be cached
    in annotation of request by callers.
    """

    implements(ISiteMembers)
    adapts(ISiteRoot)  # also optionally multi-adapter view with request

    _rtool = _mdata = None

    def __init__(self, context=None, request=None):
        self.portal = self.context = context
        if not ISiteRoot.providedBy(context):
            self.context = self.portal = getSite()
        self.request = request
        if request is None:
            # use a fake request suitable for making CMF tools happy
            self.request = request_for(self.context)
        self.status = IStatusMessage(self.request)
        self._uf = getToolByName(self.context, 'acl_users')
        self._enumerators = enumeration_plugins(self._uf)
        self._management = management_plugins(self._uf)
        self.invalidate()  # clears self._users_cache
        self._groups = None

    @property
    def groups(self):
        if self._groups is None:
            self._groups = IGroups(self.portal)
        return self._groups

    def _reg_tool(self):
        if self._rtool is None:
            self._rtool = getToolByName(self.context, 'portal_registration')
        return self._rtool

    def _memberdata_tool(self):
        if self._mdata is None:
            self._mdata = getToolByName(self.context, 'portal_memberdata')
        return self._mdata

    def _log(self, msg, level=logging.INFO):
        site = '[%s]' % self.portal.getId()
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        msg = '%s %s' % (site, msg)  # prefix with site-name all messages
        APP_LOG.log(level, msg)

    def _usernames(self):
        if self._users_cache is None:
            self._users_cache = dict(
                set().union(*map(list_users, self._enumerators))
                )
        return self._users_cache.values()

    def invalidate(self):
        self._users_cache = None

    def __contains__(self, username):
        """Does user exist in site for user login name / email"""
        within = lambda p: p.enumerateUsers(login=username, exact_match=True)
        return any(map(within, self._enumerators))

    def __len__(self):
        """Return number of users in site"""
        listids = lambda plugin: list_users(plugin, keyonly=True)
        if self._users_cache:
            return len(self._users_cache)
        return len(set().union(*map(listids, self._enumerators)))

    def __getitem__(self, username):
        """
        Get item by user login name / email or raise KeyError;
        result should provide IPropertiedUser
        """
        v = self.get(username)
        if v is None:
            raise KeyError('Unknown username: %s' % username)
        return v

    def get(self, username, default=None):
        """
        Get a user by user name / email address, or
        return default. Non-default result should provide
        IPropertiedUser.
        """
        if username not in self:
            return default
        return self._uf.getUser(username)

    def userid_for(self, key):
        """
        Given key as login name or a user object, return
        the internal user id for that user.

        Note: this implementation obtains the user for each login name, which
        avoids an optimization that would be specific to
        ZODBUserManager
        """
        user = key
        if isinstance(key, basestring):
            user = self.get(str(key))
        return user.getId()

    def login_name(self, key):
        """
        Get user login name for a user or an internal user id.
        """
        user = key
        if isinstance(key, basestring):
            key = str(key)
            user = self._uf.getUserById(key, self.get(key))
        return user.getUserName()

    def search(self, query, **kwargs):
        """
        Given a string or unicode object as a query, search for
        user by full name or email address / user id.  Return a
        iterator of tuples of (username, user) for each match.
        """
        q = {'name': query, 'email': query}  # either name or email
        q.update(kwargs or {})
        r = merge_search_results(
            itertools.chain(
                *[self._uf.searchUsers(**{field: query})
                    for field in ('login', 'fullname')]),
            key='userid',
            )
        _t = lambda username: (username, self._uf.getUser(username))
        return [_t(username) for username in [info['login'] for info in r]]

    def keys(self):
        return self._usernames()

    def __iter__(self):
        """return iterator over all user names"""
        return iter(self._usernames())

    # add and remove users:
    def register(self, username, context=None, send=True, **kwargs):
        """
        Given username and keyword arguments containing
        possible user/member attributes, register a member.
        If context is passed, use this context as part of the
        registration process (e.g. project-specific).  This
        should trigger the usual registration process: a user
        should receive an email to complete setup.
        """
        email = username
        fullname = kwargs.get('fullname', email)  # fall-back to email
        VALID_EMAIL = re.compile('[A-Za-z0-9_+\-]+@[A-Za-z0-9_+\-]+')
        if not VALID_EMAIL.search(username):
            email = kwargs.get('email', None)
        if username in self:
            raise KeyError('Duplicate username: %s in use' % username)
        rtool = self._reg_tool()
        pw = rtool.generatePassword()     # random temporary password
        props = {'email': email, 'username': username, 'fullname': fullname}
        rtool.addMember(username, pw, properties=props)
        if send:
            if email is None:
                raise KeyError('email not provided, but send specified')
            rtool.registeredNotify(email)
        self.invalidate()

    def __delitem__(self, username):
        """
        Given a key of username, purge/remove a user from the
        system.

        Note: it is expected that callers will check permissions
        accordingly in the context of the site being managed; this
        component does not check permissions.
        """
        if not self._management:
            raise KeyError('No plugins allow user removal')
        if username not in self:
            raise KeyError('Unknown username: %s' % username)
        userid = self.userid_for(username)
        removed = False
        for name, plugin in self._management:
            try:
                plugin.doDeleteUser(userid)
                removed = True
            except KeyError:
                pass  # continue, user might be in next plugin
        if not removed:
            msg = 'Unable to remove %s -- not found in removable user '\
                  'source.' % (username,)
            raise KeyError(msg)
        self._memberdata_tool().deleteMemberData(userid)
        self.invalidate()

    # other utility functionality

    def pwreset(self, username):
        """Send password reset for user id"""
        if not self._management:
            raise KeyError('No plugins allow password reset')
        if username not in self:
            raise KeyError('Unknown username: %s' % username)
        mh = aq_base(getToolByName(self.portal, 'MailHost'))
        _all = lambda s: reduce(lambda a, b: bool(a and b), s)
        if not _all([getattr(mh, k, None) for k in MAILCONF]):
            msg = u'Site mail settings incomplete; could not reset password'\
                  u'for user' % username
            self.status.add(msg, type=u'warning')
            self._log(msg, level=logging.WARNING)
            return
        rtool = self._reg_tool()
        pw = rtool.generatePassword()     # random temporary password
        changed = False
        for name, plugin in self._management:
            try:
                plugin.doChangeUser(username, password=pw)
                changed = True
            except RuntimeError:
                pass
        if not changed:
            msg = 'Could not change password for user; no suitable plugin '\
                  'allows change for %s' % username
            self.status.add(msg, type=u'warning')
            return
        self.request.form['new_password'] = pw
        rtool.mailPassword(username, REQUEST=self.request)
        msg = u'Reset user password and sent reset email to %s' % username
        self.status.add(msg, type=u'info')
        self._log(msg, level=logging.WARNING)

    def groups_for(self, username):
        """
        List all PAS groupnames for username / email; does not
        include indirect membership in nested groups.
        """
        if username not in self:
            if username not in self._uf.source_groups.listGroupIds():
                raise KeyError('Unknown username: %s' % username)
        return getGroupsForPrincipal(self.get(username), self._uf.plugins)

    def roles_for(self, context, username):
        """
        Return roles for context for a given user id (local roles)
        and all site-wide roles for the user.
        """
        result = set()
        if username in self:
            user = self.get(username)
        elif username in self._uf.source_groups.listGroupIds():
            user = self._uf.source_groups.getGroup(username)
        else:
            raise KeyError('Unknown username: %s' % username)
        role_mgr = self._uf.portal_role_manager
        lrm_plugins = self._uf.plugins.listPlugins(ILocalRolesPlugin)
        for name, plugin in lrm_plugins:
            result = result.union(plugin.getRolesInContext(user, context))
        result = result.union(role_mgr.getRolesForPrincipal(user))
        return list(result)

    def portrait_for(self, username, use_default=False):
        """
        Get portrait object for username, or return None (if use_default
        is False).  If use_default is True and no portrait exists,
        return the default.
        """
        userid = self.userid_for(username)
        portrait = self._memberdata_tool()._getPortrait(cleanId(userid))
        if portrait is None or isinstance(portrait, str):
            if use_default:
                return getattr(self.portal, default_portrait, None)
            return None
        return portrait

