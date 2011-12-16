from zope.app.component.hooks import getSite

from uu.qiext.utils import request_for
from uu.qiext.user.groups import ProjectGroup, ProjectRoster
from uu.qiext.user.utils import group_namespace, sync_group_roles


def _all_projects(site):
    """return all projects, found via catalog query"""
    r = site.portal_catalog.search({'portal_type':'qiproject'})
    return [b._unrestrictedGetObject() for b in r]


def _all_teams(site):
    """return all projects, found via catalog query"""
    r = site.portal_catalog.search({'portal_type':'qiteam'})
    return [b._unrestrictedGetObject() for b in r]


def migrate_project_groups(context, spaces=_all_projects):
    site = getSite()
    acl_users = site.acl_users
    rolemap = []
    for space in spaces(site):
        roster = ProjectRoster(space)
        for group in roster.groups.values():
            pas_groupnames = acl_users.source_groups.getGroupIds()
            groupname = group.pas_group()
            if groupname not in pas_groupnames:
                acl_users.source_groups.addGroup(groupname)
            # bind local roles, mapping group to roles from config
            sync_group_roles(context, groupname)
            if groupname.endswith('viewers'):
                old_groupname = groupname.replace('-viewers', '-members')
                if old_groupname in pas_groupnames:
                    oldgroup = ProjectGroup(space,
                                            groupid=u'members',
                                            namespace=group_namespace(space),)
                    for username in oldgroup.keys():
                        if username not in group:
                            acl_users.source_groups.addPrincipalToGroup(
                                username,
                                groupname,)
            if spaces is _all_teams and groupname.endswith('managers'):
                # old scheme had team managers called team leads. New role
                # names attempt to simplify, unify the terminology (which
                # makes for cleaner implementation).
                old_groupname = groupname.replace('-managers', '-lead')
                if old_groupname in pas_groupnames:
                    oldgroup = ProjectGroup(space,
                                            groupid=u'lead',
                                            namespace=group_namespace(space),)
                    for username in oldgroup.keys():
                        if username not in group:
                            acl_users.source_groups.addPrincipalToGroup(
                                username,
                                groupname,)


def migrate_team_groups(context):
    migrate_project_groups(context, spaces=_all_teams)


