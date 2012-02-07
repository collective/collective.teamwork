from itertools import chain
import unittest2 as unittest

from plone.registry.interfaces import IRegistry
from plone.app.testing import TEST_USER_ID, setRoles
from Products.CMFPlone.utils import getToolByName

from uu.qiext.tests.layers import DEFAULT_PROFILE_TESTING


_tmap = lambda states, s: states[s] if s in states else ()


class DefaultProfileTest(unittest.TestCase):
    """Test default profile's installed configuration settings"""
    
    THEME = 'Sunburst Theme'
    
    layer = DEFAULT_PROFILE_TESTING
    
    def setUp(self):
        self.portal = self.layer['portal']
        self.wftool = getToolByName(self.portal, 'portal_workflow')
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
    
    def _product_fti_names(self):
        """ for now, test Products.qi types used by uu.qiext """
        from Products.qi.extranet.types import interfaces
        return (
            interfaces.PROJECT_TYPE,
            interfaces.TEAM_TYPE, 
            interfaces.SUBTEAM_TYPE,
            )
    
    def test_interfaces(self):
        """Test any interface bindings configured on content"""
        ## these are markers hooked up to Products.qi types in 
        ## configure.zcml for uu.qiext:
        from Products.qi.extranet.types import project, team, subteam
        from uu.qiext.interfaces import IWorkspaceContext
        from uu.qiext.interfaces import IProjectContext, ITeamContext
        assert IWorkspaceContext.providedBy(project.Project('project'))
        assert IWorkspaceContext.providedBy(team.Team('team'))
        assert IWorkspaceContext.providedBy(subteam.SubTeam('subteam'))
        assert IProjectContext.providedBy(project.Project('project'))
        assert ITeamContext.providedBy(team.Team('team'))
        assert ITeamContext.providedBy(subteam.SubTeam('subteam'))
    
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
   
    def test_content_creation(self):
        from uu.qiext.tests.fixtures import CreateContentFixtures
        CreateContentFixtures(self, self.layer).create()
     
    def test_skin_layer(self):
        names = ('check_id', 'project.css', 'pwreset_constructURL')
        tool = self.portal['portal_skins']
        self.assertTrue('uu_qiext' in tool)
        skin = tool.getSkin(self.THEME)
        path = tool.getSkinPath(self.THEME).split(',')
        # check order in path:
        self.assertEqual(path[0], 'custom')
        self.assertEqual(path[1], 'uu_qiext')
        # get known objects from skin layer and from portal:
        self.assertTrue(getattr(skin, 'uu.qiext.txt', None) is not None)
        self.assertTrue(getattr(self.portal, 'uu.qiext.txt', None) is not None)
        for name in names:
            self.assertTrue(getattr(skin, name, None) is not None)
            self.assertTrue(getattr(self.portal, name, None) is not None)
    
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
        self.assertTrue(self._permission_has_selected_roles(
            self.portal,
            'Add portal member',
            ('Anonymous', 'Manager', 'Owner'),
            ))
        for role in ('Workspace Viewer', 'Workspace Contributor'):
            self.assertTrue(role in site_roles)
        manager_only_add = (
           'qiproject: Add Project',
           'qiproject: Add Team',
           'qiteam: Add SubTeam',
           )
        for permission in manager_only_add:
            self.assertTrue(self._permission_has_selected_roles(
                self.portal,
                permission,
                ('Manager',),  # Manager can add these...
                ))
            # ...and only Managers, nothing else!
            self.assertTrue(not self._permission_has_selected_roles(
                self.portal,
                permission,
                [r for r in site_roles if r != 'Manager'], 
                ))
    
    def test_role_manager_plugin_installed(self):
        from uu.qiext.user.localrole import WorkspaceLocalRoleManager as _CLS
        uf = self.portal.acl_users
        from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin
        _name = ILocalRolesPlugin.__name__
        lr_plugins = dict(uf.plugins.listPlugins(ILocalRolesPlugin))
        self.assertTrue('enhanced_localroles' in lr_plugins)
        self.assertTrue(isinstance(uf['enhanced_localroles'], _CLS))
        active_plugins = uf.plugins.getAllPlugins(_name)['active']
        self.assertTrue('borg_localroles' not in active_plugins)  # replaced by:
        self.assertTrue('enhanced_localroles' in active_plugins)
    
    def test_catalog_indexes(self):
        ct = self.portal.portal_catalog
        self.assertTrue('pas_groups' in ct.indexes())

    ## workflow testing: 
    def test_workspace_workflow_chain(self):
        defn_id = 'qiext_workspace_workflow'
        self.assertEqual(self.wftool.getDefaultChain(), (defn_id,))
        for ptype in ('Document', 'Link'):
            # reasonable sample of stock types
            wfchain = self.wftool.getChainForPortalType(ptype)
            self.assertEqual(wfchain, (defn_id,), 'type %s unexpected chain' % ptype)
    
    def test_project_workflow_chain(self):
        defn_id = 'qiext_project_workflow'
        self.assertNotEqual(self.wftool.getDefaultChain(), (defn_id,))
        wfchain = self.wftool.getChainForPortalType('qiproject')
        self.assertEqual(wfchain, (defn_id,), 'qiproject type: unexpected chain')
    
    def _compare_dfa(self, defn, states):
        """
        Given workflow definition object defn, assert that the DFA it
        provides matches the transition function description mapping
        provided in states, where states is:
          * a dict with:
            * state-name keys;
            * tuple/sequence values of two item tuples:
                (1) a transition name;
                (2) name of destination state or None if no state change.
        """
        # get all transitions from delta table:
        transitions = set(chain(*[(k for k,v in t) for t in states.values()]))
        # create transition function from delta table (get destination state):
        _d = lambda s,t: ([v for k,v in _tmap(states, s) if k==t] or [None])[0]
        for statename, tr in states.items():
            sdef = defn.states.get(statename)
            sdef_transitions = sdef.getTransitions()
            for tname, destination in tr:
                tdef = defn.transitions.get(tname)
                # the transition name is in the list of available transitions
                # for the source state: 
                self.assertIn(tname, sdef_transitions)
                # the destination state asserted in the delta table matches
                # the destination state queried from the workflow definition
                # for this transition:
                expected_destination = _d(statename, tname) or ''
                self.assertEqual(expected_destination, tdef.new_state_id)
     
    def test_workspace_workflow_defn(self):
        defn_id = 'qiext_workspace_workflow'
        defn = self.wftool[defn_id]
        self.assertEqual(defn.state_var, 'review_state') # standard plone name
        # transition function description (delta table) of wf def'n DFA
        # expresed as a dict of present-state keys to a sequence of 
        # two-items tuples: possible transitions and respective destination
        # state or None (indicating stay-in-state):
        states = {
            'private'               : (
                    ('share', 'visible'),
                    ('restrict', 'restricted'),
                    ('log', None), # stays in state
                ),
            'published'             :   (
                    ('archive', 'archived'),
                    ('return_for_editing', 'visible'),
                    ('log', None), # stays in state
                ),
            'restricted'            :   (
                    ('share', 'visible'),
                    ('make_private', 'private'),
                    ('log', None), # stays in state
                ),
            'visible'               :   (
                    ('submit', 'pending'),
                    ('make_private', 'private'),
                    ('restrict', 'restricted'),
                    ('collaborate', 'collaborative_editing'),
                    ('archive', 'archived'),
                    ('publish', 'published'),
                    ('log', None), # stays in state
                ),
            'pending'               :   (
                    ('reject', 'visible'),
                    ('retract', 'visible'),
                    ('archive', 'archived'),
                    ('publish', 'published'),
                    ('log', None), # stays in state
                ),
            'archived'              :   (
                    ('return_for_editing', 'visible'),
                    ('publish', 'published'),
                    ('log', None), # stays in state
                ),
            'collaborative_editing' :   (
                    ('end_collaboration', 'visible'),
                    ('log', None), # stays in state
                ),
            }
        start_state = 'visible'
        self.assertEqual(defn.initial_state, start_state)
        self._compare_dfa(defn, states)
    
    def test_project_workflow_defn(self):
        defn_id = 'qiext_project_workflow'
        defn = self.wftool[defn_id]
        self.assertEqual(defn.state_var, 'review_state') # standard plone name
        # transition function description (delta table) of wf def'n DFA
        # expresed as a dict of present-state keys to a sequence of 
        # two-items tuples: possible transitions and respective destination
        # state or None (indicating stay-in-state):
        states = {
            'private'               : (
                    ('share', 'visible'),
                    ('restrict', 'restricted'),
                    ('log', None), # stays in state
                ),
            'published'             :   (
                    ('restrict_to_project', 'visible'),
                    ('log', None), # stays in state
                ),
            'restricted'            :   (
                    ('share', 'visible'),
                    ('make_private', 'private'),
                    ('log', None), # stays in state
                ),
            'visible'               :   (
                    ('make_private', 'private'),
                    ('restrict', 'restricted'),
                    ('publish', 'published'),
                    ('log', None), # stays in state
                ),
            }
        start_state = 'visible'
        self.assertEqual(defn.initial_state, start_state)
        self._compare_dfa(defn, states)
    
    def test_workspace_workflow_content(self):
        """
        test workspace workflow bound to content with visits to each state.
        """
        defn_id = 'qiext_workspace_workflow'
        CONTENT_ID = 'mydoc_workspace_workflow'
        self.portal.invokeFactory('Document', id=CONTENT_ID)
        content = self.portal[CONTENT_ID]
        self.assertEqual(self.wftool.getChainFor(content), (defn_id,))
        # initial state looks cool:
        _state = lambda o: self.wftool.getStatusOf(defn_id, o)['review_state']
        self.assertEqual(_state(content), 'visible')  # initial state
        _actions = lambda o: self.wftool.listActions(object=o)
        # visit all states via transitions legal to the admin user -- this
        # does not ATTEMPT transitions available, but it does check that they
        # are available from each state.  Nor does this attempt to deal with
        # transitions hidden to other users using guard conditions.
        # the 'log' transition is deliberately ignored here.
        visible_transitions = (
            'publish',
            'archive',
            'make_private',
            'restrict',
            'submit',
            )
        for tname in visible_transitions:
            self.assertTrue(tname in [r['id'] for r in _actions(content)])
        self.wftool.doActionFor(content, 'submit')
        self.assertEqual(_state(content), 'pending')
        pending_transitions = (
            'archive',
            'publish',
            'reject',
            'retract',
            )
        for tname in pending_transitions:
            self.assertTrue(tname in [r['id'] for r in _actions(content)])
        self.wftool.doActionFor(content, 'publish')
        self.assertEqual(_state(content), 'published')
        published_transitions = (
            'archive',
            'return_for_editing',
            )
        for tname in published_transitions:
            self.assertTrue(tname in [r['id'] for r in _actions(content)])
        published_transitions = (
            'archive',
            'return_for_editing',
            )
        for tname in published_transitions:
            self.assertTrue(tname in [r['id'] for r in _actions(content)])
        
        self.wftool.doActionFor(content, 'archive')
        self.assertEqual(_state(content), 'archived')
        archived_transitions = (
            'publish',
            'return_for_editing',
            )
        for tname in archived_transitions:
            self.assertTrue(tname in [r['id'] for r in _actions(content)])
        self.wftool.doActionFor(content, 'return_for_editing')
        self.assertEqual(_state(content), 'visible')
        self.wftool.doActionFor(content, 'collaborate')
        self.assertEqual(_state(content), 'collaborative_editing')
        collaborative_editing_transitions = (
            'end_collaboration',
            )
        for tname in collaborative_editing_transitions:
            self.assertTrue(tname in [r['id'] for r in _actions(content)])
        self.wftool.doActionFor(content, 'end_collaboration')
        self.assertEqual(_state(content), 'visible')

        self.wftool.doActionFor(content, 'make_private')
        self.assertEqual(_state(content), 'private')
        private_transitions = (
            'restrict',
            'share',
            )
        for tname in private_transitions:
            self.assertTrue(tname in [r['id'] for r in _actions(content)])
        
        self.wftool.doActionFor(content, 'restrict')
        self.assertEqual(_state(content), 'restricted')
        restricted_transitions = (
            'make_private',
            'share',
            )
        for tname in restricted_transitions:
            self.assertTrue(tname in [r['id'] for r in _actions(content)])
        self.wftool.doActionFor(content, 'share')
        self.assertEqual(_state(content), 'visible') # all states visited now


