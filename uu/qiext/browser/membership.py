


class WorkspaceMembership(object):
    """
    Workspace membership view, provides a front-end around
    backend adapters for workspace in uu.qiext.user modules.
    """
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
   
    def update(self, *args, **kwargs):
        pass #TODO implement as needed
     
    def __call__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self.index(*args, **kwargs)  # provided by Five magic

