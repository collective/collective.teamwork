# migration for old Products.qi setup

import logging

from plone.app.folder.utils import findObjects
from plone.app.folder.migration import BTreeMigrationView
from plone.namedfile.interfaces import HAVE_BLOBS
from plone.namedfile.file import NamedImage, NamedBlobImage
from plone.uuid.interfaces import ATTRIBUTE_NAME as UUID_ATTR
from plone.uuid.interfaces import IAttributeUUID
from plone.uuid.handlers import addAttributeUUID
from Acquisition import aq_base
from DateTime import DateTime
from Persistence.mapping import PersistentMapping
from Products.CMFCore.interfaces import IContentish
from Products.CMFCore.utils import getToolByName

from uu.qiext.user.interfaces import WORKSPACE_GROUPS, IGroups
from uu.qiext.user.groups import GroupInfo
from uu.qiext.user.workgroups import WorkspaceRoster


NamedImage = NamedImage  # pyflakes
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
        filename=u'logo.jpg',
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
        MIGRATION_LOG.info(
            'BTree folder migration skipped; already migrated: %s (%s)' % (
                folder.Title(),
                '/'.join(folder.getPhysicalPath()),
                ))
        return  # already migrated
    names = folder.objectIds()
    migration = BTreeMigrationView(folder, None)
    migration.migrate(folder)
    assert hasattr(folder, '_mt_index') and hasattr(folder, '_tree')
    assert hasattr(folder, '_objects')
    for name in names:
        assert name in folder._tree                     # id in contents tree
        assert not getattr(folder, name, None) or None  # gone or empty
    MIGRATION_LOG.info(
        'BTree folder migration completed: %s (%s)' % (
            folder.Title(),
            '/'.join(folder.getPhysicalPath()),
            ))


def mark_changed(content):
    """Mark object as changed, but only if note is not None"""
    content._migration_version = 2
    content.modification_date = DateTime()  # now
    aq_base(content)._p_changed = True
    MIGRATION_LOG.info('Marked workspace or content as changed, '\
                       'bumped modification date for %s' % (
                        '/'.join(content.getPhysicalPath()),
                        )
                      )


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
                )
            )


def remove_old_roles(site):
    # roles we will not use -- either they have no use or a replacement:
    remove = ('QIC', 'ProjectViewer', 'TeamViewer', 'SubTeamViewer')
    # first remove from __ac_roles__
    before_roles = aq_base(site).__ac_roles__
    site.__ac_roles__ = tuple(sorted(set(before_roles) - set(remove)))
    MIGRATION_LOG.info(
        'Removed unused roles from __ac_roles__ '\
        'on site root: %s' % (
            repr(tuple(set(before_roles) - set(site.__ac_roles__))),
            )
        )
    # next, remove from any permission on site root object itself
    _pattr = lambda k: k.startswith('_') and k.endswith('Permission')
    _attrs = aq_base(site).__dict__.items()
    _permissions = [(k, v) for k, v in _attrs if _pattr(k)]
    for p_attr_name, roles in _permissions:
        replacement = tuple(sorted(set(roles) - set(remove)))
        if roles != replacement:
            seq_type = type(roles)  # list=inherit, tuple=don't !!!
            setattr(aq_base(site), p_attr_name, seq_type(replacement))
            MIGRATION_LOG.info(
                'Removed unused roles from permission attribute '\
                '%s on site root: %s' % (
                    p_attr_name,
                    repr(tuple(set(roles) - set(replacement))),
                    )
                )

    # finally, remove from acl_users/portal_role_manager
    mgr = site.acl_users.portal_role_manager
    before_roles_plugin_ids = mgr.listRoleIds()
    for role in remove:
        if role in before_roles_plugin_ids:
            # note: we know the old roles we are removing do not have
            # direct mapping to any users at the site root, they are only
            # used as local roles inside project workspaces so we can avoid
            # having to write a re-mapping of those users, and just remove.
            mgr.removeRole(role)  # we don't need to do more than this...
            MIGRATION_LOG.info(
                'Removed unused role from portal_role_manager '\
                'plugin: %s' % (role,)
                )
    aq_base(site)._p_changed = True
    # check sufficient: remove roles not in __ac_roles__, permission, plugin
    for role in remove:
        assert role not in aq_base(site).__ac_roles__
        _attrs = aq_base(site).__dict__.items()
        _permissions = [(k, v) for k, v in _attrs if _pattr(k)]
        for p_attr_name, roles in _permissions:
            assert role not in roles
        assert role not in mgr.listRoleIds()
    # check necessary: all roles in __ac_roles__, plugin before still there
    #                   except for the ones we wanted removed:
    after_roles = aq_base(site).__ac_roles__
    for role in before_roles:
        assert (role in remove) ^ (role in after_roles)
    for role in before_roles_plugin_ids:
        assert (role in remove) ^ (role in mgr.listRoleIds())


def _clear_groups(site, suffixes=(), readd=False):
    groups = IGroups(site)
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
            MIGRATION_LOG.info(
                'Removed and re-added group (with empty membership) in '\
                'groups plugin: %s' % (groupname,)
                )
        else:
            MIGRATION_LOG.info(
                'Removed group in groups plugin: %s' % (groupname,)
                )
    # necessary/sufficient checks:
    postremoval_groups = site.acl_users.source_groups.listGroupIds()
    # -- only necessary groups removed, verify by simple counts:
    expected_change = len(rem) if not readd else 0
    assert len(postremoval_groups) + expected_change == len(allgroups)
    # -- sufficient -- all groups remaining do not have suffixes for removal:
    for suffix in suffixes:
        for name in postremoval_groups:
            if not readd:
                assert not name.endswith(suffix)


def remove_old_groups(site):
    """
    remove unused old groups from PAS groups plugin, uses IGroups adapter
    defined in uu.qiext.user.
    """
    _clear_groups(site, suffixes=('-qics', '-faculty', '-pending'))


def recreate_contributor_groups(site):
    """
    Remove and re-add all uses IGroups adapter
    defined in uu.qiext.user.
    """
    _clear_groups(site, suffixes=('-contributors',), readd=True)


def rename_member_groups(site, oldsuffix, newsuffix):
    """
    Rename a group: create replacement, migrate users, destroy old group.
    """
    membership_before = {}
    membership_after = {}
    rename_map = {}
    groups = IGroups(site)
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
            MIGRATION_LOG.info(
                'Renamed workspace group (keeping membership) from '\
                '%s to %s ' % (name, newname)
                )
    # sufficient: ensure no remaining groups have old suffix:
    for name in groups.keys():
        assert not name.endswith(oldsuffix)
    # sufficient: for all members in group before, assert they are members of
    # the replacement group:
    after_groupnames = groups.keys()
    assert len(membership_before) == len(membership_after)  # same qty groups
    assert len(after_groupnames) == len(before_groupnames)
    for oldgroup, newgroup in rename_map.items():
        assert membership_before[oldgroup] == membership_after[newgroup]
    # necessary only: all groups in before_groupnames that do not end in
    #                 oldsuffix still exist in groups.keys() -- check w/ XOR
    for name in before_groupnames:
        assert name.endswith(oldsuffix) ^ (name in after_groupnames)


def fix_local_roles(workspace):
    """
    Given a project|team|subteam workspace, migrate old to
    new local roles, and remove any unused local roles.
    """
    _prefix = 'fix_local_roles() <Workspace "%s" at %s>:' % (
        workspace.Title(),
        '/'.join(workspace.getPhysicalPath()),
        )
    _log = lambda msg: MIGRATION_LOG.info('%s %s' % (_prefix, msg))
    remove_roles = ('QIC', 'ProjectViewer', 'TeamViewer', 'SubTeamViewer')
    remove_group_suffixes = ('-qics', '-faculty', '-members')
    unwrapped = aq_base(workspace)
    aclr = unwrapped.__ac_local_roles__
    for principal, roles in aclr.items():
        for suffix in remove_group_suffixes:
            if principal.endswith(suffix):
                del(aclr[principal])  # remove group name key for unused group
        if principal in aclr and set(roles).intersection(remove_roles):
            aclr[principal] = sorted(list(set(roles) - set(remove_roles)))
            _log('Removed old local roles for principal %s : %s ' % (
                    principal,
                    repr(tuple(set(roles) - set(aclr[principal]))),
                    )
                )
    roster = WorkspaceRoster(workspace)
    for workgroup in roster.groups.values():
        groupname = workgroup.pas_group()
        group = GroupInfo(groupname)
        existing = group.roles_for(workspace)
        roles = WORKSPACE_GROUPS[workgroup.id]['roles']
        aclr[groupname] = sorted(list(set(existing).union(roles)))
        _log('Reset mapped local roles for groupname %s to %s ' % (
                groupname,
                repr(aclr[groupname]),
                )
            )
    ## sufficient: assert that the pas_group() for each of the respective
    ## groups for the workspace has the appropriate local role binding.
    for workgroup in roster.groups.values():
        groupname = workgroup.pas_group()
        assert groupname in unwrapped.__ac_local_roles__
        for role in WORKSPACE_GROUPS[workgroup.id]['roles']:
            assert role in unwrapped.__ac_local_roles__[groupname]
    ## sufficient: old roles cleared out of aclr:
    for principal, roles in unwrapped.__ac_local_roles__.items():
        for role in remove_roles:
            assert role not in roles


def migrate_siteroot(site):
    """
    Migration for site root state and state of user storage in acl_users.
    """
    remove_old_roles(site)
    remove_old_groups(site)
    recreate_contributor_groups(site)
    rename_member_groups(site, oldsuffix='-members', newsuffix='-viewers')
    rename_member_groups(site, oldsuffix='-lead', newsuffix='-managers')


def mass_reindex(site):
    """
    Everything needs reindexing, practically speaking -- the following indexes
    are affected by changes made in this migration:
    
     * allowedRolesAndUsers -- we modify resulting roles for each workspace.
                            -- we also modify role-to-permissions in workflow
                               for *ALL* content.
     
     * review_state -- affects all content if we change the default workflow.
    
    So, get all items contained with the tree given a node.  Uses
    recursive generator plone.app.folder.utils.findObjects() to avoid
    exceeding maximum recursion or stack size.
    """
    for content in site.contentValues():
        for item in findObjects(content):
            if IContentish.providedBy(item):
                item.reindexObject()
    MIGRATION_LOG.info('Migration: mass-reindex of all content complete')


def uuid_annotate(content):
    assert IAttributeUUID.providedBy(content)
    if not hasattr(aq_base(content), UUID_ATTR):
        addAttributeUUID(content, None)
        MIGRATION_LOG.info('Generated UUID for content at %s' % (
            '/'.join(content.getPhysicalPath()),
            ))
    assert getattr(aq_base(content), UUID_ATTR, None) is not None


def migrate_project(project, version=2):
    """
    Migrate a project from previous state.
    """
    unwrapped = aq_base(project)
    if getattr(unwrapped, '_migration_version', None) == 2:
        MIGRATION_LOG.info('Project migration skipped, already '\
                           'marked as migrated: %s (%s)' % (
                                project.Title(),
                                project.getId(),
                                ))
        return  # already migrated this object (attr set by mark_changed())
    # Migrate old folder contents storage to BTree folder contents
    # compatible with Dexterity containers.
    migrate_folder(project)
    # Migrate logo attribute contents to NamedImage.
    migrate_logo(project)
    # Remove unused attributes:
    unused = (
        'dbid',
        'groupname',
        'managers',
        'faculty',
        'projectTheme',
        'cmf_uid',
        )
    remove_attributes(project, unused)
    # Fix local roles (remove old local roles, add new):
    fix_local_roles(project)
    # Add UUIDs to project object
    uuid_annotate(project)
    # Mark project._p_changed=True to ensure changes flushed at commit time
    mark_changed(project)


def migrate_team(team, version=2):
    """
    Migrate a team (or sub-team) from previous state.
    """
    unwrapped = aq_base(team)
    if getattr(unwrapped, '_migration_version', None) == 2:
        MIGRATION_LOG.info('Team migration skipped, already '\
                           'marked as migrated: %s (%s)' % (
                                team.Title(),
                                team.getId(),
                                ))
        return  # already migrated this object (attr set by mark_changed())
    # Migrate old folder contents storage to BTree folder contents
    # compatible with Dexterity containers.
    migrate_folder(team)
    # Remove unused attributes:
    unused = ('dbid', 'groupname', 'reportLocations', 'cmf_uid')
    remove_attributes(team, unused)
    # Fix local roles (remove old local roles, add new):
    fix_local_roles(team)
    # Add UUIDs to project object
    uuid_annotate(team)
    # Mark project._p_changed=True to ensure changes flushed at commit time
    mark_changed(team)


def migrate_workflow(item, site, wftool):
    unwrapped = aq_base(item)
    chain = wftool.getChainFor(item)
    use_chains = ('qiext_project_workflow', 'qiext_workspace_workflow')
    if not chain or chain[0] not in use_chains:
        return # skip item -- not bound to workflow we are migrating
    _prefix = 'migrate_workflow() content item "%s" at %s:' % (
        item.Title(),
        '/'.join(item.getPhysicalPath()),
        )
    _log = lambda msg: MIGRATION_LOG.info('%s %s' % (_prefix, msg))
    mtool = getToolByName(site, 'portal_membership')
    authuser = mtool.getAuthenticatedMember().getUserName()
    initial_state = 'visible'
    state_name_map = {  # old->new
        'project_private': 'restricted',
        'restrict_to_team': 'visible',
        'sub_team': 'visible',
        None: initial_state,
        }
    wf_name = 'qiext_workspace_workflow'
    old_wf_name = 'qi_content_workflow'
    if item.portal_type == 'qiproject':
        initial_state = 'visible'
        state_name_map = {  # old->new
            'restrict_to_managers': 'restricted',
            None: initial_state,
            }
        wf_name = 'qiext_project_workflow'
        old_wf_name = 'qi_project_workflow'
    _old_wf_state = wftool.getStatusOf(old_wf_name, item)
    if _old_wf_state:
        _old_wf_state = _old_wf_state['review_state']  # state name
    if not hasattr(unwrapped, 'workflow_history'):
        unwrapped.workflow_history = PersistentMapping()
    prev_actions = unwrapped.workflow_history.get(wf_name, ())
    action = {
        'action': None,
        'review_state': initial_state,  # may be replaced below...
        'actor': authuser,
        'comments': 'Automated migration of workflow state',
        'time': DateTime(),
        }
    if _old_wf_state is not None:
        # new state name is either remapped/renamed or stays the same as old
        state_name = state_name_map.get(_old_wf_state, _old_wf_state)
        action['review_state'] = state_name
    actions = list(prev_actions)
    unwrapped.workflow_history[wf_name] = tuple(actions + [action])
    _log('modified workflow_history, state from %s to %s' % (
            _old_wf_state,
            action['review_state'],
            )
        )
    ## finally, apply permissions-to-roles for the destination state:
    wftool.getWorkflowsFor(item)[0].updateRoleMappingsFor(item)
    _log('updated role mappings (permissions) for item from workflow state')
    item._p_changed = True
    ## test assertions about state:
    assert wf_name == wftool.getChainFor(item)[0]
    assert wf_name in unwrapped.workflow_history
    status = wftool.getStatusOf(wf_name, item)
    item_state = status['review_state']
    assert item_state == action['review_state']
    if _old_wf_state in state_name_map:
        assert item_state == state_name_map[_old_wf_state]  # remap
    else:
        assert item_state == _old_wf_state  # not change in state name
    assert unwrapped.workflow_history[wf_name][-1]['time'] == action['time']


def fix_skins(site):
    removed = 0
    orig_layers = {}  # for before/after state comparison and counts
    tool = getToolByName(site, 'portal_skins')
    remove = ('Qi-Images', 'uu_qisite', 'qi-macros')
    fsdirview_orig = tool.objectIds()
    for name in remove:
        if name in tool.objectIds():
            tool.manage_delObjects([name])
            removed += 1
            MIGRATION_LOG.info('Removed FS Directory View %s' % name)
    for theme, layerspec in tool.selections.items():
        orig_layers[theme] = layerspec.split(',')
        layers = [name for name in orig_layers[theme] if name not in remove]
        tool.selections[theme] = ','.join(layers)
        MIGRATION_LOG.info(
            'Removed stale skin layers from theme selection '\
            'for theme "%s": removed %s' % (
                theme,
                repr(set(orig_layers) - set(layers)),  # removed=before-after
                )
            )
    tool._p_changed = True
    ## check that each removed item is not in skins, layers
    for name in remove:
        for theme, layerspec in tool.selections.items():
            assert name not in layerspec  # string containment
            layers = layerspec.split(',')
            for l in orig_layers[theme]:
                if l not in remove:
                    assert l in layers  # not removed, should be there after
        assert name not in tool.objectIds()
    assert len(fsdirview_orig) - len(tool.objectIds()) == removed


def fix_inconsistent_userinfo(site):
    ## fix inconsistent userid!=login -- have seen one case where they
    ## differed by capitalization
    user_plugin = site.acl_users.source_users
    u_enumerate = user_plugin.enumerateUsers
    inconsistent = [d['id'] for d in u_enumerate() if d['id']!=d['login']]
    for userid in inconsistent:
        user_plugin._userid_to_login[userid] = userid
        MIGRATION_LOG.info('Fixed inconsistent login not matching user id '\
                           'for %s' % userid)


def migrate_site(site):
    catalog = getToolByName(site, 'portal_catalog')
    _objectfor = lambda brain: brain._unrestrictedGetObject()
    _typesearch = lambda v: catalog.search({'portal_type': v})
    MIGRATION_LOG.info(
        '-- STARTED MIGRATION FOR NOT YET MIGRATED SITE %s -- ' % (
            site.getId(),
            )
        )
    ## up-front, deal with any inconsistent user logins
    fix_inconsistent_userinfo(site)
    ## migrate site root and acl_users:
    MIGRATION_LOG.info('Migrating site root.')
    migrate_siteroot(site)
    MIGRATION_LOG.info('    --done with site root step.')
    ## get and migrate all projects, teams, subteams
    migrations = {
        'qiproject': migrate_project,
        'qiteam': migrate_team,
        'qisubteam': migrate_team,
        }
    for fti_name, migrate in migrations.items():
        items = [_objectfor(brain) for brain in _typesearch(fti_name)]
        for item in items:
            MIGRATION_LOG.info('Running migration %s() for item at %s' % (
                    migrate.__name__,
                    '/'.join(item.getPhysicalPath()),
                    )
                )
            migrate(item)
            MIGRATION_LOG.info('    --done with step for workspace.')
    ## workflow migrations:
    wftool = getToolByName(site, 'portal_workflow')
    for content in site.contentValues():
        for path, item in findObjects(content):
            migrate_workflow(item, site, wftool)
    MIGRATION_LOG.info('    --done with workflow migration step.')
    ## remove any unused skin fsdir views 'Qi-Images' and 'uu_qisite'
    fix_skins(site)
    ## finally, reindex everything:
    mass_reindex(site)
    MIGRATION_LOG.info('    --done with content reindex.')


def not_yet_migrated(site):
    catalog = getToolByName(site, 'portal_catalog')
    _objectfor = lambda brain: brain._unrestrictedGetObject()
    _typesearch = lambda v: catalog.search({'portal_type': v})
    projects = [_objectfor(brain) for brain in _typesearch('qiproject')]
    for project in projects:
        unwrapped = aq_base(project)
        if hasattr(unwrapped, 'dbid') or hasattr(unwrapped, 'managers'):
            return True  # old attributes
        if hasattr(unwrapped, '_objects'):
            return True  # unmigrated folder contents
    return False


def install_migration(context):
    """
    Install migration if and only if site appears to be in a stale,
    not-yet-migrated state.  Due to complex multi-package update,
    this is an install setup, not an upgrade step.
    """
    site = context.getSite()
    if not_yet_migrated(site):
        migrate_site(site)

