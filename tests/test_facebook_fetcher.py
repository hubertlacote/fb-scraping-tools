from core import common
from core.facebook_fetcher import FacebookFetcher
from core.facebook_soup_parser import ReactionResult, TimelineResult, \
    LikesResult
from tests.mocks import create_mock_downloader, create_mock_facebook_parser
from tests.fakes import create_ok_return_value, create_fake_config

from collections import OrderedDict
from unittest.mock import call, ANY


def test_fetch_lat_calls_downloader_correctly():

    expected_cookie = "c_user=123; xs=abc; noscript=1;"
    expected_url = \
        "https://5-edge-chat.facebook.com/pull?channel=p_123&seq=1&" + \
        "partition=-2&clientid=1a2b3c4d&cb=ze0&idle=0&qp=yisq=129169&" + \
        "msgs_recv=0&uid=123&viewer_uid=123&sticky_token=1058&" + \
        "sticky_pool=lla1c22_chat-proxy&state=active"
    expected_timeout = 15
    expected_retries = 5

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())
            fb_fetcher.fetch_last_active_times()

            mock_downloader.fetch_url.assert_called_once_with(
                cookie=expected_cookie, url=expected_url,
                timeout_secs=expected_timeout, retries=expected_retries)


def test_fetch_lat_returns_buddy_list():

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value("content1")
            fake_buddy_list = \
                OrderedDict([('111', [1500000001]), ('222', [1500000002])])
            mock_downloader.fetch_url.return_value = fake_return_value
            mock_fb_parser.parse_buddy_list.return_value = fake_buddy_list

            buddy_list = fb_fetcher.fetch_last_active_times()

            assert buddy_list == fake_buddy_list

            mock_fb_parser.parse_buddy_list.assert_called_once_with(
                "content1")


def test_fetch_lat_returns_empty_buddy_list_when_downloader_raises():

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = RuntimeError()

            buddy_list = fb_fetcher.fetch_last_active_times()

            assert len(buddy_list) == 0

            mock_downloader.fetch_url.assert_called_once_with(
                cookie=ANY, url=ANY,
                timeout_secs=ANY, retries=ANY)


def test_fetch_lat_returns_empty_buddy_list_when_fb_parser_raises():

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_fb_parser.parse_buddy_list.side_effect = RuntimeError()

            buddy_list = fb_fetcher.fetch_last_active_times()

            assert len(buddy_list) == 0

            mock_fb_parser.parse_buddy_list.assert_called_once_with(ANY)


def test_fetch_friend_list_stops_when_no_friends_returned():

    expected_friend_list = OrderedDict(
        [
            ('111', {'Name': 'Mark'}), ('222', {'Name': 'Dave'}),
            ('333', {'Name': 'John'}), ('444', {'Name': 'Paul'})
        ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                create_ok_return_value("content2"),
                create_ok_return_value("content3")
            ]
            mock_fb_parser.parse_friends_page.side_effect = [
                OrderedDict(
                    [('111', {'Name': 'Mark'}), ('222', {'Name': 'Dave'})]),
                OrderedDict(
                    [('333', {'Name': 'John'}), ('444', {'Name': 'Paul'})]),
                OrderedDict()
            ]

            res = fb_fetcher.fetch_friend_list()

            assert res == expected_friend_list

            mock_fb_parser.parse_friends_page.assert_has_calls([
                call("content1"),
                call("content2"),
                call("content3")
            ])


def test_fetch_friend_list_stops_when_downloader_raises():

    expected_friend_list = OrderedDict(
        [('111', {'Name': 'Mark'}), ('222', {'Name': 'Dave'})])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                RuntimeError()
            ]
            mock_fb_parser.parse_friends_page.side_effect = [
                expected_friend_list,
                OrderedDict()
            ]

            res = fb_fetcher.fetch_friend_list()

            assert res == expected_friend_list

            mock_fb_parser.parse_friends_page.assert_called_once_with(
                "content1")


def test_fetch_friend_list_stops_when_parser_raises():

    expected_friend_list = OrderedDict(
        [('111', {'Name': 'Mark'}), ('222', {'Name': 'Dave'})])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                create_ok_return_value("content2"),
            ]
            mock_fb_parser.parse_friends_page.side_effect = [
                expected_friend_list,
                RuntimeError("")
            ]

            res = fb_fetcher.fetch_friend_list()

            assert res == expected_friend_list

            mock_fb_parser.parse_friends_page.assert_has_calls([
                call("content1"),
                call("content2")
            ])


def test_fetch_liked_pages_stops_when_all_links_explored():

    expected_urls = [
        "https://mbasic.facebook.com/profile.php?v=likes&id=111&lst=111:1:1",
        "https://mbasic.facebook.com/showMoreLink2",
        "https://mbasic.facebook.com/showMoreLink1"
    ]

    expected_liked_pages = OrderedDict(
        [
            ('Category 1', OrderedDict([('/cat1Link1/', 'Category 1 - 1')])),
            ('Category 2',
                OrderedDict([
                    ('/cat2Link1/', 'Category 2 - 1'),
                    ('/cat2Link2/', 'Category 2 - 2'),
                    ('/cat2Link3/', 'Category 2 - 3'),
                    ('/cat2Link4/', 'Category 2 - 4')
                ]))
        ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                create_ok_return_value("content2"),
                create_ok_return_value("content3")
            ]
            mock_fb_parser.parse_likes_page.side_effect = [
                LikesResult(
                    liked_pages=OrderedDict([
                        ('Category 1',
                            OrderedDict([('/cat1Link1/', 'Category 1 - 1')])),
                        ('Category 2',
                            OrderedDict([
                                ('/cat2Link1/', 'Category 2 - 1')
                            ]))
                    ]),
                    see_more_links=[
                        '/showMoreLink1', '/showMoreLink2']
                ),
                LikesResult(
                    liked_pages=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('/cat2Link1/?fref=none&refid=17',
                                    'Category 2 - 1'),
                                ('/cat2Link2/', 'Category 2 - 2'),
                                ('/cat2Link3/', 'Category 2 - 3')
                            ]))
                    ]),
                    see_more_links=[]
                ),
                LikesResult(
                    liked_pages=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('/cat2Link4/', 'Category 2 - 4')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ]

            res = fb_fetcher.fetch_liked_pages(111)

            assert res == expected_liked_pages

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_likes_page.assert_has_calls([
                call("content1"),
                call("content2"),
                call("content3")
            ])


def test_fetch_liked_pages_is_resilient_to_downloader_exception():

    expected_urls = [
        "https://mbasic.facebook.com/profile.php?v=likes&id=111&lst=111:1:1",
        "https://mbasic.facebook.com/showMoreLink2",
        "https://mbasic.facebook.com/showMoreLink1"
    ]

    expected_liked_pages = OrderedDict(
        [
            ('Category 1', OrderedDict([('/cat1Link1/', 'Category 1 - 1')])),
            ('Category 2',
                OrderedDict([
                    ('/cat2Link1/', 'Category 2 - 1'),
                    ('/cat2Link4/', 'Category 2 - 4')
                ]))
        ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                RuntimeError("Boom"),
                create_ok_return_value("content3")
            ]
            mock_fb_parser.parse_likes_page.side_effect = [
                LikesResult(
                    liked_pages=OrderedDict([
                        ('Category 1',
                            OrderedDict([('/cat1Link1/', 'Category 1 - 1')])),
                        ('Category 2',
                            OrderedDict([
                                ('/cat2Link1/', 'Category 2 - 1')
                            ]))
                    ]),
                    see_more_links=[
                        '/showMoreLink1', '/showMoreLink2']
                ),
                LikesResult(
                    liked_pages=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('/cat2Link4/', 'Category 2 - 4')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ]

            res = fb_fetcher.fetch_liked_pages(111)

            assert res == expected_liked_pages

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_likes_page.assert_has_calls([
                call("content1"),
                call("content3")
            ])


def test_fetch_liked_pages_is_resilient_to_parser_exceptions():

    expected_urls = [
        "https://mbasic.facebook.com/profile.php?v=likes&id=111&lst=111:1:1",
        "https://mbasic.facebook.com/showMoreLink2",
        "https://mbasic.facebook.com/showMoreLink1"
    ]

    expected_liked_pages = OrderedDict(
        [
            ('Category 1', OrderedDict([('/cat1Link1/', 'Category 1 - 1')])),
            ('Category 2',
                OrderedDict([
                    ('/cat2Link1/', 'Category 2 - 1'),
                    ('/cat2Link4/', 'Category 2 - 4')
                ]))
        ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                create_ok_return_value("content2"),
                create_ok_return_value("content3")
            ]
            mock_fb_parser.parse_likes_page.side_effect = [
                LikesResult(
                    liked_pages=OrderedDict([
                        ('Category 1',
                            OrderedDict([('/cat1Link1/', 'Category 1 - 1')])),
                        ('Category 2',
                            OrderedDict([
                                ('/cat2Link1/', 'Category 2 - 1')
                            ]))
                    ]),
                    see_more_links=[
                        '/showMoreLink1', '/showMoreLink2']
                ),
                RuntimeError("Boom"),
                LikesResult(
                    liked_pages=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('/cat2Link4/', 'Category 2 - 4')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ]

            res = fb_fetcher.fetch_liked_pages(111)

            assert res == expected_liked_pages

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_likes_page.assert_has_calls([
                call("content1"),
                call("content2"),
                call("content3")
            ])


def test_fetch_user_infos_handles_ids_and_usernames():

    user_ids = [110, '111', 'profile.php?id=123', 'paul']

    expected_url_user_110 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=110"
    expected_url_user_111 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=111"
    expected_url_user_123 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=123"
    expected_url_user_paul = \
        "https://mbasic.facebook.com/paul/about"

    fake_infos_user_110 = OrderedDict(
        [('id', 110), ('Name', 'Mark')])
    fake_infos_user_111 = OrderedDict(
        [('id', 111), ('Name', 'Dave')])
    fake_infos_user_123 = OrderedDict(
        [('id', 123), ('Name', 'John')])
    fake_infos_user_paul = OrderedDict(
        [('id', 234), ('Name', 'Paul')])

    expected_results = {
        110: fake_infos_user_110,
        '111': fake_infos_user_111,
        'profile.php?id=123': fake_infos_user_123,
        'paul': fake_infos_user_paul
    }

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                create_ok_return_value("content2"),
                create_ok_return_value("content3"),
                create_ok_return_value("content4")
            ]
            mock_fb_parser.parse_about_page.side_effect = [
                fake_infos_user_110,
                fake_infos_user_111,
                fake_infos_user_123,
                fake_infos_user_paul
            ]

            res = fb_fetcher.fetch_user_infos(user_ids, False, False)

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_url_user_110,
                    cookie=ANY, timeout_secs=ANY, retries=ANY),
                call(
                    url=expected_url_user_111,
                    cookie=ANY, timeout_secs=ANY, retries=ANY),
                call(
                    url=expected_url_user_123,
                    cookie=ANY, timeout_secs=ANY, retries=ANY),
                call(
                    url=expected_url_user_paul,
                    cookie=ANY, timeout_secs=ANY, retries=ANY)
            ])
            mock_fb_parser.parse_about_page.assert_has_calls([
                call("content1"),
                call("content2"),
                call("content3"),
                call("content4")
            ])


def test_fetch_user_infos_can_fetch_mutual_friends():

    user_ids = [110]

    expected_about_page_url = \
        "https://mbasic.facebook.com/profile.php?v=info&id=110"
    expected_mutual_friends_url = \
        "https://mbasic.facebook.com/profile.php?v=friends&mutual=1&\
lst=123:110:1&id=110"

    fake_mutual_friends = OrderedDict([
        ('mutual.friend.1', OrderedDict([
            ('name', "Mutual friend 1")
        ])),
        ('mutual.friend.2', OrderedDict([
            ('name', "Mutual friend 2")
        ]))
    ])

    fake_user_infos = OrderedDict(
        [('id', 110), ('Name', 'Mark')])

    fake_user_infos_with_mutual_friends = \
        fake_user_infos
    fake_user_infos_with_mutual_friends["mutual_friends"] = \
        fake_mutual_friends

    expected_results = {
        110: fake_user_infos_with_mutual_friends,
    }

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("aboutPageContent"),
                create_ok_return_value("mutualFriendsPageContent")
            ]
            mock_fb_parser.parse_about_page.side_effect = [
                fake_user_infos
            ]
            mock_fb_parser.parse_mutual_friends_page.side_effect = [
                fake_mutual_friends
            ]

            res = fb_fetcher.fetch_user_infos(user_ids, False, True)

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_about_page_url,
                    cookie=ANY, timeout_secs=ANY, retries=ANY),
                call(
                    url=expected_mutual_friends_url,
                    cookie=ANY, timeout_secs=ANY, retries=ANY)
            ])
            mock_fb_parser.parse_about_page.assert_has_calls([
                call("aboutPageContent")])
            mock_fb_parser.parse_mutual_friends_page.assert_has_calls([
                call("mutualFriendsPageContent")])


def test_fetch_user_infos_can_fetch_likes():

    user_ids = [110]

    expected_about_page_url = \
        "https://mbasic.facebook.com/profile.php?v=info&id=110"
    expected_likes_url = \
        "https://mbasic.facebook.com/profile.php?v=likes&id=110&lst=110:1:1"

    fake_user_infos = OrderedDict(
        [('id', 110), ('Name', 'Mark')])

    fake_user_infos_with_likes = \
        fake_user_infos
    fake_user_infos_with_likes["paged_likes"] = \
        OrderedDict(
        [
            ('Category', OrderedDict([('/link/', 'Name')]))
        ])

    expected_results = {
        110: fake_user_infos_with_likes,
    }

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("aboutPageContent"),
                create_ok_return_value("likesPageContent")
            ]
            mock_fb_parser.parse_about_page.side_effect = [
                fake_user_infos
            ]
            mock_fb_parser.parse_likes_page.side_effect = [
                LikesResult(
                    liked_pages=OrderedDict([
                        ('Category',
                            OrderedDict([
                                ('/link/', 'Name')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ]

            res = fb_fetcher.fetch_user_infos(user_ids, True, False)

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_about_page_url,
                    cookie=ANY, timeout_secs=ANY, retries=ANY),
                call(
                    url=expected_likes_url,
                    cookie=ANY, timeout_secs=ANY, retries=ANY)
            ])
            mock_fb_parser.parse_about_page.assert_has_calls([
                call("aboutPageContent")])
            mock_fb_parser.parse_likes_page.assert_has_calls([
                call("likesPageContent")])


def test_fetch_user_infos_is_resilient_to_downloader_exception():

    expected_url_user_110 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=110"
    expected_url_user_111 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=111"

    fake_infos_user_110 = OrderedDict(
        [('id', 110)])
    fake_infos_user_111 = OrderedDict(
        [('id', 111), ('Name', 'Dave')])

    expected_results = {
        110: fake_infos_user_110,
        111: fake_infos_user_111
    }

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                RuntimeError(),
                create_ok_return_value("content2")
            ]
            mock_fb_parser.parse_about_page.return_value = fake_infos_user_111

            res = fb_fetcher.fetch_user_infos([110, 111], False, False)

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_url_user_110,
                    cookie=ANY, timeout_secs=ANY, retries=ANY),
                call(
                    url=expected_url_user_111,
                    cookie=ANY, timeout_secs=ANY, retries=ANY)
            ])
            mock_fb_parser.parse_about_page.assert_called_once_with("content2")


def test_fetch_user_infos_is_resilient_to_fb_parser_exception():

    expected_url_user_110 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=110"
    expected_url_user_111 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=111"

    fake_infos_user_110 = OrderedDict(
        [('id', 110)])
    fake_infos_user_111 = OrderedDict(
        [('id', 111), ('Name', 'Dave')])

    expected_results = {
        110: fake_infos_user_110,
        111: fake_infos_user_111
    }

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                create_ok_return_value("content2")
            ]
            mock_fb_parser.parse_about_page.side_effect = [
                RuntimeError(),
                fake_infos_user_111
            ]

            res = fb_fetcher.fetch_user_infos([110, 111], False, False)

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_url_user_110,
                    cookie=ANY, timeout_secs=ANY, retries=ANY),
                call(
                    url=expected_url_user_111,
                    cookie=ANY, timeout_secs=ANY, retries=ANY)
            ])
            mock_fb_parser.parse_about_page.assert_has_calls([
                call("content1"),
                call("content2"),
            ])


def test_fetch_user_infos_is_resilient_to_fb_parser_failure():

    expected_url_user_110 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=110"
    expected_url_user_111 = \
        "https://mbasic.facebook.com/profile.php?v=info&id=111"

    fake_infos_user_110 = OrderedDict(
        [('id', 110)])
    fake_infos_user_111 = OrderedDict(
        [('id', 111), ('Name', 'Dave')])

    expected_results = {
        110: fake_infos_user_110,
        111: fake_infos_user_111
    }

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content1"),
                create_ok_return_value("content2")
            ]
            mock_fb_parser.parse_about_page.side_effect = [
                None,
                fake_infos_user_111
            ]

            res = fb_fetcher.fetch_user_infos([110, 111], False, False)

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_url_user_110,
                    cookie=ANY, timeout_secs=ANY, retries=ANY),
                call(
                    url=expected_url_user_111,
                    cookie=ANY, timeout_secs=ANY, retries=ANY)
            ])
            mock_fb_parser.parse_about_page.assert_has_calls([
                call("content1"),
                call("content2"),
            ])


def test_fetch_articles_from_timelines_visits_all_links():

    expected_urls = \
        [
            "https://mbasic.facebook.com/mark?v=timeline",
            "https://mbasic.facebook.com/ShowMoreFromMainPage",
            "https://mbasic.facebook.com/Link2FromMainPage",
            "https://mbasic.facebook.com/Link1FromMainPage",
            "https://mbasic.facebook.com/ShowMoreFromLink1-1",
            "https://mbasic.facebook.com/ShowMoreFromLink1-2"
        ]
    expected_results = OrderedDict([
        ("mark", OrderedDict([
            ("posts", OrderedDict([
                (100, "orderedDict1"),
                (200, "orderedDict2"),
                (300, "orderedDict3"),
                (400, "orderedDict4"),
                (500, "orderedDict5"),
                (600, "orderedDict6"),
                (700, "orderedDict7")
                ]))
            ]))
    ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [create_ok_return_value("mainPage")] + \
                [fake_return_value] * (len(expected_urls) - 1)

            mock_fb_parser.parse_timeline_years_links.return_value =\
                ["/Link1FromMainPage", "/Link2FromMainPage"]

            mock_fb_parser.parse_timeline_page.side_effect = [
                TimelineResult(
                    articles=OrderedDict([
                        (100, "orderedDict1"),
                        (200, "orderedDict2")
                    ]),
                    show_more_link="/ShowMoreFromMainPage"),
                TimelineResult(
                    articles=OrderedDict([
                        (300, "orderedDict3")
                    ]),
                    show_more_link=""),
                TimelineResult(
                    articles=OrderedDict([
                        (400, "orderedDict4")
                    ]),
                    show_more_link=""),
                TimelineResult(
                    articles=OrderedDict([
                        (500, "orderedDict5")
                    ]),
                    show_more_link="/ShowMoreFromLink1-1"),
                TimelineResult(
                    articles=OrderedDict([
                        (600, "orderedDict6")
                    ]),
                    show_more_link="/ShowMoreFromLink1-2"),
                TimelineResult(
                    articles=OrderedDict([
                        (700, "orderedDict7")
                    ]),
                    show_more_link=""),
            ]

            res = fb_fetcher.fetch_articles_from_timeline(["mark"])

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_timeline_years_links.assert_called_once_with(
                "mainPage")
            mock_fb_parser.parse_timeline_page.assert_has_calls(
                [call("mainPage")] + [
                        call(
                            fake_return_value.text
                        ) for i in range(0, len(expected_urls) - 1)
                    ])


def test_fetch_articles_from_timelines_is_resilient_to_fb_parser_failure():

    expected_urls = \
        [
            "https://mbasic.facebook.com/mark?v=timeline",
            "https://mbasic.facebook.com/Link2FromMainPage",
            "https://mbasic.facebook.com/Link1FromMainPage"
        ]
    expected_results = OrderedDict([
        ("mark", OrderedDict([
            ("posts", OrderedDict([
                (300, "orderedDict3")
                ]))
            ]))
    ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [create_ok_return_value("mainPage")] + \
                [fake_return_value] * (len(expected_urls) - 1)

            mock_fb_parser.parse_timeline_years_links.return_value =\
                ["/Link1FromMainPage", "/Link2FromMainPage"]

            mock_fb_parser.parse_timeline_page.side_effect = [
                RuntimeError(),
                None,
                TimelineResult(
                    articles=OrderedDict([
                        (300, "orderedDict3")
                    ]),
                    show_more_link=""),
            ]

            res = fb_fetcher.fetch_articles_from_timeline(["mark"])

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_timeline_years_links.assert_called_once_with(
                "mainPage")
            mock_fb_parser.parse_timeline_page.assert_has_calls(
                [call("mainPage")] + [
                        call(
                            fake_return_value.text
                        ) for i in range(0, len(expected_urls) - 1)
                    ])


def test_fetch_likers_for_article():

    expected_url = \
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" + \
        "limit=500&total_count=1000000&ft_ent_identifier=100"

    expected_likers = set(["username1", "username2"])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [fake_return_value]

            mock_fb_parser.parse_reaction_page.side_effect = \
                [
                    ReactionResult(
                        likers=["username1", "username2"],
                        see_more_link=None)
                ]

            res = fb_fetcher.fetch_likers_for_article(100)

            assert sorted(res) == sorted(expected_likers)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_url,
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                )
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)])


def test_fetch_likers_for_article_continue_until_no_show_more_links():

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&shown_ids=1111%2C2222&total_count=4&" +
        "ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&shown_ids=1111%2C2222%2C3333%2C4444&total_count=4&" +
        "ft_ent_identifier=100",
    ]

    expected_likers = set(["1111", "2222", "3333", "4444"])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [fake_return_value] * len(expected_urls)

            mock_fb_parser.parse_reaction_page.side_effect = \
                [
                    ReactionResult(
                        likers=["1111", "2222"],
                        see_more_link="/ufi/" +
                                      "reaction/profile/browser/fetch/?" +
                                      "limit=10&shown_ids=1111%2C2222&" +
                                      "total_count=4&ft_ent_identifier=100"),
                    ReactionResult(
                        likers=["3333", "4444"],
                        see_more_link="/ufi/" +
                                      "reaction/profile/browser/fetch/?" +
                                      "limit=10&shown_ids=1111%2C2222" +
                                      "%2C3333%2C4444&" +
                                      "total_count=4&ft_ent_identifier=100"),
                    ReactionResult(
                        likers=[],
                        see_more_link=None)
                ]

            res = fb_fetcher.fetch_likers_for_article(100)

            assert sorted(res) == sorted(expected_likers)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)] * len(expected_urls))


def test_fetch_likers_for_article_retries_5_times_while_decreasing_max_likes():

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=250&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=166&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=125&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=100&total_count=1000000&ft_ent_identifier=100"
    ]

    expected_likers = set([])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = \
                [RuntimeError("Boom")] * len(expected_urls)

            res = fb_fetcher.fetch_likers_for_article(100)

            assert sorted(res) == sorted(expected_likers)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])


def test_fetch_likers_for_article_with_success_on_last_retry():

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=250&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=166&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=125&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=100&total_count=1000000&ft_ent_identifier=100"
    ]

    expected_likers = set(["username1", "username2"])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [RuntimeError("Boom")] * (len(expected_urls) - 1) + \
                [fake_return_value]

            mock_fb_parser.parse_reaction_page.side_effect = \
                [
                    ReactionResult(
                        likers=["username1", "username2"],
                        see_more_link=None)
                ]

            res = fb_fetcher.fetch_likers_for_article(100)

            assert sorted(res) == sorted(expected_likers)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)])


def test_fetch_likers_for_article_with_show_more_links_and_failure():

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&shown_ids=1111%2C2222&total_count=4&" +
        "ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=250&shown_ids=1111%2C2222&total_count=4&" +
        "ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=166&shown_ids=1111%2C2222&total_count=4&" +
        "ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=125&shown_ids=1111%2C2222&total_count=4&" +
        "ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=100&shown_ids=1111%2C2222&total_count=4&" +
        "ft_ent_identifier=100",
    ]

    expected_likers = set(["1111", "2222"])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [fake_return_value] + \
                [RuntimeError("Boom")] * (len(expected_urls) - 1)

            mock_fb_parser.parse_reaction_page.side_effect = \
                [
                    ReactionResult(
                        likers=["1111", "2222"],
                        see_more_link="/ufi/" +
                                      "reaction/profile/browser/fetch/?" +
                                      "limit=10&shown_ids=1111%2C2222&" +
                                      "total_count=4&ft_ent_identifier=100")
                ]

            res = fb_fetcher.fetch_likers_for_article(100)

            assert sorted(res) == sorted(expected_likers)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)])


def test_fetch_likers_for_article_with_invalid_see_more_link():

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=100"
    ]

    expected_likers = set(["1111", "2222"])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [fake_return_value]

            mock_fb_parser.parse_reaction_page.side_effect = \
                [
                    ReactionResult(
                        likers=["1111", "2222"],
                        # Limit=666 is invalid as limit=10 is
                        # hardcoded in FacebookFetcher
                        see_more_link="/ufi/" +
                                      "reaction/profile/browser/fetch/?" +
                                      "limit=666&shown_ids=1111%2C2222&" +
                                      "total_count=4&ft_ent_identifier=100")
                ]

            res = fb_fetcher.fetch_likers_for_article(100)

            assert sorted(res) == sorted(expected_likers)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)])


def test_fetch_likers_for_article_with_parser_exception():

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=100",
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&shown_ids=1111%2C2222&total_count=4&" +
        "ft_ent_identifier=100"
    ]

    expected_likers = set(["1111", "2222"])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [fake_return_value] * len(expected_urls)

            mock_fb_parser.parse_reaction_page.side_effect = \
                [
                    ReactionResult(
                        likers=["1111", "2222"],
                        see_more_link="/ufi/" +
                                      "reaction/profile/browser/fetch/?" +
                                      "limit=10&shown_ids=1111%2C2222&" +
                                      "total_count=4&ft_ent_identifier=100"),
                    RuntimeError("Boom")
                ]

            res = fb_fetcher.fetch_likers_for_article(100)

            assert sorted(res) == sorted(expected_likers)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)] * len(expected_urls))


def test_fetch_reactions_per_user_for_articles():

    input_articles = [
        OrderedDict([
            ('post_id', 100),
            ('additional', 'DataAreCopied')]),
        OrderedDict([
            ('post_id', 200)]),
        OrderedDict([
            ('post_id', 300)])
    ]

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=100",

        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=200",

        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=300"
    ]

    expected_results = OrderedDict([
        ('username1', {
            "likes": [
                OrderedDict([
                    ('post_id', 100),
                    ('additional', 'DataAreCopied')])
            ]
        }),
        ('username2', {
            "likes": [
                OrderedDict([
                    ('post_id', 100),
                    ('additional', 'DataAreCopied')]),
                OrderedDict([
                    ('post_id', 200)])
            ]
        }),
        ('username3', {
            "likes": [
                OrderedDict([
                    ('post_id', 200)])
            ]
        })
    ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [fake_return_value] * len(expected_urls)

            mock_fb_parser.parse_reaction_page.side_effect = \
                [
                    ReactionResult(
                        likers=["username1", "username2"],
                        see_more_link=None),
                    ReactionResult(
                        likers=["username2", "username3"],
                        see_more_link=None),
                    ReactionResult(
                        likers=[],
                        see_more_link=None)
                ]

            res = fb_fetcher.fetch_reactions_per_user_for_articles(
                input_articles, False)

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)] * len(expected_urls))


def test_fetch_reactions_per_user_for_articles_can_exclude_non_users():

    input_articles = [
        OrderedDict([
            ('post_id', 100)])
    ]

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=500&total_count=1000000&ft_ent_identifier=100"
    ]

    expected_results = OrderedDict([
        ('user.name', {
            "likes": [
                OrderedDict([
                    ('post_id', 100)])
            ]
        })
    ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            fake_return_value = create_ok_return_value()
            mock_downloader.fetch_url.side_effect = \
                [fake_return_value] * len(expected_urls)

            mock_fb_parser.parse_reaction_page.side_effect = \
                [
                    ReactionResult(
                        likers=[
                            "a/profile.php?fan&id=1234&gfid=AB12CD",
                            "SomeGroup/",
                            "user.name"
                        ],
                        see_more_link=None)
                ]

            res = fb_fetcher.fetch_reactions_per_user_for_articles(
                input_articles, True)

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)] * len(expected_urls))
