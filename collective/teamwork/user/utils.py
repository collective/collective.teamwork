from plone.app.workflow.browser.sharing import SharingView
from Acquisition import aq_base

from collective.teamwork.interfaces import IProjectContext
from collective.teamwork.utils import request_for, containing_workspaces
from collective.teamwork.user.interfaces import PROJECT_GROUPS
from collective.teamwork.user.interfaces import WORKSPACE_GROUPS
from collective.teamwork.user.interfaces import APP_ROLES


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
        Manage additional roles in addition to the default, these
        app-specific roles need not have ISharingPageRole utilities
        registered.
        """
        sharing_page_managed_roles = SharingView.roles(self)
        return sharing_page_managed_roles + APP_ROLES


def group_namespace(context):
    """Get group namespace/prefix for a project or workspace context"""
    if not IProjectContext.providedBy(context):
        containing = containing_workspaces(context)
        ids = [workspace.getId() for workspace in containing
               if workspace is not context]
        ids.append(context.getId())
        return '-'.join(ids)
    return context.getId()


def always_inherit_local_roles(context):
    if bool(getattr(aq_base(context), '__ac_local_roles_block__', False)):
        context.__ac_local_roles_block__ = None  # always inherit local roles


def _roles_for(name, groupcfg):
    basename = name.split('-')[-1]  # either name or suffix from it
    config = groupcfg.get(basename, None)
    if config is None:
        return []  # default, unknown group name means empty roles
    return config.get('roles', [])


def _project_roles_for(name):
    """Given full or partial groupname, return roles from map"""
    return _roles_for(name, PROJECT_GROUPS)


def _workspace_roles_for(name):
    """Given full or partial groupname, return roles from map"""
    return _roles_for(name, WORKSPACE_GROUPS)


def grouproles(groupname, roles):
    """
    Return a dict of role mapping that works with plone.app.workflow
    SharingView expectations.
    """
    return {
        'type': 'group',
        'id': groupname,
        'roles': [unicode(r) for r in roles],
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
        roles = _workspace_roles_for(groupname)
    manager.update_role_settings([grouproles(groupname, roles)])

