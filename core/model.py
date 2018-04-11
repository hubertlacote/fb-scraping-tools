from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil import parser
import logging
import re


def append_times(new_times, times):
    """ Add times from new_times that are not in times.

    >>> append_times(OrderedDict([('1', {'times': [1500000000]})]), {})
    True
    >>> append_times(OrderedDict([('1', {'times': [1500000000]})]), \
{'1': {'times': [1500000000]}})
    False
    >>> append_times(OrderedDict([('2', {'times': [1500000000]})]), \
{'1': {'times': [1500000000]}})
    True
    >>> append_times(OrderedDict([('1', {'times': [1500000099]})]), \
{'1': {'times': [1500000000]}})
    True
    """
    changes = False
    for user in new_times.keys():

        new_lats = new_times[user]
        if "times" not in new_lats:
            logging.warn("No times found for user '{0}'".format(user))
            continue
        new_lats = new_times[user]["times"]

        if user not in times:
            times[user] = {"times": []}

        for new_lat in new_lats:
            if not times[user]["times"]:
                logging.info("User {0}: {1}".format(user, new_lat))
                times[user]["times"].append(new_lat)
                changes = True
            elif new_lat != times[user]["times"][-1]:
                logging.info("User {0}: {1} > {2}".format(
                    user, new_lat, times[user]["times"][-1]))
                times[user]["times"].append(new_lat)
                changes = True

    return changes


def parse_relative_time(date_str):
    """
    >>> parse_relative_time("5 mins")
    datetime.timedelta(0, 300)
    >>> parse_relative_time("1 min")
    datetime.timedelta(0, 60)
    >>> parse_relative_time("7 hrs")
    datetime.timedelta(0, 25200)
    >>> parse_relative_time("1 hr")
    datetime.timedelta(0, 3600)
    >>> parse_relative_time("Just now")
    datetime.timedelta(0)
    >>> parse_relative_time("Not a date")
    """

    found = re.findall(r'\d+ hr', date_str)
    if found:
        hours = int(found[0].split(" hr")[0])
        return timedelta(hours=hours)

    found = re.findall(r'\d+ min', date_str)
    if found:
        mins = int(found[0].split(" min")[0])
        return timedelta(minutes=mins)

    if "Just now" in date_str:
        return timedelta(minutes=0)

    return None


def parse_fuzzy_time(date_str):
    """
    >>> parse_fuzzy_time("Yesterday at 19:34")
    (datetime.time(19, 34), datetime.timedelta(1))
    >>> parse_fuzzy_time("Today at 19:34")
    (datetime.time(19, 34), datetime.timedelta(0))
    >>> parse_fuzzy_time("Not a date")
    """

    try:
        # fuzzy_with_tokens=True ignores yesterday / today when parsing
        t = parser.parse(date_str, fuzzy_with_tokens=True)
        parsed_time = t[0].time()
        ignored = t[1]

        delta = timedelta(seconds=0)
        for ignored_part in ignored:
            if "yesterday" in ignored_part.lower():
                delta = timedelta(hours=24)

        return tuple([parsed_time, delta])

    except Exception:

        return None


def parse_date(date_str):
    """
    >>> parse_date("22 April 2011 at 20:34")
    datetime.datetime(2011, 4, 22, 20, 34)
    >>> parse_date("9 July 2011")
    datetime.datetime(2011, 7, 9, 0, 0)
    >>> parse_date("September 2003")
    datetime.datetime(2003, 9, 1, 0, 0)
    """

    try:
        return datetime.strptime(date_str, "%d %B %Y at %H:%M")

    except Exception:

        logging.info("Parsing date: {0} - date incomplete".format(date_str))
        try:
            # We could directly parse all dates with parser,
            # but this allows to have logging only for incomplete dates
            return parser.parse(
                date_str, default=datetime(
                    year=datetime.now().year, month=1, day=1))

        except Exception:

            relative_time = parse_relative_time(date_str)
            if relative_time:
                return datetime.now() - relative_time

            fuzzy_t = parse_fuzzy_time(date_str)
            if fuzzy_t:
                fuzzy_time = fuzzy_t[0]
                delta = fuzzy_t[1]
                return datetime.now().replace(
                    hour=fuzzy_time.hour,
                    minute=fuzzy_time.minute,
                    second=fuzzy_time.second) - delta

            else:
                logging.error("Failed to parse date: {0}".format(date_str))
                return datetime.now()
