from plone.app.testing import TEST_USER_ID, setRoles
from plone.uuid.interfaces import IUUID
from Products.CMFPlone.utils import getToolByName
from zope.component import queryUtility

from collective.teamwork.tests.layers import DEFAULT_PROFILE_TESTING
from collective.teamwork.tests.base import WorkspaceTestBase
from collective.teamwork.tests.fixtures import CreateContentFixtures
from collective.teamwork.user.groups import GroupInfo
from collective.teamwork.user.members import SiteMembers
from collective.teamwork.user.interfaces import IWorkspaceRoster
from collective.teamwork.user.interfaces import IMembershipModifications
from collective.teamwork.user.interfaces import IWorkgroupTypes


class WorkgroupAdaptersTest(WorkspaceTestBase):
    """Test workgroup roster/membership management adapters"""

    layer = DEFAULT_PROFILE_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self._users = self.portal.acl_users
        self.groups_plugin = self._users.source_groups
        self.site_members = SiteMembers(self.portal)
        self._fixtures()

    def _fixtures(self):
        adapter = CreateContentFixtures(self, self.layer)  # noqa
        adapter.create()
        self.test_member = adapter.TEST_MEMBER

    def test_group_parent_ref(self):
        """Role group __parent__ reference is roster, roster has no parent"""
        workspace, roster = self._base_fixtures()
        group = roster.groups.get('managers')
        self.assertEqual(group.__parent__, roster)
        self.assertIsNone(roster.__parent__)

    def test_group_name(self):
        """Role group __name__ matches key in roster"""
        workspace, roster = self._base_fixtures()
        name = 'managers'
        group = roster.groups.get(name)
        self.assertEqual(group.__name__, name)

    def test_workspace_namespace(self):
        """Workgroup namespace uses content UUID"""
        workspace, roster = self._base_fixtures()
        from plone.uuid.interfaces import IUUID
        self.assertEqual(roster.namespace, IUUID(workspace))

    def test_pas_groupname(self):
        """Test PAS groupname construction for groups in roster"""
        workspace, roster = self._base_fixtures()
        namespace = IUUID(workspace)
        for name, group in roster.groups.items():
            self.assertEqual(name, group.__name__)
            expected_groupname = namespace + '-' + name
            self.assertEqual(expected_groupname, group.pas_group()[0])

    def test_user_add_and_containment(self):
        """
        Test user addition, containment matches containment in associated group
        """
        workspace, roster = self._base_fixtures()
        # add a user to the roster, then to the 'managers' group;
        # test containment/success of both in roster, workgroup, and PAS
        # group.
        username = 'mefoo@example.com'
        self.site_members.register(username, send=False)
        original_membercount = len(roster)
        roster.add(username)
        roster.groups['managers'].add(username)
        assert username in roster
        assert username in roster.groups['managers']
        # test reverse indexing user to groups:
        assert 'managers' in roster.user_groups(username)
        assert 'viewers' in roster.user_groups(username)
        # get PAS group, via IGroup:
        pas_group = GroupInfo(roster.groups['managers'].pas_group()[0])
        assert username in pas_group
        self.assertEqual(len(roster), original_membercount + 1)

    def test_get_user(self):
        """Get user from roster"""
        username = self.test_member
        workspace, roster = self._base_fixtures()
        assert username in roster  # was added by fixture
        group = GroupInfo(roster.groups['viewers'].pas_group()[0])
        assert username in group
        # equal propertied user objects:
        self.assertEqual(group.get(username)._id, roster.get(username)._id)
        self.assertEqual(
            group.get(username)._login,
            roster.get(username)._login
            )

    def test_stored_group(self):
        attr = '_group'
        workspace, roster = self._base_fixtures()
        group = getattr(roster, attr, None)
        self.assertIsNotNone(group)
        self.assertIn(roster.__name__, group.name)
        self.assertTrue(group.name.startswith(IUUID(workspace)))

    def test_add_user_already_added(self):
        """Attempt to add user already added"""
        workspace, roster = self._base_fixtures()
        self.assertIn(self.test_member, roster)  # added by fixture
        try:
            roster.add(self.test_member)
        except:
            raise AssertionError('Add existing user; unexpected exception')

    def test_assign_bogus_to_group(self):
        """
        Test that addition of user to group is disallowed if not in
        roster (via 'viewers' role group).
        """
        username = 'registeredButNotInWorkspace@example.com'
        # note about case: register case-normalizing, containment insensitive
        self.site_members.register(username, send=False)
        self.assertIn(username, self.site_members)
        workspace, roster = self._base_fixtures()
        self.assertRaises(
            RuntimeError,
            roster.groups.get('managers').add,
            username,
            )

    def test_assign_invalid_user(self):
        """Assigning invalid username fails with exception"""
        non_existent_user = 'samiam@example.com'
        workspace, roster = self._base_fixtures()
        self.assertRaises(
            RuntimeError,
            roster.add,
            non_existent_user,
            )

    def test_unassign_user_from_workgroup(self):
        """Unassign user from workgroup, basic case."""
        workspace, roster = self._base_fixtures()
        username = 'add-and-remove@example.com'
        self.site_members.register(username, send=False)
        workspace, roster = self._base_fixtures()
        self.assertNotIn(username, roster)
        roster.add(username)
        self.assertIn(username, roster)
        roster.unassign(username)
        self.assertNotIn(username, roster)

    def test_assign_unassign_recursive(self):
        """Unassigning user from project removes from contained workspaces"""
        workspace, roster = self._base_fixtures()
        username = 'recurisve-add-remove@example.com'
        self.site_members.register(username, send=False)
        project, project_roster = self._base_fixtures()
        team = project['team1']
        team_roster = IWorkspaceRoster(team)
        subteam = team['subteam']
        subteam_roster = IWorkspaceRoster(subteam)
        self.assertNotIn(username, project_roster)
        self.assertNotIn(username, team_roster)
        self.assertNotIn(username, subteam_roster)
        # add recursively adds to parent workspaces, walking upward:
        subteam_roster.add(username)
        self.assertIn(username, subteam_roster)
        self.assertIn(username, team_roster)
        self.assertIn(username, project_roster)
        # remove recursively removes from contained workspaces:
        project_roster.unassign(username)
        self.assertNotIn(username, project_roster)
        self.assertNotIn(username, team_roster)
        self.assertNotIn(username, subteam_roster)

    def test_unassign_groups(self):
        """
        Unassigning from 'viewers' group or roster, via IWorkspaceRoster
        removes user from other groups in workpace.
        """
        workspace, roster = self._base_fixtures()
        username = 'removegroups@example.com'
        self.site_members.register(username, send=False)
        roster.add(username)
        roster.groups['managers'].add(username)
        self.assertIn(username, roster)
        self.assertIn(username, roster.groups['managers'])
        roster.unassign(username)
        self.assertNotIn(username, roster)
        self.assertNotIn(username, roster.groups['managers'])

    def test_unassign_single_secondary_group(self):
        """Unassign a single non-viewer role group from user"""
        workspace, roster = self._base_fixtures()
        username = 'removegroups@example.com'
        self.site_members.register(username, send=False)
        roster.add(username)
        roster.groups['managers'].add(username)
        self.assertIn(username, roster)
        self.assertIn(username, roster.groups['managers'])
        roster.unassign(username, 'managers')
        # still assigned to roster, but not to managers group:
        self.assertIn(username, roster)
        self.assertNotIn(username, roster.groups['managers'])

    def test_unassign_contained_secondary(self):
        """Unassign from workgroup, removed from secondary contained"""
        project, roster = self._base_fixtures()
        team = project['team1']
        team_roster = IWorkspaceRoster(team)
        username = 'unassign-secondary-contained@example.com'
        self.site_members.register(username, send=False)
        roster.add(username)
        team_roster.add(username)
        team_roster.groups['managers'].add(username)
        self.assertIn(username, roster)
        self.assertIn(username, team_roster)
        self.assertIn(username, team_roster.groups['managers'])
        roster.unassign(username)
        self.assertNotIn(username, roster)
        self.assertNotIn(username, team_roster)
        self.assertNotIn(username, team_roster.groups['managers'])

    def test_unassign_base_group_removes_secondary(self):
        """Unassign from base group, get removed from others."""
        workspace, roster = self._base_fixtures()
        username = 'removebasegroup@example.com'
        self.site_members.register(username, send=False)
        roster.add(username)
        roster.groups['contributors'].add(username)
        self.assertIn(username, roster)
        self.assertIn(username, roster.groups['viewers'])
        self.assertIn(username, roster.groups['contributors'])
        # removing from the base group ought to remove all traces of user
        # from the workspace roster and groups:
        roster.groups['viewers'].unassign(username)
        self.assertNotIn(username, roster)
        self.assertNotIn(username, roster.groups['viewers'])
        self.assertNotIn(username, roster.groups['contributors'])

    def test_can_purge(self):
        """Testing IWorkspaceRoster.can_purge()"""
        project1, roster1 = self._base_fixtures()
        project2 = self.portal['project2']
        roster2 = IWorkspaceRoster(project2)
        user_oneproject = 'justone@example.com'
        user_twoprojects = 'busyone@example.com'
        self.site_members.register(user_oneproject, send=False)
        self.site_members.register(user_twoprojects, send=False)
        roster1.add(user_oneproject)
        roster1.add(user_twoprojects)
        roster2.add(user_twoprojects)
        self.assertTrue(roster1.can_purge(user_oneproject))
        self.assertFalse(roster1.can_purge(user_twoprojects))  # disallowed
        self.assertFalse(roster2.can_purge(user_twoprojects))  # here too.
        self.assertFalse(roster2.can_purge(user_oneproject))  # not in here
        # cannot purge from a team, even with otherwise purgeable user:
        self.assertFalse(
            IWorkspaceRoster(project1['team1']).can_purge(user_oneproject)
            )

    def test_purge_exceptions(self):
        """Test for expected failure on disallowed purge of user"""
        project1, roster1 = self._base_fixtures()
        project2 = self.portal['project2']
        roster2 = IWorkspaceRoster(project2)
        username = 'busyhere@example.com'
        self.site_members.register(username, send=False)
        roster1.add(username)
        roster2.add(username)
        # user cannot be purged because of membership elsewhere:
        self.assertRaises(
            RuntimeError,
            roster2.purge_user,
            username,
            )
        # user not in roster
        self.assertRaises(
            RuntimeError,
            roster2.purge_user,
            'notanywhereinroster@example.com',
            )

    def test_purge_success(self):
        """Allowed purge of user succeeds."""
        project1, roster1 = self._base_fixtures()
        username = 'expendable@example.com'
        self.site_members.register(username, send=False)
        roster1.add(username)
        self.assertIn(username, self.site_members)
        self.assertIn(username, roster1)
        self.assertTrue(roster1.can_purge(username))
        roster1.purge_user(username)
        self.assertNotIn(username, self.site_members)
        self.assertNotIn(username, roster1)

    def _test_roles(self, username, role, permissions, group=None):
        """
        Test local roles and permissions for user in context: viewer; this
        indirectly tests both the local role plugin and the workflow used
        in this package.
        """
        workspace, roster = self._base_fixtures()
        self.site_members.register(username, send=False)
        user = self.site_members.get(username)  # IPropertiedUser
        userid = self.site_members.userid_for(username)
        self.assertNotIn(
            role,
            user.getRolesInContext(workspace),
            )
        pmap = workspace.manage_getUserRolesAndPermissions(userid)
        self.assertNotIn(
            role,
            pmap['roles_in_context']
            )
        for permission in permissions:
            self.assertNotIn(
                permission,
                pmap['allowed_permissions'],
                )
        roster.add(username)
        if group is not None:
            roster.groups[group].add(username)
        # we need to get a new IPropertiedUser, because previous unaware
        # of new group assignments...
        user = self.site_members.get(username)  # IPropertiedUser
        self.assertIn(
            role,
            user.getRolesInContext(workspace),
            )
        pmap = workspace.manage_getUserRolesAndPermissions(userid)
        self.assertIn(
            role,
            pmap['roles_in_context']
            )
        for permission in permissions:
            self.assertIn(
                permission,
                pmap['allowed_permissions'],
                )
        # unassign from group:
        roster.unassign(username, group)
        # again, get new propertied user to avoid cached group membership:
        user = self.site_members.get(username)  # IPropertiedUser
        self.assertNotIn(
            role,
            user.getRolesInContext(workspace),
            )
        pmap = workspace.manage_getUserRolesAndPermissions(userid)
        self.assertNotIn(
            role,
            pmap['roles_in_context']
            )
        for permission in permissions:
            self.assertNotIn(
                permission,
                pmap['allowed_permissions'],
                )

    def test_roles_viewer(self):
        username = 'projectroles@example.com'
        return self._test_roles(username, 'Workspace Viewer', ('View',))

    def test_roles_manager(self):
        """Test local roles and permissions for user in context: manager"""
        username = 'projectroles-manager@example.com'
        role = 'Manager'
        permissions = ('Manage users', 'Modify portal content')
        return self._test_roles(username, role, permissions, group='managers')

    def test_roles_contributor(self):
        """Test local roles and permissions for user in context: contributor"""
        username = 'projectroles-contrib@example.com'
        role = 'Workspace Contributor'
        permissions = ('Add portal content',)
        group = 'contributors'
        return self._test_roles(username, role, permissions, group)

    def test_mixedcase_email(self):
        """Some basic tests for mixed-case email"""
        username = 'MixedCaseInWorkspace@example.com'
        # note about case: register case-normalizing, containment insensitive
        self.site_members.register(username, send=False)
        self.assertIn(username, self.site_members)
        self.assertIn(username.lower(), self.site_members.keys())
        workspace, roster = self._base_fixtures()
        roster.add(username)
        # case-normalized:
        self.assertIn(username.lower(), roster.keys())
        # case-insensitive containment:
        self.assertIn(username, roster)
        self.assertIn(username.lower(), roster)
        self.assertTrue(roster.get(username) is not None)
        self.assertTrue(roster[username] is not None)

    def test_bulk_modification(self):
        workspace, roster = self._base_fixtures()
        config = queryUtility(IWorkgroupTypes)
        bulk = IMembershipModifications(workspace)
        self.assertTrue(IMembershipModifications.providedBy(bulk))
        self.assertTrue(bulk.context is workspace)
        for rolegroup in config:
            self.assertIn(rolegroup, bulk.planned_assign)
            self.assertIn(rolegroup, bulk.planned_unassign)
        # order does not matter for queuing, something slightly askew but ok:
        email1 = 'bulk1@example.com'
        self.site_members.register(email1, send=False)
        bulk.assign(email1, 'contributors')
        bulk.assign(email1)  # group of 'viewers' implied by default
        self.assertIn(email1, bulk.planned_assign['viewers'])
        self.assertIn(email1, bulk.planned_assign['contributors'])
        # not yet applied:
        self.assertNotIn(email1, roster)
        self.assertNotIn(email1, roster.groups['contributors'])
        # assign another user:
        email2 = 'bulk2@example.com'
        self.site_members.register(email2, send=False)
        bulk.assign(email2, 'viewers')
        self.assertIn(email2, bulk.planned_assign['viewers'])
        self.assertNotIn(email2, roster)  # not yet applied.
        self.assertTrue(len(bulk.planned_assign['viewers']) == 2)
        # assign and unassign (yes, contradictory, but we handle gracefully):
        email3 = 'bulk3@example.com'
        self.site_members.register(email3, send=False)
        bulk.assign(email3, 'viewers')
        self.assertIn(email3, bulk.planned_assign['viewers'])
        self.assertNotIn(email3, roster)  # not yet applied.
        self.assertTrue(len(bulk.planned_assign['viewers']) == 3)
        bulk.unassign(email3)
        self.assertIn(email3, bulk.planned_unassign['viewers'])
        # now, let's apply all this:
        bulk.apply()
        # check worklists are empty:
        self.assertTrue(len(bulk.planned_assign['viewers']) == 0)
        self.assertTrue(len(bulk.planned_assign['contributors']) == 0)
        # check email1, email2 in respective expected groups/roster:
        self.assertIn(email1, roster)
        self.assertIn(email1, roster.groups['contributors'])
        self.assertIn(email2, roster)
        # check that email3, which was added, then removed is gone:
        self.assertNotIn(email3, roster)


class WorkgroupMembershipStateTest(WorkspaceTestBase):

    def test_basic(self):
        from collective.teamwork.user.workgroups import WorkgroupMembershipState
        workspace, roster = self._base_fixtures()
        adapter = WorkgroupMembershipState(workspace)
        data = adapter()
        self.assertIsInstance(data, dict)
        data = adapter(use_json=True)
        self.assertIsInstance(data, basestring)

