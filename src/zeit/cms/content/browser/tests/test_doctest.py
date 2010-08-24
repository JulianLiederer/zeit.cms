# Copyright (c) 2007-2010 gocept gmbh & co. kg
# See also LICENSE.txt

import doctest
import unittest
import zeit.cms.testing


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(zeit.cms.testing.FunctionalDocFileSuite(
        'form.txt',
        'keyword.txt',
        'template.txt',
        'typechange.txt',
        'widget-subnav.txt',
        package='zeit.cms.content.browser'))
    suite.addTest(doctest.DocFileSuite(
        'widget.txt',
        optionflags=(doctest.REPORT_NDIFF + doctest.NORMALIZE_WHITESPACE +
                     doctest.ELLIPSIS),
        package='zeit.cms.content.browser'))
    return suite