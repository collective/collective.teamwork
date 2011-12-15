# migration for old Products.qi setup
import transaction
from plone.app.folder.migration import BTreeMigrationView
from plone.namedfile.interfaces import HAVE_BLOBS
from plone.namedfile.file import NamedImage, NamedBlobImage
from Acquisition import aq_base
from DateTime import DateTime


if HAVE_BLOBS:
    NamedImage = NamedBlobImage


is_jpeg = lambda data: 'JFIF' in data[:12]


def logo_image_factory(data):
    """Create NamedImage / NamedBlobImage object from raw image data"""
    ctype = 'image/jpeg' if is_jpeg(data) else 'image/png'
    return NamedImage(
        data=data,
        contentType=ctype,
        filename='logo.jpg',
        )


def migrate_logo(project):
    if hasattr(project, 'logo') and isinstance(project.logo, str):
        # old-style logo, needs migration to plone.namedfile object
        project.logo = logo_image_factory(state['logo'])
        return 'Logo attribute migrated to NamedImage'


def migrate_folder(folder):
    if not hasattr(project, '_objects'):
        return # already migrated
    folder = aq_base(folder)
    names = folder.objectIds()
    migration = BTreeMigrationView(folder, None)
    migration.migrate(folder)
    assert hasattr(folder, '_mt_index') and hasattr(folder, '_tree')
    assert not hasattr(folder, '_objects')
    for name in names:
        assert name in folder._tree         # id in contents tree
        assert not hasattr(folder, name)    # no longer attribute
    return 'Migrated old folder contents to BTree'


def mark_changed(content, note):
    """Mark object as changed, but only if note is not None"""
    if note is None:
        return # no change
    content._migration_version = 2
    content.modification_date = DateTime() #now
    aq_base(content)._p_changed = True
    txn = transaction.get()
    path = '/'.join(content.getPhysicalPath())[1:]
    if path:
        txn.note(path)
    txn.note(note)


def remove_attributes(content, names=()):
    """
    Given a seqeuence of names, remove attributes, if they
    exist, from the content object content
    """
    removed = []
    for name in names:
        if hasattr(project, name):
            delattr(project, name)
            removed.append(name)
    if removed:
        return 'Removed unused attributes %s' % repr(tuple(tuple))


def migrate_project(project, version=2):
    """
    Migrate a project from previous state.

    Each migration step called within will return a string 
    describing the change or None if no change was needed. Either
    possible return value is appended to a log list.  Each element
    in the log list is ignored if None, or appended to a transaction
    note by mark_changed().
    """
    changes = []
    wrapped = project
    project = aq_base(project)
    if getattr(project, '_migration_version', None) == 2:
        return # already migrated this object (attr set by mark_changed())
    # Migrate old folder contents storage to BTree folder contents
    # compatible with Dexterity containers.
    changes.append(migrate_folder(project))
    # Migrate logo attribute contents to NamedImage.
    changes.append(migrate_logo(project))
    # Remove unused attributes:
    unused = ('dbid', 'groupname', 'managers', 'faculty')
    changes.append(remove_attributes(project, unused))
    # Remove reference to QIC Role from all roles in __ac_local_roles__:
    pass # TODO IMPLEMENT TODO
    # Remove -qics group items from __ac_local_roles__.
    pass # TODO IMPLEMENT TODO
    # Rename group keys in __ac_local_roles__ from *-members to *-viewers
    # suffix to match changes to group names in acl_users group source
    # storage/plugin.
    pass # TODO IMPLEMENT TODO
    # Replace references to the 'ProjectViewer' role in 
    # __ac_local_roles__ with 'WorkspaceViewer'.
    pass # TODO IMPLEMENT TODO
    # Add UUIDs to project object, calling
    # plone.uuid.handlers.addAttributeUUID(context, None)
    pass # TODO IMPLEMENT TODO
    # For each permission attribute on the project, replace any
    # references to 'ProjectViewer' with 'WorkspaceViewer'
    pass # TODO IMPLEMENT TODO
    # Mark project._p_changed=True to ensure changes flushed at
    # transaction commit. Log changes to transaction note:
    changes = [change for change in changes if change is not None]
    if changes:
        log = '; '.join(changes) if len(changes)>1 else changes[0]
        mark_changed(wrapped, log) # use aq-wrapped project here...

