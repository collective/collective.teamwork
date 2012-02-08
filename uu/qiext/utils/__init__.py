from datetime import datetime
import sys

import pytz
from zope.component.hooks import getSite
from zope.publisher.browser import setDefaultSkin
from zope.interface import alsoProvides, implements
from z3c.form.interfaces import IFormLayer
from Acquisition import aq_base
from Products.CMFCore.utils import getToolByName
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.HTTPRequest import HTTPRequest

from uu.qiext.interfaces import WORKSPACE_TYPES, IWorkspaceFinder


def fake_request():
    """ 
    make request suitable for browser views and Zope2 security.
    """
    response = HTTPResponse(stdout=sys.stdout)
    request = HTTPRequest(sys.stdin,
                      {'SERVER_NAME'    : 'localhost',
                       'SERVER_PORT'    : '80',
                       'REQUEST_METHOD' : 'GET', },
                      response)
    setDefaultSkin(request)
    alsoProvides(request, IFormLayer) #suitable for testing z3c.form views
    return request


def request_for(context):
    r = getattr(context, 'REQUEST', None)
    if isinstance(r, str) or r is None:
        return fake_request()  # could not acquire REQUEST
    return r


def _all_the_things(context, portal_type):
    site = getSite()
    query = {'portal_type': portal_type}
    if context is not site:
        query.extend({'path': '/'.join(context.getPhysicalPath())})
    r = site.portal_catalog.search(query)
    return [b._unrestrictedGetObject() for b in r]


def all_projects(site):
    """return all projects in site, found via catalog query"""
    return _all_the_things(site, portal_type='qiproject')


def all_teams(context):
    """
    return all projects for site or arbitrary context,
    found via catalog query.
    """
    return _all_the_things(context, portal_type='qiteam')


def group_workspace(groupname):
    portal = getSite()
    r = portal.portal_catalog.search({'pas_groups':groupname})
    if not r:
        return None
    return r[0]._unrestrictedGetObject()


def find_parents(context, typename=None, findone=False, start_depth=2):
    if findone and typename is None:
        parent = getattr(context, '__parent__', None)
        if parent:
            return parent   # immediate parent of context
    result = []
    catalog = getToolByName(context, 'portal_catalog')
    path = context.getPhysicalPath()
    for subpath in [path[0:i] for i in range(len(path) + 1)][start_depth:]:
        query = {
            'path': {
                'query': '/'.join(subpath),
                'depth': 0,
                },
            'portal_type': typename,
            }
        if typename is None:
            del(query['portal_type'])
        brains = catalog.search(query)
        if not brains:
            continue
        else:
            item = brains[0]._unrestrictedGetObject()
            if aq_base(item) is aq_base(context):
                continue # don't return or append the context itself!
            if findone:
                return item
            result.append(item)
    if findone:
        return None     # never found one
    return result


def find_parent(context, typename=None, start_depth=2):
    return find_parents(
        context,
        typename,
        findone=True,
        start_depth=start_depth,
        )


def project_containing(context):
    return find_parent(context, typename='qiproject')


def workspace_containing(context):
    subteam = find_parent(context, typename='qisubteam', start_depth=3)
    if subteam:
        return subteam
    team = find_parent(context, typename='qiteam', start_depth=3)
    if team:
        return team
    return project_containing(context)  # fallback


def getProjectsInContext(context):
    catalog = getToolByName(context, 'portal_catalog')
    path = '/'.join(context.getPhysicalPath())
    query = {
        'path': {
            'query': path,
            'depth': 2
            },
        'portal_type': 'qiproject',
        }
    return [b._unrestrictedGetObject() for b in catalog.search(query)]


def getTeamsInContext(context):
    catalog = getToolByName(context, 'portal_catalog')
    path = '/'.join(context.getPhysicalPath())
    query = {
        'path': {
            'query': path,
            'depth': 2
            },
        'portal_type': 'qiteam',
        }
    return [b._unrestrictedGetObject() for b in catalog.search(query)]


class WorkspaceUtilityView(object):
    """
    Workspace utility view: view or adapter for content context in
    a Plone site to get team or project workspace context.
    """
    
    implements(IWorkspaceFinder)
    
    def __init__(self, context, request=None):
        self.context = context
        self.request = request
    
    def __call__(self, *args, **kwargs):
        content = "Workspace utility view"
        response = self.request.response
        response.setHeader('Content-type', 'text/plain')
        response.setHeader('Content-Length', len(content))
        return content
    
    def workspace(self):
        """get most immediate workspace containing or None"""
        return workspace_containing(self.context)        # may be None
    
    def project(self):
        """get project containing or None"""
        return project_containing(self.context)     # may be None


def contained_workspaces(context):
    """
    Return a tuple for the chain of workspace items somewhere
    contained, either directly or indirectly, inside the context.
    Order of chain is left-to-right in path.
    """
    _sortkey = lambda o:len(o.getPhysicalPath())
    result = set()
    for fti_name in WORKSPACE_TYPES:
        result = result.union(_all_the_things(context, fti_name))
    return tuple(sorted(result, key=_sortkey, reverse=True))


def containing_workspaces(context):
    """
    Return a tuple for the chain of workspace items containing the
    context -- each must be a direct ancestor of the context. Order
    of chain is top-to-bottom (left-to-right in path).
    """
    _sortkey = lambda o:len(o.getPhysicalPath())
    result = set()
    for fti_name in WORKSPACE_TYPES:
        result = result.union(
            find_parents(context, fti_name, start_depth=1)
            )
    return tuple(sorted(result, key=_sortkey))

