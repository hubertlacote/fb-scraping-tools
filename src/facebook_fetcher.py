from src.downloader import Downloader
from src import common

from collections import OrderedDict
from datetime import datetime
import json
import logging

def parse_buddy_list(raw_json):
    """
    >>> parse_buddy_list('for (;;); {"ms": [{"type": "chatproxy-presence", '
    ... '"userIsIdle": false, "chatNotif": 0, "gamers": [], "buddyList": {'
    ... '"111": {"lat": 1500000001}, '
    ... '"222": {"lat": 1500000002}}}, {"type": "buddylist_overlay",'
    ...  '"overlay": {"333": {"la": 1500000003, "a": 0, "vc": 0, "s":'
    ... '"push"}}}], "t": "msg", "u": 123, "seq": 3}')
    OrderedDict([('111', [1500000001]), ('222', [1500000002])])
    >>> parse_buddy_list("")
    OrderedDict()
    >>> parse_buddy_list('{ "overlay": { "111": { '
    ... '"a": 0, "c": 74, "la": 1500000003, "s": "push", "vc": 74 }}, '
    ... '"type": "buddylist_overlay"}')
    OrderedDict()
    >>> parse_buddy_list('{ "seq": 1, "t": "fullReload" }')
    OrderedDict()
    """
    valid_raw_json = raw_json.replace("for (;;); ", "")
    decoded_json = ""
    try:
        decoded_json = json.loads(valid_raw_json)
    except Exception as e:
        logging.error("Failed to decode JSON: '{0}', got exception:"
            " '{1}'".format(valid_raw_json, e))
        return OrderedDict()

    logging.debug("Got json: '{0}'".format(common.prettify(decoded_json)))
    if not "ms" in decoded_json:
        logging.error("Invalid json returned - not found 'ms'")
        logging.debug("Got instead: {0}".format(common.prettify(decoded_json)))
        return OrderedDict()

    flattened_json = {}
    for item in decoded_json["ms"]:
        flattened_json.update(item)
    if "buddyList" not in flattened_json:
        logging.error("Invalid json returned - not found 'buddyList'")
        logging.debug("Got instead: {0}".format(
            common.prettify(flattened_json)))
        return OrderedDict()

    buddy_list = flattened_json["buddyList"]
    flattened_buddy_list = {}
    for user in buddy_list:
        if "lat" in buddy_list[user]:
            flattened_buddy_list[user] = [buddy_list[user]["lat"]]

    return OrderedDict(sorted(flattened_buddy_list.items()))

def build_buddy_feed_url(user_id, client_id):
    return ("https://5-edge-chat.facebook.com/pull?channel=p_{0}&" + \
        # seq = 1 directly gives the full list
        "seq=1&" + \
        "partition=-2&clientid={1}&cb=ze0&idle=0&qp=yisq=129169&" + \
        "msgs_recv=0&uid={0}&viewer_uid={0}&sticky_token=1058&" + \
        "sticky_pool=lla1c22_chat-proxy&state=active"). \
            format(user_id, client_id)

def append_times(new_times, times):
    """ Add times from new_times that are not in times.

    >>> append_times(OrderedDict([('1', [150000])]), {})
    True
    >>> append_times(OrderedDict([('1', [150000])]), {'1': [150000]})
    False
    >>> append_times(OrderedDict([('2', [150000])]), {'1': [150000]})
    True
    >>> append_times(OrderedDict([('1', [150099])]), {'1': [150000]})
    True
    """
    changes = False
    for user in new_times.keys():

        new_lats = new_times[user]
        if not new_lats:
            logging.warn("No times found for user '{O}'".format(user))
            continue

        if user not in times:
            times[user] = []

        for new_lat in new_lats:
            if not times[user]:
                logging.info("User {0}: {1}".format(user, new_lat))
                times[user].append(new_lat)
                changes = True
            elif new_lat > times[user][-1]:
                logging.info("User {0}: {1} > {2}".format(
                    user, new_lat, times[user][-1]))
                times[user].append(new_lat)
                changes = True

    return changes

def parse_times(times, user_infos):
    """ Parse names using user_infos and times.

    >>> parse_times(OrderedDict([('1', [1500])]), {'1': {"Name": "John"}})
    {'John': ['1970-01-01 01:25:00']}
    >>> parse_times(OrderedDict([('1', None)]), {'1': {"Name": "John"}})
    {}
    >>> parse_times(OrderedDict([('1', [])]), {'1': {"Name": "John"}})
    {}
    >>> parse_times(OrderedDict([('1', [1500])]), {})
    {'1': ['1970-01-01 01:25:00']}
    >>> parse_times(OrderedDict([('1', [1500])]), {'1': {}})
    {'1': ['1970-01-01 01:25:00']}
    >>> parse_times(OrderedDict([('1', [1500])]), {'1': {"Name": ""}})
    {'1': ['1970-01-01 01:25:00']}
    """
    parsed = {}
    for user_id in times:

        current_times = times[user_id]
        if not current_times:
            logging.warn("Skipping user '{0}' - no times found".
                format(user_id))
            continue

        name = user_id
        if user_id not in user_infos or \
            "Name" not in user_infos[user_id] or \
                not user_infos[user_id]["Name"] :
            logging.warn("No name found for user '{0}'".
                format(user_id))
        else:
            name = user_infos[user_id]["Name"]

        parsed[name] = []
        for time in current_times:
            time_parsed = time
            if int(time) != -1:
                time_parsed = str(datetime.fromtimestamp(int(time)))
            parsed[name].append(time_parsed)

    return parsed

class FacebookFetcher:

    def __init__(self, downloader, config):
        self.downloader = downloader
        self.cookie = common.build_cookie(config)
        self.buddy_feed_url = build_buddy_feed_url(
            config.user_id, config.client_id)

    def fetch_last_active_times(self):
        """ Returns an OrderedDict, mapping user_id to list of epoch times.

        Does not throw, returns an empty OrderedDict if an error occurs.
        """

        try:
            response = self.downloader.fetch_url(self.cookie,
                self.buddy_feed_url, timeout_secs = 15)

            return parse_buddy_list(response.text)

        except Exception as e:
            logging.error("Error while downloading page '{0}', "
                "got exception: '{1}'".format(self.buddy_feed_url, e))
            return OrderedDict()
