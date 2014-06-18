from setuptools import setup, find_packages

version = '1.0.dev0'

setup(
    name='collective.teamwork',
    version=version,
    description="Plone add-on for workspace/workgroup components.",
    long_description=(
        open("README.rst").read() + "\n" +
        open("CHANGES.rst").read()
        ),
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Plone",
        ],
    keywords='',
    author='Sean Upton',
    author_email='sean.upton@hsc.utah.edu',
    url='http://github.com/collective',
    license='GPL',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['collective'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'pytz',
        'zope.schema>=3.8.0',
        'plone.app.dexterity',
        'plone.browserlayer',
        'Products.CMFPlone',
        'collective.wtf>=1.0b9',
        # -*- Extra requirements: -*-
    ],
    extras_require={
        'test': ['plone.app.testing'],
    },
    entry_points="""
    # -*- Entry points: -*-
    [z3c.autoinclude.plugin]
    target = plone
    """,
    )

