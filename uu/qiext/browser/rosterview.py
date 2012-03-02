
from uu.qiext.user.interfaces import IWorkspaceRoster


class RosterView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.roster = None  # to be set in self.update()
    
    def update(self):
        self.roster = IWorkspaceRoster(self.context)
        self.members = self.roster.values() # list of IPropertiedUser objects
    
    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)

