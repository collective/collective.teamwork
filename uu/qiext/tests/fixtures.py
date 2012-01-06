# content fixtures shared across tests -- multi-adapter component 
# adapts test-suite and test layer

from Products.qi.extranet.types.interfaces import IProject, ITeam
from Products.qi.extranet.types.project import Project
from Products.qi.extranet.types.team import Team


class CreateContentFixtures(object):
    """
    Create fixtures shared per layer, but since this stuff is persistent,
    we only want it once... whichever test suite calls this first will
    create the content, others will rely on that as given.
    """
    def __init__(self, context, layer):
        self.context = context #suite
        self.layer = layer
        self.portal = self.layer['portal']
        self.layer.fixtures_completed = False  # create() only once per layer
    
    def _add_check(self, typename, id, iface, cls, title=None, parent=None):
        if parent is None:
            parent = self.portal
        if title is None:
            title = id
        if isinstance(title, str):
            title = title.decode('utf-8')
        parent.invokeFactory(typename, id, title=title)
        self.context.assertTrue(id in parent.contentIds())
        o = parent[id]
        self.context.assertTrue(isinstance(o, cls))
        self.context.assertTrue(iface.providedBy(o))
        o.reindexObject()
        return o # return constructed content for use in additional testing

    def _add_project(self, id, title=None):
        return self._add_check('qiproject', id, IProject, Project)

    def _add_team_to(self, parent, id, title=None):
        return self._add_check('qiteam', id, ITeam, Team, parent=parent)

    def create(self):
        """
        project1/
        project1/team1/
        project1/team1/stuff    (folder)
        project1/team2
        project1/folder1        (folder)
        otherstuff/             (folder)
        """
        if self.layer.fixtures_completed:
            return # run once, already run
        portal = self.portal
        project = self._add_project('project1')
        team1 = self._add_team_to(project, 'team1')
        team1.invokeFactory('Folder', 'stuff', title='Normal folder')
        team2 = self._add_team_to(project, 'team2')
        project.invokeFactory('Folder', 'folder1', title='Normal folder')
        portal.invokeFactory('Folder', 'otherstuff', title='Not in project')
        self.layer.fixtures_completed = True

