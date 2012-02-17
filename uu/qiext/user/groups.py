import logging
import itertools

from zope.component import adapts
from zope.component.hooks import getSite
from zope.interface import implements
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName

from uu.qiext.interfaces import APP_LOG
from uu.qiext.user.interfaces import IGroup, IGroups, ISiteMembers


_str = lambda v: v.encode('utf-8') if isinstance(v, unicode) else str(v)
_u = lambda v: v.decode('utf-8') if isinstance(v, str) else unicode(v)


class GroupInfo(object):
    
    implements(IGroup)
   
    def __init__(self, name, site=None, members=None):
        self._name = _str(name)
        self._site = site if site is not None else getSite()
        self._users = self._site.acl_users
        self._plugin = self._users.source_groups  # PAS groups plugin
        self._info = self._plugin.getGroupInfo(self._name)
        for k in ('title', 'description'):
            v = self._info.get(k, None)
            if v:
                v = _u(v)
            setattr(self, '_%s' % k, v)  # title -> _title, etc.
        self._members = self._members_adapter(members)
    
    # alternate constructor: creates PAS group
    @classmethod
    def create(cls, name, title=None, description=None, site=None):
        name = _str(name)
        site = site if site is not None else getSite()
        site.acl_users.source_groups.addGroup(name, title, description)
        return GroupInfo(name, site)
    
    @property
    def name(self):
        """Name property: read-only"""
        return self._name
    
    def _get_title(self):
        info = self._info
        return _u(info.get('title', '')) or None
    
    def _set_title(self, value):
        IGroup['title'].validate(_u(value))
        self._plugin.updateGroup(self.name, title=_str(value))
    
    title = property(_get_title, _set_title)

    def _get_description(self):
        info = self._info
        return _u(info.get('description', '')) or None
    
    def _set_description(self, value):
        IGroup['description'].validate(_u(value))
        self._plugin.updateGroup(self.name, description=_str(value))
   
    description = property(_get_description, _set_description)

    def _members_adapter(self, members=None):
        return members if members is not None else ISiteMembers(self._site)
    
    def keys(self):
        _group_users = self._plugin.listAssignedPrincipals(self.name)
        return [k for k,v in _group_users if k in self._members]
    
    def values(self):
        return [self._members.get(k) for k in self.keys()]

    def items(self):
        return zip(self.keys(), self.values())
    
    def __iter__(self):
        return self.keys().__iter__()
    
    iterkeys = __iter__
    
    def itervalues(self):
        _get = lambda k: self._members.get(k)
        return itertools.imap(_get, self.keys()) 

    def iteritems(self):
        _itemtuple = lambda k: (k, self._members.get(k))
        return itertools.imap(_itemtuple, self.keys()) 
    
    def __contains__(self, userid):
        return userid in self.keys()

    def __len__(self):
        return len(self.keys())
    
    def __getitem__(self, userid):
        if userid in self.keys():
            return self._members.get(userid)
        raise KeyError(userid)

    def get(self, userid, default=None):
        if userid in self.keys():
            return self._members.get(userid)
        return default

    def roles_for(self, context):
        ## this works because a group name is considered a principal:
        return self._members.roles_for(context, self._name)
    
    # methods that cause state change in underlying user/group storage:
    
    def assign(self, userid):
        """Add/assign a userid to group"""
        self._plugin.addPrincipalToGroup(userid, self.name)
        
    def unassign(self, userid):
        """Unassign a userid from a group"""
        if userid not in self.keys():
            raise ValueError('userid provided is not in group')
        self._plugin.removePrincipalFromGroup(userid, self.name)


class Groups(object):

    implements(IGroups)
    adapts(ISiteRoot)
    
    def __init__(self, context=None):
        if context is None:
            context = getSite()
        if not ISiteRoot.providedBy(context):
            raise TypeError('context must be site root')
        self.context = context
        self._users = self.context.acl_users
        self._plugin = self._users.source_groups  # PAS groups plugin
    
    def __getitem__(self, name):
        if name in self.keys():
            info = self._plugin.getGroupInfo(name)
            return GroupInfo(name, site=self.context) 
        raise KeyError(name)
    
    def get(self, name, default=None):
        if name in self.keys():
            info = self._plugin.getGroupInfo(name)
            return GroupInfo(name, site=self.context) 
        return default
    
    def __contains__(self, name):
        return name in self.keys()
    
    def __len__(self):
        return len(self.keys())
    
    def keys(self):
        return list(self._plugin.listGroupIds())  # force iteration
    
    def values(self):
        """Get values: prefer itervalues() when possible"""
        return [self.get(k) for k in self.keys()]
    
    def items(self):
        """Get items: prefer iteritems() when possible"""
        return zip(self.keys(), self.values())
    
    def __iter__(self):
        return self.keys().__iter__()
    
    iterkeys = __iter__
    
    def itervalues(self):
        return itertools.imap(self.get, self.keys()) 

    def iteritems(self):
        _itemtuple = lambda k: (k, self.get(k))
        return itertools.imap(_itemtuple, self.keys()) 
    
    # write/create:
    
    def add(self, groupname, title=None, description=None, members=()):
        group = GroupInfo.create(
            groupname,
            title,
            description,
            site=self.context,
            )
        if members:
            for member in members:
                group.assign(member)
        return group
    
    def remove(self, groupname):
        """Remove a group by name"""
        self._plugin.removeGroup(groupname)
    
    def clone(self, source, destination):
        """
        Clone a group, with its members intact from a name (source) to 
        a new name (destination).
        """
        source = GroupInfo(source)  # name -> group obj
        return self.add(
            destination,
            source.title,
            source.description,
            source.keys(),              # copies members
            )
    
    def rename(self, oldname, newname):
        """
        Rename a group, migrate members appropriately.
        
        Note: this does not affect objects using local roles assigned
        to these groups as principals.  Calling code renaming a group
        has the responsibility to sort out the consequences of that.
        """
        newgroup = self.clone(oldname, newname)  # clone attrs, members
        self.remove(oldname)
        return newgroup

