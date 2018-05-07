from core.downloader import Downloader
from core.facebook_soup_parser import FacebookSoupParser
from core import common
from core import model

from collections import OrderedDict
import logging
import re


def create_production_fetcher(config):

    downloader = Downloader()
    fb_parser = FacebookSoupParser()

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


def build_about_page_url_from_id(user_id):
    return "https://mbasic.facebook.com/profile.php?v=info&id={0}". \
        format(user_id)


def build_about_page_url_from_username(username):
    return "https://mbasic.facebook.com/{0}/about". \
        format(username)


def build_friends_page_from_id(user_id):
    """
    >>> build_friends_page_from_id(123)
    'https://mbasic.facebook.com/profile.php?v=friends&id=123'
    """
    return "https://mbasic.facebook.com/profile.php?v=friends&" + \
           "id={0}".format(user_id)


def build_likes_page_from_id(user_id):
    """
    >>> build_likes_page_from_id(123)
    'https://mbasic.facebook.com/profile.php?v=likes&id=123'
    """
    return "https://mbasic.facebook.com/profile.php?v=likes&" + \
           "id={0}".format(user_id)


def build_mutual_friends_page_url_from_id(c_user, user_id):
    """
    >>> build_mutual_friends_page_url_from_id(123, 456)
    'https://mbasic.facebook.com/profile.php?v=friends&mutual=1&\
lst=123:456:1&id=456'
    """
    return "https://mbasic.facebook.com/profile.php?v=friends&mutual=1&" + \
        "lst={0}:{1}:{2}&id={1}".format(c_user, user_id, 1)


def build_timeline_page_url_from_username(username):
    return "https://mbasic.facebook.com/{0}?v=timeline". \
        format(username)


def build_timeline_page_url_from_id(id):
    return "https://mbasic.facebook.com/profile.php?id={0}&v=timeline&". \
        format(id)


def build_reaction_page_url(article_id, max_total_likes):
    """
    >>> build_reaction_page_url(123, 5000000)
    'https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?\
limit={0}&total_count=5000000&ft_ent_identifier=123'
    """
    # Not replacing limit={0} on purpose
    return \
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" + \
        "limit={0}" + \
        "&total_count={0}&".format(max_total_likes) + \
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


def strip_link_refs(link):
    """
    >>> strip_link_refs("/profile.php?id=1234&fref=none&refid=17")
    '/profile.php?id=1234'
    >>> strip_link_refs("/SomeGroup/?refid=17")
    '/SomeGroup/'
    >>> strip_link_refs("/some.page/?fref=none&refid=17")
    '/some.page/'
    >>> strip_link_refs("/neilstrauss/?fref=none")
    '/neilstrauss/'
    """
    link = link.split("&fref")[0]
    link = link.split("?fref")[0]
    link = link.split("?refid")[0]
    link = link.split("&refid")[0]
    return link


def is_user(username):
    """
    >>> is_user("SomeName/")
    False
    >>> is_user("a/profile.php?fan&id=1234&origin=liked_menu&gfid=AB12CD")
    False
    >>> is_user("SomeName /")
    False
    >>> is_user("profile.php?id=1234")
    True
    >>> is_user("some.name")
    True
    """
    if username[-1:] == "/":
        return False
    elif "profile.php?fan" in username:
        return False
    else:
        return True


class FacebookFetcher:

    def __init__(self, downloader, fb_parser, config):
        self.downloader = downloader
        self.fb_parser = fb_parser
        self.cookie = common.build_cookie(config)
        self.buddy_feed_url = build_buddy_feed_url(config.cookie_c_user)
        self.c_user = config.cookie_c_user

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

    def fetch_content_recursively(self, initial_url, parsing_function):

        content = OrderedDict()

        links_to_explore = [initial_url]
        links_explored = 0
        while links_to_explore:

            url = links_to_explore.pop()

            logging.info(
                "Exploring page {0} - {1} left after, ".format(
                    links_explored + 1, len(links_to_explore)) +
                "url: {0}".format(url))

            try:
                response = self.downloader.fetch_url(
                    cookie=self.cookie, url=url,
                    timeout_secs=15, retries=5)
                likes_results = parsing_function(response.text)
                if likes_results:
                    logging.info("Found items: {0}".format(
                        likes_results.content))
                    for category in likes_results.content:
                        if category not in content:
                            content[category] = OrderedDict()
                        processed_content = OrderedDict()
                        for link in likes_results.content[category]:
                            processed_content[strip_link_refs(link)] = \
                                likes_results.content[category][link]

                        content[category].update(processed_content)

                    if likes_results.see_more_links:
                        logging.info("Found more links to explore: {0}".format(
                            likes_results.see_more_links))
                        links_to_explore.extend(
                            [build_relative_url(link)
                                for link in likes_results.see_more_links])

            except Exception as e:
                logging.error(
                    "Error while downloading page '{0}', "
                    "got exception: '{1}'".format(url, e))

            links_explored += 1

        return content

    def do_fetch_friends(self, user_id):

        content = self.fetch_content_recursively(
            build_friends_page_from_id(user_id),
            lambda content: self.fb_parser.parse_friends_page(content))

        friend_list = OrderedDict()

        if not content or "friends" not in content:
            logging.error("Error while fetching friend list")
            return friend_list

        for username in content["friends"]:
            friend_name = content["friends"][username]
            friend_list[username] = {"name": friend_name}

        logging.info("Friends of user '{0}': {1}".format(
            user_id, common.prettify(friend_list)))

        return friend_list

    def fetch_user_friend_list(self):
        return self.do_fetch_friends(self.c_user)

    def do_fetch_liked_pages(self, user_id):

        result = self.fetch_content_recursively(
            build_likes_page_from_id(user_id),
            lambda content: self.fb_parser.parse_likes_page(content))

        logging.info("Liked pages of user '{0}': {1}".format(
            user_id, common.prettify(result)))

        return result

    def do_fetch_mutual_friends(self, user_id):

        result = self.fetch_content_recursively(
            build_mutual_friends_page_url_from_id(
                self.c_user, user_id),
            lambda content: self.fb_parser.parse_mutual_friends_page(content))

        mutual_friends = OrderedDict()

        if not result or "mutual_friends" not in result:
            logging.error("Error while fetching mutual friends")
            return mutual_friends

        for mutual_friend_link in result["mutual_friends"]:
            friend_name = result["mutual_friends"][mutual_friend_link]
            username = mutual_friend_link
            mutual_friends[username] = {"name": friend_name}

        logging.info("Mutual friends for user '{0}': {1}".format(
            user_id, common.prettify(mutual_friends)))

        return mutual_friends

    def fetch_user_infos(self, user_refs,
                         fetch_friends, fetch_likes, fetch_mutual_friends):
        """ Fetch details about some users from their about page.

        fetch_friends: if True, fetch the list of friends.
        fetch_likes: if True, fetch the list of likes from the about page.
        fetch_mutual_friends: if True, fetch the list of mutual friends.
        Only the first page of mutual friends is fetched / parsed.
        Adding "&startindex=36" to the url would return the next 35 friends
        and so on...
        """

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
                    cookie=self.cookie, url=url, timeout_secs=30, retries=5)

                user_infos = self.fb_parser.parse_about_page(
                    response.text)
                if not user_infos \
                   or "id" not in user_infos or not user_infos["id"]:
                    raise RuntimeError(
                        "Failed to extract infos for user {0}".format(
                            user_ref))

                logging.info("Got infos for user '{0}' - {1}".format(
                    user_ref, common.prettify(user_infos)))

                if fetch_friends:
                    user_infos["friends"] = self.do_fetch_friends(
                        user_infos["id"])
                    user_infos["friend_count"] = len(user_infos["friends"])

                if fetch_likes:
                    liked_pages = self.do_fetch_liked_pages(
                        user_infos["id"])
                    liked_page_count = 0
                    for category in liked_pages:
                        liked_page_count += len(liked_pages[category])
                    user_infos["liked_pages"] = liked_pages
                    user_infos["liked_page_count"] = liked_page_count

                if fetch_mutual_friends:
                    user_infos["mutual_friends"] = \
                        self.do_fetch_mutual_friends(user_infos["id"])
                    user_infos["mutual_friend_count"] = \
                        len(user_infos["mutual_friends"])

                infos[user_ref] = user_infos

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

    def fetch_likers_for_article(self, article_id):
        """ Return a set of users / pages who liked the article."""

        max_likes_per_page = 500
        max_attempts = 5

        likers = set()

        links_to_explore = [build_reaction_page_url(
            article_id=article_id,
            max_total_likes=1000000)]
        links_explored = 1
        nb_like_found = 0

        while links_to_explore:

            url = links_to_explore.pop()
            logging.info(
                "Fetching reactions page {0}, url: {1}".format(
                    links_explored, common.truncate_text(url, 200)))

            succeeded = False
            for attempt_no in range(1, max_attempts + 1):
                current_url = ""
                try:
                    current_url = url.format(
                        max_likes_per_page // attempt_no)
                    response = self.downloader.fetch_url(
                        cookie=self.cookie, url=current_url,
                        timeout_secs=15, retries=5)
                    succeeded = True
                    break

                except Exception as e:
                    logging.info(
                        "Attempt to fetch '{0}' did not succeed".format(
                            common.truncate_text(current_url, 200)))

            if not succeeded:
                logging.error(
                    "Failed to fetch all reactions for post '{0}'".format(
                            article_id))
                break

            try:

                result = self.fb_parser.parse_reaction_page(
                        response.text)
                if not result:
                    raise RuntimeError(
                        "Failed to fetch reactions - no result")

                nb_like_found += len(result.likers)
                logging.info("New likers found: {0}".format(
                    result.likers))
                logging.info(
                    "Found {0} like(s) - Total found: {1}".format(
                        len(result.likers), nb_like_found))

                likers.update(result.likers)

                see_more_link = result.see_more_link
                if see_more_link:
                    see_more_link = build_relative_url(
                        see_more_link)

                    logging.info("Found see more link: {0}".format(
                        common.truncate_text(see_more_link, 200)))
                    if "limit=10" not in see_more_link:
                        logging.error(
                            "See more link found does not match "
                            "the expected pattern.")
                    else:
                        see_more_link = see_more_link.replace(
                            "limit=10", "limit={0}")
                        links_to_explore.append(
                            see_more_link)

            except Exception as e:
                logging.error(
                    "Error while processing page '{0}', "
                    "got exception: '{1}'".format(
                        common.truncate_text(url, 200), e))

            links_explored += 1

        return likers

    def fetch_reactions_per_user_for_articles(self,
                                              articles, exclude_non_users):
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

            like_count = ""
            if "like_count" in article:
                like_count = article["like_count"]

            logging.info(
                "Fetching {0} reaction(s) for post {1}/{2}, id: '{3}'".format(
                    like_count, articles_processed + 1,
                    len(articles), article_id))

            likers = sorted(self.fetch_likers_for_article(article_id))

            logging.info(
                "Found {0} like(s) / {1} expected".format(
                    len(likers), like_count))

            for username in likers:
                if not exclude_non_users or \
                        (exclude_non_users and is_user(username)):
                    if username not in reactions_per_user:
                        reactions_per_user[username] = {}
                        reactions_per_user[username]["likes"] = []
                    reactions_per_user[username]["likes"].append(
                        article
                    )

        return reactions_per_user
