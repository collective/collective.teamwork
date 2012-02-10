# event handlers for lifecycle events on projects and teams

from zope.component.hooks import getSite
from zope.lifecycleevent.interfaces import IObjectCopiedEvent
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from Acquisition import aq_base

from uu.qiext.user.workgroups import WorkspaceRoster
from uu.qiext.user.utils import sync_group_roles, LocalRolesView, grouproles
from uu.qiext.user.utils import group_namespace
from uu.qiext.utils import request_for, contained_workspaces


def handle_workspace_copy(context, event):
    """
    On IObjectCopiedEvent, we do not have an acqusition-wrapped object
    yet, so we just need to flag the copy so that a handler for
    IObjectAddedEvent can be smart about the difference between a
    copy and a non-copy created workspace object.
    """
    # flag and original object for use/clear by subsequent handlers
    context._v_workspace_copy_of = event.original.getPhysicalPath()


def create_workspace_groups_roles(context):
    plugin = getSite().acl_users.source_groups
    roster = WorkspaceRoster(context)
    for group in roster.groups.values():
        groupname = group.pas_group()
        if groupname not in plugin.getGroupIds():
            plugin.addGroup(groupname)
        # bind local roles, mapping group to roles from config
        sync_group_roles(context, groupname)


def handler_workspace_pasted(context, event, original_path):
    """handle IObjectAddedEvent after a copy/paste opertion"""
    create_workspace_groups_roles(context)
    site = getSite()
    plugin = site.acl_users.source_groups
    original = site.unrestrictedTraverse('/'.join(original_path[1:]))
    original_groupname_prefix = group_namespace(original)
    for workspace in contained_workspaces(context):
        create_workspace_groups_roles(workspace)


def handle_workspace_added(context, event):
    """
    May be added via construction (new item) or copy (cloned item).
    Handle either case, creating new groups if needed.
    
    If context._v_workspace_copy is set attrbute, then consider the
    added itam a copy, not new, and act accordingly, then finally
    unset that attribute.
    """
    ob = aq_base(context)
    if hasattr(ob, '_v_workspace_copy_of'):
        original_path = getattr(ob, '_v_workspace_copy_of')
        handle_workspace_pasted(context, event, original_path)
        delattr(ob, '_v_workspace_copy_of')
        return
    create_workspace_groups_roles(context)


def handle_workspace_move_or_rename(context, event):
    """
    Handler for IObjectMovedEvent on a workspace, ignores
    IObjectRemovedEvent.
    """
    if IObjectRemovedEvent.providedBy(event):
        return  # not a move with new/old, but a removal -- handled elsewhere
    if IObjectAddedEvent.providedBy(event):
        return  # not an add, but a move of existing 
    old_id = event.oldName
    new_id = event.newName
    site = getSite()
    plugin = site.acl_users.source_groups
    roster = WorkspaceRoster(context)
    manager = LocalRolesView(context, request_for(context))
    for group in roster.groups.values():
        groupname = group.pas_group()
        old_groupname = groupname.replace(new_id, old_id, 1)
        # unhook (empty) roles for old group name:
        manager.update_role_settings([grouproles(old_groupname, [])])
        if old_groupname in plugin.getGroupIds():
            plugin.removeGroup(old_groupname)
        if groupname not in plugin.getGroupIds():
            plugin.addGroup(groupname)
        # hook-up new local roles for the new groupname:
        sync_group_roles(context, groupname)
    # changes to the workspace short name affect the groupnames of 
    # all nested spaces, so we should handle the renaming and associated
    # local roles re-mapping for each nested workspace.  Passsing the
    # original event will yield the portion of the groupname (old/new id)
    # needing change.
    if context.getId() == event.newName:
        for workspace in contained_workspaces(context):
            handle_workspace_move_or_rename(workspace, event=event)


def handle_workspace_removal(context, event):
    """Handler for IObjectRemovedEvent on a workspace"""
    site = getSite()
    if site is None:
        return  # in case of recursive plone site removal, ignore
    plugin = site.acl_users.source_groups
    roster = WorkspaceRoster(context)
    for group in roster.groups.values():
        groupname = group.pas_group()
        if groupname in plugin.getGroupIds():
            plugin.removeGroup(groupname)
    # remove group names for nested workspaces (also, by implication, 
    #   removed from the PAS group manager plugin).
    for workspace in contained_workspaces(context):
        handle_workspace_removal(workspace, event=event)

