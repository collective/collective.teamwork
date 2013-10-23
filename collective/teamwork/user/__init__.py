# collective.teamwork.user: User/group management for team workspaces

import itertools


class ExtensionMapping(object):
    """
    Mapping adapter has its own keys/values aggregated with adapted
    mapping context's keys and values.
    """

    def __init__(self, context, items=()):
        self.context = context
        self._own = dict(items)

    def __len__(self):
        return len(self._own) + len(self.context)

    def __contains__(self, key):
        return key in self._own or key in self.context

    def get(self, key, default=None):
        return self._own.get(key, self.context.get(key, default))

    def __getitem__(self, key):
        v = self.get(key, None)
        if v is None:
            raise KeyError(key)
        return v

    def iterkeys(self):
        unique = lambda key: key not in self._own
        return itertools.chain(
            iter(self._own),
            itertools.ifilter(unique, iter(self.context)),
            )

    __iter__ = iterkeys

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

    # setters
    def __setitem__(self, key, value):
        self._own[key] = value

    def __delitem__(self, key):
        if key in self._own:
            del(self._own[key])
        raise KeyError('Cannot remove key from wrapped mapping.')

    def owns(self, key):
        return key in self._own


# global per-project / per-workspace group/role templates

BASE_GROUPNAME = u'viewers'

# APP_ROLES are roles that do not have normal local role inheritance,
# subject to the custom role manager excluding them from being used
# in workspaces contained within other workspaces.
APP_ROLES = [
    {'id': u'Workspace Viewer', 'title': 'Workspace Viewer'},
    {'id': u'Workspace Contributor', 'title': 'Workspace Contributor'},
    ]


WORKSPACE_GROUPS = {
    'viewers': {
        'groupid': u'viewers',
        'title': u'Workspace Viewers',
        'description': u'Workspace viewers group.',
        'roles': [u'Workspace Viewer'],
    },
    'contributors': {
        'groupid': u'contributors',
        'title': u'Workspace Contributors',
        'description': u'Contributor group for workspace context.',
        'roles': [u'Workspace Viewer', u'Workspace Contributor'],
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
    },
    'forms': {
        'groupid': u'forms',
        'title': u'Form entry',
        'description': u'Form entry and submission for workspace context.',
        'roles': [u'FormEntry'],  # defined in uu.workflows role map
    },
}

# project may have distinct groups:
PROJECT_GROUPS = ExtensionMapping(WORKSPACE_GROUPS)


_u = lambda v: v.decode('utf-8') if isinstance(v, str) else unicode(v)


def add_workgroup_type(name, project_only=False, **kwargs):
    global PROJECT_GROUPS, WORKSPACE_GROUPS
    config = PROJECT_GROUPS if project_only else WORKSPACE_GROUPS
    name = str(name)
    config[name] = {'groupid': _u(name)}
    config[name]['title'] = _u(kwargs.get('title', name))
    config[name]['description'] = _u(kwargs.get('description', u''))
    config[name]['roles'] = [_u(r) for r in kwargs.get('roles', [])]


def delete_workgroup_type(name, project_only=False):
    global PROJECT_GROUPS, WORKSPACE_GROUPS
    config = PROJECT_GROUPS if project_only else WORKSPACE_GROUPS
    if name in config:
        del(config[name])

