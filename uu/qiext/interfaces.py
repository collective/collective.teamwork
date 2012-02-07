import logging
import sys

from zope.interface import Interface

from Products.qi.extranet.types.interfaces import WORKSPACE_TYPES


# logger for application code: logging to a default stream output
# of sys.stderr is doctest-safe, only pays attention to sys.stdout
LOG_NAME = 'uu.qiext'
APP_LOG = logging.getLogger(LOG_NAME)
APP_LOG.addHandler(logging.StreamHandler(sys.stderr))



class IQIExtranetProductLayer(Interface):
    """Product browser layer for uu.qiext"""


class IIdentifiableContext(Interface):
    """identifiable context base interface"""
    
    def getId():
        """Return the string id (in local context) for object"""


class IProjectContext(IIdentifiableContext):
    """Marker for a QI project context"""


class ITeamContext(IIdentifiableContext):
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

