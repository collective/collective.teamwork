# test layers for uu.qiext -- requires plone.app.testing

from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting, FunctionalTesting
from plone.testing import z2
from zope.configuration import xmlconfig


# fixture layer classes:
class ProductLayer(PloneSandboxLayer):
    """base product layer, for use by per-profile layers"""

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        """load package zcml to initialize product"""
        import z3c.form
        self.loadZCML(name='meta.zcml', package=z3c.form)
        self.loadZCML(package=z3c.form) # needed for testing product views
        import plone.uuid
        self.loadZCML(package=plone.uuid)
        import collective.z3cform.datagridfield
        self.loadZCML(package=collective.z3cform.datagridfield)
        import Products.qi
        self.loadZCML(package=Products.qi)
        self.loadZCML(name='overrides.zcml', package=Products.qi)
        import uu.qiext
        self.loadZCML(package=uu.qiext)
    
    def setUpPloneSite(self, portal):
        """Install named setup profile for class to portal"""
        self.applyProfile(portal, self.PROFILE)


class DefaultProfileTestLayer(ProductLayer):
    """Layer for testing the default setup profile of the product"""
    
    PROFILE = 'uu.qiext:default'


# fixture bases:
DEFAULT_PROFILE_FIXTURE = DefaultProfileTestLayer()

# layers for use by Integration tests:
DEFAULT_PROFILE_TESTING = IntegrationTesting(
    bases=(DEFAULT_PROFILE_FIXTURE,),
    name='uu.qiext:Default Profile')

# Functional testing layers:
DEFAULT_PROFILE_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(DEFAULT_PROFILE_FIXTURE,),
    name='uu.qiext:Default Profile Functional')

