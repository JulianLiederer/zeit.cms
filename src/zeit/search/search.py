# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import urllib
import urllib2

import zope.component
import zope.interface

import gocept.lxml.objectify

import zeit.cms.interfaces
import zeit.cms.browser.interfaces
import zeit.connector.search

import zeit.search.config
import zeit.search.interfaces


class SearchResult(object):
    """Represents one item in a list of results."""

    zope.interface.implements(zeit.search.interfaces.ISearchResult)

    title = None
    author = None

    year = None
    volume = None
    page = None

    searchableText = None

    def __init__(self, unique_id):
        self.uniqueId = unique_id
        self.__name__ = unique_id.rsplit('/', 1)[1]


class MetaSearch(object):

    zope.interface.implements(zeit.search.interfaces.ISearch)

    def __call__(self, search_terms):
        search_interfaces = zope.component.getUtilitiesFor(
            zeit.search.interfaces.ISearchInterface)
        result = set()
        for name, search in search_interfaces:
            # XXX be more smart about combining results
            result = search(search_terms) | result
        return result


class XapianSearch(object):
    """Interface to Zeit Xapian."""

    zope.interface.implements(zeit.search.interfaces.ISearchInterface)

    indexes = set(['text'])

    def __call__(self, search_terms):
        if 'text' not in search_terms:
            return set()
        text = search_terms['text']
        tree = self.get_tree(text)
        return set(self.get_result(tree))

    def get_tree(self, text):
        base_url = zeit.search.config.XAPIAN_URL
        query = dict(q=text, op='AND', ps=100)
        url = '%s?%s' % (base_url, urllib.urlencode(query))
        request = urllib2.urlopen(url)
        return gocept.lxml.objectify.fromfile(request)

    def get_result(self, tree):
        for node in tree.page.result[:]:
            unique_id = node.get('url').replace(
                'http://www.zeit.de/', zeit.cms.interfaces.ID_NAMESPACE)
            result = SearchResult(unique_id)

            result.year = int(node.get('year'))
            result.volume = int(node.get('volume'))
            result.title = node.title
            result.author = node.author
            yield result


class MetadataSearch(object):

    _search_map = {
        'author': zeit.connector.search.SearchVar(
            'author', 'http://namespaces.zeit.de/document/'),
        'ressort': zeit.connector.search.SearchVar(
            'ressort', 'http://namespaces.zeit.de/document/'),
        'volume': zeit.connector.search.SearchVar(
            'volume', 'http://namespaces.zeit.de/document/'),
        'year': zeit.connector.search.SearchVar(
            'year', 'http://namespaces.zeit.de/document/'),
    }

    indexes = set(_search_map.keys())

    zope.interface.implements(zeit.search.interfaces.ISearchInterface)

    def __call__(self, search_terms):
        term = self.get_search_term(search_terms)
        if term is None:
            return set()
        var = self._search_map.get
        search_result = self.connector.search(
            [var('author'), var('year')], term)
        #return [SearchResult(*r) for r in search_result]

    def get_search_term(self, search):
        terms = []
        for field, var in self._search_map.items():
            value = search.get(field)
            if not value:
                continue
            terms.append(var == value)
        if not terms:
            return None
        return reduce(operator.and_, terms)

    @property
    def connector(self):
        return zope.component.getUtility(zeit.cms.interfaces.IConnector)
