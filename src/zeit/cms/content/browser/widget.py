import SilverCity.XML
import StringIO
import json
import lxml.etree
import zc.form.browser.combinationwidget
import zeit.cms.content.interfaces
import zeit.cms.content.sources
import zope.app.form.browser.interfaces
import zope.app.form.browser.textwidgets
import zope.app.form.browser.widget
import zope.app.form.interfaces
import zope.app.pagetemplate
import zope.component
import zope.formlib.widgets
import zope.interface


class XMLTreeWidget(zope.app.form.browser.textwidgets.TextAreaWidget):

    def _toFieldValue(self, input):
        try:
            return self.context.fromUnicode(input)
        except zope.schema.ValidationError, e:
            raise zope.app.form.interfaces.ConversionError(e)

    def _toFormValue(self, value):
        if value == self.context.missing_value:
            return self._missing
        else:
            # Etree very explicitly checks for the type and doesn't like a
            # proxied object
            value = zope.proxy.removeAllProxies(value)
            if value.getparent() is None:
                # When we're editing the whole tree we want to serialize the
                # root tree to get processing instructions.
                value = value.getroottree()
            return lxml.etree.tounicode(value, pretty_print=True).replace(
                '\n', '\r\n')


class XMLTreeDisplayWidget(zope.app.form.browser.widget.DisplayWidget):

    def __call__(self):
        if self._renderedValueSet():
            content = self._data
            content = zope.proxy.removeAllProxies(content)
            content = lxml.etree.tostring(content, pretty_print=True,
                                          encoding=unicode)
        else:
            content = self.context.default
        if not content:
            return u''
        io = StringIO.StringIO()
        SilverCity.XML.XMLHTMLGenerator().generate_html(
            io, content.encode('UTF-8'))
        return io.getvalue().decode('UTF-8')


# XXX This needs to be much smarter. Users need to be able to input
# - Special characters (like quotation marks),
#   outside of tags they need to be quoted, but not inside.
# - Markup (like <b>tags</b>), they must be stored unquoted and displayed
#   in the browser properly.
class XMLSnippetWidget(zope.app.form.browser.textwidgets.TextAreaWidget):

    def _toFieldValue(self, input):
        as_unicode = super(XMLSnippetWidget, self)._toFieldValue(input)
        if as_unicode:
            try:
                return self.context.fromUnicode(as_unicode)
            except zope.schema.ValidationError, error:
                raise zope.app.form.interfaces.ConversionError(
                    error.__doc__, error)
        return as_unicode


class CombinationWidget(
        zc.form.browser.combinationwidget.CombinationWidget):
    """Subclassed combination widget to change the template.

    NamedTemplate doesn't take the request into account so we cannot register a
    new template in our skin. This sucks.

    """

    template = zope.app.pagetemplate.ViewPageTemplateFile(
        'combinationwidget.pt')


class MasterSlaveDropdownUpdater(object):

    master_source = NotImplemented
    slave_source = NotImplemented

    def __init__(self, context, request):
        super(MasterSlaveDropdownUpdater, self).__init__(context, request)
        self.master_source = self.master_source(self.context)
        self.master_terms = zope.component.getMultiAdapter(
            (self.master_source, request),
            zope.app.form.browser.interfaces.ITerms)

    def get_result(self, master_token):
        try:
            master_value = self.master_terms.getValue(master_token)
        except KeyError:
            return []

        class Fake(object):
            zope.interface.implements(
                self.slave_source.factory.master_value_iface)
        fake = Fake()
        setattr(fake, self.slave_source.factory.master_value_key, master_value)

        source = self.slave_source(fake)
        terms = zope.component.getMultiAdapter(
            (source, self.request), zope.app.form.browser.interfaces.ITerms)
        result = []
        for value in source:
            term = terms.getTerm(value)
            result.append((term.title, term.token))

        return sorted(result)

    def __call__(self, master_token):
        result = self.get_result(master_token)
        self.request.response.setHeader('Cache-Control', 'public;max-age=3600')
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(sorted(result)).encode('utf8')


class SubNavigationUpdater(MasterSlaveDropdownUpdater):

    master_source = zeit.cms.content.sources.RessortSource()
    slave_source = zeit.cms.content.sources.SubRessortSource()


class ChannelUpdater(MasterSlaveDropdownUpdater):

    master_source = zeit.cms.content.sources.ChannelSource()
    slave_source = zeit.cms.content.sources.SubChannelSource()
