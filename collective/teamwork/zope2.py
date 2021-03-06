from AccessControl.Permissions import add_user_folders
from Products.PluggableAuthService import registerMultiPlugin

from collective.teamwork.user import localrole
from collective.teamwork.patch import patch_atct_copyrefs
from collective.teamwork.patch import patch_atct_buildquery

registerMultiPlugin(localrole.WorkspaceLocalRoleManager.meta_type)


def initialize(context):
    """called to make this a Zope 2 product package"""
    context.registerClass(
        localrole.WorkspaceLocalRoleManager,
        permission=add_user_folders,
        constructors=(localrole.manage_addEnhancedWorkspaceLRMForm,
                      localrole.manage_addEnhancedWorkspaceLRM,),
        visibility = None,
        )
    patch_atct_copyrefs()
    patch_atct_buildquery()

