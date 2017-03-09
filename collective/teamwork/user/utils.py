import itertools
import os

from AccessControl.SecurityManagement import getSecurityManager
from Acquisition import aq_base
from plone.app.workflow.browser.sharing import SharingView
from plone.uuid.interfaces import IUUID
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import queryUtility
from zope.component.hooks import getSite

from collective.teamwork.interfaces import IProjectContext
from collective.teamwork.utils import request_for, get_workspaces
from collective.teamwork.utils import group_workspace
from config import APP_ROLES
from collective.teamwork.user.interfaces import IWorkgroupTypes, ISiteMembers
from collective.teamwork.user.interfaces import IWorkspaceRoster


# fork of plone.app.workflow sharing.pt to fill non-main slot via metal macro:
SHARING_MACRO_TEMPLATE = os.path.join(
    os.path.dirname(__file__),
    '../browser/sharing.pt'
    )


def authenticated_user(site):
    user = aq_base(getSecurityManager().getUser())
    return user.__of__(site.acl_users) if user is not None else None


def user_workspaces(username, context=None, finder=get_workspaces):
    """
    Get workspaces for username, matching only workspaces for which
    the given user is a member; may be given context or use the
    site root as default context.

    A workspace enumerator/finder other than get_workspaces() may be passed
    (e.g. collective.teamwork.utils.get_projects).
    """
    suffix = '-viewers'
    site = getSite()
    context = context or site
    # get all PAS groups for workspaces contained within context:
    all_workspaces = finder(context)
    if not all_workspaces:
        # context contains no workspaces, even if context itself is workspace
        return []
    _pasgroup = lambda g: g.pas_group()
    _wgroups = lambda w: map(_pasgroup, IWorkspaceRoster(w).groups.values())
    local_groups = set(
        zip(*itertools.chain(*map(_wgroups, all_workspaces)))[0]
        )
    if not local_groups:
        return []
    # get all '-viewers' groups user belongs to, intersect with local:
    user = ISiteMembers(site).get(username)
    usergroups = [name for name in user.getGroups() if name.endswith(suffix)]
    considered = [name for name in local_groups.intersection(usergroups)]
    # each considered group (by suffix convention) is always 1:1 with
    # workspaces, no dupes, so we can map those workspaces:
    return map(group_workspace, set(considered))


class LocalRolesView(SharingView):
    """
    This is a multi-adapter of a context and request that acts
    similar to the Sharing page/tab view from plone.app.workflow.

    Special (ab)use of Sharing view, permitting management of
    application-specific local roles that do not appear
    in the sharing tab normally.  This avoids implementing
    yet another means of managing local roles.
    """

    template = ViewPageTemplateFile(SHARING_MACRO_TEMPLATE)

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

