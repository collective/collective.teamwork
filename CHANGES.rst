Changelog
=========

1.0 (unreleased)
----------------

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



