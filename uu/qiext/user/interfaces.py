"""
uu.qiext.user.interfaces: interfaces for membership management adapters
for QI projects.
"""

__author__ = 'Sean Upton'
__copyright__ = """ 
                Copyright, 2011, The University of Utah
                """.strip()
__license__ = 'GPL'


from zope.location.interfaces import ILocation
from zope.interface import Interface
from zope import schema


# global per-project / per-team configuration templates

BASE_GROUPNAME = u'viewers'

APP_ROLES = [
    {'id': u'Workspace Viewer', 'title': 'Workspace Viewer'},
    {'id': u'Workspace Contributor', 'title': 'Workspace Contributor'},
    ]

PROJECT_GROUPS = {
    'viewers' : {
        'groupid'       : u'viewers',
        'title'         : u'Viewers',
        'description'   : u'Viewers group for project context.',
        'roles'         : [u'Workspace Viewer',],
    },
    'contributors' : {
        'groupid'       : u'contributors',
        'title'         : u'Contributors',
        'description'   : u'Contributor group for project context.',
        'roles'         : [u'Workspace Viewer', u'Workspace Contributor'],
    },
    'managers' : {
        'groupid'       : u'managers',
        'title'         : u'Project managers',
        'description'   : u'Project managers group for project context.',
        'roles'         : [ u'Workspace Viewer',
                            u'Workspace Contributor',
                            u'Editor',
                            u'Reviewer',
                            u'FormEntry', # defined in uu.workflows role map
                            u'Manager',],
    },
    'forms' : {
        'groupid'       : u'forms',
        'title'         : u'Form entry',
        'description'   : u'Form entry and submission for project context.',
        'roles'         : [u'FormEntry'], # defined in uu.workflows role map
    },
}

TEAM_GROUPS = {
    'viewers' : {
        'groupid'       : u'viewers',
        'title'         : u'Viewers',
        'description'   : u'Viewers group for team context.',
        'roles'         : [u'Workspace Viewer',],
    },
    'contributors' : {
        'groupid'       : u'contributors',
        'title'         : u'Contributors',
        'description'   : u'Contributor group for team context.',
        'roles'         : [u'Workspace Viewer', u'Workspace Contributor'],
    },
    'managers' : {
        'groupid'       : u'managers',
        'title'         : u'Team leads',
        'description'   : u'Team leads (managers) group for team context.',
        'roles'         : [ u'Workspace Viewer',
                            u'Workspace Contributor',
                            u'Editor',
                            u'Reviewer',
                            u'FormEntry', # defined in uu.workflows role map
                            u'Manager',],
    },
    'forms' : {
        'groupid'       : u'forms',
        'title'         : u'Form entry',
        'description'   : u'Form entry and submission for team context.',
        'roles'         : [u'FormEntry'], # defined in uu.workflows role map
    },
}


# project adapter interfaces:

class IProjectGroup(ILocation):
    """
    A group roster for a project or team; each is named and iterable
    read-only mapping over group members. A simple add/delete
    interface exists for adding and removing members from the
    respective project/team group by email address.
    """
   
    # clarify intent of the ILocation attributes in this context:

    __parent__ = schema.Object(
        title=u'Parent group',
        description=u'Parent group, usually the base/minimum group for '\
                    u'project membership.  For the base group, the parent '\
                    u'should be None',
        schema=Interface,
        required=False,
        default=None,
        )
   
    __name__ = schema.TextLine(
        title=u'Name',
        description=u'Alternate (read-only) access to self.id',
        readonly=True,
        required=False, #may be None value
        )
   
    # properties of a project group:

    namespace = schema.TextLine(title=u'PAS group name prefix', required=True)
   
    id = schema.TextLine(title=u'Group id', required=True)
    
    title = schema.TextLine(title=u'Group title', default=u'')
    
    description = schema.Text(title=u'Group description', default=u'')
    
    # identity method(s):
    
    def pas_group():
        """
        Given group name like 'member' or 'manager', compose fully 
        qualified PAS group name using self.namespace and group name.
        """

    # read-mapping methods:

    def __contains__(email):
        """
        Given name (as email address), is it contained in group?
        """
    
    def __getitem__(email):
        """
        Get object providing IPropertiedUser for the given name, or
        raise KeyError.
        """
    
    def get(email, default=None):
        """
        Get object providing IPropertiedUser for the given name, or
        return default.
        """
   
    def refresh():
        """If roster caching is employed, invalidate/refresh cache"""
    
    def keys():
        """
        Return list of string email addresses for group.
        """
    
    def values():
        """
        Return list of user objects providing IProperiedUser for group.
        Do not use this on larger groups, instead call itervalues().
        """
    
    def items():
        """
        Return list of tuples containing email address and user object
        each.  Do not use this for large groups, prefer to use 
        iteritems(), or iterate over each key from keys() or iterkeys()
        and obtain user object Lazily.
        """
    
    def iterkeys():
        """
        Iterable over (string-email address) keys; often iter(self.keys())
        """
    
    def itervalues():
        """
        Return iterable of objects providing IProperiedUser for group.
        """
    
    def iteritems():
        """
        Return iterable over group keys and lazy-fetched PAS
        IPropertiedUser objects.
        """
    
    def __iter__():
        """
        Return iterable over group keys (email address strings).
        """
    
    def __len__():
        """
        Return the number of users in the group == len(self.keys())
        """
   
    # add/remove interface methods:

    def add(email):
        """
        Given email of existing user, add that user to group.  If user
        is not a site member, raise ValueError.
        """
     
    def unassign(email):
        """
        Given email of existing user, remove user from group.  Raise 
        ValueError if user is not a member of the group.
        """


class IProjectRoster(IProjectGroup):
    """
    A roster of the base project or team members group (usually called
    'viewers') referencing more specialized groups in the groups mapping.
    """
    
    groups = schema.Dict(
        title=u'Groups',
        description=u'Specific project or team groups',
        key_type=schema.BytesLine(title=u'Group id'),
        value_type=schema.Object(schema=IProjectGroup),
        defaultFactory=dict, #requires zope.schema >= 3.8.0
        )
   
    def unassign(email):
        """
        Given email of existing user, remove user from group.  Riase
        ValueError if user is not a member of the group.
        
        Behaves similar to self.remove(email, purge=False): the 
        user is removed from the project.  remove() should be 
        preferred in most usage (especially in user-facing actions),
        as it is more explicit, and only remove() has a purge option.
        
        Unassigning a user from the base group also unassigns them
        recursively from contained groups.
        """

    def can_purge(email):
        """
        Return true if user is not member of other projects: that is, that
        all the groups the user for given email belong to the namespace of
        this (and only this) project.
        
        Always returns False in the context of a team.
        """

    def remove(email, purge=False):
        """
        Remove a user from the project or team, and also unassign from all
        mappings in contained groups (self.groups).  

        This does not remove the user from the site, unless all of the
        following conditions are met: 

            1. The purge argument is true.
            2. The adaptation context is a project, not a team.
            3. The user is not a member of other projects.
        
            If #1 is true, but either #2 or #3 is False, raises a
            RuntimeError with a message indicating which assertion
            caused a failure.

        Raises ValueError if email specified is not a project member.
        """

