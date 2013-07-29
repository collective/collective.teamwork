import logging
import sys

from plone.app.layout.navigation.interfaces import INavigationRoot
from zope.interface import Interface

from Products.qi.extranet.types.interfaces import WORKSPACE_TYPES  # noqa


# logger for application code: logging to a default stream output
# of sys.stderr is doctest-safe, only pays attention to sys.stdout
LOG_NAME = 'collective.groupspaces'
APP_LOG = logging.getLogger(LOG_NAME)
APP_LOG.addHandler(logging.StreamHandler(sys.stderr))


class IGroupspacesProductLayer(Interface):
    """Product browser layer for collective.groupspaces"""


class IWorkspaceContext(Interface):
    """Marker for a workspace, should be identifiable by id"""

    def getId():
        """Return the string id (in local context) for object"""


class IProjectContext(IWorkspaceContext, INavigationRoot):
    """Marker for a QI project context"""


class ITeamContext(IWorkspaceContext):
    """Marker for a QI team context"""


class IWorkspaceFinder(Interface):
    """
    Adapter interface finding the workspace context for projects and
    teams, given some location being adapted.
    """

    def team():
        """
        Return containing team workspace for context or None
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

