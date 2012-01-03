from plone.app.workflow.browser.sharing import SharingView

from uu.qiext.interfaces import IProjectContext, ITeamContext
from uu.qiext.utils import request_for
from uu.qiext.user.interfaces import PROJECT_GROUPS, APP_ROLES, TEAM_GROUPS


class LocalRolesView(SharingView):
    """
    This is a multi-adapter of a context and request that acts
    similar to the Sharing page/tab view from plone.app.workflow.
    
    Special (ab)use of Sharing view, permitting management of
    application-specific local roles that do not appear
    in the sharing tab normally.  This avoids implementing
    yet another means of managing local roles.
    """
    
    def roles(self):
        """
        /anage additional roles in addition to the default, these
        app-specific roles need not have ISharingPageRole utilities
        registered.
        """
        sharing_page_managed_roles = SharingView.roles(self)
        return sharing_page_managed_roles + APP_ROLES 


def group_namespace(context):
    """Get group namespace/prefix for a project or team context"""
    if not IProjectContext.providedBy(context):
        project = IProjectContext(context)
        return '%s-%s' % (project.getId(), context.getId())
    return context.getId()


def always_inherit_local_roles(context):
    if bool(getattr(aq_base(context), '__ac_local_roles_block__', False)):
        context.__ac_local_roles_block__ = None #always inherit local roles


def _roles_for(name, groupcfg):
    basename = name.split('-')[-1] # either name or suffix from it
    config = groupcfg.get(basename, None)
    if config is None:
        return [] #default, unknown group name means empty roles
    return config.get('roles', [])


def _project_roles_for(name):
    """Given full or partial groupname, return roles from map"""
    return _roles_for(name, PROJECT_GROUPS)


def _team_roles_for(name):
    """Given full or partial groupname, return roles from map"""
    return _roles_for(name, TEAM_GROUPS)


def _grouproles(groupname, roles):
    """
    Return a dict of role mapping that works with plone.app.workflow
    SharingView expectations.
    """
    return {
        'type'  : 'group',
        'id'    : groupname,
        'roles' : [unicode(r) for r in roles],
        }


def sync_group_roles(context, groupname):
    """
    Given a group name as a full PAS groupname, infer appropriate
    roles for that group based on configuration, and bind those
    local roles to the context.
    """
    always_inherit_local_roles(context)
    manager = LocalRolesView(context, request_for(context))
    if IProjectContext.providedBy(context):
        roles = _project_roles_for(groupname)
    else:
        roles = _team_roles_for(groupname)
    manager.update_role_settings(_grouproles(groupname, roles))

