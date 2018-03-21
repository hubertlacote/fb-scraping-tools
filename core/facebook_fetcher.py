from core.downloader import Downloader
from core.facebook_soup_parser import FacebookSoupParser
from core import common

from collections import OrderedDict
import json
import logging
import re


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
    return "https://mbasic.facebook.com/friends/center/friends/?ppk={0}". \
        format(page_no)


def build_about_page_url_from_id(user_id):
    return "https://mbasic.facebook.com/profile.php?v=info&id={0}". \
        format(user_id)


def build_about_page_url_from_username(username):
    return "https://mbasic.facebook.com/{0}/about". \
        format(username)


def build_timeline_page_url(user_id):
    return "https://mbasic.facebook.com/{0}?v=timeline". \
        format(user_id)


def build_relative_url(relative_url):
    return "https://mbasic.facebook.com{0}". \
        format(relative_url)


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
                    self.cookie, url, timeout_secs=15, retries=5)

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

            logging.info("Processing {0}".format(user_id))

            is_id = re.match("^\d+$", str(user_id))
            if is_id or "profile.php?id=" in user_id:
                url = build_about_page_url_from_id(
                    str(user_id).replace("profile.php?id=", ""))
            else:
                url = build_about_page_url_from_username(user_id)

            try:
                response = self.downloader.fetch_url(
                    self.cookie, url, timeout_secs=15, retries=5)

                user_infos = self.fbParser.parse_about_page(
                    response.text)
                if not user_infos:
                    raise RuntimeError(
                        "Failed to extract infos for user {0}".format(user_id))
                infos[user_id] = user_infos

                logging.info("Got infos for user '{0}' - {1}".format(
                    user_id, common.prettify(user_infos)))

            except Exception as e:
                logging.error(
                    "Error while downloading page '{0}', "
                    "got exception: '{1}'".format(url, e))

        return infos

    def fetch_articles_from_timeline(self, user_id):
        """ Return a dictionary mapping article id to time of the post."""

        logging.info(
            "Fetching timeline for user '{0}' from Facebook".
            format(user_id))

        articles_found = OrderedDict()

        links_to_explore = [build_timeline_page_url(user_id)]
        links_explored = 0

        while links_to_explore:

            url = links_to_explore.pop()

            logging.info("Exploring link {0} - {1} left after".format(
                links_explored + 1, len(links_to_explore)))

            try:

                response = self.downloader.fetch_url(
                    self.cookie, url, timeout_secs=15, retries=5)

                if links_explored == 0:
                    links = self.fbParser.parse_years_links_from_timeline_page(
                        response.text)
                    logging.info("Found {0} year links to explore".format(
                        len(links)))
                    full_links = [build_relative_url(link) for link in links]
                    links_to_explore.extend(full_links)

                result = self.fbParser.parse_timeline_page(response.text)
                if not result:
                    raise RuntimeError("Failed to parse timeline - no result")

                for article_id in result.articles:
                    logging.info("Found article {0} - date: {1}".format(
                        article_id, result.articles[article_id]))

                articles_found.update(result.articles)

                show_more_link = result.show_more_link
                if show_more_link:
                    logging.info("Found show more link")
                    links_to_explore.append(build_relative_url(show_more_link))

            except Exception as e:
                logging.error(
                    "Error while downloading page '{0}', "
                    "got exception: '{1}'".format(url, e))

            links_explored += 1

        return articles_found
