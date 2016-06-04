#!/usr/bin/env python
# Uses Woosh and zimpy to Index ZIM files for searching

import sys
import os
import re
import signal
import logging
import argparse
import traceback
from datetime import datetime, timedelta

from whoosh import index
from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import TEXT, NUMERIC, ID, Schema
from whoosh.qparser import QueryParser

from iiab.zimpy import ZimFile
from iiab.whoosh_search import index_directory_path

# Install progress bar package as it is really needed
# to help understand where the processing is
from progressbar import ProgressBar, Percentage, Bar, ETA

# For rendering HTML to text for indexing
from html2text import html2text

try:
    unicode
except NameError:
    unicode = str

logger = logging.getLogger()

ZIM_CACHE_SIZE = 1024
DEFAULT_MIME_TYPES = ["text/html", "text/plain"]
DEFAULT_MEMORY_LIMIT = 256
DEFAULT_COMMIT_PERIOD = 300
DEFAULT_COMMIT_LIMIT = 1000

def article_info_as_unicode(articles):
    for article_info in articles:
        # Make any strings into unicode objects
        for k,v in list(article_info.items()):
            if type(v) is str:
                article_info[k] = unicode(v)
        yield article_info

def content_as_text(zim_obj, article_info, index):
    "Return the contents of an article at a given index from the ZIM file as text"

    raw_content = zim_obj.get_article_by_index(index)[0]

    try:
        content = raw_content.decode("utf-8")
    except:
        content = raw_content.decode("latin1")
    
    # Strip out HTML so it is not indexed
    # It also converts to unicode in the process
    # Only do the stripping on HTML article types
    if "html" in zim_obj.mimeTypeList[article_info['mimetype']]:
        try:
            content = html2text(content)
        except ValueError:
            logger.error("Failed converting html to text from: %s at index: %d, skipping article" % (os.path.basename(zim_obj.filename), index))
            content = None

    return content

def get_schema():
    # Create schema used by all indexes
    # Use an unbounded cache for StemmingAnalyzer to speed up indexing
    schema = Schema(title=TEXT(stored=True, sortable=True), 
                    url=ID(stored=True, sortable=True),
                    content=TEXT(stored=False, analyzer=StemmingAnalyzer(cachesize = -1)),
                    blobNumber=NUMERIC(stored=True, sortable=True),
                    namespace=ID(stored=True, sortable=True),
                    fullUrl=ID,
                    clusterNumber=NUMERIC,
                    mimetype=NUMERIC,
                    parameter=ID,
                    parameterLen=NUMERIC,
                    revision=NUMERIC,
                    index=NUMERIC,
                    # Links to an article from others
                    reverse_links=NUMERIC(stored=True, sortable=True),
                    # Links from an article to others
                    forward_links=NUMERIC(stored=True, sortable=True))
    return schema

def load_links_file(zim_fn, links_dir):
    """Returns the contents of a links file with a count of forward and backward
    links for each file. The data type returned is a dictionary with the key
    being the article index and the value being a tuple with the TO and FROM
    links in that order."""
    
    links_filename = os.path.join(links_dir, os.path.splitext(os.path.basename(zim_fn))[0] + ".links")

    links_info = {}
    with open(links_filename, "r") as links_contents:
        # Discard header
        header = links_contents.readline()
        for links_line in links_contents.readlines():
            line_match = re.search('(\d+)\s+(\d+)\s+(\d+)', links_line)
            index, to_links, from_links = [ int(g) for g in line_match.groups() ]
            links_info[index] = (to_links, from_links)

    return links_info

class InProgress(object):
    """Stores articles being added to the index in case the writer stage is interrupted."""
    written = True
    content = None
    article_info = {}

    def start(self, content, article_info):
        self.written = False
        self.content = content
        self.article_info

    def finish(self):
        self.written = True
        self.content = None
        self.article_info = {}

def index_zim_file(zim_filename, output_dir=".", links_dir=None, index_contents=True, mime_types=DEFAULT_MIME_TYPES, memory_limit=DEFAULT_MEMORY_LIMIT, processors=1, commit_period=DEFAULT_COMMIT_PERIOD, commit_limit=DEFAULT_COMMIT_LIMIT, use_progress_bar=False, **kwargs):
    zim_obj = ZimFile(zim_filename, cache_size=ZIM_CACHE_SIZE)

    logger.info("Indexing: %s" % zim_filename)

    if not index_contents:
        logger.info("Not indexing article contents")


    if links_dir != None:
        logger.debug("Loading links file")
        links_info = load_links_file(zim_filename, links_dir)
        if len(links_info) == 0:
            logger.error("No links loaded from links directory: %s" % links_dir)
    else:
        links_info = {}
        logger.warning("No links directory specified.")

    # Figure out which mime type indexes from this file we will use
    logger.debug("All mime type names: %s" % zim_obj.mimeTypeList)
    logger.info("Using mime types:")
    mime_type_indexes = []
    for mt_re in mime_types:
        for mt_idx, mt_name in enumerate(zim_obj.mimeTypeList):
            if re.search(mt_re, mt_name):
                mime_type_indexes.append(mt_idx)
                logger.info(mt_name)

    index_dir = index_directory_path(output_dir, zim_filename)
    if not os.path.exists(index_dir):
        logger.debug("Creating index directory: %s" % index_dir)
        os.mkdir(index_dir)

    # Don't overwrite an existing index
    if index.exists_in(index_dir):
        logger.debug("Loading existing index")
        ix = index.open_dir(index_dir)
        searcher = ix.searcher()
    else:
        logger.debug("Creating new index")
        ix = index.create_in(index_dir, get_schema())
        searcher = None

    writer = ix.writer(limitmb=memory_limit, procs=processors)

    num_articles = zim_obj.header['articleCount']
    if use_progress_bar:
        pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], maxval=num_articles).start()
    else:
        logger.info("Not using progress bar, will display timestamped occasional updates.")

    # Counter for when to output occasional updates
    update_count = 0
    last_update = datetime.now()
    needs_commit = False

    for idx, article_info in enumerate(article_info_as_unicode(zim_obj.articles())):
        if use_progress_bar:
            pbar.update(idx)
        else:
            now = datetime.now()
            if update_count >= commit_limit or now > (last_update + timedelta(seconds=commit_period)):
                logger.info("%s - %d/%d - %.2f%%" % (now.isoformat(), idx, num_articles, (idx / float(num_articles)) * 100.0 ))
                update_count = 0
                last_update = now

                if needs_commit:
                    writer.commit()
                    writer = ix.writer(limitmb=memory_limit, procs=processors)
                    needs_commit = False
            else:
                update_count += 1

        # Skip articles of undesired mime types
        if article_info['mimetype'] not in mime_type_indexes:
            continue

        # Protect read of existing documents as sometimes there
        # incomplete writes
        try:
            if searcher != None:
                existing = searcher.document(url=article_info['url'])
            else:
                existing = None
        except:
            logger.exception("Unexpected exception when looking for existing indexed article for index: %d" % idx)
            existing = None
        
        # Skip articles that have already been indexed
        if existing != None:
            continue

        if index_contents:
            content = content_as_text(zim_obj, article_info, idx)
            # Whoosh seems to take issue with empty content
            # and complains about it not being unicode ?!
            if content != None and len(content.strip()) == 0:
                content = None
        else:
            content = None

        # Look for forward and backwards links
        if len(links_info) > 0:
            article_links = links_info.get(article_info['index'], None)
            if article_links != None:
                article_info['reverse_links'] = article_links[0]
                article_info['forward_links'] = article_links[1]
            else:
                logger.debug("No links info found for index: %d" % idx)

        writer.add_document(content=content, **article_info)
        needs_commit = True

    if use_progress_bar:
        pbar.finish()

    logger.info("Making final commit")

    writer.commit()

    logger.info("Finished")

def main(argv):
    parser =  argparse.ArgumentParser(description="Indexes the contents of a ZIM file using Woosh")
    parser.add_argument("zim_files", nargs="+", 
                        help="ZIM files to index")
    parser.add_argument("-o", "--output-dir", dest="output_dir", action="store",
                        default="./zim-index",
                        help="The base directory where Woosh indexes are written. One sub directory per file.")
    parser.add_argument("-l", "--links-dir", dest="links_dir", action="store",
                        default="./zim-links",
                        help="Directory where a pre-created text file with statistics of forward and reverse article links is located.")
    parser.add_argument("-m", "--mime-types", dest="mime_types",
                        metavar="MIME_TYPE", nargs="*", 
                        default=DEFAULT_MIME_TYPES,
                        help="Mimetypes of articles to index")
    parser.add_argument("--no-contents", dest="index_contents", action="store_false",
                        default=True,
                        help="Turn of indexing of article contents")
    parser.add_argument("--memory-limit", dest="memory_limit", action="store",
                        default=DEFAULT_MEMORY_LIMIT, type=int,
                        help="Set maximum memory in Mb to consume by writer")
    # Commented out as it seems to cause more problems than its worth
    #    parser.add_argument("--processors", dest="processors", action="store",
    #                        default=1, type=int,
    #                        help="Set the number of processors for use by the writer")
    parser.add_argument("--commit_period", dest="commit_period", action="store",
                        default=DEFAULT_COMMIT_PERIOD, type=int,
                        help="The maximum amount of time (in seconds) between commits")
    parser.add_argument("--commit_limit", dest="commit_limit", action="store",
                        default=DEFAULT_COMMIT_LIMIT, type=int,
                        help="The maximum number of documents to buffer before committing.")
    parser.add_argument("-p", dest="use_progress_bar", action="store_true",
                        help="Turn on a progress bar instead of time stamped percentage") 
    parser.add_argument("-v", dest="verbose", action="store_true",
                        help="Turn on verbose logging")

    args = parser.parse_args()

    # Set up logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    console = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(console)

    # Create base directory for indexes
    if not os.path.exists(args.output_dir):
        logger.debug("Creating output dir: %s" % args.output_dir)
        os.mkdir(args.output_dir)

    logger.debug("Using schema: %s" % get_schema())

    for zim_file in args.zim_files:
        index_zim_file(zim_file, **args.__dict__)


if __name__ == "__main__":
    main(sys.argv)
