import unittest as unittest

from Acquisition import aq_base
from plone.app.testing import TEST_USER_ID, setRoles

from collective.teamwork.tests.layers import DEFAULT_PROFILE_TESTING
from collective.teamwork.interfaces import IProjectContext, IWorkspaceContext

from fixtures import CreateContentFixtures


class UtilityTest(unittest.TestCase):
    """
    Test functions of collective.teamwork.utils
    """

    layer = DEFAULT_PROFILE_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        CreateContentFixtures(self, self.layer).create()

    def same(self, a, b):
        return aq_base(a) is aq_base(b)

    def test_get_projects(self):
        from collective.teamwork.utils import get_projects, get_workspaces
        from zope.component.hooks import getSite
        assert self.same(getSite(), self.portal)
        assert len(get_projects()) < len(get_workspaces())
        assert len(get_projects()) == len(get_projects(self.portal))
        assert len(get_projects()) == 2
        isproject = lambda o: IProjectContext.providedBy(o)
        for project in get_projects():
            assert isproject(project)
        found = get_projects()
        for project in filter(isproject, self.portal.objectValues()):
            assert project in found

    def test_get_workspaces(self):
        from collective.teamwork.utils import get_workspaces
        project1 = self.portal['project1']
        # test without context, without site
        workspaces = get_workspaces()
        assert len(workspaces) == 5
        # test sort order, items closest to root first
        assert self.same(workspaces[0], project1)
        assert all(
            map(lambda o: IWorkspaceContext.providedBy(o), workspaces)
            )
        # after first two workspaces, remainder are not projects
        assert all(
            map(lambda o: not IProjectContext.providedBy(o), workspaces[2:])
            )
        _path = lambda o: o.getPhysicalPath()
        assert len(_path(workspaces[2])) > len(_path(workspaces[0]))
        # test without context, passing site
        found = get_workspaces()
        assert len(found) == len(workspaces)
        for workspace in found:
            assert workspace in workspaces
        # test with context
        contained_workspaces = get_workspaces(project1)
        assert len(contained_workspaces) == 3

    def test_project_for(self):
        from collective.teamwork.utils import project_for
        path = 'project1/team1/stuff'
        content = self.portal.unrestrictedTraverse(path)
        project_expected = self.portal['project1']
        assert self.same(project_for(content), project_expected)
        assert self.same(IProjectContext(content), project_expected)

    def test_workspace_for(self):
        from collective.teamwork.utils import workspace_for
        path = 'project1/team1/stuff'
        content = self.portal.unrestrictedTraverse(path)
        workspace_expected = self.portal['project1']['team1']
        assert self.same(workspace_for(content), workspace_expected)
        assert self.same(IWorkspaceContext(content), workspace_expected)

    def test_parent_workspaces(self):
        from collective.teamwork.utils import parent_workspaces
        path = 'project1/team1/stuff'
        content = self.portal.unrestrictedTraverse(path)
        project_expected = self.portal['project1']
        workspace_expected = project_expected['team1']
        parents = parent_workspaces(content)
        assert len(parents) == 2
        assert self.same(parents[-1], workspace_expected)
        assert self.same(parents[-2], project_expected)

    def test_utility_view(self):
        from collective.teamwork.utils import make_request
        from collective.teamwork.utils import WorkspaceUtilityView
        from collective.teamwork.utils import workspace_for, project_for
        request = make_request()
        path = 'project1/team1/stuff'
        content = self.portal.unrestrictedTraverse(path)
        view = WorkspaceUtilityView(content, request)
        assert isinstance(view(), str)  # calling returns string label
        assert self.same(view.workspace(), workspace_for(content))
        assert self.same(view.workspace(), IWorkspaceContext(content))
        assert self.same(view.project(), project_for(content))
        assert self.same(view.project(), IProjectContext(content))

