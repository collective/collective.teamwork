import sys
import unittest2 as unittest

from zope.interface import alsoProvides
from zope.publisher.browser import setDefaultSkin
from z3c.form.interfaces import IFormLayer
from ZPublisher.HTTPResponse import HTTPResponse
from ZPublisher.HTTPRequest import HTTPRequest

from collective.groupspaces.interfaces import IGroupspacesProductLayer


class PkgTest(unittest.TestCase):
    """basic unit tests for package go here"""

    def test_pkg_import(self):
        """test package import, looks like zcml-initialized zope2 product"""
        import collective.groupspaces  # noqa (unused import)
        from collective.groupspaces.zope2 import initialize  # noqa (unused import)


def test_request():
    """
    make request suitable for browser views and Zope2 security.
    """
    response = HTTPResponse(stdout=sys.stdout)
    request = HTTPRequest(
        sys.stdin,
        {
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'REQUEST_METHOD': 'GET',
        },
        response,
        )
    request['ACTUAL_URL'] = 'http://nohost/plone/myform'
    setDefaultSkin(request)
    alsoProvides(request, IFormLayer)  # suitable for testing z3c.form views
    alsoProvides(request, IGroupspacesProductLayer)  # product layer
    return request

