import logging
import sys

from plone.app.layout.navigation.interfaces import INavigationRoot
from zope.interface import Interface


PROJECT_TYPE = 'collective.teamwork.project'
WORKSPACE_TYPE = 'collective.teamwork.workspace'
TEAM_WORKSPACE_TYPE = 'collective.teamwork.team'  # team alias for workspace

# queryable workspace types, can be extended by add-ons:
WORKSPACE_TYPES = [PROJECT_TYPE, WORKSPACE_TYPE, TEAM_WORKSPACE_TYPE]


# logger for application code: logging to a default stream output
# of sys.stderr is doctest-safe, only pays attention to sys.stdout
LOG_NAME = 'collective.teamwork'
APP_LOG = logging.getLogger(LOG_NAME)
APP_LOG.addHandler(logging.StreamHandler(sys.stderr))


class ITeamworkProductLayer(Interface):
    """Product browser layer for collective.teamwork"""


class IWorkspaceContext(Interface):
    """Marker for a workspace, should be identifiable by id"""

    def getId():
        """Return the string id (in local context) for object"""


class IProjectContext(IWorkspaceContext, INavigationRoot):
    """
    Marker for a top-level workspace / project context that is
    also, always a navigation root.
    """


class IWorkspaceFinder(Interface):
    """
    Adapter interface finding the workspace context for projects and
    workspaces, given some content within being adapted.
    """

    def project():
        """
        Return containing project workspace for context or None
        """

    def workspace():
        """
        Return containing project or team workspace for context or None.
        If there is a team context, return that in preference to outer
        containing project.
        """

