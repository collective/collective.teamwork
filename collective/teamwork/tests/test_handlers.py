import unittest2 as unittest

from plone.app.testing import TEST_USER_ID, TEST_USER_NAME, setRoles
from plone.uuid.interfaces import IUUID
from Products.CMFPlone.utils import getToolByName
import transaction

from collective.teamwork.user.config import WORKSPACE_GROUPS
from collective.teamwork.user.workgroups import WorkspaceRoster
from collective.teamwork.tests.layers import DEFAULT_PROFILE_RENAME_TESTING
from collective.teamwork.tests.fixtures import CreateContentFixtures
        

class HandlerTest(unittest.TestCase):
    """Test event subscribers/handlers"""

    # This uses isolated, functional test layer to isolate the
    # unfortunate database side-effects of commiting ZODB
    # transactions (required to test object renames,
    # unfortunately) -- has wrapped DemoStorage to isolate.
    layer = DEFAULT_PROFILE_RENAME_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.groups_plugin = self.portal.acl_users.source_groups

    def test_create(self):
        adapter = CreateContentFixtures(self, self.layer)
        suffixes = WORKSPACE_GROUPS.keys()
        proj_id1 = 'proj_handler_test_create1'
        allgroups_before = self.groups_plugin.listGroupIds()
        proj = adapter.add_project(proj_id1)
        proj_uid = IUUID(proj)
        allgroups_after = self.groups_plugin.listGroupIds()
        ## necessary/sufficient: all expected groups (and only these):
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 3)
        for g in ['%s-%s' % (proj_uid, suffix) for suffix in suffixes]:
            assert g in allgroups_after
        ## now create a team workspace inside the project, similarly:
        team_id1 = 'team1'
        allgroups_before = self.groups_plugin.listGroupIds()
        team = adapter.add_workspace_to(proj, team_id1)
        team_uid = IUUID(team)
        allgroups_after = self.groups_plugin.listGroupIds()
        ## necessary/sufficient: all expected groups (and only these):
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 3)
        for g in ['-'.join((team_uid, s)) for s in suffixes]:
            assert g in allgroups_after

    def test_move_rename(self):
        """Test move or rename"""
        adapter = CreateContentFixtures(self, self.layer)
        suffixes = WORKSPACE_GROUPS.keys()
        proj_id1 = 'proj_handler_test_move_rename'
        self.assertNotIn(proj_id1, self.portal.contentIds())
        allgroups_before = self.groups_plugin.listGroupIds()
        proj = adapter.add_project(proj_id1, title='Project 1')
        proj_uid = IUUID(proj)
        transaction.get().commit()   # necessary for rename to work below
        self.assertIn(proj_id1, self.portal.contentIds())
        allgroups_after = self.groups_plugin.listGroupIds()
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 3)
        for g in ['%s-%s' % (proj_uid, suffix) for suffix in suffixes]:
            assert g in allgroups_after
        proj.setTitle('Project 1a')
        self.portal.manage_renameObject(proj_id1, proj_id1 + 'a')
        self.assertNotIn(proj_id1, self.portal.contentIds())     # old name
        self.assertIn(proj_id1 + 'a', self.portal.contentIds())  # new name
        allgroups_postrename = self.groups_plugin.listGroupIds()
        self.assertEquals(len(allgroups_postrename), len(allgroups_after))
        for suffix in suffixes:
            groupname = '%s-%s' % (proj_uid, suffix)
            assert groupname in allgroups_postrename        # new names
            title_suffix = WORKSPACE_GROUPS.get(suffix).get('title')
            title = self.groups_plugin.getGroupInfo(groupname).get('title')
            expected = 'Project 1a - %s' % title_suffix
            self.assertEquals(title, expected)
            
        ## now create a team workspace inside the project, similarly:
        team_id1 = 'team1'
        allgroups_before = self.groups_plugin.listGroupIds()
        team = adapter.add_workspace_to(proj, team_id1)
        team_uid = IUUID(team)
        roster = WorkspaceRoster(team)
        roster.add(TEST_USER_NAME)
        assert TEST_USER_NAME in roster
        assert len(roster) == 1
        transaction.get().commit()   # necessary for rename to work below
        allgroups_after = self.groups_plugin.listGroupIds()
        ## necessary/sufficient: all expected groups (and only these):
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 3)
        for g in ['-'.join((team_uid, s)) for s in suffixes]:
            assert g in allgroups_after
        ## now rename the team
        newid = team_id1 + 'a'
        proj.manage_renameObject(team_id1, newid)
        team = proj.get(newid)
        assert IUUID(team) == team_uid  # UUID does not change
        # ensure that users are copied to groups on rename:
        roster = WorkspaceRoster(team)
        assert TEST_USER_NAME in roster
        assert len(roster) == 1
        allgroups_postrename = self.groups_plugin.listGroupIds()
        self.assertEquals(len(allgroups_postrename), len(allgroups_after))
        for g in ['-'.join((team_uid, s)) for s in suffixes]:
            assert g in allgroups_postrename        # new names

    def test_remove(self):
        """test removal of project and team, make sure no orphan groups"""
        adapter = CreateContentFixtures(self, self.layer)
        suffixes = WORKSPACE_GROUPS.keys()
        proj_id1 = 'proj_handler_test_remove'
        self.assertNotIn(proj_id1, self.portal.contentIds())
        allgroups_before = self.groups_plugin.listGroupIds()
        proj = adapter.add_project(proj_id1)
        proj_uid = IUUID(proj)
        self.assertIn(proj_id1, self.portal.contentIds())
        allgroups_after = self.groups_plugin.listGroupIds()
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 3)
        for g in ['%s-%s' % (proj_uid, suffix) for suffix in suffixes]:
            assert g in allgroups_after
        ## now create a team workspace inside the project, similarly:
        team_id1 = 'team1'
        allgroups_before = self.groups_plugin.listGroupIds()
        team = adapter.add_workspace_to(proj, team_id1)
        team_uid = IUUID(team)
        allgroups_after = self.groups_plugin.listGroupIds()
        ## necessary/sufficient: all expected groups (and only these):
        self.assertEquals(len(allgroups_after) - len(allgroups_before), 3)
        for g in ['-'.join((team_uid, s)) for s in suffixes]:
            assert g in allgroups_after
        ## now remove from inside-out, starting with team
        proj.manage_delObjects([team_id1])
        allgroups_postdel = self.groups_plugin.listGroupIds()
        self.assertEquals(len(allgroups_after) - len(allgroups_postdel), 3)
        for g in ['-'.join((team_uid, s)) for s in suffixes]:
            assert g not in allgroups_after
        self.portal.manage_delObjects([proj_id1])
        allgroups_donedel = self.groups_plugin.listGroupIds()
        self.assertEquals(len(allgroups_postdel) - len(allgroups_donedel), 3)
        for g in ['-'.join((team_uid, s)) for s in suffixes]:
            assert g not in allgroups_donedel
        for g in ['-'.join((proj_uid, s)) for s in suffixes]:
            assert g not in allgroups_donedel

