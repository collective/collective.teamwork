# collective.teamwork.user: User/group management for team workspaces

# global per-project / per-workspace group/role templates

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
    'forms': {
        'groupid': u'forms',
        'title': u'Form entry',
        'description': u'Form entry and submission for workspace context.',
        'roles': [u'FormEntry'],  # defined in uu.workflows role map
        'scopes': ALL_SCOPES,
    },
}


_u = lambda v: v.decode('utf-8') if isinstance(v, str) else unicode(v)


# hooks for global group type configuration:

def add_workgroup_type(name, **kwargs):
    global WORKSPACE_GROUPS
    config = WORKSPACE_GROUPS
    name = str(name)
    config[name] = {'groupid': _u(name)}
    config[name]['title'] = _u(kwargs.get('title', name))
    config[name]['description'] = _u(kwargs.get('description', u''))
    config[name]['roles'] = [_u(r) for r in kwargs.get('roles', [])]
    config[name]['scopes'] = tuple(kwargs.get('scopes', ALL_SCOPES))


def delete_workgroup_type(name):
    global WORKSPACE_GROUPS
    config = WORKSPACE_GROUPS
    if name in config:
        del(config[name])

