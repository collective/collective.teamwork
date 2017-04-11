from Acquisition import aq_base

from plone.app.workflow.browser.sharing import SharingView

from collective.teamwork.interfaces import IWorkspaceContext


class SharingDirector(object):
    """
    Wrapper for Plone's sharing view, that either acts as a front for that
    view that appears identical, or issues a 302 redirect to workspace
    membership management if and only if the context of this view is either:

        1. a workspace;

        2. The default view of a workspace.

    If the context is neither, the request and response is delegated by
    wrapping the call to the OOTB Plone @@sharing view in plone.app.workflow.

    For workspaces, we override @@sharing with a wrapper:

      - GET requests redirect to @@workspace_membership, from which the
        original sharing view is available by clicking to @@advanced_sharing
        of either the workspace, or its default page (this may require
        membership view to link to both).

      - POST requests submit through wrapper to normal SharingView, this is
        because the sharing form submits to an action of @@sharing, regardless
        of how it is served.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._view = SharingView(context, request)

    def _workspace_context(self):
        """
        Returns workspace if context is workspace, or default page of one
        Otherwise returns None.
        """
        if IWorkspaceContext.providedBy(self.context):
            return self.context
        container = self.context.__parent__
        if IWorkspaceContext.providedBy(container):
            # a bit more work, check if the context is the containing
            # workspace's default page:
            default_page = getattr(aq_base(container), 'default_page', None)
            if self.context.getId() == default_page:
                return container
        return None

    def __call__(self, *args, **kwargs):
        if self.request.REQUEST_METHOD == 'GET':
            workspace = self._workspace_context()
            if workspace is not None:
                url = '/'.join(
                    (workspace.absolute_url(), '@@workspace_membership')
                    )
                return self.request.response.redirect(url)
        return self._view.__call__(*args, **kwargs)

