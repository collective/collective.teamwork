# event handlers for lifecycle events on projects and teams

from zope.component.hooks import getSite

from uu.qiext.user.groups import ProjectRoster
from uu.qiext.user.utils import sync_group_roles


def new_workspace_groups(context, event):
    # context is a workspace, either project or team
    site = getSite()
    plugin = site.acl_users.source_groups
    roster = ProjectRoster(context)
    for group in roster.groups:
        groupname = group.pas_groupname()
        if groupname not in plugin.getGroupIds():
            plugin.addGroup(groupname)
        # bind local roles, mapping group to roles from config
        sync_group_roles(context, groupname)

