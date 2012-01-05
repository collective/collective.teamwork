# local role components including a PAS local role manager plugin
#  See http://goo.gl/ymRxG for (slightly outdated) documentation of the
#   basic idea here, or look at source for borg.localrole.workspace module..

from borg.localrole.workspace import WorkspaceLocalRoleManager as BasePlugin
from borg.localrole.workspace import clra_cache_key, store_on_request
from plone.memoize.volatile import cache
from zope.interface import implements
from AccessControl.class_init import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin
from AccessControl import ClassSecurityInfo

from Products.qi.extranet.types.interfaces import IWorkspace
from uu.qiext.user.interfaces import APP_ROLES


BLOCKROLES = tuple(r.get('id') for r in APP_ROLES)

filter_roles = lambda s: filter(lambda r: r not in BLOCKROLES, s)

manage_addEnhancedWorkspaceLRMForm = PageTemplateFile(
        "zmi/WorkspaceLocalRoleManagerForm.pt", globals(),
        __name__="manage_addWorkspaceRoleManagerForm")

def manage_addEnhancedWorkspaceLRM(dispatcher, id, title=None, REQUEST=None):
    plugin = WorkspaceLocalRoleManager(id, title)
    dispatcher._setObject(plugin.getId(), plugin)
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(
            '%s/manage_workspace?manage_tabs_message=WorkspaceLocalRoleManager+added.'
                % dispatcher.absolute_url())


class WorkspaceLocalRoleManager(BasePlugin):
    """
    PAS local roles manager plugin for a workspaces site; acts
    like the base plugin, except:
    
        *   Roles defined in uu.qiext.user.interfaces.APP_ROLES are
            not inherited via getRolesInContext() method if the context
            itself is a workspace.  This allows for this role to be
            inherited in contained folders, but such implied access is
            not assumed for nested workspaces.
       
        *   All other roles have stock Plone behavior.
    
    Some method code borrowed as useful from superclass
    borg.localrole.workspace.WorkspaceLocalRoleManager.
    """
    
    meta_type = 'Enhanced workspace roles manager'
    
    security = ClassSecurityInfo()
    
    implements(ILocalRolesPlugin)
    
    def _user_info(self, user):
        """Return tuple of user id and list of principal ids"""
        uf = self._get_userfolder(user)
        if uf is not None:
            user = aq_inner(user).__of__(uf)  # re-wrap, if we have uf
        principal_ids = self._get_principal_ids(user)  # user id, group names
        return (user, principal_ids)
    
    security.declarePrivate("getRolesInContext")
    def getRolesInContext(self, user, object):
        roles = set()
        workspace = None
        user, principal_ids = self._user_info(user)
        for obj in self._parent_chain(object):
            if user._check_context(obj):
                for provider in self._getAdapters(obj):
                    for princial_id in principal_ids:
                        context_roles = list(provider.getRoles(principal_id))
                        if workspace:
                            # once you have seen a previous workspace, there
                            # are certain roles you DO NOT want to inherit
                            # from a higher-level workspace in the containment
                            # hierarchy.  We filter those roles from the list
                            # for all but the first seen workspace walking up
                            # the hierarchy.
                            context_roles = filter_roles(context_roles)
                        roles.update(context_roles)
            if IWorkspace.providedBy(obj):
                workspace = obj  # mark ws as seen before looking at parents
        return list(roles)
    
    security.declarePrivate("checkLocalRolesAllowed")
    @cache(get_key=clra_cache_key, get_cache=store_on_request)
    def checkLocalRolesAllowed(self, user, object, object_roles):
        user, principal_ids = self._user_info(user)
        workspace = None
        check_roles = set(object_roles)
        for obj in self._parent_chain(object):
            for provider in self._getAdapters(obj):
                for principal_id in principal_ids:
                    roles = list(provider.getRoles(principal_id))
                    if workspace:
                        # seen previous workspace, don't inherit some roles
                        roles = filter_roles(roles)
                    if check_roles.intersection(roles):
                        if user._check_context(obj):
                            return 1
                        else:
                            return 0
            if IWorkspace.providedBy(obj):
                workspace = obj  # mark ws as seen before looking at parents
        return None
    
    security.declarePrivate("getAllLocalRolesInContext")
    def getAllLocalRolesInContext(self, object):
        rolemap = {}
        workspace = None
        for obj in self._parent_chain(object):
            for provider in self._getAdapters(obj):
                iter_roles = provider.getAllRoles()
                for principal, roles in iter_roles:
                    if workspace:
                        # seen previous workspace, don't inherit some roles
                        roles = filter_roles(roles)
                    rolemap.setdefault(principal, set()).update(roles)
            if IWorkspace.providedBy(obj):
                workspace = obj  # mark ws as seen before looking at parents
        return rolemap


InitializeClass(WorkspaceLocalRoleManager)  # set up traversal security!

