from collective.teamwork.interfaces import IProjectContext
from collective.teamwork.user.interfaces import IWorkspaceRoster
from collective.teamwork.browser.membership import WorkspaceViewBase


class PurgeUserView(WorkspaceViewBase):
    """View to purge a single user from project"""

    def __init__(self, context, request):
        if not IProjectContext.providedBy(context):
            raise ValueError('Can only purge from top-level projects')
        super(PurgeUserView, self).__init__(context, request)

    def update(self, *args, **kwargs):
        self.roster = IWorkspaceRoster(self.context)
        if 'confirm_purge' in self.request.form:
            username = self.request.form.get('purgeuser').strip()
            if username not in self.roster:
                raise ValueError('User name for purge not found %s' % username)
            if not self.roster.can_purge(username):
                raise ValueError('User name %s locked from purging.' % username)
            self.roster.purge(username)
            msg = u'User %s permanently removed from site.' % (username,)
            self.status.addStatusMessage(msg, type='info')
            self._log(msg)

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # form template

