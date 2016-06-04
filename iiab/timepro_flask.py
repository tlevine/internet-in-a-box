# -*- coding: utf-8 -*-
"""
    This module provides a simple WSGI profiler middleware for finding
    bottlenecks in web application.

    Example usage::

        from timepro_flask import TimeProMiddleware
        app = TimeProMiddleware(app)
"""
import sys
import time
import os.path

from . import timepro


class MergeStream(object):
    """An object that redirects `write` calls to multiple streams.
    Use this to log to both `sys.stdout` and a file::

        f = open('profiler.log', 'w')
        stream = MergeStream(sys.stdout, f)
        profiler = ProfilerMiddleware(app, stream)
    """

    def __init__(self, *streams):
        if not streams:
            raise TypeError('at least one stream must be given')
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)


class TimeProMiddleware(object):
    """Simple profiler middleware.  Wraps a WSGI application and profiles
    a request.  This intentionally buffers the response so that timings are
    more exact.

    By giving the `profile_dir` argument, pstat.Stats files are saved to that
    directory, one file per request. Without it, a summary is printed to
    `stream` instead.

    For the exact meaning of `sort_by` and `restrictions` consult the
    :mod:`profile` documentation.

    .. versionadded:: 0.9
       Added support for `restrictions` and `profile_dir`.

    :param app: the WSGI application to profile.
    :param stream: the stream for the profiled stats.  defaults to stderr.
    :param sort_by: a tuple of columns to sort the result by.
    :param restrictions: a tuple of profiling strictions, not used if dumping
                         to `profile_dir`.
    :param profile_dir: directory name to save pstat files
    """

    def __init__(self, app, stream=None,
                 sort_by=('time', 'calls'), restrictions=(), profile_dir=None):
        self._app = app
        self._stream = stream or sys.stdout
        self._sort_by = sort_by
        self._restrictions = restrictions
        self._profile_dir = profile_dir

    def __call__(self, environ, start_response):
        response_body = []

        def catching_start_response(status, headers, exc_info=None):
            start_response(status, headers, exc_info)
            return response_body.append

        def runapp():
            appiter = self._app(environ, catching_start_response)
            response_body.extend(appiter)
            if hasattr(appiter, 'close'):
                appiter.close()

        url = environ.get('PATH_INFO').strip('/').replace('/', '.') or 'root'
        timepro.timepro().activate()
        timepro.timepro().start(url)
        start = time.time()
        runapp()
        body = ''.join(response_body)
        elapsed = time.time() - start
        timepro.timepro().end(url)
        if elapsed > 1.0:
            timepro.timepro().log_all()
            timepro.timepro().deactivate()

        if self._profile_dir is not None:
            prof_filename = os.path.join(self._profile_dir,
                                         '%s.%s.%06dms.%d.prof' % (
                                             environ['REQUEST_METHOD'],
                                             environ.get('PATH_INFO').strip('/').replace('/', '.') or 'root',
                                             elapsed * 1000.0,
                                             time.time()
                                        ))
            #p.dump_stats(prof_filename)

        else:
            #stats = Stats(p, stream=self._stream)
            #stats.sort_stats(*self._sort_by)

            #self._stream.write('-' * 80)
            #self._stream.write('\nPATH: %r\n' % environ.get('PATH_INFO'))
            #stats.print_stats(*self._restrictions)
            #self._stream.write('-' * 80 + '\n\n')
            pass

        return [body]
