from __future__ import absolute_import, division, print_function, unicode_literals

import os, sys, datetime, errno

USING_PYTHON2 = True if sys.version_info < (3, 0) else False

if USING_PYTHON2:
    from StringIO import StringIO
    from repr import Repr
    str = unicode # noqa
    from ..packages.backports.functools_lru_cache import lru_cache
    from ..packages.backports.shutil_get_terminal_size import get_terminal_size
    from ..packages.backports.tempfile import TemporaryDirectory
    import subprocess32 as subprocess

    def makedirs(name, mode=0o777, exist_ok=False):
        try:
            os.makedirs(name, mode)
        except OSError as e:
            if not (exist_ok and e.errno == errno.EEXIST and os.path.isdir(name)):
                raise

    def median(data):
        data = sorted(data)
        n = len(data)
        if n == 0:
            raise Exception("no median for empty data")
        if n % 2 == 1:
            return data[n // 2]
        else:
            i = n // 2
            return (data[i - 1] + data[i]) / 2

    def timestamp(dt):
        if dt.tzinfo is None:
            from time import mktime
            return mktime((dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, -1, -1, -1)) + dt.microsecond / 1e6
        else:
            from dateutil.tz import tzutc
            return (dt - datetime.datetime(1970, 1, 1, tzinfo=tzutc())).total_seconds()
else:
    from io import StringIO
    from reprlib import Repr
    str = str
    from functools import lru_cache
    from shutil import get_terminal_size
    from tempfile import TemporaryDirectory
    import subprocess
    from os import makedirs
    from statistics import median
    timestamp = datetime.datetime.timestamp
