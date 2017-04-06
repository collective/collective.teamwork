# -*- coding: utf-8 -*-

import copy
import json
import logging

from AccessControl import getSecurityManager
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage
from zope.component.hooks import getSite
from zope.component import queryUtility

from collective.teamwork.interfaces import IProjectContext
from collective.teamwork.user.members import SiteMembers
from collective.teamwork.user.workgroups import WorkspaceRoster
from collective.teamwork.user.workgroups import WorkgroupMembershipState
from collective.teamwork.user.interfaces import IWorkgroupTypes
from collective.teamwork.user.interfaces import IMembershipModifications
from collective.teamwork.user.utils import LocalRolesView  # ~~▶ SharingView
from collective.teamwork.utils import log_status


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
        self.config = None
        self.authuser = self.mtool.getAuthenticatedMember().getUserName()

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
        log_status(msg, self.context, level=level)

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


class WorkspaceMembership(WorkspaceViewBase):
    """
    Workspace membership view, provides a front-end around
    backend adapters for workspace in collective.teamwork.user modules.
    """

    def __init__(self, context, request=None):
        super(WorkspaceMembership, self).__init__(context, request)
        self.search_user_result = []
        self.form = self.request.form
        self.config = None
        self.rolesview = LocalRolesView(context, request)

    def project_brains(self, exclude=()):
        q = {'portal_type': 'collective.teamwork.project'}
        search = self.portal.portal_catalog.unrestrictedSearchResults
        brains = search(q)
        if exclude:
            brains = filter(
                lambda brain: brain.UID not in exclude,
                brains
                )
        return brains

    def purge(self, username):
        if not self.can_purge(username):
            raise ValueError('cannot purge this user %s' % username)
        self.roster.purge(username)

    def _manager_can_remove_themself(self):
        return self.sm.checkPermission('Manage site', self.context.__parent__)

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
        modqueue = IMembershipModifications(self.context)
        for username in _add:
            err = None
            if username in self.roster:
                err = (
                    u'User %s is already a workspace member' % username,
                    logging.WARNING
                    )
            if username not in self.site_members:
                err = (
                    'User not found: %s' % username,
                    logging.ERROR,
                    )
            if err:
                self._log(*err)
                if err[1] == logging.ERROR:
                    raise KeyError(err[0])
                continue
            modqueue.assign(username)
        modqueue.apply()
        self.refresh()

    def _update_grid(self, *args, **kwargs):
        groupmeta = self.groups()
        modqueue = IMembershipModifications(self.context)
        ## Intersect currently known users with those in form, to handle
        ## any possibility of removal of users in between form render, submit
        known = set(self.roster.keys())
        managed = set(k.replace('managegroups-', '') for k in self.form.keys()
                      if k.startswith('managegroups-'))
        managed = managed.intersection(known)
        for info in groupmeta:
            groupid = info['groupid']
            group = self.roster.groups[groupid]
            form_group_users = set(
                k.split('/')[1] for k, v in self.form.items()
                if k.startswith('group-%s/' % groupid)
                )
            for username in managed:
                if username not in form_group_users and username in group:
                    if username == self.authuser:
                        # tread carefully here; do not let manager remove
                        # themselves without acquired safety net:
                        disallowed = ('viewers', 'managers')
                        safe_removal = self._manager_can_remove_themself()
                        if groupid in disallowed and not safe_removal:
                            msg = (
                                u'Managers cannot remove manager role '
                                u'or remove themselves from a workspace '
                                u'if they do not retain ability to '
                                u'manage inherited from parent '
                                u'workspaces (%s)' % (username,)
                                )
                            self._log(msg, logging.WARNING)
                            continue
                    # was in group existing, but ommitted/unchecked in form
                    # for this username -- mark for removal.
                    modqueue.unassign(username, groupid)
                elif username in form_group_users and username not in group:
                    # not yet in existing group, but specified/checked
                    # in form, so we need to mark for adding
                    modqueue.assign(username, groupid)
        modqueue.apply()
        self.refresh()

    def _update_register(self, *args, **kwargs):
        email = self.form.get('newuser_email', None)
        fullname = self.form.get('newuser_fullname', None)
        if not email:
            self.status.addStatusMessage(
                u'Empty email address (required).', type='error')
            return
        if not fullname:
            msg = u'Empty full name (required).'
            self._log(msg, logging.ERROR)
            return
        username = self.site_members.applyTransform(email.strip())
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


class WorkgroupRolesAPI(WorkspaceViewBase):
    """
    JSON API for managing roles and relationships of workgroup members,
    by handling modifications to users including:

        - Unassign ("remove") from workspace (removes all group assignments)
        - Assign/unassign from non-base groups

    Write API processes modifications, which means that a front-end could
    send as much or little user data (e.g. all users, versus just changed
    users).  Modification data that doesn't materially make modification
    is ignored.

    Modification receipts and status messages are returned in JSON for
    the changes made.  Clients should make use of modification
    receipts to reset any visual state useful (e.g. remove modification
    cues, or remove display or removed/unassigned users).

    Read API returns JSON enumerating role-groups and user entry
    membserhip state.

    This view excludes purge/deregister, password-reset, registration,
    addition/search of existing users -- all of these are handled in
    distinct views.

    This component behaves:

        - A GET request to this view returns JSON enumerating users;
        - A POST request must be valid JSON containing modifications and
          any relevant status for the client to optionally display.
    """

    def __init__(self, context, request=None):
        super(WorkgroupRolesAPI, self).__init__(context, request)
        self.modlog = []
        self.messages = []

    def _index_post(self):
        data = json.dumps({
            'modifications': self.modlog,  # receipts
            'messages': self.messages,
            })
        return data

    def index(self, *args, **kwargs):
        post_request = self.request and self.request.REQUEST_METHOD == 'POST'
        if post_request:
            data = self._index_post()
        else:
            data = WorkgroupMembershipState(self.context)(use_json=True)
        if self.request is not None:
            setHeader = self.request.response.setHeader
            setHeader('Content-Type', 'application/json')
            setHeader('Content-Length', str(len(data)))
        return data

    def processModifications(self, data):
        if isinstance(data, basestring):
            data = json.loads(data)
        # TODO process

    def update(self, *args, **kwargs):
        if self.request and self.request.REQUEST_METHOD == 'POST':
            data = self.request.get('role_modifications', {})
            self.processModifications(data)

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)

