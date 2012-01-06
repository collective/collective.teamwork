from StringIO import StringIO

from borg.localrole.config import LOCALROLE_PLUGIN_NAME as STOCK_PLUGIN_NAME
from borg.localrole.workspace import WorkspaceLocalRoleManager as STOCK_CLS
from Products.CMFCore.utils import getToolByName
from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin
from Products.PlonePAS.Extensions.Install import activatePluginInterfaces

from uu.qiext.user.localrole import manage_addEnhancedWorkspaceLRM


def _install_replacement_plugin(portal, uf, out, name='enhanced_localroles'):
    installed = uf.objectIds()
    if name not in installed:
        manage_addEnhancedWorkspaceLRM(uf, name)
        activatePluginInterfaces(portal, name)
        print >> out, 'Installed %s PAS local role plugin' % name
    else:
        print >> out, '%s PAS local role plugin already installed' % name


def replace_localrole_plugin(portal):
    """
    Replace the stock borg.localrole PAS plugin with our
    enhanced subclass.
    """
    out = StringIO()
    
    uf = getToolByName(portal, 'acl_users')
    
    installed = uf.objectIds()
    
    if STOCK_PLUGIN_NAME in installed:
        if STOCK_PLUGIN_NAME in uf.objectIds():
            original_plugin = getattr(uf, STOCK_PLUGIN_NAME)
            if isinstance(original_plugin, STOCK_CLS):
                print >> out, 'deactivated stock borg.localrole plugin'
                uf.plugins.deactivatePlugin(ILocalRolesPlugin, 'borg_localroles')
                #uf.plugins.removePluginById('local_roles')
    _install_replacement_plugin(portal, uf, out)
    
    return out.getvalue()

def setup_localrole_plugin(context):
    replace_localrole_plugin(context.getSite())

