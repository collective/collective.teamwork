from zope.app.component.hooks import getSite
from zope.publisher.browser import setDefaultSkin
from zope.interface import alsoProvides
from z3c.form.interfaces import IFormLayer
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.HTTPRequest import HTTPRequest


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
    return getattr(context, 'REQUEST', fake_request())


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

