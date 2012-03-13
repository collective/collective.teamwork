from plone.app.layout.viewlets.common import LogoViewlet, ViewletBase
from plone.app.layout.navigation.root import getNavigationRootObject
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


TAG = '<img src="%s" title="%s" alt="%s" />'


class ProjectLogoViewlet(LogoViewlet):
    
    def update(self):
        super(ProjectLogoViewlet, self).update()
        portal = self.portal_state.portal()
        navroot = getNavigationRootObject(self.context, portal)
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
            # backward-compatibility, old custom logo content item
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
    """ 
    
    index = ViewPageTemplateFile('home_icons.pt')
     
    def links(self):
        """
        returns list of dict containing icon link, link target, title.
        should only be accessed after calling self.update() (called
        by template should be fine).
        """
        result = []
        portal = self.portal_state.portal()
        navroot = getNavigationRootObject(self.context, portal)
        if navroot is portal:
            return result # empty links: in non-workspace (indirect) contexts
        mtool = getToolByName(portal, 'portal_membership')
        result.append({
            'url': self.navigation_root_url,    # set by ViewletBase.update()
            'icon': '%s/%s' % (self.site_url, '++resource++uu.qiext/homefolder.png'),
            'title': u'Go to home workspace / project',
            })
        if mtool.checkPermission('Manage site', navroot):
            # for the moment, only project managers see site root link.
            result.append({
                'url': self.site_url,           # set by ViewletBase.update()
                'icon': '%s/%s' % (self.site_url, '++resource++uu.qiext/go-top.png'),
                'title': u'Go to site root',
                })
        return result

