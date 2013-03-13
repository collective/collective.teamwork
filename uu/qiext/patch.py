from plone.app.layout.navigation.root import getNavigationRoot
from Products.ATContentTypes.content.schemata import ATContentTypeSchema
from Products.ATContentTypes.content.topic import ATTopic
from Products.ATContentTypes.criteria.path import ATPathCriterionSchema


def patch_atct_copyrefs():
    """
    Works around ATCT bug on copy/paste:
        https://dev.plone.org/ticket/9919
    """
    ATContentTypeSchema['relatedItems'].keepReferencesOnCopy = True
    ATPathCriterionSchema['value'].keepReferencesOnCopy = True


def patch_atct_buildquery():
    """
    ATTopic does not filter to navigation root when no location
    criterion is provided, this is a problem for isolating
    project workspaces from content of other workspaces.
    
    This is monkey-patched instead of fixed upstream because
    ATTopic is officially deprecated, and plone.app.collection,
    which may later fully replace it already respects nav roots.
    """
    # ref to original unpatched ATTopic.buildQuery() method:
    orig_buildQuery_method = ATTopic.buildQuery

    # wrapper method injects navroot path when no path:
    def buildQuery(self):
        """monkey patch wrapper injects navroot path when path is missing"""
        q = orig_buildQuery_method(self)
        if 'path' not in q:
            navroot_path = getNavigationRoot(self)
            q['path'] = navroot_path
        return q

    # apply the monkey patch:
    ATTopic.buildQuery = buildQuery

