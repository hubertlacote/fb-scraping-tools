from core.downloader import Downloader
from core.facebook_soup_parser import FacebookSoupParser
from core import common

from collections import OrderedDict
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
        logging.error(
            "Failed to decode JSON: '{0}', got exception:"
            " '{1}'".format(valid_raw_json, e))
        return OrderedDict()

    logging.debug("Got json: '{0}'".format(common.prettify(decoded_json)))
    if "ms" not in decoded_json:
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
    return (
        "https://5-edge-chat.facebook.com/pull?channel=p_{0}&" + \
        # seq = 1 directly gives the full list
        "seq=1&" + \
        "partition=-2&clientid={1}&cb=ze0&idle=0&qp=yisq=129169&" + \
        "msgs_recv=0&uid={0}&viewer_uid={0}&sticky_token=1058&" + \
        "sticky_pool=lla1c22_chat-proxy&state=active"). \
            format(user_id, client_id)


def build_friends_page_url(page_no):
    return "https://m.facebook.com/friends/center/friends/?ppk={0}". \
        format(page_no)


def build_about_page_url(user_id):
    return "https://m.facebook.com/profile.php?v=info&id={0}". \
        format(user_id)


class FacebookFetcher:

    def __init__(self, downloader, config):
        self.downloader = downloader
        self.fbParser = FacebookSoupParser()
        self.cookie = common.build_cookie(config)
        self.buddy_feed_url = build_buddy_feed_url(
            config.user_id, config.client_id)

    def fetch_last_active_times(self, retries=1):
        """ Returns an OrderedDict, mapping user_id to list of epoch times.

        Does not throw, returns an empty OrderedDict if an error occurs.
        """

        try:
            response = self.downloader.fetch_url(
                self.cookie, self.buddy_feed_url,
                timeout_secs=15, retries=retries)

            return parse_buddy_list(response.text)

        except Exception as e:
            logging.error(
                "Error while downloading page '{0}', "
                "got exception: '{1}'".format(self.buddy_feed_url, e))
            return OrderedDict()

    def fetch_friend_list(self):

        friend_list = {}
        page_no = 0

        while True:

            url = build_friends_page_url(page_no)
            try:
                response = self.downloader.fetch_url(
                    self.cookie, url, timeout_secs=15)

                friends_found = self.fbParser.parse_friends_page(
                    response.text)
                friend_list.update(friends_found)
                if not friends_found:
                    logging.info(
                        "No friends found on page {0}".
                        format(page_no))
                    return friend_list

                page_no = page_no + 1
                logging.info("Found {0} friends".format(len(friends_found)))

            except Exception as e:
                logging.error(
                    "Error while downloading page '{0}', "
                    "got exception: '{1}'".format(url, e))
                return friend_list

    def fetch_user_infos(self, user_ids):

        logging.info(
            "Querying '{0}' users from Facebook".
            format(len(user_ids)))

        infos = {}
        for user_id in user_ids:

            url = build_about_page_url(user_id)
            try:
                response = self.downloader.fetch_url(
                    self.cookie, url, timeout_secs=15)

                user_infos = self.fbParser.parse_about_page(
                    response.text)
                infos[user_id] = user_infos

                logging.info("Got infos for user '{0}' - {1}".format(
                    user_id, common.prettify(user_infos)))

            except Exception as e:
                logging.error(
                    "Error while downloading page '{0}', "
                    "got exception: '{1}'".format(url, e))

        return infos
