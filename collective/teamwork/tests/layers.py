# test layers for collective.teamwork -- requires plone.app.testing

from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting, FunctionalTesting
from zope.component.hooks import getSite


# fixture layer classes:
class ProductLayer(PloneSandboxLayer):
    """base product layer, for use by per-profile layers"""

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        """load package zcml to initialize product"""
        import z3c.form
        self.loadZCML(name='meta.zcml', package=z3c.form)
        self.loadZCML(package=z3c.form)  # needed for testing product views
        import plone.uuid
        self.loadZCML(package=plone.uuid)
        import collective.z3cform.datagridfield
        self.loadZCML(package=collective.z3cform.datagridfield)
        import uu.workflows
        self.loadZCML(package=uu.workflows)
        import collective.teamwork
        self.loadZCML(package=collective.teamwork)

    def setUpPloneSite(self, portal):
        """Install named setup profile for class to portal"""
        from Products.CMFPlone.tests.utils import MockMailHost
        from Products.MailHost.interfaces import IMailHost
        mockmail = MockMailHost('MailHost')
        portal.MailHost = mockmail
        sm = getSite().getSiteManager()
        sm.registerUtility(mockmail, provided=IMailHost)
        self.applyProfile(portal, self.PROFILE)


class DefaultProfileTestLayer(ProductLayer):
    """Layer for testing the default setup profile of the product"""

    PROFILE = 'collective.teamwork:default'


# fixture bases:
DEFAULT_PROFILE_FIXTURE = DefaultProfileTestLayer()

# layers for use by Integration tests:
DEFAULT_PROFILE_TESTING = IntegrationTesting(
    bases=(DEFAULT_PROFILE_FIXTURE,),
    name='collective.teamwork:Default Profile')

# Functional testing layers:
DEFAULT_PROFILE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(DEFAULT_PROFILE_FIXTURE,),
    name='collective.teamwork:Default Profile Functional')

