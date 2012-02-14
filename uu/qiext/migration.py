# migration for old Products.qi setup

import logging

import transaction
from plone.app.folder.migration import BTreeMigrationView
from plone.namedfile.interfaces import HAVE_BLOBS
from plone.namedfile.file import NamedImage, NamedBlobImage
from Acquisition import aq_base
from DateTime import DateTime


from uu.qiext.user.interfaces import WORKSPACE_GROUPS, IGroups
from uu.qiext.user.groups import GroupInfo
from uu.qiext.user.workgroups import WorkspaceRoster


if HAVE_BLOBS:
    NamedImage = NamedBlobImage

MIGRATION_LOG = logging.getLogger('uu.qiext.migration')

is_jpeg = lambda data: 'JFIF' in data[:12]


def logo_image_factory(data):
    """Create NamedImage / NamedBlobImage object from raw image data"""
    ctype = 'image/jpeg' if is_jpeg(data) else 'image/png'
    return NamedImage(
        data=data,
        contentType=ctype,
        filename='logo.jpg',
        )


def migrate_logo(project):
    state = aq_base(project).__getstate__()
    if hasattr(project, 'logo') and isinstance(project.logo, str):
        # old-style logo, needs migration to plone.namedfile object
        project.logo = logo_image_factory(state['logo'])
        assert isinstance(project.logo, NamedImage)
        MIGRATION_LOG.info('Logo attribute migrated to NamedImage '\
                           'for project %s (%s) -- %s bytes' % (
                                project.Title(),
                                project.getId(),
                                len(state['logo']),
                                ))
    project.logo = None  # may be previously unset
    MIGRATION_LOG.info('Logo attribute set to None'\
                       'for project %s (%s)' % (
                            project.Title(),
                            project.getId(),
                            ))


def migrate_folder(folder):
    folder = aq_base(folder)
    if not hasattr(folder, '_objects'):
        return # already migrated
        MIGRATION_LOG.info(
            'BTree folder migration skipped; already migrated: %s (%s)' % (
                folder.Title(),
                '/'.join(folder.getPhysicalPath()),
                ))
    names = folder.objectIds()
    migration = BTreeMigrationView(folder, None)
    migration.migrate(folder)
    assert hasattr(folder, '_mt_index') and hasattr(folder, '_tree')
    assert not hasattr(folder, '_objects')
    for name in names:
        assert name in folder._tree         # id in contents tree
        assert not hasattr(folder, name)    # no longer attribute
    MIGRATION_LOG.info(
        'BTree folder migration completed: %s (%s)' % (
            folder.Title(),
            '/'.join(folder.getPhysicalPath()),
            ))


def mark_changed(content, note):
    """Mark object as changed, but only if note is not None"""
    if note is None:
        return # no change
    content._migration_version = 2
    content.modification_date = DateTime() #now
    aq_base(content)._p_changed = True
    txn = transaction.get()
    path = '/'.join(content.getPhysicalPath())[1:]
    if path:
        txn.note(path)
    txn.note(note)


def remove_attributes(content, names=()):
    """
    Given a seqeuence of names, remove attributes, if they
    exist, from the content object content
    """
    unwrapped = aq_base(content)
    removed = []
    for name in names:
        if hasattr(unwrapped, name):
            delattr(unwrapped, name)
            removed.append(name)
    if removed:
        MIGRATION_LOG.info(
            'Removed unused attributes on object: %s (%s) -- %s' % (
                content.Title(),
                '/'.join(content.getPhysicalPath()),
                repr(removed),
                ))


def remove_old_roles(portal):
    # roles we will not use -- either they have no use or a replacement:
    remove = ('QIC', 'ProjectViewer', 'TeamViewer', 'SubTeamViewer')
    # first remove from __ac_roles__
    before_roles = aq_base(portal).__ac_roles__
    portal.__ac_roles__ = tuple(sorted(set(before_roles) - set(remove)))
    # next, remove from any permission on site root object itself
    _pattr = lambda k: k.startswith('_') and k.endswith('Permission')
    _attrs = aq_base(portal).__dict__.items()
    _permissions = [(k,v) for k,v in _attrs if _pattr(k)]
    for p_attr_name, roles in _permissions:
        replacement = tuple(sorted(set(roles) - set(remove)))
        if roles != replacement:
            setattr(aq_base(portal), p_attr_name, replacement)
    # finally, remove from acl_users/portal_role_manager
    mgr = portal.acl_users.portal_role_manager
    before_roles_plugin_ids = mgr.listRoleIds()
    for role in remove:
        if role in before_roles_plugin_ids:
            # note: we know the old roles we are removing do not have
            # direct mapping to any users at the site root, they are only
            # used as local roles inside project workspaces so we can avoid
            # having to write a re-mapping of those users, and just remove.
            mgr.removeRole(role)  # we don't need to do more than this...
    aq_base(portal)._p_changed = True
    # check sufficient: remove roles not in __ac_roles__, permission, plugin
    for role in remove:
        assert role not in aq_base(portal).__ac_roles__
        _attrs = aq_base(portal).__dict__.items()
        _permissions = [(k,v) for k,v in _attrs if _pattr(k)]
        for p_attr_name, roles in _permissions:
            assert role not in roles
        assert role not in mgr.listRoleIds()
    # check necessary: all roles in __ac_roles__, plugin before still there
    #                   except for the ones we wanted removed:
    after_roles = aq_base(portal).__ac_roles__
    for role in before_roles:
        assert role in remove ^ role in after_roles
    for role in before_roles_plugin_ids:
        assert role in remove ^ role in mgr.listRoleIds()


def _clear_groups(portal, suffixes=(), readd=False):
    groups = IGroups(portal)
    # get a list of all groups from which to filter:
    allgroups = groups.keys()
    # define the removal set of groups matching suffixes:
    rem = set()
    for suffix in suffixes:
        rem = rem.union(name for name in allgroups if name.endswith(suffix))
    # deleting matching groups:
    for groupname in rem:
        assert '-%s' % groupname.split('-')[-1] in suffixes  # sanity check
        title = groups.get(groupname).title or None
        groups.remove(groupname)
        assert groupname not in groups
        if readd:
            # re-add with previous title, but not previous principals:
            groups.add(groupname, title=title)
    # necessary/sufficient checks:
    postremoval_groups = portal.acl_users.source_groups.listGroupIds()
    # -- only necessary groups removed, verify by simple counts:
    assert len(postremoval_groups) + len(rem) == len(allgroups)
    # -- sufficient -- all groups remaining do not have suffixes for removal:
    for suffix in suffixes:
        for name in postremoval_groups:
            assert not name.endswith(suffix)


def remove_old_groups(portal):
    """
    remove unused old groups from PAS groups plugin, uses IGroups adapter
    defined in uu.qiext.user.
    """
    _clear_groups(portal, suffixes=('-qic', '-faculty','-pending'))


def recreate_contributor_groups(portal):
    """
    Remove and re-add all uses IGroups adapter
    defined in uu.qiext.user.
    """
    _clear_groups(portal, suffixes=('-contributors'), readd=True)


def rename_member_groups(portal, oldsuffix, newsuffix):
    """
    Rename a group: create replacement, migrate users, destroy old group.
    """
    membership_before = {}
    membership_after = {}
    rename_map = {}
    groups = IGroups(portal)
    before_groupnames = groups.keys()
    for name in before_groupnames:
        if name.endswith(oldsuffix):
            # application-specific replacement: suffix assumption is that
            # suffix begins with but does not otherwise containe a hyphen
            newname = '%s%s' % ('-'.join(name.split('-')[:-1]), newsuffix)
            membership_before[name] = groups.get(name).keys()
            groups.rename(name, newname)
            membership_after[newname] = groups.get(newname).keys()
            rename_map[name] = newname
    # sufficient: ensure no remaining groups have old suffix:
    for name in groups.keys():
        assert not name.endswith(oldsuffix)
    # sufficient: for all members in group before, assert they are members of
    # the replacement group:
    after_groupnames = groups.keys()
    assert len(membership_before) == len(membership_after) # same number of groups
    assert len(after_groupnames) == len(before_groupnames)
    for oldgroup, newgroup in rename_map.items():
        assert membership_before[oldgroup] == membership_after[newgroup]
    # necessary only: all groups in before_groupnames that do not end in oldsuffix
    #                 still exist in groups.keys() -- use XOR to check
    for name in before_groupnames:
        assert name.endswith(oldsuffix) ^ name in after_groupnames


def fix_local_roles(workspace):
    """
    Given a project|team|subteam workspace, migrate old to 
    new local roles, and remove any unused local roles.
    """
    remove_roles = ('QIC', 'ProjectViewer', 'TeamViewer', 'SubTeamViewer')
    unwrapped = aq_base(workspace)
    aclr = unwrapped.__ac_local_roles__
    for principal, roles in aclr.items():
        if set(roles).intersection(remove_roles):
            aclr[principal] = sorted(list(set(roles) - set(remove_roles)))
    roster = WorkspaceRoster(workspace)
    for group in roster.values():
        groupname = group.pas_group()
        group = GroupInfo(groupname)
        existing = group.roles_for(workspace)
        roles = WORKSPACE_GROUPS[group.id].roles
        aclr[groupname] = sorted(list(set(existing).union(roles)))
    ## assert that the pas_group() for each of the respective groups
    ## for the workspace has the appropriate local role binding.
    
    ## sufficient
    ## necessary


def migrate_siteroot(portal):
    """
    Migration for site root state and state of user storage in acl_users.
    """
    remove_old_roles(portal)
    remove_old_groups(portal)
    recreate_contributor_groups(portal)
    rename_member_groups(portal, oldsuffix='-members', newsuffix='-viewers')
    rename_member_groups(portal, oldsuffix='-lead', newsuffix='-managers')



def migrate_project(project, version=2):
    """
    Migrate a project from previous state.

    Each migration step called within will return a string 
    describing the change or None if no change was needed. Either
    possible return value is appended to a log list.  Each element
    in the log list is ignored if None, or appended to a transaction
    note by mark_changed().
    """
    unwrapped = aq_base(project)
    if getattr(unwrapped, '_migration_version', None) == 2:
        MIGRATION_LOG.info('Project migration skipped, already '\
                           'marked as migrated: %s (%s)' % (
                                project.Title(),
                                project.getId(),
                                ))
        return # already migrated this object (attr set by mark_changed())
    # Migrate old folder contents storage to BTree folder contents
    # compatible with Dexterity containers.
    migrate_folder(project)
    # Migrate logo attribute contents to NamedImage.
    migrate_logo(project)
    # Remove unused attributes:
    unused = ('dbid', 'groupname', 'managers', 'faculty', 'projectTheme')
    remove_attributes(project, unused)
    # Remove reference to QIC Role from all roles in __ac_local_roles__:
    pass # TODO IMPLEMENT TODO
    # Remove -qics group items from __ac_local_roles__.
    pass # TODO IMPLEMENT TODO
    # Rename group keys in __ac_local_roles__ from *-members to *-viewers
    # suffix to match changes to group names in acl_users group source
    # storage/plugin.
    pass # TODO IMPLEMENT TODO
    # Replace references to the 'ProjectViewer' role in 
    # __ac_local_roles__ with 'Workspace Viewer'.
    pass # TODO IMPLEMENT TODO
    # Add UUIDs to project object, calling
    # plone.uuid.handlers.addAttributeUUID(context, None)
    pass # TODO IMPLEMENT TODO
    # For each permission attribute on the project, replace any
    # references to 'ProjectViewer' with 'Workspace Viewer'
    pass # TODO IMPLEMENT TODO
    # Mark project._p_changed=True to ensure changes flushed at
    # transaction commit. Log changes to transaction note:
    mark_changed(project, 'Migrated project') # use aq-wrapped project here...


def migrate_team(team, version=2):
    """
    Migrate a team from previous state.
    """
    unwrapped = aq_base(team)
    if getattr(unwrapped, '_migration_version', None) == 2:
        MIGRATION_LOG.info('Team migration skipped, already '\
                           'marked as migrated: %s (%s)' % (
                                team.Title(),
                                team.getId(),
                                ))
        return # already migrated this object (attr set by mark_changed())
    # Migrate old folder contents storage to BTree folder contents
    # compatible with Dexterity containers.
    migrate_folder(team)
    # Remove unused attributes:
    unused = ('dbid', 'groupname', 'reportLocations')
    remove_attributes(team, unused)
    # Remove reference to QIC Role from all roles in __ac_local_roles__:
    pass # TODO IMPLEMENT TODO
    # Remove -qics group items from __ac_local_roles__.
    pass # TODO IMPLEMENT TODO
    # Rename group keys in __ac_local_roles__ from *-members to *-viewers
    # suffix to match changes to group names in acl_users group source
    # storage/plugin.
    pass # TODO IMPLEMENT TODO
    # Replace references to the 'ProjectViewer' role in 
    # __ac_local_roles__ with 'Workspace Viewer'.
    pass # TODO IMPLEMENT TODO


######## reindex all content --wflows changed
#### reindex all wspaces -- groups lookup


def migrate_subteam(subteam, version=2):
    """
    Migrate a subteam from previous state.
    """

