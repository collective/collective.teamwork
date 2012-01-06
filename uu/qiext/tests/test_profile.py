import unittest2 as unittest

from plone.registry.interfaces import IRegistry
from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName

from uu.qiext.tests.layers import DEFAULT_PROFILE_TESTING


class DefaultProfileTest(unittest.TestCase):
    """Test default profile's installed configuration settings"""
    
    THEME = 'Sunburst Theme'
    
    layer = DEFAULT_PROFILE_TESTING
    
    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
    
    def _product_fti_names(self):
        """ for now, test Products.qi types used by uu.qiext """
        from Products.qi.extranet.types import interfaces
        return (
            interfaces.PROJECT_TYPE,
            interfaces.TEAM_TYPE, 
            interfaces.SUBTEAM_TYPE,
            )

    def test_browserlayer(self):
        """Test product layer interfaces are registered for site"""
        from uu.qiext.interfaces import IQIExtranetProductLayer
        from Products.qi.interfaces import IQIProductLayer
        from plone.browserlayer.utils import registered_layers
        self.assertTrue(IQIExtranetProductLayer in registered_layers())
        self.assertTrue(IQIProductLayer in registered_layers())
    
    def test_ftis(self):
        types_tool = getToolByName(self.portal, 'portal_types')
        typenames = types_tool.objectIds()
        for name in self._product_fti_names():
            self.assertTrue(name in typenames)
   
    def _add_check(self, typename, id, iface, cls, title=None, parent=None):
        if parent is None:
            parent = self.portal
        if title is None:
            title = id
        if isinstance(title, str):
            title = title.decode('utf-8')
        parent.invokeFactory(typename, id, title=title)
        self.assertTrue(id in parent.contentIds())
        o = parent[id]
        self.assertTrue(isinstance(o, cls))
        self.assertTrue(iface.providedBy(o))
        o.reindexObject()
        return o # return constructed content for use in additional testing
    
    def test_skin_layer(self):
        names = ('check_id', 'project.css', 'pwreset_constructURL')
        tool = self.portal['portal_skins']
        assert 'uu_qiext' in tool
        skin = tool.getSkin(self.THEME)
        path = tool.getSkinPath(self.THEME).split(',')
        # check order in path:
        assert path[0] == 'custom' and path[1] == 'uu_qiext'
        # get known objects from skin layer and from portal:
        assert getattr(skin, 'uu.qiext.txt', None) is not None
        assert getattr(self.portal, 'uu.qiext.txt', None) is not None
        for name in names:
            assert getattr(skin, name, None) is not None
            assert getattr(self.portal, name, None) is not None
    
    def _permission_has_selected_roles(self, context, permission, roles=()):
        """Returns true if ALL roles passed are selected for permission"""
        pmap = context.rolesOfPermission(permission)
        for role in roles:
            records = [r for r in pmap if r.get('name') == role]
            if not records:
                return False
            if not bool(records[0].get('selected', None)):
                return False
        return True     # iff non-empty selected for all roles+permission
    
    def test_rolemap_installed(self):
        site_roles = self.portal.valid_roles()
        assert self._permission_has_selected_roles(
            self.portal,
            'Add portal member',
            ('Anonymous', 'Manager', 'Owner'),
            )
        for role in ('Workspace Viewer', 'Workspace Contributor'):
            assert role in site_roles
        manager_only_add = (
           'qiproject: Add Project',
           'qiproject: Add Team',
           'qiteam: Add SubTeam',
           )
        for permission in manager_only_add:
            assert self._permission_has_selected_roles(
                self.portal,
                permission,
                ('Manager',),  # Manager can add these...
                )
            # ...and only Managers, nothing else!
            assert not self._permission_has_selected_roles(
                self.portal,
                permission,
                [r for r in site_roles if r != 'Manager'], 
                )
    
    def test_role_manager_plugin_installed(self):
        from uu.qiext.user.localrole import WorkspaceLocalRoleManager as _CLS
        uf = self.portal.acl_users
        from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin
        _name = ILocalRolesPlugin.__name__
        lr_plugins = dict(uf.plugins.listPlugins(ILocalRolesPlugin))
        assert 'enhanced_localroles' in lr_plugins
        assert isinstance(uf['enhanced_localroles'], _CLS)
        active_plugins = uf.plugins.getAllPlugins(_name)['active']
        assert 'borg_localroles' not in active_plugins  # replaced by:
        assert 'enhanced_localroles' in active_plugins

