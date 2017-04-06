import unittest2 as unittest

from collective.teamwork.interfaces import ITeamworkProductLayer
from collective.teamwork.tests.fixtures import CreateContentFixtures
from collective.teamwork.tests.layers import DEFAULT_PROFILE_TESTING
from collective.teamwork.user.interfaces import IWorkspaceRoster
from collective.teamwork.user.members import SiteMembers
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from Products.CMFPlone.utils import getToolByName
from zope.interface import alsoProvides


class WorkspaceTestBase(unittest.TestCase):
    """Base for test of workspace/workgroup related adapters and views"""

    layer = DEFAULT_PROFILE_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        alsoProvides(self.request, ITeamworkProductLayer)
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

    def _base_fixtures(self):
        """
        Simple membership, workspace, and roster fixture, for DRY reasons.
        """
        if not getattr(self, '_workspace', None):
            self._workspace = self.portal['project1']
        if not getattr(self, '_roster', None):
            self._roster = IWorkspaceRoster(self._workspace)
        return (self._workspace, self._roster)
