
from plone.app.layout.navigation.defaultpage import isDefaultPage
from zope.annotation.interfaces import IAnnotations
from zope.component import queryAdapter
from zope.interface import Interface, implements
from zope import schema
from AccessControl.SecurityManagement import getSecurityManager
from Acquisition import aq_base
from Products.CMFCore.interfaces import IContentish

from collective.teamwork.interfaces import IWorkspaceContext


_marker = object()


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
        _WS_KEY = '_qiext_workspace_%s' % context.getId()
        self.context = context
        self.request = request
        self.secmgr = None  # too early to get security manager in ctor
        self.annotations = IAnnotations(request)
        self.workspace = self.annotations.get(_WS_KEY, _marker)
        if self.workspace is _marker:
            if not IContentish.providedBy(context):
                # site root or plone.schemaeditor.interfaces.ISchemaContext
                self.annotations[_WS_KEY] = self.workspace = None
                return
            if IWorkspaceContext.providedBy(context):
                self.annotations[_WS_KEY] = self.workspace = self.context
            else:
                self.annotations[_WS_KEY] = self.workspace = queryAdapter(
                    self.context,
                    IWorkspaceContext,
                    )

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
        _TAB_KEY = '_qiext_workspace_tabs_%s' % self.context.getId()
        result = self.annotations.get(_TAB_KEY, None)
        if result is not None:
            return result  # if already cached for request
        result = []
        if self.workspace is None:
            self.annotations[_TAB_KEY] = ()
            return tuple(result)  # empty. no workspace
        if self.secmgr is None:
            self.secmgr = getSecurityManager()
        mgr = self.secmgr.checkPermission('Manage users', self.workspace)
        if self.context_is_workspace() or self.context_is_workspace_view():
            if mgr:
                result.append('membership')
            else:
                result.append('roster')
        self.annotations[_TAB_KEY] = tuple(result)  # cache on request
        return tuple(result)

    def __call__(self, *args, **kwargs):
        msg = 'Workspace Context Helper'
        self.request.response.setHeader('Content-Type', 'text/plain')
        self.request.response.setHeader('Content-Length', str(len(msg)))
        return msg

