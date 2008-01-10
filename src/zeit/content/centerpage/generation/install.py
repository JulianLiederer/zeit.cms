# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import zope.app.component
import zope.app.component.hooks
import zope.app.zopeappgenerations

import zeit.cms.generation.install

import zeit.cms.content.interfaces
import zeit.cms.content.template


def install(root):
    site_manager = zope.component.getSiteManager()
    name = u'Centerpage templates'
    zeit.cms.generation.install.installLocalUtility(
        root, zeit.cms.content.template.TemplateManager,
        name, zeit.cms.content.interfaces.ITemplateManager,
        utility_name=name)


def evolve(context):
    site = zope.app.component.hooks.getSite()
    try:
        root = zope.app.zopeappgenerations.getRootFolder(context)
        zope.app.component.hooks.setSite(root)
        install(root)
    finally:
        zope.app.component.hooks.setSite(site)
