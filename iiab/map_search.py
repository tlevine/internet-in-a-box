# Internet-in-a-Box System
# By Braddock Gaskill, 16 Feb 2013
from .utils import whoosh_open_dir_32_or_64
from whoosh.qparser import QueryParser
from whoosh import sorting

from .utils import whoosh2dict


class MapSearch(object):
    def __init__(self, index_dir):
        """Initialize a search object.
        index_dir is the Whoosh index directory to use."""
        self.index_dir = index_dir

    def search(self, query, page=1, pagelen=20):
        """Return a sorted list of results.
        pagelen specifies the number of hits per page.
        page specifies the page of results to return (first page is 1)
        Set pagelen = None or 0 to retrieve all results.
        """
        query = unicode(query)  # Must be unicode
        population_sort_facet = sorting.FieldFacet("population", reverse=True)
        ix = whoosh_open_dir_32_or_64(self.index_dir)
        with ix.searcher() as searcher:
            query = QueryParser("ngram_name", ix.schema).parse(query)
            if pagelen is not None and pagelen != 0:
                try:
                    results = searcher.search_page(query, page, pagelen=pagelen,
                                                sortedby=population_sort_facet)
                except ValueError as e:  # Invalid page number
                    results = []
            else:
                results = searcher.search(query, limit=None, sortedby=population_sort_facet)
            #r = [x.items() for x in results]
            r = whoosh2dict(results)
        ix.close()
        # experiment with tucking away content for display in popup.
        for d in r:
            d['popupText'] = 'test content'
        return r

    def count(self, query):
        """Return total number of matching documents in index"""
        query = unicode(query)  # Must be unicode
        ix = whoosh_open_dir_32_or_64(self.index_dir)
        with ix.searcher() as searcher:
            query = QueryParser("title", ix.schema).parse(query)
            results = searcher.search(query)
            n = len(results)
        ix.close()
        return n
