from plone.app.layout.viewlets.common import PersonalBarViewlet as BASE
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class PersonalBarViewlet(BASE):
    """Personal bar with tools menu, overrides base/stock viewlet with
    a local template to inject the tools menu into the HTML right-of/
    next-to the personal bar.
    """
    index = ViewPageTemplateFile('personal_bar.pt')


