from datetime import datetime
from zeit.cms.checkout.helper import checked_out
from zeit.cms.interfaces import ICMSContent
from zeit.cms.related.interfaces import IRelatedContent
from zeit.cms.testcontenttype.testcontenttype import ExampleContentType
from zeit.cms.workflow.interfaces import IPublishInfo, IPublish
import gocept.testing.mock
import mock
import pytz
import threading
import time
import transaction
import zeit.cms.related.interfaces
import zeit.cms.testing
import zeit.workflow.publish
import zeit.workflow.testing
import zope.app.appsetup.product


class FakePublishTask(zeit.workflow.publish.PublishRetractTask):

    def __init__(self):
        self.test_log = []

    def run(self, obj):
        time.sleep(0.1)
        self.test_log.append(obj)


class PublishRetractLockingTest(zeit.cms.testing.FunctionalTestCase):

    layer = zeit.workflow.testing.LAYER

    def setUp(self):
        super(PublishRetractLockingTest, self).setUp()
        self.obj = zeit.cms.interfaces.ICMSContent(
            'http://xml.zeit.de/testcontent')
        self.desc = zeit.workflow.publish.SingleInput(self.obj)
        self.task = FakePublishTask()

    def run_task_in_thread(self, i, desc):
        zeit.cms.testing.set_site(self.getRootFolder())
        zeit.cms.testing.create_interaction()
        self.task(None, i, desc)
        transaction.abort()

    def test_simple(self):
        self.task(None, 1, self.desc)
        self.assertEquals(1, len(self.task.test_log))

    def test_parallel_with_same_obj(self):
        import zope.component
        t1 = threading.Thread(
            target=self.run_task_in_thread, args=(1, self.desc))
        t2 = threading.Thread(
            target=self.run_task_in_thread, args=(2, self.desc))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEquals(1, len(self.task.test_log))
        log = list(zope.component.getUtility(
            zeit.objectlog.interfaces.IObjectLog).get_log(self.obj))
        self.assertEquals(1, len(log))
        self.assertEquals(
            u'A publish/retract job is already active. Aborting',
            log[0].message)

    def test_parallel_with_differnt_obj(self):
        t1 = threading.Thread(
            target=self.run_task_in_thread, args=(1, self.desc))
        desc = zeit.workflow.publish.SingleInput(
            zeit.cms.interfaces.ICMSContent('http://xml.zeit.de/politik.feed'))
        t2 = threading.Thread(
            target=self.run_task_in_thread, args=(2, desc))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEquals(2, len(self.task.test_log))


class RelatedDependency(object):

    zope.component.adapts(zeit.cms.interfaces.ICMSContent)
    zope.interface.implements(
        zeit.workflow.interfaces.IPublicationDependencies)

    def __init__(self, context):
        self.context = context

    def get_dependencies(self):
        relateds = zeit.cms.related.interfaces.IRelatedContent(self.context)
        return relateds.related


class PublicationDependencies(zeit.cms.testing.FunctionalTestCase):

    layer = zeit.workflow.testing.LAYER

    def setUp(self):
        super(PublicationDependencies, self).setUp()
        self.patches = gocept.testing.mock.Patches()
        self.populate_repository_with_dummy_content()
        self.setup_dates_so_content_is_publishable()
        self.patches.add_dict(
            zope.app.appsetup.product.getProductConfiguration('zeit.workflow'),
            {'dependency-publish-limit': 2})
        zope.component.getSiteManager().registerAdapter(
            RelatedDependency, name='related')

    def tearDown(self):
        self.patches.reset()
        zope.component.getSiteManager().unregisterAdapter(
            RelatedDependency, name='related')
        super(PublicationDependencies, self).tearDown()

    def populate_repository_with_dummy_content(self):
        self.related = []
        for i in range(3):
            item = ExampleContentType()
            self.repository['t%s' % i] = item
            self.related.append(self.repository['t%s' % i])

    def setup_dates_so_content_is_publishable(self):
        DAY1 = datetime(2010, 1, 1, tzinfo=pytz.UTC)
        DAY2 = datetime(2010, 2, 1, tzinfo=pytz.UTC)
        DAY3 = datetime(2010, 3, 1, tzinfo=pytz.UTC)

        # XXX it would be nicer to patch this just for the items in question,
        # but we lack the mechanics to easily substitute adapter instances
        sem = self.patches.add('zeit.cms.content.interfaces.ISemanticChange')
        sem().last_semantic_change = DAY1
        sem().has_semantic_change = False
        for item in self.related:
            info = IPublishInfo(item)
            info.published = True
            info.date_last_published = DAY2
        dc = self.patches.add('zope.dublincore.interfaces.IDCTimes')
        dc().modified = DAY3

    def publish(self, content):
        IPublishInfo(content).urgent = True
        IPublish(content).publish()
        zeit.workflow.testing.run_publish()

    def test_should_not_publish_more_dependencies_than_the_limit_breadth(self):
        content = self.repository['testcontent']
        with checked_out(content) as co:
            IRelatedContent(co).related = tuple(self.related)

        BEFORE_PUBLISH = datetime.now(pytz.UTC)
        self.publish(content)

        self.assertEqual(
            2, len([x for x in self.related
                    if IPublishInfo(x).date_last_published > BEFORE_PUBLISH]))

    def test_should_not_publish_more_dependencies_than_the_limit_depth(self):
        content = [self.repository['testcontent']] + self.related
        for i in range(3):
            with checked_out(content[i]) as co:
                IRelatedContent(co).related = tuple([content[i + 1]])

        BEFORE_PUBLISH = datetime.now(pytz.UTC)
        self.publish(content[0])

        self.assertEqual(
            2, len([x for x in self.related
                    if IPublishInfo(x).date_last_published > BEFORE_PUBLISH]))


class SynchronousPublishTest(zeit.cms.testing.FunctionalTestCase):

    layer = zeit.workflow.testing.LAYER

    def test_publish_and_retract_in_same_process(self):
        article = ICMSContent('http://xml.zeit.de/online/2007/01/Somalia')
        info = IPublishInfo(article)
        info.urgent = True
        publish = IPublish(article)
        self.assertFalse(info.published)
        publish.publish(async=False)
        self.assertTrue(info.published)
        publish.retract(async=False)
        self.assertFalse(info.published)

        logs = reversed(zeit.objectlog.interfaces.ILog(article).logs)
        self.assertEqual(
            ['${name}: ${new_value}', 'Published', 'Retracted'],
            [x.message for x in logs])

    def test_synchronous_multi_publishing_works_with_unique_ids(self):
        article = ICMSContent('http://xml.zeit.de/online/2007/01/Somalia')
        info = IPublishInfo(article)
        info.urgent = True
        IPublish(article).publish_multiple([article.uniqueId], async=False)
        self.assertTrue(info.published)


class PublishPriorityTest(zeit.cms.testing.FunctionalTestCase):

    layer = zeit.workflow.testing.LAYER

    def test_determines_priority_via_adapter(self):
        content = self.repository['testcontent']
        info = IPublishInfo(content)
        info.urgent = True
        self.assertFalse(info.published)
        publish = IPublish(content)
        with mock.patch(
                'zeit.cms.workflow.interfaces.IPublishPriority') as priority:
            priority.return_value = zeit.cms.workflow.interfaces.PRIORITY_LOW
            publish.publish()
        zeit.workflow.testing.run_publish()
        self.assertFalse(info.published)
        zeit.workflow.testing.run_publish(
            zeit.cms.workflow.interfaces.PRIORITY_LOW)
        self.assertTrue(info.published)


class MultiPublishTest(zeit.cms.testing.FunctionalTestCase):

    layer = zeit.workflow.testing.LAYER

    def test_publishes_multiple_objects_in_single_script_call(self):
        c1 = zeit.cms.interfaces.ICMSContent(
            'http://xml.zeit.de/online/2007/01/Somalia')
        c2 = zeit.cms.interfaces.ICMSContent(
            'http://xml.zeit.de/online/2007/01/eta-zapatero')
        IPublishInfo(c1).urgent = True
        IPublishInfo(c2).urgent = True
        IPublish(self.repository).publish_multiple([c1, c2])
        with mock.patch(
                'zeit.workflow.publish.PublishTask'
                '.call_publish_script') as script:
            zeit.workflow.testing.run_publish(
                zeit.cms.workflow.interfaces.PRIORITY_LOW)
            script.assert_called_with(['work/online/2007/01/Somalia',
                                       'work/online/2007/01/eta-zapatero'])
        self.assertTrue(IPublishInfo(c1).published)
        self.assertTrue(IPublishInfo(c2).published)

    def test_accepts_uniqueId_as_well_as_ICMSContent(self):
        with mock.patch('zeit.workflow.publish.MultiPublishTask.run') as run:
            IPublish(self.repository).publish_multiple([
                self.repository['testcontent'],
                'http://xml.zeit.de/online/2007/01/Somalia'], async=False)
            objs = run.call_args[0][0]
            self.assertEqual([
                zeit.cms.interfaces.ICMSContent(
                    'http://xml.zeit.de/testcontent'),
                zeit.cms.interfaces.ICMSContent(
                    'http://xml.zeit.de/online/2007/01/Somalia')], objs)

    def test_empty_list_of_objects_does_not_start_publish_task(self):
        IPublish(self.repository).publish_multiple([])
        with mock.patch(
                'zeit.workflow.publish.PublishTask'
                '.call_publish_script') as script:
                    zeit.workflow.testing.run_publish(
                        zeit.cms.workflow.interfaces.PRIORITY_LOW)
                    self.assertFalse(script.called)

    def test_error_in_one_item_continues_with_other_items(self):
        c1 = zeit.cms.interfaces.ICMSContent(
            'http://xml.zeit.de/online/2007/01/Somalia')
        c2 = zeit.cms.interfaces.ICMSContent(
            'http://xml.zeit.de/online/2007/01/eta-zapatero')
        IPublishInfo(c1).urgent = True
        IPublishInfo(c2).urgent = True
        IPublish(self.repository).publish_multiple([c1, c2])
        transaction.commit()

        calls = []

        def after_publish(context, event):
            calls.append(context.uniqueId)
            if context.uniqueId == c1.uniqueId:
                raise RuntimeError('provoked')
        self.zca.patch_handler(
            after_publish,
            (zeit.cms.interfaces.ICMSContent,
             zeit.cms.workflow.interfaces.IPublishedEvent))

        log = zeit.objectlog.interfaces.ILog(c1)
        logs = len(list(log.get_log()))

        zeit.workflow.testing.run_publish(
            zeit.cms.workflow.interfaces.PRIORITY_LOW)

        # PublishedEvent still happens for c2, even though c1 raised
        self.assertIn(c2.uniqueId, calls)
        # Error is logged
        self.assertEqual(logs + 1, len(list(log.get_log())))
