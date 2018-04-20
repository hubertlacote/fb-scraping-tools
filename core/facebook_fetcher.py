from core.downloader import Downloader
from core.facebook_soup_parser import FacebookSoupParser
from core import common
from core import model

from collections import OrderedDict
import logging
import re


def create_production_fetcher():

    downloader = Downloader()
    fb_parser = FacebookSoupParser()
    config = common.load_config()

    return FacebookFetcher(downloader, fb_parser, config)


def build_buddy_feed_url(user_id):
    return (
        "https://5-edge-chat.facebook.com/pull?channel=p_{0}&" + \
        # seq = 1 directly gives the full list
        "seq=1&" + \
        "partition=-2&clientid={1}&cb=ze0&idle=0&qp=yisq=129169&" + \
        "msgs_recv=0&uid={0}&viewer_uid={0}&sticky_token=1058&" + \
        # Hardcoded client_id, any value seems ok as long as there is one
        "sticky_pool=lla1c22_chat-proxy&state=active"). \
            format(user_id, "1a2b3c4d")


def build_friends_page_url(page_no):
    return "https://mbasic.facebook.com/friends/center/friends/?ppk={0}". \
        format(page_no)


def build_about_page_url_from_id(user_id):
    return "https://mbasic.facebook.com/profile.php?v=info&id={0}". \
        format(user_id)


def build_about_page_url_from_username(username):
    return "https://mbasic.facebook.com/{0}/about". \
        format(username)


def build_timeline_page_url_from_username(username):
    return "https://mbasic.facebook.com/{0}?v=timeline". \
        format(username)


def build_timeline_page_url_from_id(id):
    return "https://mbasic.facebook.com/profile.php?id={0}&v=timeline&". \
        format(id)


def build_reaction_page_url(article_id, max_likes):
    """
    >>> build_reaction_page_url(123, 500)
    'https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?\
limit=500&total_count=500&ft_ent_identifier=123'
    """
    return \
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" + \
        "limit={0}&total_count={0}&".format(max_likes) + \
        "ft_ent_identifier={0}".format(article_id)


def build_relative_url(relative_url):
    return "https://mbasic.facebook.com{0}". \
        format(relative_url)


def get_user_id(user_ref):
    """
    >>> get_user_id("mark")
    >>> get_user_id("150")
    150
    >>> get_user_id("profile.php?id=151")
    151
    """
    is_id = re.match(r"^\d+$", str(user_ref))
    if is_id or "profile.php?id=" in user_ref:
        return int(str(user_ref).replace("profile.php?id=", ""))
    else:
        return None


class FacebookFetcher:

    def __init__(self, downloader, fb_parser, config):
        self.downloader = downloader
        self.fb_parser = fb_parser
        self.cookie = common.build_cookie(config)
        self.buddy_feed_url = build_buddy_feed_url(config.cookie_c_user)

    def fetch_last_active_times(self):
        """ Returns an OrderedDict, mapping user_id to list of epoch times.

        Does not throw, returns an empty OrderedDict if an error occurs.
        """

        try:
            response = self.downloader.fetch_url(
                cookie=self.cookie, url=self.buddy_feed_url,
                timeout_secs=15, retries=5)

            return self.fb_parser.parse_buddy_list(response.text)

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
                    cookie=self.cookie, url=url, timeout_secs=15, retries=5)

                friends_found = self.fb_parser.parse_friends_page(
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

    def fetch_user_infos(self, user_refs):

        logging.info(
            "Querying '{0}' users from Facebook".
            format(len(user_refs)))

        infos = {}
        for user_no, user_ref in enumerate(user_refs, 1):

            logging.info("Processing user '{0}' - {1}/{2}".format(
                user_ref, user_no, len(user_refs)))

            user_id = get_user_id(user_ref)
            if user_id:
                url = build_about_page_url_from_id(user_id)
            else:
                url = build_about_page_url_from_username(user_ref)

            try:
                response = self.downloader.fetch_url(
                    cookie=self.cookie, url=url, timeout_secs=15, retries=5)

                user_infos = self.fb_parser.parse_about_page(
                    response.text)
                if not user_infos:
                    raise RuntimeError(
                        "Failed to extract infos for user {0}".format(
                            user_ref))
                infos[user_ref] = user_infos

                logging.info("Got infos for user '{0}' - {1}".format(
                    user_ref, common.prettify(user_infos)))

            except Exception as e:
                if user_id:
                    infos[user_ref] = OrderedDict([("id", user_id)])
                logging.error(
                    "Error while downloading page '{0}', "
                    "got exception: '{1}'".format(url, e))

        return infos

    def fetch_articles_from_timeline(self, user_refs):
        """ For every user_ref provided, return a dictionary mapping article id
        to time of the post."""

        articles_found = OrderedDict()

        for users_processed, user_ref in enumerate(user_refs, 1):

            logging.info("Processing user '{0}' - {1}/{2}".format(
                user_ref, users_processed, len(user_refs)))

            articles_found[user_ref] = OrderedDict()
            articles_found[user_ref]["posts"] = OrderedDict()

            logging.info(
                "Fetching timeline for user '{0}' from Facebook".
                format(user_ref))

            user_id = get_user_id(user_ref)
            if user_id:
                url = build_timeline_page_url_from_id(user_id)
            else:
                url = build_timeline_page_url_from_username(user_ref)

            links_to_explore = [url]
            links_explored = 0

            while links_to_explore:

                url = links_to_explore.pop()

                logging.info(
                    "Exploring link {0} - {1} left after, url: {2}".format(
                        links_explored + 1, len(links_to_explore), url))

                try:

                    response = self.downloader.fetch_url(
                        cookie=self.cookie, url=url,
                        timeout_secs=15, retries=5)

                    if links_explored == 0:
                        links = \
                            self.fb_parser.parse_timeline_years_links(
                                response.text)
                        logging.info("Found {0} year links to explore".format(
                            len(links)))
                        full_links = \
                            [build_relative_url(link) for link in links]
                        links_to_explore.extend(full_links)

                    result = self.fb_parser.parse_timeline_page(response.text)
                    if not result:
                        raise RuntimeError(
                            "Failed to parse timeline - no result")

                    articles_found[user_ref]["posts"].update(result.articles)

                    show_more_link = result.show_more_link
                    if show_more_link:
                        logging.info("Found show more link: {0}".format(
                            build_relative_url(show_more_link)))
                        links_to_explore.append(
                            build_relative_url(show_more_link))

                except Exception as e:
                    logging.error(
                        "Error while downloading page '{0}', "
                        "got exception: '{1}'".format(url, e))

                links_explored += 1

        return articles_found

    def fetch_reactions_per_user_for_articles(self, articles):
        """ Return a dictionary mapping users who liked articles
        to the list of articles they liked.

        articles is a list of dictionaries containing the key post_id
        for every article.
        """

        reactions_per_user = OrderedDict()

        logging.info(
                "Fetching reactions for {0} articles".format(
                    len(articles)))

        for articles_processed, article in enumerate(articles):

            if "post_id" not in article:
                logging.error(
                    "Invalid input, every article in the list "
                    "must contain the key post_id")
                return OrderedDict()

            article_id = article["post_id"]
            article_url = build_reaction_page_url(article_id, 10000)

            logging.info(
                "Fetching reactions for article {0}/{1} - id: '{2}'".format(
                    articles_processed + 1, len(articles), article_id))

            try:

                response = self.downloader.fetch_url(
                    cookie=self.cookie, url=article_url,
                    timeout_secs=15, retries=5)

                usernames = self.fb_parser.parse_reaction_page(
                        response.text)
                logging.info("Article got {0} like(s): {1}".format(
                    len(usernames), usernames))

                for username in usernames:
                    if username not in reactions_per_user:
                        reactions_per_user[username] = {}
                        reactions_per_user[username]["likes"] = []
                    reactions_per_user[username]["likes"].append(
                        article
                    )

            except Exception as e:
                logging.error(
                    "Error while downloading page '{0}', "
                    "got exception: '{1}'".format(article_url, e))

        return reactions_per_user
