from bs4 import BeautifulSoup
from collections import OrderedDict

import logging
import re


class FacebookSoupParser:

    def parse_about_page(self, content):
        """Extract information from the mobile version of the about page.

        Returns an OrderedDict([('Name', ''), ...]).

        It always contains 27 keys (see below) and values are set if
        the fields were found in the about page.

        >>> FacebookSoupParser().parse_about_page('''
        ...    <title id="pageTitle">Mark Zuckerberg</title>
        ... ''')["Name"]
        'Mark Zuckerberg'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div class="dc dd dq" title="Birthday">
        ...             <div class="dv">14 May 1984</div>
        ...         </div>
        ...    </div>
        ...    ''')["Birthday"]
        '14 May 1984'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div class="_5cds _2lcw _5cdu" title="Gender">
        ...             <div class="_5cdv r">Male</div>
        ...         </div>
        ...    </div>
        ...    ''')["Gender"]
        'Male'
        >>> len(FacebookSoupParser().parse_about_page(""))
        27
        """
        soup = BeautifulSoup(content, "lxml")

        user_info = OrderedDict()

        name_tag = soup.find("title")
        name = ""
        if name_tag:
            name = name_tag.text
        user_info["Name"] = name

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
                user_info[tag] = found_tag.text. \
                    replace(tag, "").replace("\n", "")
            else:
                user_info[tag] = ''

        relationship_tag = soup.find("div", attrs={"id": "relationship"})
        if relationship_tag:
            user_info["Relationship"] = \
                relationship_tag.get_text("|").replace("Relationship|", "")

        return user_info

    def parse_friends_page(self, content):
        """Extract information from the mobile version of the friends page.

        JavaScript has to be disabled when fetching the page, otherwise, the
        content returned by requests does not contain the UIDs.

        Returns an OrderedDict([('111', {'Name': ''}), ...]) mapping user ids
        to names.

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
        OrderedDict([('111', {'Name': 'Mark'}), ('222', {'Name': 'Dave'})])
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
        """

        soup = BeautifulSoup(content, "lxml")

        friends_found = OrderedDict()

        main_soup = soup.find(id="friends_center_main")
        if not main_soup:
            logging.error("Failed to parse friends page")
            return friends_found

        links_soup = main_soup.find_all("a")
        for link in links_soup:
            if "href" in link.attrs:
                uid_found = re.findall(r'uid=\d+', link.attrs["href"])
                if uid_found:
                    friends_found[uid_found[0].replace("uid=", "")] =\
                        { "Name": link.text }

        return friends_found
