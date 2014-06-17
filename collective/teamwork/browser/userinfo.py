from zope.component.hooks import getSite
from AccessControl.SecurityManagement import getSecurityManager
from Products.CMFCore.utils import getToolByName

from collective.teamwork.interfaces import IWorkspaceContext
from collective.teamwork.user.interfaces import ISiteMembers
from collective.teamwork.user.interfaces import IWorkspaceRoster
from collective.teamwork.user.utils import user_workspaces


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

    def linked_workspaces(self, username):
        if self._secmgr is None:
            self._secmgr = getSecurityManager()
        # get all workspaces for user in the current context
        workspaces = user_workspaces(username, self.context)
        _you_can_see = lambda w: self._secmgr.checkPermission('View', w)
        _nolink = lambda w: {'absolute_url': '#', 'Title': w.Title()}
        # only provide links to workspaces the current auth. user can View:
        return [
            (w if _you_can_see(w) else _nolink(w)) for w in workspaces
            ]

    def user_display_info(self, username):
        """
        Given username, get information for that user, returning
        it as a dict of portrait_url (if existing), properties,
        assignments (in this workspace), and memberships (in
        contained workspaces).
        """
        if self._secmgr is None:
            self._secmgr = getSecurityManager()
        roster = self._roster
        data = {}  # use dict in lieu of object, simple
        user = self._members.get(username, None)
        if user is None or username not in roster:
            return data  # empty if no user data or user not in workspace
        portrait = self._members.portrait_for(username)
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
        if self._mtool.getAuthenticatedMember().getId() == username:
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
        data['assignments'] = [g.title for g in groups if username in g]
        workspaces = self.linked_workspaces(username)
        if workspaces:
            data['workspaces'] = workspaces
        return data

