from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.HTTPRequest import HTTPRequest
from zope.publisher.browser import setDefaultSkin
from zope.interface import alsoProvides
from z3c.form.interfaces import IFormLayer


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

