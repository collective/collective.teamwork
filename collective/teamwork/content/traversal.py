from Acquisition import aq_base
from zope.component import adapts
from zope.publisher.interfaces.browser import IBrowserRequest
from plone.dexterity.browser.traversal import DexterityPublishTraverse

from interfaces import IWorkspace


class WorkspacePublishTraverse(DexterityPublishTraverse):
    """
    Work-around https://dev.plone.org/ticket/14266 -- favor
    contained content versus attributes for traversal.
    """

    adapts(IWorkspace, IBrowserRequest)

    def publishTraverse(self, request, name):
        marker = object()
        attr_v = getattr(aq_base(self.context), name, marker)
        if attr_v is not marker and name in self.context.objectIds():
            # collision, only in this case favor the content:
            return self.context.get(name)
        # otherwise, no collision means business as usual:
        default = super(WorkspacePublishTraverse, self).publishTraverse
        return default(request, name)

