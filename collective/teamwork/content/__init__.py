from plone.dexterity.content import Container
from zope.interface import implements

from interfaces import IWorkspace, IProject


class Workspace(Container):
    """Core workspace class"""

    implements(IWorkspace)

    portal_type = 'collective.teamwork.workspace'


class Project(Workspace):
    """Project workspace is also navigation root"""
    implements(IProject)

    portal_type = 'collective.teamwork.project'
