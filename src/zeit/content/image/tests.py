# Copyright (c) 2007-2012 gocept gmbh & co. kg
# See also LICENSE.txt

from __future__ import with_statement
import mock
import pkg_resources
import unittest2 as unittest
import zeit.cms.interfaces
import zeit.cms.repository.interfaces
import zeit.cms.testing
import zeit.content.image.image
import zeit.content.image.imagegroup
import zope.component


ImageLayer = zeit.cms.testing.ZCMLLayer(
    pkg_resources.resource_filename(__name__, 'ftesting.zcml'),
    __name__, 'ImageLayer', allow_teardown=True)


class TestImageMetadataAcquisition(zeit.cms.testing.FunctionalTestCase):

    layer = ImageLayer

    def setUp(self):
        super(TestImageMetadataAcquisition, self).setUp()
        self.group_id = create_image_group().uniqueId
        with zeit.cms.checkout.helper.checked_out(self.group) as co:
            metadata = zeit.content.image.interfaces.IImageMetadata(co)
            metadata.title = u'Title'

    @property
    def group(self):
        return zeit.cms.interfaces.ICMSContent(self.group_id)

    @property
    def img(self):
        return self.group['new-hampshire-450x200.jpg']

    def test_acquired_in_repository(self):
        metadata = zeit.content.image.interfaces.IImageMetadata(self.img)
        self.assertEqual(u'Title', metadata.title)

    def test_acquired_in_workingcopy(self):
        with zeit.cms.checkout.helper.checked_out(self.img) as co:
            metadata = zeit.content.image.interfaces.IImageMetadata(co)
            self.assertEqual(u'Title', metadata.title)
            metadata.title = u'Image title'
        metadata = zeit.content.image.interfaces.IImageMetadata(self.img)
        self.assertEqual(u'Image title', metadata.title)

    def test_in_workingcopy_when_removed_in_repository(self):
        co = zeit.cms.checkout.interfaces.ICheckoutManager(self.img).checkout()
        del self.group[self.img.__name__]
        metadata = zeit.content.image.interfaces.IImageMetadata(co)
        self.assertEqual(None, metadata.title)


class TestGroupType(unittest.TestCase):

    def ggt(self, items, master=None):
        from zeit.content.image.imagegroup import get_group_type
        group = mock.Mock()
        group.__iter__ = lambda x:iter(items)
        group.master_image = master
        return get_group_type(group)

    def test_master_image_should_not_be_used_for_type(self):
        self.assertEqual('e2', self.ggt(['a.e1', 'b.e2', 'c.e3'],
                                        master='a.e1'))

    def test_no_master_image_should_chooses_first_image(self):
        self.assertEqual('e1', self.ggt(['a.e1', 'b.e2', 'c.e3']))

    def test_only_master_image_should_choose_master_image(self):
        self.assertEqual('e1', self.ggt(['a.e1'], master='a.e1'))

    def test_items_without_extensions_should_be_ignored(self):
        self.assertEqual('e2', self.ggt(['a', 'b.e2', 'c.e3']))

    def test_no_items_should_return_empty_type(self):
        self.assertEqual('', self.ggt([]))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(zeit.cms.testing.FunctionalDocFileSuite(
        'README.txt',
        'syndication.txt',
        'syndication2.txt',
        'transform.txt',
        'masterimage.txt',
        layer=ImageLayer))
    suite.addTest(unittest.makeSuite(TestImageMetadataAcquisition))
    suite.addTest(unittest.makeSuite(TestGroupType))
    return suite


def create_image_group(file_name=None):
    repository = zope.component.getUtility(
        zeit.cms.repository.interfaces.IRepository)
    group = zeit.content.image.imagegroup.ImageGroup()
    repository['image-group'] = group
    group = repository['image-group']
    for filename in ('new-hampshire-450x200.jpg',
                     'new-hampshire-artikel.jpg',
                     'obama-clinton-120x120.jpg'):
        image = zeit.content.image.image.LocalImage()
        image.mimeType = 'image/jpeg'
        fh = image.open('w')
        if file_name is None:
            file_name = pkg_resources.resource_filename(
                __name__, 'browser/testdata/%s' % filename)
        fh.write(open(file_name, 'rb').read())
        fh.close()
        group[filename] = image
    return group


def create_image_group_with_master_image(file_name=None):
    repository = zope.component.getUtility(
        zeit.cms.repository.interfaces.IRepository)
    group = zeit.content.image.imagegroup.ImageGroup()
    group.master_image = u'master-image.jpg'
    repository['group'] = group
    image = zeit.content.image.image.LocalImage()
    image.mimeType = 'image/jpeg'
    if file_name is None:
        fh = repository['2006']['DSC00109_2.JPG'].open()
    else:
        fh = open(file_name)
    image.open('w').write(fh.read())
    repository['group']['master-image.jpg'] = image
    return repository['group']
