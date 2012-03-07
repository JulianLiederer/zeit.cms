# coding: utf8
# Copyright (c) 2007-2011 gocept gmbh & co. kg
# See also LICENSE.txt

from zeit.cms.i18n import MessageFactory as _
import time
import xml.sax.saxutils
import zc.datetimewidget.datetimewidget
import zeit.cms.browser.interfaces
import zeit.cms.browser.view
import zeit.cms.interfaces
import zeit.cms.repository.interfaces
import zope.app.form.browser
import zope.app.form.browser.interfaces
import zope.app.form.browser.itemswidgets
import zope.app.form.browser.sequencewidget
import zope.app.form.browser.widget
import zope.app.form.interfaces
import zope.app.pagetemplate
import zope.cachedescriptors.property
import zope.component
import zope.formlib.interfaces
import zope.interface
import zope.schema
import zope.schema.interfaces
import zope.traversing.browser.interfaces


class ObjectReferenceWidget(zope.app.form.browser.widget.SimpleInputWidget):

    _missing = u""
    template = zope.app.pagetemplate.ViewPageTemplateFile(
        'object-reference-widget.pt')

    def __init__(self, context, source, request):
        super(ObjectReferenceWidget, self).__init__(context, request)
        self.source = source

    def __call__(self):
        return self.template()

    def _toFieldValue(self, input):
        if input == self._missing:
            return self.context.missing_value
        content = zeit.cms.interfaces.ICMSContent(input, None)
        if content is None:
            raise zope.app.form.interfaces.ConversionError(
                _("The object could not be found."))
        try:
            self.context.validate(content)
        except zope.schema.ValidationError, e:
            self._error = zope.app.form.interfaces.WidgetInputError(
                self.context.__name__, self.label, e)
            raise self._error

        return content

    def _toFormValue(self, value):
        if value == self.context.missing_value:
            return self._missing
        return value.uniqueId

    @property
    def default_browsing_location(self):
        location = zope.component.queryMultiAdapter(
            (self.context.context, self.source),
            zeit.cms.browser.interfaces.IDefaultBrowsingLocation)
        if location is None:
            return self.repository
        return location

    @zope.cachedescriptors.property.Lazy
    def repository(self):
        return zope.component.getUtility(
            zeit.cms.repository.interfaces.IRepository)

    @property
    def type_filter_token(self):
        return self.source.name

    @property
    def show_popup(self):
        """True if the popup should be displayed automatically upon page load.
        """
        present_marker = self.request.form.get('%s.present' % self.name)
        has_input = self._getFormValue()

        # Only show the object browser when there was no previous input, i.e.
        # when the field was just added. Also only show the object browser
        # automatically when we are in a sequence widget (endswith .)
        if not has_input and not present_marker and self.name.endswith('.'):
            return 'true'

        return 'false'

    @property
    def add_view(self):
        view = self.context.queryTaggedValue('zeit.cms.addform.contextfree')
        if view is None:
            return 'null'
        return "'%s'" % view

    @property
    def workflow(self):
        workflow = zope.component.getMultiAdapter(
            (self._getCurrentValue(), self.request, self),
            zope.viewlet.interfaces.IViewletManager,
            name='zeit.cms.workflow-indicator')
        workflow.update()
        return workflow.render()


class ObjectReferenceSequenceWidget(
    zope.app.form.browser.sequencewidget.SequenceWidget):
    """A specialised sequence widget which allows dropping objects."""

    def __call__(self):
        quoted_name = xml.sax.saxutils.quoteattr(self.name)
        result = ['<div id=%s>%s</div>' % (
            quoted_name,
            super(ObjectReferenceSequenceWidget, self).__call__())]
        result.append('<script language="javascript">')
        result.append('new zeit.cms.ObjectReferenceSequenceWidget(%s);' %
                      quoted_name)
        result.append('</script>')
        return ''.join(result)


class ObjectReferenceDisplayWidget(
    zope.app.form.browser.widget.DisplayWidget):

    def __init__(self, context, source, request):
        super(ObjectReferenceDisplayWidget, self).__init__(context, request)
        self.source = source

    def __call__(self):
        if self._renderedValueSet():
            value = self._data
        else:
            value = self.context.default
        if value == self.context.missing_value:
            return ""

        url = zope.component.getMultiAdapter(
            (value, self.request),
            zope.traversing.browser.interfaces.IAbsoluteURL)
        link_id = 'link.%s' % time.time()

        link = zope.app.form.browser.widget.renderElement(
            'a', href=url, id=link_id,
            contents=value.uniqueId)
        script = ('<script language="javascript">\n'
                  '    new zeit.cms.LinkToolTip("%s")\n'
                  '</script>') % link_id
        workflow = zope.component.getMultiAdapter(
            (value, self.request, self),
            zope.viewlet.interfaces.IViewletManager,
            name='zeit.cms.workflow-indicator')
        workflow.update()
        return link + '\n' + workflow.render() + '\n' + script


@zope.component.adapter(
    zope.schema.interfaces.ITuple,
    zope.schema.interfaces.IObject,
    zope.publisher.interfaces.browser.IBrowserRequest)
@zope.interface.implementer(zope.app.form.interfaces.IInputWidget)
def objectWidgetMultiplexer(context, field, request):
    return zope.component.getMultiAdapter(
        (context, field, field.schema, request),
        zope.app.form.interfaces.IInputWidget)


@zope.component.adapter(
    zope.schema.interfaces.ITuple,
    zope.schema.interfaces.IObject,
    zope.publisher.interfaces.browser.IBrowserRequest)
@zope.interface.implementer(zope.app.form.interfaces.IDisplayWidget)
def objectDisplayWidgetMultiplexer(context, field, request):
    return zope.component.getMultiAdapter(
        (context, field, field.schema, request),
        zope.app.form.interfaces.IDisplayWidget)


class MultiObjectSequenceWidget(
    zope.app.form.browser.widget.SimpleInputWidget):

    template = zope.app.pagetemplate.ViewPageTemplateFile(
        'objectsequence-edit-widget.pt')

    def __init__(self, context, source, request):
        super(MultiObjectSequenceWidget, self).__init__(context, request)
        self.source = source

    def __call__(self):
        return self.template()

    def hasInput(self):
        return self.name + '.count' in self.request.form

    def _toFormValue(self, value):
        result = []
        if value is None:
            return result
        for obj in value:
            if zeit.cms.interfaces.ICMSContent.providedBy(obj):
                result.append({'uniqueId': obj.uniqueId})
        return result

    def _getFormValue(self):
        """Returns a value suitable for use in an HTML form.

        Detects the status of the widget and selects either the input value
        that came from the request, the value from the _data attribute or the
        default value.
        """
        try:
            input_value = self._getCurrentValueHelper()
        except zope.app.form.interfaces.InputErrors:
            form_value = self._toFormValue(
                self._toFieldValue(self._getFormInput(self._missing)))
        else:
            form_value = self._toFormValue(input_value)
        return form_value

    def _getFormInput(self, default=None):
        count_str = self.request.get(self.name + '.count')
        if count_str is None:
            return default
        count = int(count_str)
        result = []
        for idx in range(count):
            result.append(self.request.get('%s.%s' % (self.name, idx)))
        return result

    def _toFieldValue(self, value):
        field_value = tuple(zeit.cms.interfaces.ICMSContent(unique_id, None)
                            for unique_id in value)
        return tuple(value for value in field_value if value is not None)

    @property
    def marker(self):
        count = len(self._getFormValue())
        return (
            '<input type="hidden" id="%s.count" name="%s.count" value="%d" />'
            % (self.name, self.name, count))

    @zope.cachedescriptors.property.Lazy
    def query_view(self):
        return zope.component.queryMultiAdapter(
            (self.source, self.request),
            zope.formlib.interfaces.ISourceQueryView)

    @zope.cachedescriptors.property.Lazy
    def add_view(self):
        return self.context.value_type.queryTaggedValue(
            'zeit.cms.addform.contextfree')

    @property
    def accept_classes(self):
        return js_escape_check_types(self.source)


class ObjectSequenceWidgetDetails(zeit.cms.browser.view.Base):
    """Render details about an content object."""

    @zope.cachedescriptors.property.Lazy
    def list_repr(self):
        return zope.component.queryMultiAdapter(
            (self.context, self.request),
            zeit.cms.browser.interfaces.IListRepresentation)

    @zope.cachedescriptors.property.Lazy
    def common_metadata(self):
        return zeit.cms.content.interfaces.ICommonMetadata(self.context, None)

    @property
    def teaser_title(self):
        if self.common_metadata is not None:
            return self.common_metadata.teaserTitle
        if self.list_repr is not None:
            return self.list_repr.title

    @property
    def supertitle(self):
        if self.common_metadata is not None:
            return self.common_metadata.supertitle

    @property
    def preview_url(self):
        return zope.component.queryMultiAdapter(
            (self.context, 'preview'),
            zeit.cms.browser.interfaces.IPreviewURL)

    @zope.cachedescriptors.property.Lazy
    def graphical_preview_url(self):
        thumbnail = zope.component.queryMultiAdapter(
            (self.context, self.request), name='thumbnail')
        if thumbnail is None:
            return
        return self.url('@@thumbnail')


class MultiObjectSequenceDisplayWidget(
    zope.app.form.browser.widget.DisplayWidget):

    template = zope.app.pagetemplate.ViewPageTemplateFile(
        'objectsequence-display-widget.pt')

    def __init__(self, context, source, request):
        super(MultiObjectSequenceDisplayWidget, self).__init__(
            context, request)
        self.source = source

    def __call__(self):
        return self.template()

    def get_values(self):
        if self._renderedValueSet():
            value = self._data
        else:
            value = self.context.default
        result = []
        for obj in value:
            if zeit.cms.interfaces.ICMSContent.providedBy(obj):
                result.append(obj)
        return result


def js_escape_check_types(source):
    # convert unicode, JS needs 'foo', not u'foo'
    return repr(['type-' + str(x) for x in source.get_check_types()])


DROP_TEMPLATE = u"""\
<div class="drop-object-widget" id="%(name)s">
    <input type="hidden" name="%(name)s" value="%(value)s" />
    <div class="object-reference"></div>
</div>
<script>new zeit.cms.DropObjectWidget("%(name)s", %(accept)s);</script>
"""


class DropObjectWidget(zope.app.form.browser.widget.SimpleInputWidget):

    def __init__(self, context, source, request):
        super(DropObjectWidget, self).__init__(context, request)
        self.source = source

    def __call__(self):
        return DROP_TEMPLATE % {
            'name': self.name,
            'value': self._getFormValue(),
            'accept': self.accept_classes,
        }

    def _toFieldValue(self, input):
        if input == self._missing:
            return self.context.missing_value
        try:
            return zeit.cms.interfaces.ICMSContent(input)
        except TypeError:
            msg = _("The object '${id}' could not be found.",
                    mapping=dict(id=input))
            msg = zope.i18n.translate(msg, context=self.request)
            raise zope.formlib.interfaces.ConversionError(msg)

    def _toFormValue(self, value):
        if value == self.context.missing_value:
            return self._missing
        return value.uniqueId

    @property
    def accept_classes(self):
        return js_escape_check_types(self.source)


DATETIME_WIDGET_ADDITIONAL = """\
<input type="button" value="%(label)s"
    onclick="javascript:var date = new Date();
        %(increase)s;
        $('%(field)s').value = date.print('%%Y-%%m-%%d %%H:%%M:%%S');
        $('%(field)s').focus();
        MochiKit.Signal.signal(
            '%(field)s', 'onchange', {target: $('%(field)s')});
        " />
"""
DATETIME_WIDGET_INFTY = u"""\
<input type="button" value="∞"
    onclick="javascript:$('%(field)s').value = '';
        $('%(field)s').focus();
        MochiKit.Signal.signal(
            '%(field)s', 'onchange', {target: $('%(field)s')});
    " />
"""


class DatetimeWidget(zc.datetimewidget.datetimewidget.DatetimeWidget):
    """A datetime widget with additional buttons."""

    def __call__(self):
        html = super(self.__class__, self).__call__()
        week = DATETIME_WIDGET_ADDITIONAL % dict(
            field=self.name,
            label="1W",
            increase="date.setDate(date.getDate() + 7)")
        month = DATETIME_WIDGET_ADDITIONAL % dict(
            field=self.name,
            label="1M",
            increase="date.setMonth(date.getMonth() + 1)")
        infty = DATETIME_WIDGET_INFTY % dict(
            field=self.name)
        return (u'<div class="dateTimeWidget">'
                + html + week + month + infty
                + '</div>')

    def _configuration(self):
        conf = super(DatetimeWidget, self)._configuration()
        conf.onClose = "zeit.cms.get_datetime_close('{0}')".format(self.name)
        return conf


def CheckboxWidget(context, request):
    widget = zope.app.form.browser.CheckBoxWidget(context, request)
    widget.reversed = True
    return widget


def CheckboxDisplayWidget(context, request):
    widget = CheckboxWidget(context, request)
    widget.extra = 'disabled="disabled"'
    return widget
