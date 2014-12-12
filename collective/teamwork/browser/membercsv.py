import csv
from cStringIO import StringIO

from zope.globalrequest import getRequest

from collective.teamwork.interfaces import IWorkspaceContext
from collective.teamwork.user.interfaces import IWorkspaceRoster


class WorkspaceMembershipCSV(object):
    """
    Adapter or view of workspace providing CSV output of membership.
    """

    DISP = 'attachment; filename=%s'

    ORDER = (
        'email',
        'fullname',
        'timezone',
        'description',
        )

    # some legacy or largely unused settings fields are noise:
    EXCLUDE = (
        'last_activity',
        'ext_editor',
        'wysiwyg_editor',
        'error_log_update',
        'portal_skin',
        'visible_ids',
        'listed',
        )

    def __init__(self, context, request=None):
        if not IWorkspaceContext.providedBy(context):
            raise ValueError
        self.context = context
        self.request = request if request else getRequest()
        self.schemakeys = []

    def _update_schema(self, members):
        """introspect schema keys from property sheet on first member found"""
        first = members[0]
        sheet = first.getPropertysheet(first.listPropertysheets()[0])
        # remove excluded keys from consideration:
        schemakeys = filter(
            lambda key: key not in self.EXCLUDE,
            sheet.propertyIds(),
            )
        # sorted base columns:
        base = [k for k in self.ORDER if k in schemakeys]
        # everything else, unsorted is appended to the sorted base:
        self.schemakkeys = base + [k for k in schemakeys if k not in base]

    def _info(self, user):
        _get = lambda name: user.getProperty(name)
        return dict((name, _get(name)) for name in self.schemakeys)

    def update(self, *args, **kwargs):
        # get list of IPropertiedUser objects for all members
        members = IWorkspaceRoster(self.context).values()
        self._update_schema(members)
        self.info = map(self._info, members)
        self.output = StringIO()
        self.output.write(u'\ufeff'.encode('utf8'))  # UTF-8 BOM for MSExcel
        self.writer = csv.DictWriter(
            self.output,
            self.schemakeys,
            extrasaction='ignore',
            )
        # write heading row:
        self.writer.writerow(dict([(n, n) for n in self.schemakeys]))
        for record in self.info:
            self.writer.writerow(record)
        self.output.seek(0)

    def index(self, *args, **kwargs):
        filename = '%s.csv' % self.context.getId()
        self.output.seek(0)
        output = self.output.read()
        if self.request:
            self.request.response.setHeader('Content-Type', 'text/csv')
            self.request.response.setHeader('Content-Length', str(len(output)))
            self.request.response.setHeader(
                'Content-Disposition',
                self.DISP % filename,
                )
        return output

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)

