# collective.teamwork.user: User/group management for team workspaces

import copy

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

# modify metadata specific to slightly different roles and groups in project:
PROJECT_GROUPS = copy.deepcopy(WORKSPACE_GROUPS)

