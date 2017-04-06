import unittest2 as unittest

from lxml import etree
from lxml.html import HTMLParser
from plone.app.testing import TEST_USER_ID, TEST_USER_NAME, TEST_USER_PASSWORD
from plone.app.testing import setRoles, login, logout
from plone.testing.z2 import Browser
from Acquisition import aq_base

from collective.teamwork.tests.base import WorkspaceTestBase
from collective.teamwork.tests.fixtures import CreateContentFixtures

from layers import DEFAULT_PROFILE_FUNCTIONAL_TESTING
from layers import TEAM_PROFILE_FUNCTIONAL_TESTING

_tmap = lambda states, s: states[s] if s in states else ()


class WorkspaceViewsTest(WorkspaceTestBase):
    """Test workspace-related views for product"""

    def test_request_fixture(self):
        """Verify that test request fixture has layer"""
        from collective.teamwork.interfaces import ITeamworkProductLayer
        from collective.teamwork.tests import test_request
        from plone.browserlayer.utils import registered_layers
        layer = ITeamworkProductLayer
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


class WorkspaceViewTemplateTest(unittest.TestCase):
    """Test workspace-related view template rendering"""

    layer = DEFAULT_PROFILE_FUNCTIONAL_TESTING

    # expected values:
    PROJECTLABEL = 'project'
    WORKSPACELABEL = 'workspace'
    TEAMLABEL = 'team'

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        CreateContentFixtures(self, self.layer).create()
        import transaction
        transaction.get().commit()
        #login(self.portal, TEST_USER_NAME)
        self.browser = Browser(self.layer['app'])
        self.portal_url = 'http://nohost/plone'
        if not getattr(self, 'logged_in', False):
            self.login()

    def login(self):
        _get = self.browser.getControl
        self.browser.open(self.portal_url + '/login_form')
        _get(name='__ac_name').value = TEST_USER_NAME
        _get(name='__ac_password').value = TEST_USER_PASSWORD
        _get(name='submit').click()
        self.logged_in = True
        self.browser.handleErrors = False

    def get(self, url, html=False):
        self.browser.open(url)
        if html:
            return etree.fromstring(self.browser.contents, parser=HTMLParser())
        return self.browser.contents

    def _test_membership_type_title(self, url, expected_label):
        _match = lambda e: e.text and e.text.strip().lower() == expected_label
        doc = self.get(url, html=True)
        assert doc is not None
        elements = doc.find_class('type_title')
        self.assertEqual(len(elements), 13)
        self.assertTrue(all(map(_match, elements)))

    def test_membership_workspace_title(self):
        workspace_label = {
            DEFAULT_PROFILE_FUNCTIONAL_TESTING: self.WORKSPACELABEL,
            TEAM_PROFILE_FUNCTIONAL_TESTING: self.TEAMLABEL,
        }[self.layer]
        spec = (
            ('project1', self.PROJECTLABEL),
            ('project1/team1', workspace_label),
            )
        # test expected type_title labels in template for project, workspace
        for path, label in spec:
            url = '/'.join((self.portal_url, path, '@@workspace_membership'))
            self._test_membership_type_title(url, label)


class WorkspaceViewTeamTemplateTest(WorkspaceViewTemplateTest):

    layer = TEAM_PROFILE_FUNCTIONAL_TESTING

    TEAMLABEL = 'team'

