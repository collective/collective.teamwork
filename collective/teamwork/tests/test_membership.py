import unittest2 as unittest

from Acquisition import aq_base
from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName
from zope.component.hooks import getSite

from collective.teamwork.tests.layers import DEFAULT_PROFILE_TESTING
from collective.teamwork.user.interfaces import ISiteMembers, IGroups
from collective.teamwork.user.members import SiteMembers


class MembershipTest(unittest.TestCase):
    """Test ISiteMembers / SiteMembers membership adapter for site"""

    THEME = 'Sunburst Theme'

    layer = DEFAULT_PROFILE_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self._users = self.portal.acl_users
        self.groups_plugin = self._users.source_groups

    def test_getadapter(self):
        adapters = (
            SiteMembers(),
            SiteMembers(self.portal),
            )
        for adapter in adapters:
            assert adapter.context is adapter.portal
            assert aq_base(adapter.context) is aq_base(getSite())
            assert aq_base(adapter.context) is aq_base(self.portal)

    def test_adapter_registration(self):
        self.assertIsInstance(ISiteMembers(self.portal), SiteMembers)
        self.assertEqual(ISiteMembers(self.portal).context, self.portal)

    def test_groups_property(self):
        members = SiteMembers(self.portal)
        members._groups = None  # force uncached
        groups = members.groups
        assert IGroups.providedBy(groups)
        assert aq_base(groups.context) is aq_base(self.portal)
        assert members.groups is groups   # cached, identical
        members._groups = None  # force uncached again
        assert IGroups.providedBy(members.groups)
        assert members.groups is not groups  # cached, new adapter

    def test_unknown_userid(self):
        # note: testing add/remove typically tests known user
        #       ids, the point of this test is to ensure the
        #       right things happen when an unknown user is used.
        unknown = 'ME@NOTHERE.example.com'
        members = SiteMembers(self.portal)
        assert unknown not in members
        assert members.get(unknown) is None
        self.assertRaises(KeyError, lambda: members[unknown])
        self.assertRaises(KeyError, lambda: members.__delitem__(unknown))
        self.assertRaises(
            KeyError,
            lambda: members.roles_for(self.portal, unknown)
            )
        self.assertRaises(KeyError, lambda: members.groups_for(unknown))

    def test_add_user(self):
        _ID = 'user@example.com'
        adapter = SiteMembers(self.portal)
        adapter.register(_ID, send=False)
        orig_len = len(adapter)
        self.assertIn(_ID, adapter)
        self.assertIn(_ID, adapter.keys())
        self.assertIn(_ID, list(iter(adapter)))
        # now do the same with a non-email id and email kwarg
        _ID = 'metoo'
        _EMAIL = 'foo@example.com'
        adapter.register(_ID, email=_EMAIL, send=False)
        self.assertEqual(len(adapter), orig_len + 1)
        self.assertIn(_ID, adapter)
        self.assertIn(_ID, adapter.keys())
        self.assertIn(_ID, list(iter(adapter)))
        self.assertEqual(adapter.get(_ID).getProperty('email'), _EMAIL)
        # check length again, potentially cached:
        self.assertEqual(len(adapter), orig_len + 1)

    def test_addremove_user(self, clearcache=True):
        _ID = 'user2@example.com'
        adapter = SiteMembers(self.portal)
        if clearcache:
            adapter.invalidate()
        orig_len = len(adapter)
        adapter.register(_ID, send=False)
        if clearcache:
            adapter.invalidate()
        self.assertEqual(len(adapter), orig_len + 1)
        self.assertIn(_ID, adapter)
        self.assertIn(_ID, adapter.keys())
        self.assertIn(_ID, list(iter(adapter)))
        # check length again, potentially cached:
        self.assertEqual(len(adapter), orig_len + 1)
        del(adapter[_ID])
        if clearcache:
            adapter.invalidate()
        self.assertEqual(len(adapter), orig_len)
        self.assertNotIn(_ID, adapter)
        self.assertNotIn(_ID, adapter.keys())
        self.assertNotIn(_ID, list(iter(adapter)))
        # check length again, potentially cached:
        self.assertEqual(len(adapter), orig_len)

    def test_addremove_nocache(self):
        self.test_addremove_user(clearcache=True)

    def test_roles_groups_for_user(self):
        """test groups_for() and roles_for()"""
        _ID = 'user3@example.com'
        _GROUP = 'testgroup1'
        adapter = SiteMembers(self.portal)
        adapter.register(_ID, send=False)
        self.groups_plugin.addGroup(_GROUP)
        self.groups_plugin.addPrincipalToGroup(_ID, _GROUP)
        self.assertIn(_GROUP, adapter.groups_for(_ID))
        self.assertIn('Member', adapter.roles_for(self.portal, _ID))


