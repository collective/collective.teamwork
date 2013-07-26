import logging
import re
from itertools import chain

from Aquisition import aq_base
from plone.app.workflow.browser.sharing import merge_search_results
from zope.component import adapts
from zope.component.hooks import getSite
from zope.interface import implements
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin
from Products.PlonePAS.tools.membership import default_portrait
from Products.PlonePAS.utils import cleanId

from uu.qiext.interfaces import APP_LOG
from uu.qiext.utils import request_for
from uu.qiext.user.interfaces import ISiteMembers

MAILCONF = ('smtp_host', 'email_from_address')


class SiteMembers(object):
    """
    Adapter implementation for SiteMembers for a site.  Should be
    constructed once per request by callers ideally, because
    construction creates references to half-a-dozen persistent
    tool components in a site.
    """

    implements(ISiteMembers)
    adapts(ISiteRoot)  # also optionally multi-adapter view with request

    def __init__(self, context, request=None):
        if not ISiteRoot.providedBy(context):
            raise ValueError('context does not provide ISiteRoot')
        self.portal = self.context = context
        self.request = request
        if request is None:
            self.request = request_for(context)  # a request, real or fake
        self._uf = getToolByName(context, 'acl_users')
        self._mtool = getToolByName(context, 'portal_membership')
        self._rtool = getToolByName(context, 'portal_registration')
        self._mdata = getToolByName(context, 'portal_memberdata')
        self._utils = getToolByName(context, 'plone_utils')
        self._groups = getToolByName(context, 'portal_groups')
        self._users_cache = None

    def _log(self, msg, level=logging.INFO):
        site = '[%s]' % self.portal.getId()
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        msg = '%s %s' % (site, msg)  # prefix with site-name all messages
        APP_LOG.log(level, msg)

    def _usernames(self):
        if self._users_cache is None:
            self._users_cache = list(self._uf.getUserNames())
        return self._users_cache

    def __contains__(self, userid):
        """Does user exist in site for user id / email"""
        return userid in self._usernames()

    def __len__(self):
        """Return number of users in site"""
        return len(self._usernames())

    def __getitem__(self, userid):
        """
        Get item by user id / email or raise KeyError;
        result should provide IPropertiedUser
        """
        if userid not in self._usernames():
            raise KeyError('Unknown username: %s' % userid)
        return self._uf.getUserById(userid)

    def get(self, userid, default=None):
        """
        Get a user by user id / email address, or
        return default. Non-default result should provide
        IPropertiedUser.
        """
        if userid not in self._usernames():
            return default
        return self._uf.getUserById(userid)

    def search(self, query, **kwargs):
        """
        Given a string or unicode object as a query, search for
        user by full name or email address / user id.  Return a
        iterator of tuples of (userid, user) for each match.
        """
        q = {'name': query, 'email': query}  # either name or email
        q.update(kwargs or {})
        r = merge_search_results(
            chain(
                *[self._uf.searchUsers(**{field: query})
                    for field in ('login', 'fullname')]),
            key='userid',
            )
        _t = lambda userid: (userid, self._uf.getUserById(userid))
        return [_t(userid) for userid in [info['userid'] for info in r]]

    def keys(self):
        return self._usernames()

    def __iter__(self):
        """return iterator over all user names"""
        return iter(self._usernames())

    # add and remove users:
    def register(self, userid, context=None, send=True, **kwargs):
        """
        Given userid and keyword arguments containing
        possible user/member attributes, register a member.
        If context is passed, use this context as part of the
        registration process (e.g. project-specific).  This
        should trigger the usual registration process: a user
        should receive an email to complete setup.
        """
        email = userid
        fullname = kwargs.get('fullname', email)  # fall-back to email
        VALID_EMAIL = re.compile('[A-Za-z0-9_+\-]+@[A-Za-z0-9_+\-]+')
        if not VALID_EMAIL.search(userid):
            email = kwargs.get('email', None)
        if userid in self._usernames():
            raise KeyError('Duplicate username: %s in use' % userid)
        pw = self._rtool.generatePassword()     # random temporary password
        props = {'email': email, 'username': userid, 'fullname': fullname}
        self._rtool.addMember(userid, pw, properties=props)
        if send:
            if email is None:
                raise KeyError('email not provided, but send specified')
            self._rtool.registeredNotify(email)
        self._users_cache = None

    def __delitem__(self, userid):
        """
        Given a key of userid (email), purge/remove a
        user from the system, if and only if the user id looks
        like an email address.

        Note: it is expected that callers will check permissions
        accordingly in the context of the site being managed; this
        component does not check permissions.
        """
        if userid not in self._usernames():
            raise KeyError('Unknown username: %s' % userid)
        member = self._mtool.getMemberById(userid)
        self._uf.userFolderDelUsers([userid])       # del from acl_users
        if member is not None:
            self._mdata.deleteMemberData(userid)    # del member data
        ## remove for now local role removal, too expensive without a more
        ## targeted approach.
        #self._mtool.deleteLocalRoles(               # del local roles site-wide
        #    self.portal,
        #    [userid],
        #    reindex=1,
        #    recursive=1,
        #    )
        self._users_cache = None

    # other utility functionality

    def pwreset(self, userid):
        """Send password reset for user id"""
        if userid not in self._usernames():
            raise KeyError('Unknown username: %s' % userid)
        mh = aq_base(getToolByName(self.portal, 'MailHost'))
        _all = lambda s: reduce(lambda a, b: bool(a and b), s)
        if not _all([getattr(mh, k, None) for k in MAILCONF]):
            msg = u'Site mail settings incomplete; could not reset password'\
                  u'for user' % userid
            self._utils.addPortalMessage(msg)
            self._log(msg, level=logging.WARNING)
            return
        pw = self._rtool.generatePassword()     # random temporary password
        self._uf.source_users.doChangeUser(userid, password=pw)
        self.request.form['new_password'] = pw
        self._rtool.mailPassword(userid, REQUEST=self.request)
        msg = u'Reset user password and sent reset email to %s' % userid
        self._utils.addPortalMessage(msg)
        self._log(msg, level=logging.WARNING)

    def groups_for(self, userid):
        """
        List all PAS groupnames for userid / email; does not
        include indirect membership in nested groups.
        """
        if userid not in self._usernames():
            if userid not in self._uf.source_groups.listGroupIds():
                raise KeyError('Unknown username: %s' % userid)
        return self._groups.getGroupsForPrincipal(self.get(userid))

    def roles_for(self, context, userid):
        """
        Return roles for context for a given user id (local roles)
        and all site-wide roles for the user.
        """
        result = set()
        if userid in self._usernames():
            user = self.get(userid)
        elif userid in self._uf.source_groups.listGroupIds():
            user = self._uf.source_groups.getGroup(userid)
        else:
            raise KeyError('Unknown username: %s' % userid)
        role_mgr = self._uf.portal_role_manager
        lrm_plugins = self._uf.plugins.listPlugins(ILocalRolesPlugin)
        for name, plugin in lrm_plugins:
            result = result.union(plugin.getRolesInContext(user, context))
        result = result.union(role_mgr.getRolesForPrincipal(user))
        return list(result)

    def portrait_for(self, userid, use_default=False):
        """
        Get portrait object for userid, or return None (if use_default
        is False).  If use_default is True and no portrait exists,
        return the default.
        """
        site = getSite()
        portrait = self._mdata._getPortrait(cleanId(userid))
        if portrait is None or isinstance(portrait, str):
            if use_default:
                return getattr(site, default_portrait, None)
            return None
        return portrait

