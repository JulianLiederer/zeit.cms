# Copyright (c) 2006-2011 gocept gmbh & co. kg
# See also LICENSE.txt

import z3c.flashmessage.interfaces
import zc.resourcelibrary
import zc.resourcelibrary.resourcelibrary
import zeit.cms.browser
import zeit.cms.browser.interfaces
import zeit.cms.checkout.interfaces
import zeit.cms.repository.interfaces
import zeit.cms.section.interfaces
import zope.app.basicskin.standardmacros
import zope.component
import zope.location.interfaces
import zope.security.proxy


EXCLUDE_LIBRARIES = [
    'zeit.cms.error',  # only makes sense on error pages
    'zeit.wysiwyg.fckeditor',  # too convoluted to make behave nicely
]


class StandardMacros(zope.app.basicskin.standardmacros.StandardMacros):

    macro_pages = ('main_template',)

    def messages(self):
        receiver = zope.component.getUtility(
            z3c.flashmessage.interfaces.IMessageReceiver)
        return list(receiver.receive())

    @property
    def context_title(self):
        title = ''
        list_repr = zope.component.queryMultiAdapter(
            (self.context, self.request),
            zeit.cms.browser.interfaces.IListRepresentation)
        if list_repr is not None:
            title = list_repr.title
        if not title:
            title = self.context.__name__
        if (not title
            and zope.location.interfaces.ISite.providedBy(self.context)):
                title = '/'
        if not title:
            title = str(self.context)
        return title

    @property
    def resource_libraries(self):
        for library in zc.resourcelibrary.resourcelibrary.library_info.keys():
            if library in EXCLUDE_LIBRARIES:
                continue
            zc.resourcelibrary.need(library)

    @property
    def type_declaration(self):
        no_type = type(
            'NoTypeDeclaration', (object,), dict(type_identifier='unknown'))
        return zeit.cms.interfaces.ITypeDeclaration(self.context, no_type)

    @property
    def context_location(self):
        if zeit.cms.checkout.interfaces.ILocalContent.providedBy(self.context):
            return 'workingcopy'
        elif zeit.cms.repository.interfaces.IRepositoryContent.providedBy(
            self.context):
            return 'repository'
        else:
            return 'unknown'

    @property
    def section(self):
        section = zeit.cms.section.interfaces.ISection(self.context, None)
        for iface in zope.interface.providedBy(section):
            if issubclass(zope.security.proxy.getObject(iface),
                          zeit.cms.section.interfaces.ISection):
                return iface.__name__
        return 'unknown'
