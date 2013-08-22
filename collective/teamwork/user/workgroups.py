"""
collective.teamwork.user.workgroups: membership management adapters for QI
workspaces.
"""

__author__ = 'Sean Upton'
__email__ = 'sean.upton@hsc.utah.edu'
__copyright__ = """
                Copyright, 2011-2013, The University of Utah
                """.strip()
__license__ = 'GPL'


import itertools

from plone.indexer.decorator import indexer
from zope.interface import implements
from zope.component import adapts
from zope.component.hooks import getSite

from collective.teamwork.interfaces import IWorkspaceContext, IProjectContext
from collective.teamwork.user import interfaces
from collective.teamwork.user.groups import GroupInfo, Groups
from collective.teamwork.user.utils import group_namespace


def valid_setattr(obj, field, value):
    field.validate(value)
    setattr(obj, field.__name__, value)

_decode = lambda v: v.decode('utf-8') if isinstance(v, str) else v


class WorkspaceGroup(object):
    """
    Workspace group adapter: provides mapping for managing workspace
    membership in a specific group.
    """

    implements(interfaces.IWorkspaceGroup)
    adapts(IWorkspaceContext)

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
        if not IWorkspaceContext.providedBy(context):
            raise ValueError('Could not adapt: context not a workspace')
        schema = interfaces.IWorkspaceGroup
        if schema.providedBy(parent):
            self.__parent__ = parent
        self.context = context
        self.adapts_project = IProjectContext.providedBy(context)
        valid_setattr(self, schema['id'], _decode(groupid))
        valid_setattr(self, schema['title'], _decode(title))
        valid_setattr(self, schema['description'], _decode(description))
        valid_setattr(self, schema['namespace'], _decode(namespace))
        self._keys = None
        self.portal = getSite()
        self.site_members = interfaces.ISiteMembers(self.portal)
        groups = Groups(self.portal)
        groupname = self.pas_group()
        if groupname not in groups:
            groups.add(groupname)  # TODO: refactor?  may cause write-on-read
        self._group = GroupInfo(self.pas_group())

    @property
    def __name__(self):
        return self.id or None

    def pas_group(self):
        return '-'.join((self.namespace, self.id))

    def _get_user(self, email):
        return self.site_members.get(email)

    def __contains__(self, email):
        return email in self.keys()

    def __getitem__(self, email):
        if email not in self.keys():
            raise KeyError('email %s not in group %s' % (
                email, self.pas_group()))
        return self._get_user(email)

    def get(self, email, default=None):
        if email not in self.keys():
            return default
        return self._get_user(email)

    # mapping enumeration -- keys/values/items:

    def keys(self):
        """
        List of email addresses as group members.  This may be cached,
        as it is expensive to list assigned group principals in the
        stock Plone group plugin (ZODBGroupManager).
        """
        if self._keys is None:
            self._keys = self._group.keys()
        return self._keys  # cached lookup for session

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
        func = lambda email: (email, self._get_user(email))  # tuple (k,v)
        return itertools.imap(func, self.keys())

    # add / delete (assign/unassign) methods:

    def add(self, email):
        if email not in self.site_members:
            raise RuntimeError('User %s unknown to site' % email)
        if email not in self.keys():
            self._group.assign(email)
        self.refresh()  # need to invalidate keys -- membership modified.

    def unassign(self, email):
        if email not in self.keys():
            raise ValueError('user %s is not group member' % email)
        self._group.unassign(email)
        self.refresh()  # need to invalidate keys -- membership modified.

    def refresh(self):
        self._keys = None  # invalidate previous cached keys
        if interfaces.IWorkspaceGroup.providedBy(self.__parent__):
            if self.__parent__.id == self.id:
                # group equivalence, invalidate parent group too!
                self.__parent__._keys = None


class WorkspaceRoster(WorkspaceGroup):
    """
    Adapts project or other workspace (e.g. team) context, loads base
    group roster (for 'viewers') and loads contained groups.

    Provides interface to add (assign), remove (unassign and purge),
    and iterate over users and (other) groups for workspace.

    Some operations may be project-specific and raise exceptions in
    non-project workspace context per interface specification.
    """

    implements(interfaces.IWorkspaceRoster)
    adapts(IWorkspaceContext)

    def __init__(self, context):
        self.adapts_project = IProjectContext.providedBy(context)
        self._load_config()
        super(WorkspaceRoster, self).__init__(
            context,
            parent=None,
            groupid=self._base['groupid'],
            title=self._base['title'],
            description=self._base['description'],
            namespace=group_namespace(context),
            )
        self._load_groups()

    def _load_config(self):
        basename, config, project_config = (
            interfaces.BASE_GROUPNAME,
            interfaces.WORKSPACE_GROUPS,
            interfaces.PROJECT_GROUPS,
            )
        self._config = project_config if self.adapts_project else config
        self._base = self._config[basename]

    def _load_groups(self):
        self.groups = {}
        for name, group_cfg in self._config.items():
            self.groups[name] = WorkspaceGroup(
                self.context,
                parent=self,
                namespace=self.namespace,
                **group_cfg)  # title, description, groupid

    def can_purge(self, email):
        if not self.adapts_project:
            return False  # no purge in workspace other than top-level project
        if email not in self.keys():
            return False  # sanity check, email must be in project roster
        if not self.namespace:
            return False  # empty namespace -- seems wrong!
        user_groups = self.site_members.get(email).getGroups()
        for group in user_groups:
            if group in ('AuthenticatedUsers',):
                continue
            if not group.startswith(self.namespace):
                return False  # any match outside our scope == fail
        return True

    def unassign(self, email):
        # recursive removal: relies on transaction atomicity from ZODB
        # and ZODB group plugin to provide complete rollback on exception.
        super(WorkspaceRoster, self).unassign(email)  # WorkspaceGroup impl
        for group in self.groups.values():
            if email in group.keys():
                group.unassign(email)

    def remove(self, email, purge=False):
        if not purge:
            return self.unassign(email)  # without purge: remove===unassign
        ## purge from site -- or check if possible and attempt:
        if not self.adapts_project:
            # no purge in workspace other than top-level project
            raise RuntimeError('Cannot purge user from non-project workspace')
        if not self.can_purge(email):
            raise RuntimeError('Cannot purge: user member of other projects')
        self.unassign(email)
        del(self.site_members[email])

    def refresh(self):
        super(WorkspaceRoster, self).refresh()
        if self.id in self.groups:
            # there is an equivalent group to roster, invalidate it too!
            self.groups[self.id].refresh()


# indexer adapter for project/workspace context group names:

@indexer(IWorkspaceContext)
def workspace_pas_groups(context, **kw):
    roster = interfaces.IWorkspaceRoster(context)
    names = set([roster.pas_group()])
    groups = roster.groups.values()
    names = names.union(group.pas_group() for group in groups)
    return list(names)

