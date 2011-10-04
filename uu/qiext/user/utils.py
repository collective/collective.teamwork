from uu.qiext.interfaces import IProjectContext


def group_namespace(context):
    """Get group namespace/prefix for a project or team context"""
    if not IProjectContext.providedBy(context):
        project = IProjectContext(context)
        return '%s-%s' % (project.getId(), context.getId())
    return context.getId()

