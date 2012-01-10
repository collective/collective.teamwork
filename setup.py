from setuptools import setup, find_packages
import os

version = '0.1dev'

setup(name='uu.qiext',
      version=version,
      description="Plone add-on for quality-improvement groupware/extranet components.",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Plone",
        ],
      keywords='',
      author='Sean Upton',
      author_email='sean.upton@hsc.utah.edu',
      url='http://launchpad.net/upiq',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['uu'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'pytz',
          'zope.schema>=3.8.0',
          'plone.app.dexterity',
          'plone.browserlayer',
          'Products.qi',
          'Products.CMFPlone',
          # -*- Extra requirements: -*-
      ],
      extras_require = {
          'test': [ 'plone.app.testing', ],
      },
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )

