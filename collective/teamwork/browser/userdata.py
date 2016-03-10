from plone.app.users.browser.userdatapanel import UserDataConfiglet

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


from collective.teamwork.user.interfaces import IWorkspaceRoster


class WorkspaceUserInfoForm(UserDataConfiglet):

    template = ViewPageTemplateFile('userprops.pt')

    def __init__(self, context, request):
        super(WorkspaceUserInfoForm, self).__init__(context, request)
        if self.userid is not None:
            roster = IWorkspaceRoster(context)
            if self.userid not in roster:
                self.userid = None

