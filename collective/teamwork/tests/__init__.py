import unittest2 as unittest

from collective.teamwork.utils import make_request as test_request  # noqa


class PkgTest(unittest.TestCase):
    """basic unit tests for package go here"""

    def test_pkg_import(self):
        """test package import, looks like zcml-initialized zope2 product"""
        import collective.teamwork  # noqa (unused import)
        from collective.teamwork.zope2 import initialize  # noqa (unused import)
