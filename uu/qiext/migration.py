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

def migrate_folder(folder):
    folder = aq_base(folder)
    names = folder.objectIds()
    migration = BTreeMigrationView(folder, None)
    migration.migrate(folder)
    assert hasattr(folder, '_mt_index') and hasattr(folder, '_tree')
    assert not hasattr(folder, '_objects')
    for name in names:
        assert name in folder._tree         # id in contents tree
        assert not hasattr(folder, name)    # no longer attribute


def mark_changed(content, note=None):
    content.modification_date = DateTime() #now
    aq_base(content)._p_changed = True
    if note is not None:
        txn = transaction.get()
        path = '/'.join(content.getPhysicalPath())[1:]
        if path:
            txn.note(path)
        txn.note(note)


def migrate_project(project):
    changes = []
    wrapped = project
    project = aq_base(project)
    if hasattr(project, 'logo') and isinstance(project.logo, str):
        # old-style logo, needs migration to plone.namedfile object
        project.logo = logo_image_factory(state['logo'])
        changes.append('Logo attribute migrated to NamedImage')
    if hasattr(project, '_objects'):
        # migrate from old-style folder to BTreeFolder2
        migrate_folder(project) # will mark folder as _p_changed
        changes.append('Migrated old folder contents to BTree')
    if changes:
        log = '; '.join(changes) if len(changes)>1 else changes[0]
        mark_changed(wrapped, log) # use aq-wrapped project here...
        


