from zope.interface import Interface


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

