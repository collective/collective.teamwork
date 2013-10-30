import logging

from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage
from zope.component.hooks import getSite
from zope.component import queryUtility

from collective.teamwork.interfaces import APP_LOG, IProjectContext
from collective.teamwork.user.members import SiteMembers
from collective.teamwork.user.workgroups import WorkspaceRoster
from collective.teamwork.user.interfaces import IWorkgroupTypes
from collective.teamwork.utils import containing_workspaces
from collective.teamwork.utils import contained_workspaces


_true = lambda a, b: bool(a) and a == b  # for reduce()


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

    # TODO: memoize this
    def groups(self, email=None):
        if self.config is None:
            self.config = queryUtility(IWorkgroupTypes)
        if IProjectContext.providedBy(self.context):
            _groups = self.config.select('project')
        else:
            _groups = self.config.values()
        if email is not None:
            for groupinfo in _groups:
                groupid = groupinfo['groupid']
                if groupid == 'viewers':
                    groupinfo['checked'] = True  # given for any user in grid
                else:
                    workspace_group = self.roster.groups[groupid]
                    groupinfo['checked'] = email in workspace_group
        return _groups

    def can_purge(self, email):
        """
        Return true if user can be purged from site -- only if they
        are not member of another project.
        """
        if email == self.authuser:
            return False  # managers cannot remove themselves
        return self.roster.can_purge(email)

    def purge(self, email):
        if not self.can_purge(email):
            raise ValueError('cannot purge this user %s' % email)
        self.roster.remove(email, purge=True)

    def _add_user_to_containing_workspaces(self, email, log_prefix=u''):
        """
        If there are workspaces containing this workspace,
        add the user to the containing workspace roster (as a viewer),
        so, if you (for example) add a user to a team, they also get
        added to the project containing that team:
        """
        for container in containing_workspaces(self.context):
            roster = WorkspaceRoster(container)
            if email not in roster:
                roster.add(email)
                user = self.site_members.get(email)
                fullname = user.getProperty('fullname', '')
                msg = u'Added user %s (%s) to workspace "%s"' % (
                    fullname.decode('utf-8'),
                    email,
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
            {'email': id, 'fullname': user.getProperty('fullname')}
            for id, user in r if id not in self.roster
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
        for email in _add:
            if email in self.roster:
                msg = u'User %s is already a workspace member' % email
                self.status.addStatusMessage(msg, type='warning')
                continue  # add status message, skip user, move to next
            member = self.site_members.get(email, None)
            if member is None:
                msg = 'User not found: %s' % email
                self.status.addStatusMessage(msg, type='error')
                self._log(msg, level=logging.ERROR)
                return
            fullname = member.getProperty('fullname')
            self.roster.add(email)
            msg = u'Added user %s (%s) to workspace "%s"' % (
                fullname.decode('utf-8'),
                email,
                self.title,
                )
            self.status.addStatusMessage(msg, type='info')
            self._log(msg, level=logging.INFO)
            self._add_user_to_containing_workspaces(
                email,
                log_prefix=u'_update_select_existing',
                )
        self.roster.refresh()

    def _update_grid(self, *args, **kwargs):
        groupmeta = self.groups()
        ## create a mapping of named (by group) queues for each action
        ## each mapping will maintain a set of email addresses per group
        ## for removal, addition:
        _unassign = dict((info['groupid'], set()) for info in groupmeta)
        _add = dict((info['groupid'], set()) for info in groupmeta)
        ## get a list of known email addresses to form at time of its render
        ## -- this avoids race condition when roster changes do to a member
        ##    being added in the meantime; however, if a member is deleted,
        ##    between form render and form submit, we need to handle that
        ##    by getting an intersection of roster for workspace and the
        ##    set of all email addresses known to the form.
        ##    (the form template is responsible to render a hidden input
        ##      for each email with a name containing the email address).
        known = set(self.roster.keys())
        managed = set(k.split('-')[1] for k in self.form.keys()
                      if k.startswith('managegroups-'))
        managed = managed.intersection(known)
        ## iterate through each known group (column in grid):
        for info in groupmeta:
            groupid = info['groupid']
            group = self.roster.groups[groupid]
            form_group_users = set(k.split('/')[1] for k, v in self.form.items()
                                   if k.startswith('group-%s/' % groupid))
            for email in managed:
                if email not in form_group_users and email in group:
                    # was in group existing, but ommitted/unchecked in form
                    # for this email address / user id -- mark for removal.
                    _unassign[groupid].add(email)
                elif email in form_group_users and email not in group:
                    # not yet in existing group, but specified/checked
                    # in form, so we need to mark for adding
                    _add[groupid].add(email)
        groups = self.roster.groups.values()
        for groupid, deletions in _unassign.items():
            group = self.roster.groups[groupid]
            for email in deletions:
                if email in group:
                    existing_user_groups = [g for g in groups
                                            if email in g]
                    if email == self.authuser and groupid == 'managers':
                        msg = u'Managers cannot remove manager role for '\
                              u'themselves (%s)' % (email,)
                        self.status.addStatusMessage(msg, type='warning')
                        continue
                    if groupid == 'viewers' and len(existing_user_groups) > 1:
                        other_deletions = reduce(
                            _true,
                            [email in v for k, v in _unassign.items()
                             if k != 'viewers'],
                            )
                        if not other_deletions:
                            # danger, danger: user in non-viewers group
                            # not also marked for deletion
                            msg = u'User %s cannot be removed from '\
                                  u'Viewers group when also member '\
                                  u'of other groups.  To remove '\
                                  u'use please uncheck all group '\
                                  u'assignments in the grid.' % (email,)
                            self.status.addStatusMessage(
                                msg,
                                type="warning",
                                )
                            continue
                    group.unassign(email)
                    rmsg = u'%s removed from %s group for workspace (%s).'
                    msg = rmsg % (
                        email,
                        group.title,
                        self.title,
                        )
                    if groupid == 'viewers':
                        # a total removal from workspace implies removal
                        # of all assignments from contained workspaces.
                        self.status.addStatusMessage(msg, type='info')
                        self._log(msg, level=logging.INFO)
                        for workspace in contained_workspaces(self.context):
                            roster = WorkspaceRoster(workspace)
                            if email in roster.groups['viewers']:
                                for group in roster.groups.values():
                                    if email in group:
                                        group.unassign(email)
        for groupid, additions in _add.items():
            group = self.roster.groups[groupid]
            for email in additions:
                if email not in group:
                    group.add(email)
                    msg = u'%s added to %s group for workspace (%s).' % (
                        email,
                        group.title,
                        self.title,
                        )
                    self.status.addStatusMessage(msg, type='info')
                    self._log(msg, level=logging.INFO)

    def _update_register(self, *args, **kwargs):
        email = self.form.get('newuser_email', None)
        fullname = self.form.get('newuser_fullname', None)
        if email is None:
            self.status.addStatusMessage(
                u'Empty email (required).', type='error')
            return
        if fullname is None:
            self.status.addStatusMessage(
                u'Empty full name (required).', type='error')
            return
        email, fullname = email.strip(), fullname.decode('utf-8').strip()
        if email in self.roster or email in self.site_members:
            msg = u'%s is already registered.' % email
            if email in self.roster:
                msg = '%s User already member of workspace.' % email
            self.status.addStatusMessage(msg, type='error')
            self._log(msg, level=logging.WARNING)
            return
        try:
            _m = 'newuser_sendmail'
            send = bool(self.form[_m]) if _m in self.form else False
            self.site_members.register(email, fullname=fullname, send=send)
            msg = u'Registered user %s (%s) to site, added to project. ' % (
                fullname,
                email,
                )
            if send:
                msg += u'Sent notification email to user.'
            self.status.addStatusMessage(msg, type='info')
            self._log(msg, level=logging.INFO)
        except ValueError:
            # registration tool registeredNotify() email validation error
            msg = u'Error registering user %s. Invalid email address.' % email
            self.status.addStatusMessage(msg, type='error')
            self._log(msg, level=logging.WARNING)
            return
        except KeyError:
            msg = u'%s is already registered and a workspace member.' % email
            self.status.addStatusMessage(msg, type='error')
            self._log(msg, level=logging.WARNING)
            return
        self.roster.add(email)  # finally, add newly registered to workspace
        msg = u'Added user %s (%s) to workspace "%s"' % (
            fullname.decode('utf-8'),
            email,
            self.title,
            )
        self.status.addStatusMessage(msg, type='info')
        msg = u'_update_register(): %s' % msg
        self._log(msg, level=logging.INFO)
        self._add_user_to_containing_workspaces(
            email,
            log_prefix=u'_update_register:',
            )
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

