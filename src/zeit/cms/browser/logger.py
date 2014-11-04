import json
import logging
import zeit.cms.browser.view
import zope.component
import zope.error.interfaces


log = logging.getLogger('JavaScript')


class JSONLog(zeit.cms.browser.view.JSON):

    def json(self):
        decoded = json.loads(self.request.bodyStream.read(
            int(self.request['CONTENT_LENGTH'])))
        log_func = getattr(log, decoded['level'].lower())

        error_reporting_util = zope.component.getUtility(
            zope.error.interfaces.IErrorReportingUtility)
        username = error_reporting_util._getUsername(self.request)
        message = '%s (%s) %s' % (
            decoded['url'],
            username,
            '\n'.join(str(x) for x in decoded['message']))
        # XXX should we populate Python's logmessage timestamp from json?
        log_func(message)
        return {}
