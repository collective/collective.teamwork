"""
register.py:    registration views for Projects and/or Teams in Plone 4,
                with email of project managers for respective project.
"""

__author__ = 'Sean Upton'
__copyright__ = 'Copyright, 2011-2013, The University of Utah.'
__license__ = 'GPL'


from zope.component import getUtility, getMultiAdapter


NEW_REG_SUBJ = '[%s] New User Registered'

NEW_REG_MSG = """
A new user registration related to your project is pending your approval.

A user has registered for the %s site, because they wish to
join the %s project.

The user name provided on registration is: %s

If you are a project manager, you can visit the project to search for
this user, and add them as a member of your project:

  %s


--

(This message is an automated notification).
"""

from plone.app.users.browser.register import RegistrationForm
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName

from collective.groupspaces.user.interfaces import IWorkspaceRoster
from collective.groupspaces.utils import project_containing


class ProjectRegistrationForm(RegistrationForm):
    """
    Custom registration form notifies project managers of new
    registrations for a project.
    """
    def _notification_subscribers(self, project):
        users = getToolByName(self.context, 'acl_users')
        if getattr(project, 'contacts', None):
            return project.contacts
        else:
            addr = lambda u: users.getUserById(u).getProperty('email')
            roster = IWorkspaceRoster(project)
            managers = roster.groups['managers'].keys()
            return [addr(u) for u in managers]

    def _notify_project_managers(self, username):
        """Notify project managers about registration, given username"""
        project = project_containing(self.context)
        title = project.Title()
        mailhost = getToolByName(self.context, 'MailHost')
        site = getUtility(ISiteRoot)
        recipients = self._notification_subscribers(project)
        if not recipients:
            return
        sender = site.getProperty('email_from_address')
        message = NEW_REG_MSG.strip() % (
            site.Title(),
            title,
            username,
            '%s/members.html' % project.absolute_url(),)
        mailhost.send(
            message,
            mto=recipients,
            mfrom=sender,
            subject=NEW_REG_SUBJ % title
            )

    @property
    def showForm(self):
        site = getUtility(ISiteRoot)
        panel = getMultiAdapter((site, self.request),
                                name='overview-controlpanel')
        return not (panel.mailhost_warning() and
                    site.getProperty('validate_email', True))

    def handle_join_success(self, data):
        """
        Call superclass handle_join_success(), then notify project
        managers for the project in which registration was called.
        """
        RegistrationForm.handle_join_success(self, data)
        self._notify_project_managers(data['username'])

