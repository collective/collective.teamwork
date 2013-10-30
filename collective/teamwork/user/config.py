# collective.teamwork.user: User/group management for team workspaces

# global per-project / per-workspace group/role templates

import itertools

from zope.component import getSiteManager, getGlobalSiteManager
from zope.component.hooks import getSite
from zope.interface import implements

import interfaces


BASE_GROUPNAME = u'viewers'

# APP_ROLES are roles that do not have normal local role inheritance,
# subject to the custom role manager excluding them from being used
# in workspaces contained within other workspaces.
APP_ROLES = [
    {'id': u'Workspace Viewer', 'title': 'Workspace Viewer'},
    {'id': u'Workspace Contributor', 'title': 'Workspace Contributor'},
    ]


ALL_SCOPES = ('project', 'workspace')


WORKSPACE_GROUPS = {
    'viewers': {
        'groupid': u'viewers',
        'title': u'Workspace Viewers',
        'description': u'Workspace viewers group.',
        'roles': [u'Workspace Viewer'],
        'scopes': ALL_SCOPES,
    },
    'contributors': {
        'groupid': u'contributors',
        'title': u'Workspace Contributors',
        'description': u'Contributor group for workspace context.',
        'roles': [u'Workspace Viewer', u'Workspace Contributor'],
        'scopes': ALL_SCOPES,
    },
    'managers': {
        'groupid': u'managers',
        'title': u'Workgroup managers',
        'description': u'Workgroup managers/leads group for workspace '
                       u'context.',
        'roles': [
            u'Workspace Viewer',
            u'Workspace Contributor',
            u'Editor',
            u'Reviewer',
            u'FormEntry',  # defined in uu.workflows role map
            u'Manager',
            ],
        'scopes': ALL_SCOPES,
    },
}


_u = lambda v: v.decode('utf-8') if isinstance(v, str) else unicode(v)


class MappingWrapperBase(object):
    ATTR = None  # abstract
    ORDER = None

    def __init__(self, items=(), order=()):
        setattr(self, self.ATTR, dict(items))
        if self.ORDER:
            if order:
                setattr(self, self.ORDER, list(order))
            else:
                setattr(self, self.ORDER, zip(*items)[0])

    # plug point abstract methods:
    def get(self, key, default=None):
        raise NotImplementedError('abstract')

    def iterkeys(self):
        raise NotImplementedError('abstract')

    # implementation details:

    def _keys(self):
        if self.ORDER:
            return getattr(self, self.ORDER)
        return getattr(self, self.ATTR).keys()

    def _items(self):
        return getattr(self, self.ATTR)

    # common:
    def __len__(self):
        return len(self._keys())

    def __contains__(self, key):
        return key in self._keys()

    def __getitem__(self, key):
        v = self.get(key, None)
        if v is None:
            raise KeyError(key)
        return v

    def __iter__(self):
        return self.iterkeys()

    def itervalues(self):
        return itertools.imap(self.get, self.iterkeys())

    def iteritems(self):
        fn = lambda key: (key, self.get(key))
        return itertools.imap(fn, self.iterkeys())

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    def select(self, scope=None, fn=None):
        if fn is not None:
            if fn not in (self.items, self.keys, self.values):
                raise ValueError('disallowed function')
        fn = fn if fn is not None else self.values
        if scope is None:
            return fn()
        filt = lambda info: scope in info.get('scopes', ALL_SCOPES)
        if fn in (self.keys, self.items):
            result = []
            for name, info in self.items():
                if filt(info):
                    v = (name, info) if fn == self.items else name
                    result.append(v)
            return result
        values = self.values()
        return filter(filt, values)

    def __delitem__(self, key):
        if key not in self._keys():
            raise KeyError(key)
        del(self._items()[key])
        if self.ORDER:
            self._keys().remove(key)

    def __setitem__(self, key, value):
        self._items()[key] = value
        if self.ORDER:
            self._keys().append(key)

    def set_order(self, order):
        if not self.ORDER:
            raise NotImplementedError('Not ordered mapping')
        order = list(order)
        setattr(self, self.ORDER, order)

    def get_order(self):
        return self.keys()

    order = property(get_order, set_order)


class WorkspaceGroupTypes(MappingWrapperBase):
    """Global registry of group type configuration (mapping)"""

    implements(interfaces.IWorkgroupTypes)

    ATTR = '_config'
    ORDER = '_order'
    BASE = WORKSPACE_GROUPS
    BASE_KEYS = ('viewers', 'contributors', 'managers')
    BASE_GROUPNAME = BASE_GROUPNAME

    def __init__(self):
        items = self.BASE.items()
        order = list(self.BASE_KEYS)
        super(WorkspaceGroupTypes, self).__init__(items, order)

    def get(self, key, default=None):
        attr = getattr(self, self.ATTR)
        return attr.get(key)

    def iterkeys(self):
        return iter(getattr(self, self.ORDER))


# hooks for global group type configuration:

def add_workgroup_type(name, local=False, **kwargs):
    sm = getGlobalSiteManager()
    if local:
        sm = getSiteManager(getSite())
    config = sm.queryUtility(interfaces.IWorkgroupTypes)
    name = str(name)
    info = {'groupid': _u(name)}
    info['title'] = _u(kwargs.get('title', name))
    info['description'] = _u(kwargs.get('description', u''))
    info['roles'] = [_u(r) for r in kwargs.get('roles', [])]
    info['scopes'] = tuple(kwargs.get('scopes', ALL_SCOPES))
    config[name] = info


def delete_workgroup_type(name, local=False):
    sm = getGlobalSiteManager()
    if local:
        sm = getSiteManager(getSite())
    config = sm.queryUtility(interfaces.IWorkgroupTypes)
    if name in config:
        del(config[name])

