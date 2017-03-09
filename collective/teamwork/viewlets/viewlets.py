from plone import api
from plone.app.layout.viewlets.common import LogoViewlet, ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.teamwork.interfaces import IWorkspaceContext


TAG = '<img src="%s" title="%s" alt="%s" />'

_marker = object()


class ProjectLogoViewlet(LogoViewlet):

    def update(self):
        super(ProjectLogoViewlet, self).update()
        navroot = api.portal.get_navigation_root(self.context)
        logo_title = navroot.Title()
        logofile = getattr(navroot, 'logo', None)
        if logofile is not None:
            filename = getattr(logofile, 'filename', None)
            if filename and logofile.getSize():
                # logo field has filename and data is not zero-byte/empty
                url = '%s/@@download/logo/%s' % (
                    self.navigation_root_url,
                    filename,
                    )
                self.logo_tag = TAG % (url, logo_title, logo_title)
        elif 'project_logo.jpg' in navroot.contentIds():
            # logo could be content in navroot, using naming convention
            url = '%s/project_logo.jpg/image' % self.navigation_root_url
            self.logo_tag = TAG % (url, logo_title, logo_title)
        else:
            # fallback to application logo image, navroot title alt text
            url = '%s/logo.png' % (self.navigation_root_url,)
            self.logo_tag = TAG % (url, logo_title, logo_title)


class HomeIconsViewlet(ViewletBase):
    """
    Viewlet for home and/or site icons for any context inside a
    site of project and team workspaces.
    
    ViewletBase makes available URLs for icon links via:
      * self.navigation_root_url
      * self.site_url
    """
    _can_manage = _marker
    _workspace_url = _marker

    index = ViewPageTemplateFile('home_icons.pt')
     
    def can_manage_membership(self):
        if self._can_manage is _marker:
            workspace = self.workspace_url()
            if workspace is None:
                return False
            permissions = api.user.get_permissions(obj=self.context)
            self._can_manage = permissions.get('Manage portal', False)
        return self._can_manage

    def workspace_url(self):
        if self._workspace_url is _marker:
            context = self.context
            # are we in a workspace or its front page?
            workspace = IWorkspaceContext.providedBy(context)
            if workspace:
                self._workspace_url = context.absolute_url()
            else:
                parent = context.__parent__
                if IWorkspaceContext.providedBy(parent):
                    name = context.getId()
                    workspace = getattr(parent, 'default_page', None) == name
                if not workspace:
                    self._workspace_url = None
                else:
                    self._workspace_url = parent.absolute_url()
        return self._workspace_url
 
    def links(self):
        """
        returns list of dict containing icon link, link target, title.
        should only be accessed after calling self.update() (called
        by template should be fine).
        """
        result = []
        # is workspace, provide membership link if user can manage
        if self.can_manage_membership():
            result.append({
                'url': '%s/%s' % (
                    self.workspace_url(),
                    '@@workspace_membership'
                    ),
                'icon': '%s/%s' % (
                    self.site_url,
                    '++resource++collective.teamwork/images/team48.png',
                    ),
                'title': 'Manage membership of this workspace',
                })
        portal = api.portal.get()
        navroot = api.portal.get_navigation_root(self.context)
        if navroot is portal:
            return result  # empty links: in non-workspace (indirect) contexts
        result.append({
            'url': self.navigation_root_url,
            'icon': '%s/%s' % (
                self.site_url,
                '++resource++collective.teamwork/images/Home-icon.svg',
                ),
            'title': u'Go to home workspace / project',
            })
        result.append({
            'url': self.site_url,
            'icon': '%s/%s' % (
                self.site_url,
                '++resource++collective.teamwork/images/Arrow_top_svg.svg',
                ),
            'title': u'Go to site root',
            })
        return result


class ProjectCSSViewlet(ViewletBase):
    """
    Inject project-specific CSS at ./project.css into page via
    plone.htmlhead.links viewlet manager.
    """
    
    index = ViewPageTemplateFile('projectcss.pt')

