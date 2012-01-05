import unittest2 as unittest

from plone.registry.interfaces import IRegistry
from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName

from uu.qiext.tests.layers import DEFAULT_PROFILE_TESTING


class DefaultProfileTest(unittest.TestCase):
    """Test default profile's installed configuration settings"""

    layer = DEFAULT_PROFILE_TESTING
    
    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
    
    def _product_fti_names(self):
        """ for now, test Products.qi types used by uu.qiext """
        from Products.qi.extranet.types import interfaces
        return (
            interfaces.PROJECT_TYPE,
            interfaces.TEAM_TYPE, 
            interfaces.SUBTEAM_TYPE,
            )

    def test_browserlayer(self):
        """Test product layer interfaces are registered for site"""
        from uu.qiext.interfaces import IQIExtranetProductLayer
        from Products.qi.interfaces import IQIProductLayer
        from plone.browserlayer.utils import registered_layers
        self.assertTrue(IQIExtranetProductLayer in registered_layers())
        self.assertTrue(IQIProductLayer in registered_layers())
    
    def test_ftis(self):
        types_tool = getToolByName(self.portal, 'portal_types')
        typenames = types_tool.objectIds()
        for name in self._product_fti_names():
            self.assertTrue(name in typenames)
   
    def _add_check(self, typename, id, iface, cls, title=None, parent=None):
        if parent is None:
            parent = self.portal
        if title is None:
            title = id
        if isinstance(title, str):
            title = title.decode('utf-8')
        parent.invokeFactory(typename, id, title=title)
        self.assertTrue(id in parent.contentIds())
        o = parent[id]
        self.assertTrue(isinstance(o, cls))
        self.assertTrue(iface.providedBy(o))
        o.reindexObject()
        return o # return constructed content for use in additional testing


