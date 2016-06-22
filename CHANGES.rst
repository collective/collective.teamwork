Changelog
=========

1.0 (unreleased)
----------------

- Logging refactor: site members, workgroup/roster logging in adapters, not
  only in the view.  Unified utility method for status/logging.
  [seanupton]

- ISiteMembers now totally case-insensitive for all methods, not only case
  normalizing on registration (as was previous behavior).
  [seanupton]

- Workgroup membership components are case insensitive for traversal/get,
  containment, and normalizing for mutating operations.
  [seanupton]

- Tests for role and permission application via membership management;
  this tests that roles and permissions are appropriately applied by
  local roles manager plugin/adapter in concert with product workflow
  when users are granted roles in membership management adapters.
  [seanupton]

- Cache invalidation for local roles plugin annotations stored on request,
  when modifications are made to workgroup membership via WorkspaceGroup.
  [seanupton]

- Test fixtures: added a second test project.
  [seanupton]

- Added comprehensive tests for workgroup roster management.
  [seanupton]

- Refactored user purge API for workgroup/workspace.
  [seanupton]

- Refactored roster unassign() method to allow wholesale or per-group 
  unassign; removed the remove() method as duplicative in favor of
  unassign() and purge().
  [seanupton]

- WorkspaceGroup now disallows adding user to subsidiary role group
  of a workspace if they are not a member of that workspace's workgroup
  roster (viewers role-group).
  [seanupton]

- WorkspaceRoster wholesale unassign() now removes user from contained
  workspaces, rather than assuming that this is the calling view's job.
  [seanupton]

- Test fixtures add a sub-team workspace for use by tests.
  [seanupton]

- Thread-local key invalidation for multiple GroupInfo instances, and
  removed extra unnecessary caching layer in WorkspaceGroup, which caused
  problems for no real gain.  Making this change allows for callers
  to largely modify a workgroup's membership without having to explicitly
  call refresh to invalidate.  A thread-local singleton invalidation
  coordinator object is used to dispatch invalidations
  to other subscribed GroupInfo objects.
  [seanupton]

- Include collective.teamwork.team portal_type in TinyMCE configuration as
  both linkable and contains objects.
  [seanupton]

- Managers can remove own "manager" role from membership if and only if
  retaining acquired management ability from parent container (workspace
  or site).
  [seanupton]

- De-duplicate user search results based on email, not userid.
  [seanupton]

- Forward-ported missing fix from old uu.qiext package for case-insensitive
  username distinct from case-sensitive email in membership management
  template (membership.pt).
  [seanupton]

- Team workspace type in global for queryable portal types, was incidentally
  omitted in recent commits.
  [seanupton]

- Fix duplicative column heading in grid for workspace membership view.
  [seanupton]

- Viewlet for injecting ./project.css into pages.
  [seanupton]

- Test fixes for team vs. default profile workspace types.
  [seanupton]

- Attribute and method name typo fixes for CSV export.
  [seanupton]

- Explicitly add group.png (from Products.CMFPlone) into resource directory
  for this add-on.
  [seanupton]

- Make Team and Workspace distinct types, where Team is only addable inside
  a project, and workspace is implicitly addable anywhere.
  [seanupton]

- Icon fixes for FTIs.
  [seanupton]

- Jargon fixes for workspace type title usage in membership tab.
  [seanupton]

- Traversal adapter for workspaces to favor content to field values, works
  around Plone bug: https://dev.plone.org/ticket/14266
  [seanupton]

- WorkspaceContextHelper view: suppress benign AccessControl warnings about
  non-existent method of 'workspace' by declaring a class attribute to
  address magic permissions setting function of Five view class factory.
  [seanupton]

- Moved readme and changelog from txt to rst.
  [seanupton]

- Added missing iteration/enumeration mapping methods to membership adapter.
  [seanupton]

- CSS clear after floats in membership tab after register/search buttons.
  [seanupton]

- membership.js syntatical fixups: put code in IIFE, make slightly more
  modular, abstract jQuery namespace to $ inside the IIFE.
  [seanupton]

- Fix issue changing roles of users with hyphen character in username.
  [seanupton]

- Delete member data directly using PAS, not using portal_memberdata, and 
  do this before deleting the user from management plugins; also, search 
  should not include any cruft from previously deleted user data.
  [seanupton]

- Fix failure of user.utils.user_workspaces() on no contained workspaces.
  [seanupton]

- User info overlay/view now gets user workspaces without incidental
  duplication, and uses a new utility function for cleaner lookup.
  [seanupton]

- Membership tab: fix incorrect use of case-sensitive email adddress in
  group checking when loading grid; this addresses cases where the email
  address property differs in case from the normalized username.
  [seanupton]

- Explcitly name the username/email address of the user to be purged in
  the confirmation overlay purgeuser.pt
  [seanupton]

- More throrough invalidation of cached keys on membership changes;
  workgroup/roster refreshes group keys.
  [seanupton]

- fix member registration such that it correctly deals with
  userid/login_name split, works with collective.emaillogin4 properly.
  [seanupton]

- Fix 'log' workflow transition in all definitions, such that no
  permission is required as a guard, but the transition is still
  hidden (by lack of title/name) from the menu.
  [seanupton]

- Fix workflow definition id/title for source ODS spreadsheet, it
  did not match the output CSV filenames and titles.
  [seanupton]

- Replace any unicode whitespace or multiple adjacent whitespace
  characters in full name of registered user with a single ASCII space,
  in addition to stripping of leading/trailing whitespace already used.
  [seanupton]

- Fix attempt on new registration through the membership view to decode
  UTF-8 fullname twice, which caused errors on non-ASCII fullnames.
  [seanupton]

- Fix IGroups adapter failure on AutoGroups virtual groups like
  'AuthenticatedUsers' -- previously caused failure to iterate over
  group values. [seanupton]

- Additional test for basic group enumeration. [seanupton]

- Change SiteMembers.pwreset() to correctly use userid, not login name
  when interacting with PlonePAS user management plugin. [seanupton]


0.9 (2013-12-16)
----------------

- Updated to use of UUID-based group names. [seanupton]

- Various updates to make group configuration management
  pluggable.
  [seanupton]

- Moved source from uu.qiext to collective.teamwork
  [seanupton]



