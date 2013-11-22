"""
collective.teamwork.user.pas:
Common convenience functions for working with PAS/PlonePAS plugins.
"""

from Products.PluggableAuthService.interfaces import plugins as PAS
from Products.PlonePAS.interfaces.plugins import IUserManagement
from Products.PlonePAS.interfaces.group import IGroupManagement
from Products.PlonePAS.interfaces.group import IGroupIntrospection


def _plugins(acl_users, key):
    plugins = acl_users.plugins.listPlugins(key)
    return dict((name, enumerator) for name, enumerator in plugins)


def enumeration_plugins(acl_users):
    """All enumeration plugins minus known duplicative ones"""
    plugins = acl_users.plugins.listPlugins(PAS.IUserEnumerationPlugin)
    result = dict((name, enumerator) for name, enumerator in plugins)
    if 'source_users' in result and 'mutable_properties' in result:
        # we don't need both, will have same keys
        del(result['mutable_properties'])
    return result.values()


def management_plugins(acl_users):
    """All user-management plugins"""
    return acl_users.plugins.listPlugins(IUserManagement)


def group_introspection_plugins(acl_users):
    plugins = _plugins(acl_users, IGroupIntrospection).values()
    plugins = filter(lambda p: hasattr(p, 'getGroupInfo'), plugins)
    if not plugins:
        raise RuntimeError('No getGroupInfo-capable introspection plugin.')
    return plugins


def group_management_plugins(acl_users):
    return _plugins(acl_users, IGroupManagement).values()


def group_enumeration_plugins(acl_users):
    return _plugins(acl_users, PAS.IGroupEnumerationPlugin).values()
    

def list_users(plugin, keyonly=False):
    """
    Returns a list of userid, username (login) tuples for each user.
    If keyonly is True, returns a list of user id keys only.
    """
    if not PAS.IUserEnumerationPlugin.providedBy(plugin):
        raise ValueError('Plugin does not provide IUserEnumerationPlugin')
    direct_methods = ('getLoginForUserId', 'listUserIds')
    direct_listing = all(hasattr(plugin, n) for n in direct_methods)
    if direct_listing:
        # duck-typed capabilities of ZODBUserManager:
        userids = plugin.listUserIds()
        if keyonly:
            return userids  # optimal for __len__()
        pair = lambda userid: (userid, plugin.getLoginForUserId(userid))
        return map(pair, plugin.listUserIds())
    fn = lambda u: (u.get('id'), u.get('login'))
    if keyonly:
        fn = lambda u: u.get('id')
    return map(fn, plugin.enumerateUsers())


def group_ids(plugin):
    if not PAS.IGroupEnumerationPlugin.providedBy(plugin):
        raise TypeError('incorrect plugin type, not group enumerator')
    # duck type on listGroupIds() capabilty, more efficient than enumerating
    # user objects:
    if hasattr(plugin, 'listGroupIds'):
        return plugin.listGroupIds()
    return [info.get('id') for info in plugin.enumerateGroups()]

