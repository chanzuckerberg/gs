import os, sys, struct
from datetime import datetime
from dateutil.parser import parse as dateutil_parse
from dateutil.relativedelta import relativedelta

from .compat import USING_PYTHON2

class Timestamp(datetime):
    """
    Integer inputs are interpreted as milliseconds since the epoch. Sub-second precision is discarded. Suffixes (s, m,
    h, d, w) are supported. Negative inputs (e.g. -5m) are interpreted as relative to the current date. Other inputs
    (e.g. 2020-01-01, 15:20) are parsed using the dateutil parser.
    """
    def __new__(cls, t):
        if isinstance(t, (str, bytes)) and t.isdigit():
            t = int(t)
        if not isinstance(t, (str, bytes)):
            from dateutil.tz import tzutc
            return datetime.fromtimestamp(t // 1000, tz=tzutc())
        try:
            units = {"weeks", "days", "hours", "minutes", "seconds"}
            diffs = {u: float(t[:-1]) for u in units if u.startswith(t[-1])}
            if len(diffs) == 1:
                return datetime.now().replace(microsecond=0) + relativedelta(**diffs)
            return dateutil_parse(t)
        except (ValueError, OverflowError, AssertionError):
            raise ValueError('Could not parse "{}" as a timestamp or time delta'.format(t))

class CRC32C:
    def __init__(self, data=None):
        import crc32c
        self._crc32c = crc32c
        self._csum = crc32c.crc32(data if data is not None else b"")

    def update(self, data):
        self._csum = self._crc32c.crc32(data, self._csum)

    def digest(self):
        return long_to_bytes(self._csum)

def long_to_bytes(n):
    s = b''
    if USING_PYTHON2:
        n = long(n)  # noqa
    pack = struct.pack
    while n > 0:
        s = pack(b'>I', n & 0xffffffff) + s
        n = n >> 32
    for i in range(len(s)):
        if s[i] != b'\000'[0]:
            break
    else:
        s = b'\000'
        i = 0
    s = s[i:]
    return s

def get_file_size(path):
    try:
        return os.path.getsize(path)
    except Exception:
        return -1
