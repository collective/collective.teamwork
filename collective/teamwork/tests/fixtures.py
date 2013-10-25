# content fixtures shared across tests -- multi-adapter component
# adapts test-suite and test layer

from plone.app.layout.navigation.defaultpage import isDefaultPage
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.utils import createContent
from Products.CMFCore.utils import getToolByName
import transaction

from collective.teamwork.content.interfaces import IProject, IWorkspace
from collective.teamwork.content.interfaces import PROJECT_TYPE
from collective.teamwork.content import Project
from collective.teamwork.content import Workspace

from collective.teamwork.user.interfaces import ISiteMembers, IWorkspaceRoster


class CreateContentFixtures(object):
    """
    Create fixtures shared per layer, but since this stuff is persistent,
    we only want it once... whichever test suite calls this first will
    create the content, others will rely on that as given.
    """

    TEST_MEMBER = 'me@example.com'

    def __init__(self, context, layer):
        self.context = context  # suite
        self.layer = layer
        self.portal = self.layer['portal']
        if not hasattr(self.layer, 'fixtures_completed'):
            self.layer.fixtures_completed = False  # create() only once/layer

    def add_content(self, typename, name, parent, **kwargs):
        kwargs['title'] = kwargs.get('title', name)
        tool = getToolByName(self.portal, 'portal_types')
        fti = tool.getTypeInfo(typename)
        if IDexterityFTI.providedBy(fti):
            o = createContent(
                typename,
                **kwargs
                )
            o.id = name
            parent._setObject(name, o)
        else:
            parent.invokeFactory(typename, name)
        o = parent[name]
        o.setTitle(kwargs.get('title'))
        o.reindexObject()
        return o

    def add_check(self, typename, name, iface, cls, parent=None, **kwargs):
        if parent is None:
            parent = self.portal
        o = self.add_content(typename, name, parent, **kwargs)
        self.context.assertTrue(name in parent.contentIds())
        self.context.assertTrue(isinstance(o, cls))
        self.context.assertTrue(iface.providedBy(o))
        return o  # return constructed content for use in additional testing

    def add_project(self, id, title=None):
        project = self.add_check(PROJECT_TYPE, id, IProject, Project)
        members = ISiteMembers(self.portal)
        if self.TEST_MEMBER not in members:
            members.register(self.TEST_MEMBER, send=False)
        assert self.TEST_MEMBER in members
        roster = IWorkspaceRoster(project)
        roster.add(self.TEST_MEMBER)
        assert self.TEST_MEMBER in roster
        return project

    def add_workspace_to(self, parent, id, title=None):
        return self.add_check(
            'collective.teamwork.workspace',
            id,
            IWorkspace,
            Workspace,
            parent=parent,
            )

    def create(self):
        """
        project1/
        project1/welcome        (page set as default page for project)
        project1/team1/
        project1/team1/stuff    (folder)
        project1/team2
        project1/folder1        (folder)
        otherstuff/             (folder)
        """
        if self.layer.fixtures_completed:
            return  # run once, already run
        project = self.add_project('project1')
        welcome = self.add_content(
            'Document',
            'welcome',
            title='Welcome',
            parent=project,
            )
        project.default_page = 'welcome'
        assert isDefaultPage(container=project, obj=welcome)
        team1 = self.add_workspace_to(project, 'team1')
        self.add_content('Folder', 'stuff', title='Folder A', parent=team1)
        team2 = self.add_workspace_to(project, 'team2')  # noqa
        self.add_content('Folder', 'folder1', title='Folder1', parent=project)
        assert 'folder1' in project.contentIds()
        self.add_content(
            'Folder',
            'otherstuff',
            title='not in project',
            parent=self.portal,
            )
        transaction.get().commit()
        self.layer.fixtures_completed = True

