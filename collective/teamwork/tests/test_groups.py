import unittest as unittest

from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName

from collective.teamwork.tests.layers import DEFAULT_PROFILE_TESTING
from collective.teamwork.user.interfaces import IGroups
from collective.teamwork.user.members import SiteMembers
from collective.teamwork.user.groups import GroupInfo, Groups


class GroupAdaptersTest(unittest.TestCase):
    """Test IGroups adapter for site, and Group/IGroup objects"""

    layer = DEFAULT_PROFILE_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self._users = self.portal.acl_users
        self.groups_plugin = self._users.source_groups
        self.site_members = SiteMembers(self.portal)
        self.user1 = 'me@example.com'
        self.user2 = 'you@example.com'
        self.group1 = 'adapter_group1'
        self.group2 = 'adapter_gropu2'
        self.site_members.register(self.user1, send=False)
        self.site_members.register(self.user2, send=False)
        groups = IGroups(self.portal)
        groups.add(self.group1)
        groups.add(self.group2)

    def test_adapter_registration(self):
        self.assertIsInstance(IGroups(self.portal), Groups)
        self.assertEqual(IGroups(self.portal).context, self.portal)

    def test_get_groups(self):
        groups = IGroups(self.portal)
        assert self.group1 in groups.keys()
        assert self.group2 in groups.keys()
        g1 = groups[self.group1]
        self.assertIsInstance(g1, GroupInfo)
        self.assertEqual(g1.name, self.group1)
        g2 = groups.get(self.group2, None)
        assert g2 is not None
        self.assertIsInstance(g2, GroupInfo)
        self.assertEqual(g2.name, self.group2)

    def test_add_rename_remove_group(self):
        groups = IGroups(self.portal)
        _old, _new = ('rename_old', 'rename_new')
        groups.add(_old)
        assert _old in groups
        g_old = groups.get(_old)
        g_old.assign(self.user1)
        assert self.user1 in g_old
        groups.rename(_old, _new)
        assert _old not in groups
        assert _new in groups
        assert self.user1 in groups.get(_new)
        groups.get(_new).unassign(self.user1)  # tear-down
        assert self.user1 not in groups.get(_new)
        groups.remove(_new)
        assert _old not in groups
        assert _new not in groups

    def test_clone_groups(self):
        groups = IGroups(self.portal)
        _old, _new = ('rename_old', 'rename_new')
        groups.add(_old)
        assert _old in groups
        g_old = groups.get(_old)
        g_old.assign(self.user1)
        assert self.user1 in g_old
        clone = groups.clone(_old, _new)  # noqa
        assert _old in groups
        assert _new in groups
        assert self.user1 in groups.get(_new)

    def test_get_user(self):
        groups = IGroups(self.portal)
        group1 = groups[self.group1]
        group1.assign(self.user1)
        u1 = group1[self.user1]
        u1_orig = self.site_members[self.user1]
        self.assertEqual(u1._id, u1_orig._id)
        self.assertEqual(u1._roles, u1_orig._roles)
        self.assertRaises(KeyError, lambda: group1[self.user2])
        group1.unassign(self.user1)

    def test_add_remove_add_user_assignment(self):
        groups = IGroups(self.portal)
        group1 = groups[self.group1]
        group2 = groups[self.group2]
        self.assertNotIn(self.user1, group1)
        group1.assign(self.user1)
        self.assertIn(self.user1, group1)
        self.assertNotIn(self.user1, group2)
        self.assertNotIn(self.user2, group1)
        self.assertNotIn(self.user2, group2)
        group2.assign(self.user1)
        self.assertIn(self.user1, group1)
        self.assertIn(self.user1, group2)
        self.assertNotIn(self.user2, group1)
        self.assertNotIn(self.user2, group2)
        group1.assign(self.user2)
        self.assertIn(self.user2, group1)
        self.assertNotIn(self.user2, group2)
        self.assertIn(self.user1, group1)
        self.assertIn(self.user1, group2)
        group1.unassign(self.user2)
        self.assertIn(self.user1, group1)
        self.assertIn(self.user1, group2)
        self.assertNotIn(self.user2, group1)
        self.assertNotIn(self.user2, group2)
        group2.unassign(self.user1)
        self.assertIn(self.user1, group1)
        self.assertNotIn(self.user1, group2)
        self.assertNotIn(self.user2, group1)
        self.assertNotIn(self.user2, group2)
        group1.unassign(self.user1)
        self.assertNotIn(self.user1, group1)
        self.assertNotIn(self.user1, group2)
        self.assertNotIn(self.user2, group1)
        self.assertNotIn(self.user2, group2)

    def test_enumeration(self):
        """Test group enumeration"""
        groups = IGroups(self.portal)
        assert len(groups.values()) > 0

    def test_autogroups(self):
        KEY = 'AuthenticatedUsers'
        groups = IGroups(self.portal)
        assert KEY in groups
        group = groups.get(KEY)
        self.assertEqual(
            group.title,
            u'Authenticated Users (Virtual Group)'
            )
        self.assertEqual(len(group), 0)
        self.assertEqual(len(group), len(group.keys()))
