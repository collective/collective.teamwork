"""
collective.teamwork.user.interfaces: interfaces for membership
management adapters for workspace/workgroup management.
"""

__author__ = 'Sean Upton'
__copyright__ = """
                Copyright, 2011-2013, The University of Utah
                """.strip()
__license__ = 'GPL'


from zope.location.interfaces import ILocation
from zope.interface import Interface
from zope.interface.common.mapping import IIterableMapping
from zope import schema


class IGroup(Interface):
    """
    Interface for interacting with a single group of users.  Each
    named group has one group object representing it.  The name of the
    group is immutable -- any changes of group name must be done in
    an IGroups component, not in IGroup.

    The following state changes are possible with this component:

     * Change title or description field attributes/properties of group,
       which should be reflected as changes in the underlying user
       storage.

     * Add or remove group members: assign() and unassign() respectively.

    While this looks like a mapping, it is read-only except for addition
    and deletions of users (__setitem__(), __delitem__() are not provided).
    """

    name = schema.BytesLine(
        title=u'Group name',
        readonly=True,  # only set on construction, usually by framework
        required=True,
        )

    title = schema.TextLine(
        title=u'Group title',
        required=False,
        )

    description = schema.Text(
        title=u'Group description',
        required=False,
        )

    def __contains__(userid):
        """
        Is user id in group?
        """

    def __len__():
        """Return number of users in the group"""

    def __getitem__(userid):
        """
        Return the user if and only if the user id
        exists and the user is a member of the group,
        otherwise raise KeyError.
        """

    def get(userid, default=None):
        """
        Return the user if and only if the user id
        exists and the user is a member of the group,
        otherwise return default.
        """

    def roles_for(context):
        """
        Return list of roles in context for the group
        """

    def keys():
        """
        Return list of user ids.
        """

    def values():
        """
        Return list of user objects providing IPropertiedUser.
        """

    def items():
        """
        Return list of key, value tuples for user id, user object.
        """

    def __iter__():
        """Return iterable for user id keys"""

    def itervalues():
        """
        Return iterable of objects providing IProperiedUser for group.
        """

    def iteritems():
        """
        Return iterable over group membership keys and lazy-fetched PAS
        IPropertiedUser objects.
        """

    # methods that cause state change in underlying user/group storage:

    def assign(userid):
        """Add/assign a userid to group"""

    def unassign(userid):
        """Unassign a userid from a group"""


class IGroupListing(IIterableMapping):
    """
    Read-only, iterable mapping of group id keys to IGroup objects.

    Basic operations:

     * Iterate through group keys / values using iterable
       mapping interface.

     * Get groups by id, and check for their existence via
       __contains__().

     * Get number of total groups in a site via len().
    """


class IGroups(IGroupListing):
    """
    Mapping of group id keys to IGroup object values.  All
    group CRUD operations should work as expected, so:

    Create, update, delete operations:

     * Create groups using add()

     * Delete groups with remove()

     * Modify groups by interacting with group object themselves
       via the IGroup interface.

    Neither __setitem__() nor __delitem__() are supported.

    All state is stored in and queried from appropriate PAS plugins.
    """

    def add(groupname, title=None, description=None, members=()):
        """
        Given a group argument as a string group name, add a
        group to the system.  Title and description arguments
        may be optionally provided.

        Returns a group object providing IGroup.
        """

    def remove(groupname):
        """Remove a group given a group name"""

    def clone(source, destination):
        """
        Clone a group, with its members intact from a name (source) to
        a new name (destination).
        """

    def rename(oldname, newname):
        """
        Rename a group, migrate members appropriately. Return the newly
        created renamed group.

        Note: this does not affect objects using local roles assigned
        to these groups as principals.  Calling code renaming a group
        has the responsibility to sort out the consequences of that.
        """


class ISiteMembers(Interface):
    """
    Adapter interface for managing users site-wide; assumes user
    id is keyed by email address.

    This could also be used as a utility interface, but to avoid
    calls to getSite() repeatedly, it may be easier and better
    performing to have an adapter for a site (usually instantiated
    by views).
    """

    groups = schema.Object(
        title=u'Groups',
        description=u'Convenience accessor to group mapping for site.',
        schema=IGroups,
        readonly=True,
        )

    def __contains__(username):
        """Does user exist in site for user id / email"""

    def __len__():
        """Return number of users in site"""

    def __getitem__(username):
        """
        Get item by user id / email or raise KeyError;
        result should provide IPropertiedUser
        """

    def get(username, default=None):
        """
        Get a user by user id / email address, or
        return default. Non-default result should provide
        IPropertiedUser.
        """

    def search(query, **kwargs):
        """
        Given a string or unicode object as a query, search for
        user by full name or email address / user id.  Return a
        iterator of tuples of (username, user) for each match.
        Fielded search keywords can be passed for use by underlying
        user query mechanism provided by PluggableAuthService.
        """

    def __iter__():
        """return iterator over all user names"""

    def userid_for(key):
        """
        Given key as login name or a user object, return
        the internal user id for that user.
        """

    def login_name(key):
        """
        Get user login name for a user or an internal user id.
        """

    # add and remove users:
    def register(username, context=None, send=True, **kwargs):
        """
        Given username and keyword arguments containing
        possible user/member attributes, register a member.
        If context is passed, use this context as part of the
        registration process (e.g. project-specific).  This
        should trigger the usual registration process: a user
        should receive an email to complete setup.

        If send argument is false, do not notify user via email.
        """

    def __delitem__(username):
        """
        Given a key of username (email), purge/remove a
        user from the system, if and only if the user id looks
        like an email address.

        Note: it is expected that callers will check permissions
        accordingly in the context of the site being managed; this
        component does not check permissions.
        """

    # other utility functionality

    def pwreset(username):
        """Send password reset for user id"""

    def groupnames():
        """Return iterable of all groupnames"""

    def groups_for(username):
        """
        List all PAS groupnames for username / email; does not
        include indirect membership in nested groups.
        """

    def roles_for(context, username):
        """Return roles for context for a given user id"""

    def portrait_for(username, use_default=False):
        """
        Get portrait object for username, or return None (if use_default
        is False).  If use_default is True and no portrait exists,
        return the default.
        """


class IWorkspaceGroup(ILocation):
    """
    A group roster for a workspace, including top-level projects.
    Each is named and iterable read-only mapping over group members.
    A simple add/delete interface exists for adding and removing
    members from the respective workspace group by email address.
    """

    # clarify intent of the ILocation attributes in this context:

    __parent__ = schema.Object(
        title=u'Parent group',
        description=u'Parent group, usually the base/minimum group for '
                    u'project membership.  For the base group, the parent '
                    u'should be None',
        schema=Interface,
        required=False,
        default=None,
        )

    __name__ = schema.TextLine(
        title=u'Name',
        description=u'Alternate (read-only) access to self.id',
        readonly=True,
        required=False,  # may be None value
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


class IWorkspaceRoster(IWorkspaceGroup):
    """
    A roster of the base workspace members group (usually called
    'viewers') referencing more specialized groups in the groups mapping.
    """

    groups = schema.Dict(
        title=u'Groups',
        description=u'Specific project or workspace groups',
        key_type=schema.BytesLine(title=u'Group id'),
        value_type=schema.Object(schema=IWorkspaceGroup),
        defaultFactory=dict,  # requires zope.schema >= 3.8.0
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

        Always returns False in the context of a non-project workspace.
        """

    def remove(email, purge=False):
        """
        Remove a user from the workspace, and also unassign from all
        mappings in contained groups (self.groups).

        This does not remove the user from the site, unless all of the
        following conditions are met:

            1. The purge argument is true.
            2. The adaptation context is a top-level project workspace,
            3. The user is not a member of other projects.

            If #1 is true, but either #2 or #3 is False, raises a
            RuntimeError with a message indicating which assertion
            caused a failure.

        Raises ValueError if email specified is not a project member.

        Removal of member from contained workspaces is not in the scope
        of this method, and must be managed by callers.
        """


class IWorkgroupTypes(Interface):
    """
    Utilty presents ordered mapping of workgroup type identifiers
    to workgroup type configuration.
    
    May be implemented as named utility to distinguish between
    project and workspace types.
    """

    order = schema.List(
        title=u'Key order',
        description=u'Property sets/gets key order.',
        required=False,
        )
    
    def select(scope=None, fn=None):
        """
        Select values based on scope; returns list eqivalent
        to self.values() if scope is None, otherwise filtered.

        Return value function may be passed as self.items or
        self.keys to get items/keys instead of values.
        """

