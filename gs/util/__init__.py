from datetime import datetime
from dateutil.parser import parse as dateutil_parse
from dateutil.relativedelta import relativedelta

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
