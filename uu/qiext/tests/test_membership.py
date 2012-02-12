import unittest2 as unittest

from plone.registry.interfaces import IRegistry
from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName

from uu.qiext.tests.layers import DEFAULT_PROFILE_TESTING
from uu.qiext.user.interfaces import ISiteMembers
from uu.qiext.user.members import SiteMembers


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
    
    def test_adapter_registration(self):
        self.assertIsInstance(ISiteMembers(self.portal), SiteMembers)
        self.assertEqual(ISiteMembers(self.portal).context, self.portal)
    
    def test_add_user(self):
        _ID = 'user@example.com'
        adapter = SiteMembers(self.portal)
        adapter.register(_ID, send=False)
        self.assertIn(_ID, adapter)
        self.assertIn(_ID, adapter.keys())
        self.assertIn(_ID, list(iter(adapter)))
        # now do the same with a non-email id and email kwarg
        _ID = 'metoo'
        _EMAIL = 'foo@example.com'
        adapter.register(_ID, email=_EMAIL, send=False)
        self.assertIn(_ID, adapter)
        self.assertIn(_ID, adapter.keys())
        self.assertIn(_ID, list(iter(adapter)))
        self.assertEqual(adapter.get(_ID).getProperty('email'), _EMAIL)
    
    def test_addremove_user(self):
        _ID = 'user2@example.com'
        adapter = SiteMembers(self.portal)
        adapter.register(_ID, send=False)
        self.assertIn(_ID, adapter)
        self.assertIn(_ID, adapter.keys())
        self.assertIn(_ID, list(iter(adapter)))
        del(adapter[_ID])
        self.assertNotIn(_ID, adapter)
        self.assertNotIn(_ID, adapter.keys())
        self.assertNotIn(_ID, list(iter(adapter)))
    
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


