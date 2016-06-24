from collections import OrderedDict
import itertools
import threading
import weakref

from zope.component import adapts
from zope.component.hooks import getSite
from zope.interface import implements
from Products.CMFCore.interfaces import ISiteRoot

from collective.teamwork.user.interfaces import IGroup, IGroups
from collective.teamwork.user.interfaces import ISiteMembers
import pas


_str = lambda v: v.encode('utf-8') if isinstance(v, unicode) else str(v)
_u = lambda v: v.decode('utf-8') if isinstance(v, str) else unicode(v)


class GroupInvalidation(threading.local):
    """
    Thread-local state synchronizer for GroupInfo cache invalidation.
    We use this because shared state across transaction boundaries is more
    complicated and risky (if transaction is aborted), and we use
    thread-local storage as all other state is expected to comply with MVCC
    via ZODB (as each thread and instance has own state/cache).
    ** The goal is to have all state be consistent within a transaction. **

    Impact on garbage collection:

        - We use weakref to keep cached target references from preventing
          GC on GroupInfo object.

        - We use hash(target) to compute storage key, preventing duplicate
          subscription.
        
        - GroupInfo.__del__() should unsubscribe from GroupInvalidation.
    """

    def __init__(self):
        super(GroupInvalidation, self).__init__()
        self.info = {}

    def subscribe(self, name, target):
        """Subscribe target object to invalidation for group name"""
        if name not in self.info:
            self.info[name] = {}
        self.info[name][hash(target)] = weakref.ref(target)

    def unsubscribe(self, name, target):
        """Unsubscribe a target object to invalidation for group name"""
        if name in self.info and hash(target) in self.info[name]:
            del self.info[name][hash(target)]

    def invalidate(self, name, context=None):
        if name in self.info:
            for ref in self.info[name].values():
                signified = ref()
                if signified is context:
                    continue
                target = ref()
                if target is not None:
                    target._usernames = None


_group_invalidation = GroupInvalidation()


class GroupInfo(object):

    implements(IGroup)

    def __init__(self, name, site=None, members=None):
        self._name = _str(name)
        self._site = site if site is not None else getSite()
        self._acl_users = self._site.acl_users
        self._introspection = pas.group_introspection_plugins(self._acl_users)
        self._management = pas.group_management_plugins(self._acl_users)[0]
        self._init_info()
        self._members = self._members_adapter(members)
        self.refresh()
        _group_invalidation.subscribe(name, self)

    def __del__(self):
        _group_invalidation.unsubscribe(self._name, self)

    def applyTransform(self, username):
        return self._members.applyTransform(username)

    def _init_info(self):
        self._info = None
        for plugin in self._introspection:
            try:
                self._info = pas.group_info(plugin, self._name)
                if self._info is not None:
                    break
            except KeyError:
                pass
        if self._info is None:
            # fallback when introspection cannot find metadata
            self.title = self.description = _u(self._name)
            return
        for k in ('title', 'description'):
            v = self._info.get(k, None)
            if v:
                v = _u(v)
            setattr(self, '_%s' % k, v)  # title -> _title, etc.

    # alternate constructor: creates PAS group
    @classmethod
    def create(cls, name, title=None, description=None, site=None):
        name = _str(name)
        site = site if site is not None else getSite()
        management = pas.group_management_plugins(site.acl_users)[0]
        management.addGroup(name, title, description)
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
        self._management.updateGroup(self.name, title=_str(value))

    title = property(_get_title, _set_title)

    def _get_description(self):
        info = self._info
        return _u(info.get('description', '')) or None

    def _set_description(self, value):
        IGroup['description'].validate(_u(value))
        self._management.updateGroup(self.name, description=_str(value))

    description = property(_get_description, _set_description)

    def _members_adapter(self, members=None):
        return members if members is not None else ISiteMembers(self._site)

    def refresh(self):
        self._usernames = None
        _group_invalidation.invalidate(self._name, context=self)

    def keys(self):
        """User login name keys"""
        if self._usernames is None:
            _principals = []
            for plugin in self._introspection:
                group = plugin.getGroupById(self._name)
                if group:
                    _principals += list(plugin.getGroupMembers(self.name))
            _principals = filter(
                lambda login_name: login_name is not None,
                map(self._members.login_name, _principals)
                )
            # set de-duplicated list, retaining order found
            self._usernames = list(OrderedDict.fromkeys(_principals))
        return self._usernames

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

    def __contains__(self, username):
        username = self.applyTransform(username)
        return username in self.keys()

    def __len__(self):
        return len(self.keys())

    def __getitem__(self, username):
        if username in self.keys():
            return self._members.get(username)
        raise KeyError(username)

    def get(self, username, default=None):
        username = self.applyTransform(username)
        if username in self.keys():
            return self._members.get(username)
        return default

    def roles_for(self, context):
        ## this works because a group name is considered a principal:
        return self._members.roles_for(context, self._name)

    # methods that cause state change in underlying user/group storage:

    def assign(self, username):
        """Add/assign a username to group"""
        username = self.applyTransform(username)
        userid = self._members.userid_for(username)
        if userid is None:
            # possibly new user name, invalidate and try again
            self._members.refresh()
            userid = self._members.userid_for(username)
            if userid is None:
                raise ValueError('unknown user name.')
        self._management.addPrincipalToGroup(userid, self.name)
        self.refresh()

    def unassign(self, username):
        """Unassign a username from a group"""
        username = self.applyTransform(username)
        if username not in self.keys():
            raise ValueError('username provided is not in group')
        userid = self._members.userid_for(username)
        self._management.removePrincipalFromGroup(userid, self.name)
        self.refresh()


class Groups(object):

    implements(IGroups)
    adapts(ISiteRoot)

    def __init__(self, context=None):
        if context is None:
            context = getSite()
        if not ISiteRoot.providedBy(context):
            raise TypeError('context must be site root')
        self.context = context
        self._acl_users = self.context.acl_users
        self._enumeration = pas.group_enumeration_plugins(self._acl_users)
        self._management = pas.group_management_plugins(self._acl_users)[0]
        self.refresh()

    def refresh(self):
        self._group_ids = None

    def __getitem__(self, name):
        if name in self.keys():
            return GroupInfo(name, site=self.context)
        raise KeyError(name)

    def get(self, name, default=None):
        if name in self.keys():
            return GroupInfo(name, site=self.context)
        return default

    def __contains__(self, name):
        return name in self.keys()

    def __len__(self):
        return len(self.keys())

    def keys(self):
        if self._group_ids is None:
            r = []
            for plugin in self._enumeration:
                r += pas.group_ids(plugin)
            self._group_ids = list(OrderedDict.fromkeys(r))
        return self._group_ids

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
        self.refresh()
        return group

    def remove(self, groupname):
        """Remove a group by name"""
        self._management.removeGroup(groupname)
        self.refresh()

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

