import copy
import logging

from AccessControl import getSecurityManager
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage
from zope.component.hooks import getSite
from zope.component import queryUtility

from collective.teamwork.interfaces import APP_LOG, IProjectContext
from collective.teamwork.user.members import SiteMembers
from collective.teamwork.user.workgroups import WorkspaceRoster
from collective.teamwork.user.interfaces import IWorkgroupTypes
from collective.teamwork.utils import parent_workspaces
from collective.teamwork.utils import get_workspaces


_true = lambda a, b: bool(a) and a == b  # for reduce()


def normalize_fullname(value):
    """
    Normalize fullname: strip trailing whitespace, then
    use a re-join of split string to split on unicode whitespace
    characters or multiple whitespace characters.

    The purpose of this is to address copy/paste errors, such as
    incidental inclusion of excess whitespace between name tokens or
    use of unicode whitespace such as u'\u000a' (nbsp) or line-feed.
    Python u''.strip() and u''.split() appear to correctly handle:
        http://en.wikipedia.org/wiki/Whitespace_character#Unicode
    """
    if not isinstance(value, unicode):
        value = value.decode('utf-8')
    value = value.strip()
    return u' '.join(value.split())


class WorkspaceViewBase(object):
    """
    Base for views on workspaces, includes means for logging from
    a view on a workspace context.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal = getSite()
        self.site_members = SiteMembers(self.portal, self.request)
        self.mtool = getToolByName(context, 'portal_membership')
        self.roster = WorkspaceRoster(context)
        self.title = self.context.Title().decode('utf-8')
        self.path = '/'.join(self.context.getPhysicalPath())
        self.status = IStatusMessage(self.request)
        self.isproject = IProjectContext.providedBy(context)

    def type_title(self):
        """Returns workspace type title for use in templates"""
        typename = self.context.portal_type
        types_tool = getToolByName(self.portal, 'portal_types')
        return types_tool.getTypeInfo(typename).Title().lower()

    def _log(self, msg, level=logging.INFO):
        """
        Log with prefix to application log.

        Prefix includes view name, site name, context path, username
        Timestamps are not in prefix, included by logging framework.

        Example prefix:
        WorkspaceMembership: [mysite] /mysite/a/b (me@example.com) --

        """
        if not hasattr(self, 'authuser'):
            self.authuser = self.mtool.getAuthenticatedMember().getUserName()
        view_cls = self.__class__
        if view_cls.__name__.startswith('SimpleViewClass'):
            view_cls = self.__class__.__bases__[0]  # work-around Five magic
        site = self.portal.getId()
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        prefix = '%s: [%s] %s (%s) -- ' % (
            view_cls.__name__,
            site,
            '/'.join(self.context.getPhysicalPath()),
            self.authuser,
            )
        msg = '%s %s' % (prefix, msg)
        APP_LOG.log(level, msg)


class WorkspaceMembership(WorkspaceViewBase):
    """
    Workspace membership view, provides a front-end around
    backend adapters for workspace in collective.teamwork.user modules.
    """

    def __init__(self, context, request):
        super(WorkspaceMembership, self).__init__(context, request)
        self.search_user_result = []
        self.form = self.request.form
        self.config = None

    def groups(self, username=None):
        if self.config is None:
            group_types = queryUtility(IWorkgroupTypes)
            if self.isproject:
                self.config = group_types.select('project')
            else:
                self.config = group_types.values()
        if username is not None:
            config = copy.deepcopy(self.config)
            for groupinfo in config:
                groupid = groupinfo['groupid']
                if groupid == 'viewers':
                    groupinfo['checked'] = True  # given for any user in grid
                else:
                    workspace_group = self.roster.groups[groupid]
                    groupinfo['checked'] = username in workspace_group
            return config
        return self.config

    def can_purge(self, username):
        """
        Return true if user can be purged from site -- only if they
        are not member of another project.
        """
        if username == self.authuser:
            return False  # managers cannot remove themselves
        return self.roster.can_purge(username)

    def purge(self, username):
        if not self.can_purge(username):
            raise ValueError('cannot purge this user %s' % username)
        self.roster.purge(username)

    def _manager_can_remove_themself(self):
        return self.sm.checkPermission('Manage site', self.context.__parent__)

    def _add_user_to_parent_workspaces(self, username, log_prefix=u''):
        """
        If there are workspaces containing this workspace,
        add the user to the containing workspace roster (as a viewer),
        so, if you (for example) add a user to a team, they also get
        added to the project containing that team:
        """
        for container in parent_workspaces(self.context):
            roster = WorkspaceRoster(container)
            if username not in roster:
                roster.add(username)
                user = self.site_members.get(username)
                fullname = user.getProperty('fullname', '')
                msg = u'Added user %s (%s) to workspace "%s"' % (
                    fullname.decode('utf-8'),
                    username,
                    container.Title().decode('utf-8'),
                    )
                self.status.addStatusMessage(msg, type='info')
                if log_prefix:
                    msg = '%s %s' % (log_prefix, msg)
                self._log(msg, level=logging.INFO)

    def _update_search_users(self, *args, **kwargs):
        q = self.form.get('search_user_query', '').strip() or None
        if q is None:
            msg = u'Empty user search; please try again.'
            self.status.addStatusMessage(msg, type='warning')
            return
        r = self.site_members.search(q)
        msg = u'No users found.'  # default message
        self.search_user_result = [
            {
                'username': username,
                'email': user.getProperty('email'),
                'fullname': user.getProperty('fullname'),
            }
            for username, user in r if username not in self.roster
            ]
        if self.search_user_result:
            msg = u'Users matching your search appear below; please select '\
                  u'users with checkboxes and click "Add selected users" '\
                  u'button below to add user(s) to your workspace.'
        if r and not self.search_user_result:
            msg += u'Existing workspace members are excluded from results.'
        self.status.addStatusMessage(msg, type='info')

    def _update_select_existing(self, *args, **kwargs):
        """
        Given a list of existing site members to add, add each.
        Operation will not complete for all member ids passed
        if any member id is not found.
        """
        _add = [k.replace('addmember-', '')
                for k in self.form if k.startswith('addmember-')]
        for username in _add:
            if username in self.roster:
                msg = u'User %s is already a workspace member' % username
                self.status.addStatusMessage(msg, type='warning')
                continue  # add status message, skip user, move to next
            member = self.site_members.get(username, None)
            if member is None:
                msg = 'User not found: %s' % username
                self.status.addStatusMessage(msg, type='error')
                self._log(msg, level=logging.ERROR)
                return
            fullname = member.getProperty('fullname')
            self.roster.add(username)
            msg = u'Added user %s (%s) to workspace "%s"' % (
                fullname.decode('utf-8'),
                username,
                self.title,
                )
            self.status.addStatusMessage(msg, type='info')
            self._log(msg, level=logging.INFO)
            self._add_user_to_parent_workspaces(
                username,
                log_prefix=u'_update_select_existing',
                )
        self.refresh()

    def _update_grid(self, *args, **kwargs):
        groupmeta = self.groups()
        ## create a mapping of named (by group) queues for each action
        ## each mapping will maintain a set of usernames per group
        ## for removal, addition:
        _unassign = dict((info['groupid'], set()) for info in groupmeta)
        _add = dict((info['groupid'], set()) for info in groupmeta)
        ## get a list of known usernames to form at time of its render
        ## -- this avoids race condition when roster changes do to a member
        ##    being added in the meantime; however, if a member is deleted,
        ##    between form render and form submit, we need to handle that
        ##    by getting an intersection of roster for workspace and the
        ##    set of all usernames known to the form.
        ##    (the form template is responsible to render a hidden input
        ##      for each username with a name containing the username).
        known = set(self.roster.keys())
        managed = set(k.replace('managegroups-', '') for k in self.form.keys()
                      if k.startswith('managegroups-'))
        managed = managed.intersection(known)
        ## iterate through each known group (column in grid):
        for info in groupmeta:
            groupid = info['groupid']
            group = self.roster.groups[groupid]
            form_group_users = set(k.split('/')[1] for k, v in self.form.items()
                                   if k.startswith('group-%s/' % groupid))
            for username in managed:
                if username not in form_group_users and username in group:
                    # was in group existing, but ommitted/unchecked in form
                    # for this username -- mark for removal.
                    _unassign[groupid].add(username)
                elif username in form_group_users and username not in group:
                    # not yet in existing group, but specified/checked
                    # in form, so we need to mark for adding
                    _add[groupid].add(username)
        groups = self.roster.groups.values()
        for groupid, deletions in _unassign.items():
            group = self.roster.groups[groupid]
            for username in deletions:
                if username in group:
                    existing_user_groups = [g for g in groups
                                            if username in g]
                    if username == self.authuser and groupid == 'managers':
                        if not self._manager_can_remove_themself():
                            msg = u'Managers cannot remove manager role for '\
                                u'themselves (%s)' % (username,)
                            self.status.addStatusMessage(msg, type='warning')
                            continue
                    if groupid == 'viewers' and len(existing_user_groups) > 1:
                        other_deletions = reduce(
                            _true,
                            [username in v for k, v in _unassign.items()
                             if k != 'viewers'],
                            )
                        if not other_deletions:
                            # danger, danger: user in non-viewers group
                            # not also marked for deletion
                            msg = u'User %s cannot be removed from '\
                                  u'Viewers group when also member '\
                                  u'of other groups.  To remove '\
                                  u'use please uncheck all group '\
                                  u'assignments in the grid.' % (username,)
                            self.status.addStatusMessage(
                                msg,
                                type="warning",
                                )
                            continue
                    group.unassign(username)
                    rmsg = u'%s removed from %s group for workspace (%s).'
                    msg = rmsg % (
                        username,
                        group.title,
                        self.title,
                        )
                    if groupid == 'viewers':
                        # a total removal from workspace implies removal
                        # of all assignments from contained workspaces.
                        self.status.addStatusMessage(msg, type='info')
                        self._log(msg, level=logging.INFO)
                        for workspace in get_workspaces(self.context):
                            roster = WorkspaceRoster(workspace)
                            if username in roster.groups['viewers']:
                                for group in roster.groups.values():
                                    if username in group:
                                        group.unassign(username)
        for groupid, additions in _add.items():
            group = self.roster.groups[groupid]
            for username in additions:
                if username not in group:
                    group.add(username)
                    msg = u'%s added to %s group for workspace (%s).' % (
                        username,
                        group.title,
                        self.title,
                        )
                    self.status.addStatusMessage(msg, type='info')
                    self._log(msg, level=logging.INFO)
        self.refresh()

    def _update_register(self, *args, **kwargs):
        email = self.form.get('newuser_email', None)
        fullname = self.form.get('newuser_fullname', None)
        if email is None:
            self.status.addStatusMessage(
                u'Empty email address (required).', type='error')
            return
        if fullname is None:
            self.status.addStatusMessage(
                u'Empty full name (required).', type='error')
            return
        username = email.lower().strip()
        fullname = normalize_fullname(fullname)
        if username in self.roster or username in self.site_members:
            msg = u'%s is already registered.' % username
            if username in self.roster:
                msg = '%s User already member of workspace.' % username
            self.status.addStatusMessage(msg, type='error')
            self._log(msg, level=logging.WARNING)
            return
        try:
            _m = 'newuser_sendmail'
            send = bool(self.form[_m]) if _m in self.form else False
            self.site_members.register(username, fullname=fullname, send=send)
            msg = u'Registered user %s (%s) to site, added to project. ' % (
                fullname,
                username,
                )
            if send:
                msg += u'Sent notification message to user.'
            self.status.addStatusMessage(msg, type='info')
            self._log(msg, level=logging.INFO)
        except ValueError:
            # registration tool registeredNotify() username validation error
            msg = u'Error registering %s. Invalid email address.' % username
            self.status.addStatusMessage(msg, type='error')
            self._log(msg, level=logging.WARNING)
            return
        except KeyError:
            msg = u'%s is already registered and a workspace member.' % username
            self.status.addStatusMessage(msg, type='error')
            self._log(msg, level=logging.WARNING)
            return
        self.roster.add(username)  # finally, add newly registered to workspace
        msg = u'Added user %s (%s) to workspace "%s"' % (
            fullname,
            username,
            self.title,
            )
        self.status.addStatusMessage(msg, type='info')
        msg = u'_update_register(): %s' % msg
        self._log(msg, level=logging.INFO)
        self._add_user_to_parent_workspaces(
            username,
            log_prefix=u'_update_register:',
            )
        self.refresh()

    def refresh(self):
        self.site_members.refresh()
        self.roster.refresh()

    def update(self, *args, **kwargs):
        """
        Execute correct processor for respective (mutually exclusive)
        form submit for any of:
            * Search existing site users (search_users)
            * Select users from result, add (select_existing_users)
            * Update roles from grid of users (grid_update)
            * Add a new user to the site (register_new_user)

        Determining which processor to use is based upon checks for
        (named) button input values passed for each respective form.
        The button name acts as a key for processor methods to carry
        out implementation of update action.  Arguments passed to
        update() are passed as-is to each processor.
        """
        self.authuser = self.mtool.getAuthenticatedMember().getUserName()
        self.sm = getSecurityManager()
        processors = {
            'search_users': self._update_search_users,
            'select_existing_users': self._update_select_existing,
            'grid_update': self._update_grid,
            'register_new_user': self._update_register,
            }
        for key, fn in processors.items():
            if key in self.form:
                return fn(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # provided by Five magic

