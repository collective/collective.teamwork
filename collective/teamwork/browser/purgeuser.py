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
            userid = self.request.form.get('purgeuser').strip()
            if userid not in self.roster:
                raise ValueError('User id for purge not found %s' % userid)
            if not self.roster.can_purge(userid):
                raise ValueError('User id %s locked from purging.' % userid)
            self.roster.remove(userid, purge=True)
            msg = u'User %s permanently removed from site.' % (userid,)
            self.status.addStatusMessage(msg, type='info')
            self._log(msg)

    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # form template

