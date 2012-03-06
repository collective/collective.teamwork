from itertools import chain
import unittest2 as unittest

from plone.app.testing import TEST_USER_ID, TEST_USER_NAME
from plone.app.testing import setRoles, login, logout
from zope.interface import alsoProvides
from Acquisition import aq_base
from Products.CMFPlone.utils import getToolByName

from uu.qiext.interfaces import IQIExtranetProductLayer
from uu.qiext.tests.fixtures import CreateContentFixtures
from uu.qiext.tests.layers import DEFAULT_PROFILE_TESTING

_tmap = lambda states, s: states[s] if s in states else ()


class WorkspaceViewsTest(unittest.TestCase):
    """Test workspace-related views for product"""
    
    THEME = 'Sunburst Theme'
    
    layer = DEFAULT_PROFILE_TESTING
    
    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        alsoProvides(self.request, IQIExtranetProductLayer)
        CreateContentFixtures(self, self.layer).create()
        self.test_member = CreateContentFixtures.TEST_MEMBER
    
    def test_request_fixture(self):
        """Verify that test request fixture has layer""" 
        from uu.qiext.interfaces import IQIExtranetProductLayer as layer
        from uu.qiext.tests import test_request
        from plone.browserlayer.utils import registered_layers
        self.assertTrue(layer in registered_layers())
        self.assertTrue(layer.providedBy(test_request()))
        self.assertTrue(layer.providedBy(self.layer['request']))
    
    def test_helper(self, tabs=('membership',)):
        name = 'workspace_helper'
        tname = '@@%s' % name
        from zope.component import getMultiAdapter
        getview = lambda o: getMultiAdapter((o, self.request), name=name)
        traverseview = lambda o: o.restrictedTraverse(tname)
        for method in (getview, traverseview):
            # (1) site
            helper = method(self.portal)
            assert helper() == 'Workspace Context Helper'  # __call__()
            assert helper.workspace is None
            assert not helper.context_is_workspace_view()
            assert not helper.context_is_workspace()
            assert helper.show_tabs() == ()
            # (2) project
            project1 = self.portal.project1
            helper = method(project1)
            assert aq_base(helper.workspace) is aq_base(project1)
            assert helper.context_is_workspace()
            assert not helper.context_is_workspace_view()
            assert helper.show_tabs() == tabs
            # (3) content in project
            helper = method(project1.folder1)
            assert aq_base(helper.workspace) is aq_base(project1)
            assert not helper.context_is_workspace_view()
            assert not helper.context_is_workspace()
            assert helper.show_tabs() == ()
            # (4) default view page of a project
            helper = method(project1.welcome)
            assert aq_base(helper.workspace) is aq_base(project1)
            assert helper.context_is_workspace_view()
            assert helper.show_tabs() == tabs
    
    def test_helper_nonmanager(self):
        logout()
        login(self.portal, self.test_member)
        self.test_helper(tabs=('roster',)) 
        logout()
        login(self.portal, TEST_USER_NAME)

