"""
uu.qiext.user.groups: membership management adapters for QI projects.
"""

__author__ = 'Sean Upton'
__email__ = 'sean.upton@hsc.utah.edu'
__copyright__ = """ 
                Copyright, 2011, The University of Utah
                """.strip()
__license__ = 'GPL'


import itertools

from plone.indexer.decorator import indexer
from zope.interface import implements
from zope.component.hooks import getSite

from uu.qiext.interfaces import IProjectContext, ITeamContext
from uu.qiext.user import interfaces
from uu.qiext.user.utils import group_namespace


def valid_setattr(obj, field, value):
    field.validate(value)
    setattr(obj, field.__name__, value)

_decode = lambda v: v.decode('utf-8') if isinstance(v, str) else v

class ProjectGroup(object):
    """Project group adapter""" 
    
    implements(interfaces.IProjectGroup)
    
    # class attribute defaults (for instance attributes):
    __parent__ = None

    def __init__(self,
                 context,
                 parent=None,
                 groupid=u'',
                 title=u'',
                 description=u'',
                 namespace=u'',
                 roles=(),):
        self.adapts_project = IProjectContext.providedBy(context)
        self.adapts_team = ITeamContext.providedBy(context)
        if not (self.adapts_team or self.adapts_project):
            raise ValueError('Could not adapt: not project or team')
        self.context = context
        if interfaces.IProjectGroup.providedBy(parent):
            self.__parent__ = parent
        valid_setattr(self,
                      interfaces.IProjectGroup['id'],
                      _decode(groupid))
        valid_setattr(self,
                      interfaces.IProjectGroup['title'],
                      _decode(title))
        valid_setattr(self,
                      interfaces.IProjectGroup['description'],
                      _decode(description))
        valid_setattr(self,
                      interfaces.IProjectGroup['namespace'],
                      _decode(namespace))
        self._keys = None
    
    @property
    def __name__(self):
        return self.id or None
    
    def pas_group(self):
        return '-'.join((self.namespace, self.id))

    def _users(self):
        """get user folder reference"""
        if not hasattr(self, '_acl_users'):
            self._acl_users = getSite().acl_users
        return self._acl_users

    def _get_user(self, email):
        return self._users().getUserById(email)

    def __contains__(self, email):
        return email in self.keys()
    
    def __getitem__(self, email):
        if email not in self.keys():
            raise KeyError('email %s not in group %s' % (
                email, self.pas_group()))
        return self._get_user(email)
    
    def get(self, email, default=None):
        if email not in self.keys():
            return None
        return self._get_user(email)
    
    # mapping enumeration -- keys/values/items:

    def keys(self):
        """
        List of email addresses as group members.  This may be cached,
        as it is expensive to list assigned group principals in the
        stock Plone group plugin (ZODBGroupManager).  
        """
        if self._keys is None:
            listgroup = self._users().source_groups.listAssignedPrincipals
            self._keys = [user[0] for user in listgroup(self.pas_group())]
        return self._keys #cached lookup for session
     
    def values(self):
        return [self._get_user(k) for k in self.keys()]
    
    def items(self):
        return [(k, self._get_user(k)) for k in self.keys()]
   
    def __len__(self):
        return len(self.keys())

    # iterable mapping methods:

    def iterkeys(self):
        return iter(self.keys())

    __iter__ = iterkeys

    def itervalues(self):
        return itertools.imap(self._get_user, self.keys())
    
    def iteritems(self):
        func = lambda email: (email, self._get_user(email)) #tuple (k,v)
        return itertools.imap(func, self.keys())
    
    # add / delete (assign/unassign) methods:
    
    def add(self, email):
        acl_users = self._users()
        if email not in acl_users.getUserNames():
            raise RuntimeError('User %s unknown to site' % email)
        if email not in self.keys():
            plugin = self._users().source_groups
            plugin.addPrincipalToGroup(email, self.pas_group())
        self.refresh()  # need to invalidate keys -- membership modified.
    
    def unassign(self, email):
        if email not in self.keys():
            raise ValueError('user %s is not group member' % email)
        self._users().source_groups.removePrincipalFromGroup(
            email,
            self.pas_group()
            )
        self.refresh()  # need to invalidate keys -- membership modified.
    
    def refresh(self):
        self._keys = None #invalidate previous cached keys
        if interfaces.IProjectGroup.providedBy(self.__parent__):
            if self.__parent__.id == self.id:
                # group equivalence, invalidate parent group too!
                self.__parent__.refresh()


class ProjectRoster(ProjectGroup):
    """
    Adapts project or team context, loads base group roster (for
    'viewers') and loads contained groups.
    
    Provides interface to add (assign), remove (unassign and purge),
    and iterate over users and (other) groups for project or team.
    
    Some operations may be project-specific and raise exceptions in 
    team context per interface specification.
    """
    
    implements(interfaces.IProjectRoster)
    
    def __init__(self, context):
        self.adapts_project = IProjectContext.providedBy(context)
        self._load_config()
        super(ProjectRoster, self).__init__(
            context,
            parent=None,
            groupid=self._base['groupid'],
            title=self._base['title'],
            description=self._base['description'],
            namespace=group_namespace(context),
            )
        self._load_groups()
    
    def _load_config(self):
        basename, project_config, team_config = (
            interfaces.BASE_GROUPNAME,
            interfaces.PROJECT_GROUPS,
            interfaces.TEAM_GROUPS)
        self._config = project_config if self.adapts_project else team_config
        self._base = self._config[basename]

    def _load_groups(self):
        self.groups = {}
        for name, group_cfg in self._config.items():
            self.groups[name] = ProjectGroup(
                self.context,
                parent=self,
                namespace=self.namespace,
                **group_cfg) #title, description, groupid
    
    def can_purge(self, email):
        if self.adapts_team:
            return False #never purge from team context
        if not self.namespace:
            return False #empty namespace -- seems wrong!
        user_groups = self._users().getUserById(email).getGroups()
        for group in user_groups:
            if not group.starts_with(self.namespace):
                return False #any match outside our scope == fail
        return True
    
    def unassign(self, email):
        # recursive removal: relies on transaction atomicity from ZODB
        # and ZODB group plugin to provide complete rollback on exception.
        for group in self.groups:
            if email in group.keys():
                group.unassign(email)
        return super(ProjectRoster, self).unassign(email) #ProjectGroup impl
    
    def remove(self, email, purge=False):
        if not purge:
            return self.unassign(email)  # without purge: remove===unassign
        ## purge from site -- or check if possible and attempt:
        if self.adapts_team:
            # we don't want to purge user from team, only from project...
            raise RuntimeError('Cannot purge user in context of team')
        if not self.can_purge(email):
            raise RuntimeError('Cannot purge: user member of other projects')
        self.unassign(email)
        self._users().source_users.removeUser(email)
    
    def refresh(self):
        super(ProjectRoster, self).refresh()
        if self.id in self.groups:
            # there is an equivalent group to roster, invalidate it too!
            self.groups[self.id].refresh()


# indexer adapters for project/team/workspace context group names:

def _workspace_pas_groups(context):
    roster = IProjectRoster(object)
    names = set([roster.pas_group()])
    groups = roster.groups.values()
    names = names.union(group.pas_group() for group in groups)
    return list(names)


@indexer(IProjectContext)
def project_pas_groups(object, **kw):
    return _workspace_pas_groups(object)


@indexer(ITeamContext)
def team_pas_groups(object, **kw):
    return _workspace_pas_groups(object)

