# vim: fileencoding=utf8 encoding=utf8
# Copyright (c) 2007-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import zope.interface
import zope.schema

import zc.form.field

import zeit.workflow.source
from zeit.cms.i18n import MessageFactory as _


class IWorkflow(zope.interface.Interface):
    """Zeit Workflow interface.

    Currently there is only a *very* simple and static property based workflow
    implemented.

    """

    edited = zope.schema.Choice(
        title=u"Bearbeitet (Redaktion)",
        default=False,
        source=zeit.workflow.source.TriState())

    corrected = zope.schema.Choice(
        title=u"Korrigiert",
        default=False,
        source=zeit.workflow.source.TriState())

    refined = zope.schema.Choice(
        title=u"Veredelt",
        default=False,
        source=zeit.workflow.source.TriState())

    images_added = zope.schema.Choice(
        title=u"Bilder hinzugefügt (Grafik)",
        default=False,
        source=zeit.workflow.source.TriState())

    published = zope.schema.Bool(
        title=_('Published'))

    urgent = zope.schema.Bool(
        title=u"Eilmeldung / Wochenende",
        default=False)

    release_period = zc.form.field.Combination(
        (zope.schema.Datetime(title=u"Von", required=False),
         zope.schema.Datetime(title=u"Bis", required=False)),
        title=u"Veröffentlichungszeitraum",
        description=u"Leer für keine Einschränkung",
        required=False)

    released_from = zope.interface.Attribute(
        "Object is released from this date.")
    released_to = zope.interface.Attribute(
        "Object is released to this date.")
