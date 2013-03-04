from Products.ATContentTypes.content.schemata import ATContentTypeSchema
from Products.ATContentTypes.criteria.path import ATPathCriterionSchema


def patch_atct_copyrefs():
    """
    Works around ATCT bug on copy/paste:
        https://dev.plone.org/ticket/9919
    """
    ATContentTypeSchema['relatedItems'].keepReferencesOnCopy = True
    ATPathCriterionSchema['value'].keepReferencesOnCopy = True

