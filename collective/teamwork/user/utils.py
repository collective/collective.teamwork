from AccessControl.SecurityManagement import getSecurityManager
from Acquisition import aq_base
from plone.app.workflow.browser.sharing import SharingView
from plone.uuid.interfaces import IUUID
from zope.component import queryUtility

from collective.teamwork.interfaces import IProjectContext
from collective.teamwork.utils import request_for
from config import APP_ROLES
from collective.teamwork.user.interfaces import IWorkgroupTypes


def authenticated_user(site):
    user = aq_base(getSecurityManager().getUser())
    return user.__of__(site.acl_users) if user is not None else None


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
    return IUUID(context)


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
    fn = lambda info: (str(info.get('groupid')), info)
    config = dict(map(fn, queryUtility(IWorkgroupTypes).select('project')))
    return _roles_for(name, config)


def _workspace_roles_for(name):
    """Given full or partial groupname, return roles from map"""
    return _roles_for(name, queryUtility(IWorkgroupTypes))


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

