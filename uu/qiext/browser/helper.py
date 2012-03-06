
from plone.app.layout.navigation.defaultpage import isDefaultPage
from zope.component import queryAdapter
from zope.interface import Interface, implements
from zope import schema
from AccessControl.SecurityManagement import getSecurityManager
from Acquisition import aq_base
from Products.CMFCore.interfaces import ISiteRoot, IContentish

from uu.qiext.interfaces import IWorkspaceContext


class IWorkspaceContextHelper(Interface):
    """
    Interface for traversable attributes of workspace context helper view.
    """
    
    workspace = schema.Object(schema=IWorkspaceContext)
    
    def context_is_workspace():
        """IS the direct context a workspace?"""
    
    def context_is_workspace_view():
        """IS the context a selected dynamic view item for workspace?"""

    def show_tabs():
        """
        Names of tabs to show; may be used by TALES condition expressions on
        actions defined in this package.
        """


class WorkspaceContextHelper(object):
    """
    View to provide auxilliary conveniences for workspace-related views.
    Accessed via @@workspace_helper or context.restrictedTraverse().
    
    This view helper should be provided for site root and any contentish
    item.
    """
    
    implements(IWorkspaceContextHelper)
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        if ISiteRoot.providedBy(context):
            self.workspace = self.secmgr = None
        elif not IContentish.providedBy(context):
            raise ValueError('View context must be site or content')
        if IWorkspaceContext.providedBy(context):
            self.workspace = self.context
        else:
            self.workspace = queryAdapter(self.context, IWorkspaceContext)
        self.secmgr = None  # too early to get security manager in ctor
    
    def context_is_workspace(self):
        """Is the context a workspace"""
        if self.workspace is None:
            return False
        return aq_base(self.context) is aq_base(self.workspace)

    def context_is_workspace_view(self):
        """Is context a selected item as view for a workspace"""
        if self.workspace is None or self.context.__parent__ != self.workspace:
            # if not directly contained within workspace, ignore:
            return False
        return isDefaultPage(container=self.workspace, obj=self.context)
    
    def show_tabs(self):
        result = []
        if self.workspace is None:
            return tuple(result)  # empty. no workspace
        if self.secmgr is None:
            self.secmgr = getSecurityManager()
        mgr = self.secmgr.checkPermission('Manage users', self.workspace)
        if self.context_is_workspace() or self.context_is_workspace_view():
            if mgr:
                result.append('membership')
            else:
                result.append('roster')
        return tuple(result)
    
    def __call__(self, *args, **kwargs):
        msg = 'Workspace Context Helper'
        self.request.response.setHeader('Content-Type', 'text/plain')
        self.request.response.setHeader('Content-Length', str(len(msg)))
        return msg

