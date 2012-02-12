import unittest2 as unittest

from plone.registry.interfaces import IRegistry
from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName

from uu.qiext.tests.layers import DEFAULT_PROFILE_TESTING
from uu.qiext.user.interfaces import ISiteMembers, IGroups, IGroup
from uu.qiext.user.members import SiteMembers
from uu.qiext.user.groups import GroupInfo, Groups


class GroupAdaptersTest(unittest.TestCase):
    """Test IGroups adapter for site, and Group/IGroup objects"""
    
    THEME = 'Sunburst Theme'
    
    layer = DEFAULT_PROFILE_TESTING
    
    def setUp(self):
        self.portal = self.layer['portal']
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self._users = self.portal.acl_users
        self.groups_plugin = self._users.source_groups
    
    def test_adapter_registration(self):
        self.assertIsInstance(IGroups(self.portal), Groups)
        self.assertEqual(IGroups(self.portal).context, self.portal)

