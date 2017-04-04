import unittest2 as unittest

from collective.teamwork.tests.layers import DEFAULT_PROFILE_TESTING
from zope.component import queryUtility

MOCK_CONFIG = {
    'forms': {
        'groupid': u'forms',
        'title': u'Form entry',
        'description': u'Form entry and submission for workspace context.',
        'roles': [u'FormEntry'],
    }
}


MOCK_KEYS = ('viewers', 'forms', 'contributors', 'managers')


class WorkgroupConfigTest(unittest.TestCase):
    """
    Test components and hooks for plugging in and managing
    workgroup types/configuration.
    """

    layer = DEFAULT_PROFILE_TESTING

    def setUp(self):
        self.portal = self.layer['portal']

    def test_core_pluggability(self):
        """Test core pluggability of workgroup configration"""
        from collective.teamwork.user.interfaces import IWorkgroupTypes
        from collective.teamwork.user.config import add_workgroup_type
        from collective.teamwork.user.config import delete_workgroup_type
        from collective.teamwork.user.config import ALL_SCOPES
        config = queryUtility(IWorkgroupTypes)
        assert len(config) == 3
        assert 'forms' not in config
        add_workgroup_type('forms', **MOCK_CONFIG.get('forms'))
        assert len(config) == 4
        assert 'forms' in config
        assert config.get('forms').get('scopes') == ALL_SCOPES
        # re-order:
        config.order = MOCK_KEYS
        assert config.keys()[1] == 'forms'
        assert tuple(config.keys()) == MOCK_KEYS
        # clean up after ourselves, and test removal:
        delete_workgroup_type('forms')
        assert len(config) == 3
        assert 'forms' not in config

