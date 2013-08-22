from zope.component.hooks import getSite
from AccessControl.SecurityManagement import getSecurityManager
from Products.CMFCore.utils import getToolByName

from collective.teamwork.interfaces import IWorkspaceContext
from collective.teamwork.user.interfaces import ISiteMembers
from collective.teamwork.user.interfaces import IWorkspaceRoster
from collective.teamwork.utils import group_workspace


class UserInfo(object):
    """
    View for user information -- for a single user.

    May be used for either display of a single user in an overlay
    or for a macro listing multiple users (see template).
    """

    RESTRICTED_PROPS = (
        'last_login_time',
        )

    def __init__(self, context, request):
        if not IWorkspaceContext.providedBy(context):
            raise ValueError('Context not a workspace')
        self.context = context
        self.request = request
        self.portal = getSite()
        self._members = ISiteMembers(self.portal)
        self._roster = IWorkspaceRoster(self.context)
        self._mtool = getToolByName(self.portal, 'portal_membership')
        self._secmgr = None

    def user_display_info(self, principal):
        """
        Given principal id, get information for that user, returning
        it as a dict of portrait_url (if existing), properties,
        assignments (in this workspace), and memberships (in
        contained workspaces).
        """
        if self._secmgr is None:
            self._secmgr = getSecurityManager()
        roster = self._roster
        data = {}  # use dict in lieu of object, simple
        user = self._members.get(principal, None)
        if user is None or principal not in roster:
            return data  # empty if no user data or user not in workspace
        portrait = self._members.portrait_for(principal)
        if portrait is not None:
            data['portrait_url'] = portrait.absolute_url()
        propkeys = {
            'fullname': 'Full name',
            'email': 'Email',
            'description': 'User info',
            'location': 'Location',
            'home_page': 'Home page',
            'last_login_time': 'Last login',
            }
        restricted = self.RESTRICTED_PROPS
        if self._secmgr.checkPermission('Manage users', self.context):
            restricted = ()  # manager can see these properties
        if self._mtool.getAuthenticatedMember().getId() == principal:
            restricted = ()  # user can see own restricted properties
        props = {}
        for name, title in propkeys.items():
            if name in restricted:
                continue
            v = user.getProperty(name)
            if v:
                props[title] = v
        if props:
            data['properties'] = props
        groups = roster.groups.values()
        data['assignments'] = [g.title for g in groups if principal in g]
        ns, groups = roster.namespace, roster.groups
        local_groups = [o.pas_group() for o in groups.values()]
        groupfilter = lambda g: g.startswith(ns) and g not in local_groups
        contained_groups = filter(groupfilter, user.getGroups())
        all_workspaces = [group_workspace(g) for g in contained_groups]
        all_workspaces = filter(bool, all_workspaces)  # strip out errant None
        _ismember = lambda u, w: u in IWorkspaceRoster(w)
        _you_can_see = lambda w: self._secmgr.checkPermission('View', w)
        workspaces = filter(lambda w: _ismember(principal, w), all_workspaces)
        _nolink = lambda w: {'absolute_url': '#', 'Title': w.Title()}
        workspaces = [(w if _you_can_see(w) else _nolink(w))
                      for w in workspaces]
        if workspaces:
            data['workspaces'] = workspaces
        return data

