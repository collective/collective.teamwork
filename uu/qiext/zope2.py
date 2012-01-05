from AccessControl.Permissions import add_user_folders
from Products.PluggableAuthService import registerMultiPlugin

from uu.qiext.user import localrole


registerMultiPlugin(localrole.WorkspaceLocalRoleManager.meta_type)


def initialize(context):
    """called to make this a Zope 2 product package"""
    context.registerClass(localrole.WorkspaceLocalRoleManager,
        permission=add_user_folders,
        constructors = (localrole.manage_addEnhancedWorkspaceLRMForm,
                        localrole.manage_addEnhancedWorkspaceLRM,),
        visibility = None,
        )

