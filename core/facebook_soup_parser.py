from core import common
from core import model

from bs4 import BeautifulSoup
from collections import namedtuple
from collections import OrderedDict
from datetime import datetime
import json
import logging
import re


TimelineResult = namedtuple('TimelineResult', ['articles', 'show_more_link'])


def detect_error_type(content):
    """
    >>> detect_error_type('<input name="login">Login requested')
    'Cookie expired or is invalid, login requested'
    >>> detect_error_type('<div id="objects_container"><span class="bb">' + \
        'The page you requested cannot be displayed at the moment. ' + \
        'It may be temporarily unavailable, the link you clicked on may ' + \
        'be broken or expired, or you may not have permission to view ' + \
        'this page.</span></div>')
    'Page temporarily unavailable / broken / expired link'
    >>> detect_error_type('<html></html>')
    'Failed to parse page'
    """
    soup = BeautifulSoup(content, "lxml")

    if soup.find("input", attrs={"name": "login"}):
        return "Cookie expired or is invalid, login requested"
    elif soup.find_all(
            "span", string=re.compile("It may be temporarily unavailable")):
        return "Page temporarily unavailable / broken / expired link"
    else:
        return "Failed to parse page"


class FacebookSoupParser:

    def parse_buddy_list(self, raw_json):
        """
        >>> FacebookSoupParser().parse_buddy_list(
        ... 'for (;;); {"ms": [{"type": "chatproxy-presence", '
        ... '"userIsIdle": false, "chatNotif": 0, "gamers": [], "buddyList": {'
        ... '"111": {"lat": 1500000001}, '
        ... '"222": {"lat": 1500000002}, '
        ... '"333": {"lat": -1}}}, {"type": "buddylist_overlay",'
        ...  '"overlay": {"333": {"la": 1500000003, "a": 0, "vc": 0, "s":'
        ... '"push"}}}], "t": "msg", "u": 123, "seq": 3}')
        OrderedDict([('111', {'times': ['2017-07-14 04:40:01']}), \
('222', {'times': ['2017-07-14 04:40:02']}), ('333', {'times': []})])
        >>> FacebookSoupParser().parse_buddy_list("")
        OrderedDict()
        >>> FacebookSoupParser().parse_buddy_list(
        ... '{ "overlay": { "111": { '
        ... '"a": 0, "c": 74, "la": 1500000003, "s": "push", "vc": 74 }}, '
        ... '"type": "buddylist_overlay"}')
        OrderedDict()
        >>> FacebookSoupParser().parse_buddy_list(
        ... '{ "seq": 1, "t": "fullReload" }')
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
            logging.debug("Got instead: {0}".format(
                common.prettify(decoded_json)))
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
                times = []
                lat_found = buddy_list[user]["lat"]
                if lat_found > -1:
                    times.append(str(datetime.fromtimestamp(int(lat_found))))
                flattened_buddy_list[user] = \
                    {"times": times}

        return OrderedDict(sorted(flattened_buddy_list.items()))

    def parse_about_page(self, content):
        """Extract information from the mobile version of the about page.

        Returns an OrderedDict([('name', ''), ...]).

        Keys are added only if the fields were found in the about page.

        >>> FacebookSoupParser().parse_about_page('''
        ...    <title id="pageTitle">Mark Zuckerberg</title>
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ... ''')["name"]
        'Mark Zuckerberg'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ...    <div class="timeline aboutme">
        ...         <div class="dc dd dq" title="Birthday">
        ...             <div class="dv">14 May 1984</div>
        ...         </div>
        ...    </div>
        ...    ''')["birthday"]
        '14 May 1984'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ...    <div class="timeline aboutme">
        ...         <div class="dc dd dq" title="Birthday">
        ...             <div class="dv">14 May 1984</div>
        ...         </div>
        ...    </div>
        ...    ''')["year_of_birth"]
        1984
        >>> FacebookSoupParser().parse_about_page('''
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ...    <div class="timeline aboutme">
        ...         <div class="dc dd dq" title="Birthday">
        ...             <div class="dv">14 May</div>
        ...         </div>
        ...    </div>
        ...    ''')["day_and_month_of_birth"]
        '14 May'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ...    <div class="timeline aboutme">
        ...         <div class="_5cds _2lcw _5cdu" title="Gender">
        ...             <div class="_5cdv r">Male</div>
        ...         </div>
        ...    </div>
        ...    ''')["gender"]
        'Male'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ...    <div class="timeline aboutme">
        ...         <div class="_5cds _2lcw _5cdu" title="Gender">
        ...             <span class="du dm x">Gender</span>
        ...             <span aria-hidden="true"> · </span>
        ...             <span class="dl">Edit</span>
        ...             <div class="_5cdv r">Male</div>
        ...         </div>
        ...    </div>
        ...    ''')["gender"]
        'Male'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ...    <div class="timeline aboutme">
        ...         <div id="relationship"><div class="cq">''' + \
                    'Relationship</div><div class="cu do cv">' + \
                    'Married to <a class="bu" href="/someone">Someone</a>' + \
                    ' since 14 March 2010</div></div>' + '''
        ...    </div>
        ...    ''')["relationship"]
        'Married'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ...    <div class="timeline aboutme">
        ...         <div id="work">
        ...             <a class="bm" href="">
        ...                 <img src="" alt="1st work">
        ...             </a>
        ...             <a class="bm" href="">
        ...                 <img src="" alt="2nd work">
        ...             </a>
        ...         </div>
        ...    </div>''')["work"]
        '1st work'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <a href="/mark?v=timeline&amp;lst=1%3A4%3A2">Timeline</a>'
        ...    <div class="timeline aboutme">
        ...         <div id="education">
        ...             <a class="bm" href="">
        ...                 <img src="" alt="1st education">
        ...             </a>
        ...             <a class="bm" href="">
        ...                 <img src="" alt="2nd education">
        ...             </a>
        ...         </div>
        ...    </div>''')["education"]
        '1st education'
        >>> FacebookSoupParser().parse_about_page('''
        ...     <a href="/mark?v=timeline&amp;lst=1%3A12345%3A2">
        ...         Timeline
        ...     </a>''')["id"]
        12345
        >>> FacebookSoupParser().parse_about_page('''
        ...     <input name="login" type="submit" value="Log In">''')
        """
        soup = BeautifulSoup(content, "lxml")

        user_info = OrderedDict()

        name_tag = soup.find("title")
        if name_tag:
            user_info["name"] = name_tag.text

        timeline_tag = soup.find(href=re.compile(
            r"^/.*\?v=timeline.lst=\d+%3A\d+%3A"))
        if not timeline_tag:

            logging.error(detect_error_type(content))
            return None

        user_id = int(timeline_tag.attrs["href"].split(
            "%3A")[1])
        user_info["id"] = user_id

        tags = [
            'AIM', 'Address', 'BBM', 'Birth Name', 'Birthday',
            'Facebook', 'Foursquare', 'Gadu-Gadu', 'Gender', 'ICQ',
            'Instagram', 'Interested in', 'Languages', 'LinkedIn',
            'Maiden Name', 'Mobile', 'Nickname', 'Political Views',
            'Religious views', 'Skype', 'Snapchat', 'Twitter', 'VK',
            'Websites', 'Windows Live Messenger', 'Year of birth']

        for tag in tags:
            found_tag = soup.find("div", attrs={"title": tag})
            if found_tag:
                user_info[tag.replace(" ", "_").lower()] = found_tag.text. \
                    replace(tag, "").replace("\n", "").replace(" · Edit", "")

        if "birthday" in user_info:
            parsed_birthday = user_info["birthday"]
            if parsed_birthday.count(" ") != 2:
                user_info["day_and_month_of_birth"] = parsed_birthday
                del user_info["birthday"]
            else:
                user_info["day_and_month_of_birth"] = " ".join(
                    parsed_birthday.split(" ")[0:2])
                user_info["year_of_birth"] = parsed_birthday.split(" ")[-1]

        if "year_of_birth" in user_info:
            user_info["year_of_birth"] = int(user_info["year_of_birth"])

        institution_tags = ["work", "education"]
        for institution_tag in institution_tags:
            found_tag = soup.find("div", attrs={"id": institution_tag})
            if found_tag:
                found_img_tag = found_tag.find("img")
                if found_img_tag and "alt" in found_img_tag.attrs:
                    user_info[institution_tag] = \
                        found_img_tag.attrs["alt"]

        relationship_tag = soup.find("div", attrs={"id": "relationship"})
        if relationship_tag:

            relationship_choices = [
                'In a relationship', 'Engaged', 'Married',
                'In a civil partnership', 'In a domestic partnership',
                'In an open relationship', 'It\'s complicated', 'Separated',
                'Divorced', 'Widowed', 'Single'
            ]
            for relationship_choice in relationship_choices:
                if relationship_choice in relationship_tag.text:
                    user_info["relationship"] = relationship_choice
                    break

        return user_info

    def parse_friends_page(self, content):
        """Extract information from the mobile version of the friends page.

        JavaScript has to be disabled when fetching the page, otherwise, the
        content returned by requests does not contain the UIDs.

        Returns an OrderedDict([(111, {'id': 111, name': ''}), ...]) mapping
        user ids to names.

        >>> FacebookSoupParser().parse_friends_page('''
        ...     <div id="friends_center_main">
        ...         <a href="/privacyx/selector/">
        ...         <a class="bn" href="/friends/hovercard/mbasic/?
        ...             uid=111&amp;redirectURI=https%3A%2F%2Fm.facebook.com
        ...         ">Mark</a>
        ...         <a class="bn" href="/friends/hovercard/mbasic/?
        ...             uid=222&amp;redirectURI=https%3A%2F%2Fm.facebook.com
        ...         ">Dave</a>
        ...         <a href="/friends/center/friends/?ppk=1&amp;
        ...             tid=u_0_0&amp;bph=1#friends_center_main">
        ...     </div>''')
        OrderedDict([(111, OrderedDict([('id', 111), ('name', 'Mark')])), \
(222, OrderedDict([('id', 222), ('name', 'Dave')]))])
        >>> FacebookSoupParser().parse_friends_page('''
        ...     <div id="friends_center_main">
        ...         <a href="/privacyx/selector/">
        ...         <a href="/friends/center/friends/?ppk=1&amp;
        ...             tid=u_0_0&amp;bph=1#friends_center_main">
        ...     </div>''')
        OrderedDict()
        >>> FacebookSoupParser().parse_friends_page('''
        ...     <div id="friends_center_main">
        ...     </div>''')
        OrderedDict()
        >>> FacebookSoupParser().parse_friends_page("")
        OrderedDict()
        >>> FacebookSoupParser().parse_friends_page('''
        ...     <input name="login" type="submit" value="Log In">''')
        OrderedDict()
        """

        soup = BeautifulSoup(content, "lxml")

        friends_found = OrderedDict()

        main_soup = soup.find(id="friends_center_main")
        if not main_soup:

            logging.error(detect_error_type(content))
            return friends_found

        links_soup = main_soup.find_all("a")
        for link in links_soup:
            if "href" in link.attrs:
                uid_found = re.findall(r'uid=\d+', link.attrs["href"])
                if uid_found:
                    user_id = int(uid_found[0].replace("uid=", ""))
                    friends_found[user_id] =\
                        OrderedDict([("id", user_id), ("name", link.text)])

        return friends_found

    def parse_timeline_years_links(self, content):
        """
        >>> FacebookSoupParser().parse_timeline_years_links('''
        ...     <div id="tlFeed">
        ...         <a class="bn" href="badLink1">Mark</a>
        ...         <a href="link1">2010</a>
        ...         <a href="link2">2009</a>
        ...         <a class="bn" href="badLink2">Dave</a>
        ...     </div>''')
        ['link1', 'link2']
        >>> FacebookSoupParser().parse_timeline_years_links('''
        ...     <div id="timelineBody">
        ...         <a class="bn" href="badLink1">Mark</a>
        ...         <a href="link1">2010</a>
        ...         <a href="link2">2009</a>
        ...         <a class="bn" href="badLink2">Dave</a>
        ...     </div>''')
        ['link1', 'link2']
        >>> FacebookSoupParser().parse_timeline_years_links('''
        ...     <div id="m_group_stories_container">
        ...         <a class="bn" href="badLink1">Mark</a>
        ...         <a href="link1">2010</a>
        ...         <a href="link2">2009</a>
        ...         <a class="bn" href="badLink2">Dave</a>
        ...     </div>''')
        ['link1', 'link2']
        >>> FacebookSoupParser().parse_timeline_years_links('''
        ...     <div id="m_group_stories_container">
        ...         <a href="badLink">Not a 2010 link to catch</a>
        ...     </div>''')
        []
        >>> FacebookSoupParser().parse_timeline_years_links('''
        ...     <input name="login" type="submit" value="Log In">''')
        []
        """

        soup = BeautifulSoup(content, "lxml")

        links_found = []

        main_soup = soup.find(
            id=["tlFeed", "timelineBody", "m_group_stories_container"])
        if not main_soup:

            logging.error(detect_error_type(content))
            return links_found

        links_soup = main_soup.find_all('a')
        for link in links_soup:
            if "href" in link.attrs:
                year_found = re.match(r'^\d{4}$', link.text)
                if year_found:
                    links_found.append(link.attrs["href"])

        return links_found

    def parse_post(self, soup):
        """
        >>> FacebookSoupParser().parse_post(BeautifulSoup('''
        ...     <div role="article">
        ...         <abbr>13 May 2008 at 10:02</abbr>
        ...         <span id="like_151">
        ...             <a aria-label="10 reactions, including Like and \
Love" href="/link1">10</a>
        ...             <a href="/link2">React</a>
        ...         </span>
        ...         <a href="/link3">12 Comments</a>
        ...     </div>''', 'lxml'))
        OrderedDict([('post_id', 151), ('date', '2008-05-13 10:02:00'), \
('date_org', '13 May 2008 at 10:02'), ('like_count', 10), \
('comment_count', 12)])

        >>> FacebookSoupParser().parse_post(BeautifulSoup('''
        ...     <div role="article">
        ...         <abbr>13 May 2008 at 10:02</abbr>
        ...         <span id="like_151">
        ...             <a aria-label="114K reactions, including Like, Love \
and Wow" href="/link1">114,721</a>
        ...             <a href="/link2">React</a>
        ...         </span>
        ...         <a href="/link3">2,746 Comments</a>
        ...     </div>''', 'lxml'))
        OrderedDict([('post_id', 151), ('date', '2008-05-13 10:02:00'), \
('date_org', '13 May 2008 at 10:02'), ('like_count', 114721), \
('comment_count', 2746)])

        >>> FacebookSoupParser().parse_post(BeautifulSoup('''
        ...     <div role="article">
        ...         <abbr>14 May 2008 at 10:02</abbr>
        ...         <span id="like_152">
        ...             <a href="/link1">Like</a>
        ...             <a href="/link2">React</a>
        ...         </span>
        ...         <a href="/link3">Comment</a>
        ...     </div>''', 'lxml'))
        OrderedDict([('post_id', 152), ('date', '2008-05-14 10:02:00'), \
('date_org', '14 May 2008 at 10:02'), ('like_count', 0), ('comment_count', 0)])

        >>> FacebookSoupParser().parse_post(BeautifulSoup('''
        ...     <div role="article">
        ...     </div>''', 'lxml'))

        >>> FacebookSoupParser().parse_post(BeautifulSoup('''
        ...     <div role="article">
        ...         <abbr>14 May 2008 at 10:02</abbr>
        ...     </div>''', 'lxml'))
        """
        date_tag = soup.find("abbr")
        if not date_tag:
            logging.info("Skipping original article shared.")
            return None
        date_org = date_tag.text
        date = str(model.parse_date(date_org))

        span_tag = soup.find(id=re.compile(r"like_\d+"))
        if not span_tag:
            logging.info("Skipping article - no link for likes found.")
            return None
        article_id = int(re.findall(r'\d+', span_tag.attrs["id"])[0])

        like_count = 0
        reaction_link = span_tag.find(
            'a', attrs={"aria-label": re.compile(r"reaction")})
        if reaction_link:
            like_count = int(reaction_link.text.replace(",", ""))

        comment_count = 0
        comment_link = soup.find("a", string=re.compile(r"\d+ Comment"))
        if comment_link:
            comment_count = int(
                comment_link.text.split(" Comment")[0].replace(",", ""))

        return OrderedDict([
            ("post_id", article_id), ("date", date), ("date_org", date_org),
            ("like_count", like_count), ("comment_count", comment_count)])

    def parse_timeline_page(self, content):
        """
        >>> FacebookSoupParser().parse_timeline_page('''
        ...     <div id="tlFeed">
        ...         <div role="article">
        ...             <abbr>13 May 2008 at 10:02</abbr>
        ...             <span id="like_151"></span>
        ...         </div>
        ...         <div role="article">
        ...             <abbr>13 May 2008 at 10:25</abbr>
        ...             <span id="like_152"></span>
        ...         </div>
        ...         <div>
        ...             <a href="/show_more_link">Show more</a>
        ...         </div>
        ...     </div>''')
        TimelineResult(articles=OrderedDict([\
(151, OrderedDict([('post_id', 151), ('date', '2008-05-13 10:02:00'), \
('date_org', '13 May 2008 at 10:02'), ('like_count', 0), \
('comment_count', 0)])), \
(152, OrderedDict([('post_id', 152), ('date', '2008-05-13 10:25:00'), \
('date_org', '13 May 2008 at 10:25'), ('like_count', 0), \
('comment_count', 0)]))]), show_more_link='/show_more_link')
        >>> FacebookSoupParser().parse_timeline_page('''
        ...     <div id="timelineBody">
        ...         <div role="article">
        ...             <div role="article">
        ...             </div>
        ...             <abbr>13 May 2008 at 10:02</abbr>
        ...             <span id="like_151"></span>
        ...         </div>
        ...     </div>''')
        TimelineResult(articles=OrderedDict([\
(151, OrderedDict([('post_id', 151), ('date', '2008-05-13 10:02:00'), \
('date_org', '13 May 2008 at 10:02'), ('like_count', 0), \
('comment_count', 0)]))]), show_more_link='')
        >>> FacebookSoupParser().parse_timeline_page('''
        ...     <div id="m_group_stories_container">
        ...         <div role="article">
        ...             <abbr>13 May 2008 at 10:02</abbr>
        ...             <span id="like_151"></span>
        ...         </div>
        ...     </div>''')
        TimelineResult(articles=OrderedDict([\
(151, OrderedDict([('post_id', 151), ('date', '2008-05-13 10:02:00'), \
('date_org', '13 May 2008 at 10:02'), ('like_count', 0), \
('comment_count', 0)]))]), show_more_link='')
        >>> FacebookSoupParser().parse_timeline_page('''
        ...     <div id="structured_composer_async_container">
        ...         <div role="article">
        ...             <abbr>13 May 2008 at 10:02</abbr>
        ...             <span id="like_151"></span>
        ...         </div>
        ...     </div>''')
        TimelineResult(articles=OrderedDict([\
(151, OrderedDict([('post_id', 151), ('date', '2008-05-13 10:02:00'), \
('date_org', '13 May 2008 at 10:02'), ('like_count', 0), \
('comment_count', 0)]))]), show_more_link='')
        >>> FacebookSoupParser().parse_timeline_page('''
        ...     <input name="login" type="submit" value="Log In">''')
        """
        soup = BeautifulSoup(content, "lxml")

        main_soup = soup.find(
            id=[
                "tlFeed", "timelineBody", "m_group_stories_container",
                "structured_composer_async_container"])
        if not main_soup:

            logging.error(detect_error_type(content))
            return None

        articles_found = OrderedDict()
        articles_soup = main_soup.find_all("div", attrs={"role": "article"})
        for article in articles_soup:

            post = self.parse_post(article)
            if post:
                logging.info(
                    "Found post: {0}".format(post))
                # The same post_id might be returned several times,
                # e.g. when adding photos to albums. Overwrite, since
                # only the date will change.
                articles_found[post["post_id"]] = post

        show_more_link_tag = soup.find(
            "a", string=["Show more", "See more posts"])
        link_found = ""
        if show_more_link_tag and "href" in show_more_link_tag.attrs:
            link_found = show_more_link_tag.attrs["href"]

        return TimelineResult(
            articles=articles_found, show_more_link=link_found)

    def parse_reaction_page(self, content):
        """
        >>> FacebookSoupParser().parse_reaction_page('''
        ...     <div id="objects_container">
        ...         <a role="button" href="/ufi/badLink">All 2</a>
        ...         <a class="bn" href="/username1">Mark</a>
        ...         <a class="bn" href="bad/Link1">Mark</a>
        ...         <a class="bn" href="/username2">Paul</a>
        ...         <a href="/a/mobile/friends/add_friend.php?id=123"></a>
        ...         <a class="bn" href="badLink2">Dave</a>
        ...         <a href="/ufi/reaction/profile/browser/fetch/?"></a>
        ...     </div>''')
        ['username1', 'username2']
        >>> FacebookSoupParser().parse_reaction_page('''
        ...     <div id="objects_container">
        ...         <span>The page you requested cannot be displayed</span>
        ...         <a href="/home.php?rand=852723744">Back to home</a>
        ...     </div>''')
        []
        >>> FacebookSoupParser().parse_reaction_page('''
        ...     <input name="login" type="submit" value="Log In">''')
        """

        soup = BeautifulSoup(content, "lxml")

        usernames_found = []

        main_soup = soup.find(id="objects_container")
        if not main_soup:

            logging.error(detect_error_type(content))
            return None

        links_soup = main_soup.find_all(href=re.compile("^/.*"))
        invalid_links = ["add_friend.php", "ufi/reaction", "home.php?"]
        for link in links_soup:
            if "role" not in link.attrs and \
               "href" in link.attrs:

                username = link.attrs["href"][1:]

                is_invalid = False
                for invalid_link in invalid_links:
                    if invalid_link in username:
                        is_invalid = True
                        break

                if username and not is_invalid:
                    usernames_found.append(username)

        return usernames_found
