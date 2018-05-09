from core import common
from core.facebook_fetcher import FacebookFetcher
from core.facebook_soup_parser import ReactionResult, TimelineResult, \
    GenericResult
from tests.mocks import create_mock_downloader, create_mock_facebook_parser
from tests.fakes import create_ok_return_value, create_fake_config

from collections import OrderedDict
from nose.tools import assert_equal
from unittest.mock import call, Mock, ANY


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

            assert_equal(buddy_list, fake_buddy_list)

            mock_fb_parser.parse_buddy_list.assert_called_once_with(
                "content1")


def test_fetch_lat_returns_empty_buddy_list_when_downloader_raises():

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = RuntimeError()

            buddy_list = fb_fetcher.fetch_last_active_times()

            assert_equal(len(buddy_list), 0)

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

            assert_equal(len(buddy_list), 0)

            mock_fb_parser.parse_buddy_list.assert_called_once_with(ANY)


def test_fetch_user_friend_list_works():

    expected_url = "https://mbasic.facebook.com/profile.php?v=friends&id=123"

    expected_friend_list = OrderedDict(
        [
            ("username1", {'name': 'Mark'}),
            ("profile.php?id=2222", {'name': 'Dave'}),
            ("username3", {'name': 'John'}),
            ("username4", {'name': 'Paul'})
        ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.side_effect = [
                create_ok_return_value("content")
            ]
            mock_fb_parser.parse_friends_page.side_effect = [
                GenericResult(
                    content=OrderedDict([
                        ('friends',
                            OrderedDict([
                                ('username1?fref=fr_tab&amp;foo', 'Mark'),
                                ('profile.php?id=2222&fref=fr_tab', 'Dave'),
                                ('username3?fref=fr_tab&amp;foo', 'John'),
                                ('username4?fref=fr_tab&amp;foo', 'Paul')
                            ])),
                    ]),
                    see_more_links=[]
                )
            ]

            res = fb_fetcher.fetch_user_friend_list()
            assert_equal(res, expected_friend_list)

            mock_downloader.fetch_url.assert_called_once_with(
                url=expected_url,
                cookie=ANY, timeout_secs=ANY, retries=ANY
            )
            mock_fb_parser.parse_friends_page.assert_called_once_with(
                "content")


def test_fetch_liked_pages_works():

    expected_url = \
        "https://mbasic.facebook.com/profile.php?v=likes&id=111"
    expected_liked_pages = OrderedDict(
        [
            ('Music', OrderedDict([('musicLink1/', 'Music 1')]))
        ])

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, create_fake_config())

            mock_downloader.fetch_url.return_value = \
                create_ok_return_value("content")

            mock_fb_parser.parse_likes_page.return_value = \
                GenericResult(
                    content=OrderedDict([
                        ('Music',
                            OrderedDict([('musicLink1/', 'Music 1')])),
                    ]),
                    see_more_links=[]
                )

            res = fb_fetcher.do_fetch_liked_pages(111)

            assert_equal(res, expected_liked_pages)

            mock_downloader.fetch_url.assert_called_once_with(
                url=expected_url,
                cookie=ANY, timeout_secs=ANY, retries=ANY
            )
            mock_fb_parser.parse_likes_page.assert_called_once_with(
                "content")


def test_fetch_content_recursively_stops_when_all_links_explored():

    expected_urls = [
        "initialUrl",
        "https://mbasic.facebook.com/showMoreLink2",
        "https://mbasic.facebook.com/showMoreLink1"
    ]

    expected_content = OrderedDict(
        [
            ('Category 1', OrderedDict([('cat1Link1/', 'Category 1 - 1')])),
            ('Category 2',
                OrderedDict([
                    ('cat2Link1/', 'Category 2 - 1'),
                    ('cat2Link2/', 'Category 2 - 2'),
                    ('cat2Link3/', 'Category 2 - 3'),
                    ('cat2Link4/', 'Category 2 - 4')
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
            mock_parse = Mock(side_effect=[
                GenericResult(
                    content=OrderedDict([
                        ('Category 1',
                            OrderedDict([('cat1Link1/', 'Category 1 - 1')])),
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link1/', 'Category 2 - 1')
                            ]))
                    ]),
                    see_more_links=[
                        '/showMoreLink1', '/showMoreLink2']
                ),
                GenericResult(
                    content=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link1/?fref=none&refid=17',
                                    'Category 2 - 1'),
                                ('cat2Link2/', 'Category 2 - 2'),
                                ('cat2Link3/', 'Category 2 - 3')
                            ]))
                    ]),
                    see_more_links=[]
                ),
                GenericResult(
                    content=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link4/', 'Category 2 - 4')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ])

            res = fb_fetcher.fetch_content_recursively(
                "initialUrl", mock_parse)

            assert_equal(res, expected_content)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_parse.assert_has_calls([
                call("content1"),
                call("content2"),
                call("content3")
            ])


def test_fetch_content_recursively_is_resilient_to_downloader_exception():

    expected_urls = [
        "initialUrl",
        "https://mbasic.facebook.com/showMoreLink2",
        "https://mbasic.facebook.com/showMoreLink1"
    ]

    expected_content = OrderedDict(
        [
            ('Category 1', OrderedDict([('cat1Link1/', 'Category 1 - 1')])),
            ('Category 2',
                OrderedDict([
                    ('cat2Link1/', 'Category 2 - 1'),
                    ('cat2Link4/', 'Category 2 - 4')
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
            mock_parse = Mock(side_effect=[
                GenericResult(
                    content=OrderedDict([
                        ('Category 1',
                            OrderedDict([('cat1Link1/', 'Category 1 - 1')])),
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link1/', 'Category 2 - 1')
                            ]))
                    ]),
                    see_more_links=[
                        '/showMoreLink1', '/showMoreLink2']
                ),
                GenericResult(
                    content=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link4/', 'Category 2 - 4')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ])

            res = fb_fetcher.fetch_content_recursively(
                "initialUrl", mock_parse)

            assert_equal(res, expected_content)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_parse.assert_has_calls([
                call("content1"),
                call("content3")
            ])


def test_fetch_content_recursively_is_resilient_to_parser_exceptions():

    expected_urls = [
        "initialUrl",
        "https://mbasic.facebook.com/showMoreLink2",
        "https://mbasic.facebook.com/showMoreLink1"
    ]

    expected_content = OrderedDict(
        [
            ('Category 1', OrderedDict([('cat1Link1/', 'Category 1 - 1')])),
            ('Category 2',
                OrderedDict([
                    ('cat2Link1/', 'Category 2 - 1'),
                    ('cat2Link4/', 'Category 2 - 4')
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
            mock_parse = Mock(side_effect=[
                GenericResult(
                    content=OrderedDict([
                        ('Category 1',
                            OrderedDict([('cat1Link1/', 'Category 1 - 1')])),
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link1/', 'Category 2 - 1')
                            ]))
                    ]),
                    see_more_links=[
                        '/showMoreLink1', '/showMoreLink2']
                ),
                RuntimeError("Boom"),
                GenericResult(
                    content=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link4/', 'Category 2 - 4')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ])

            res = fb_fetcher.fetch_content_recursively(
                "initialUrl", mock_parse)

            assert_equal(res, expected_content)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_parse.assert_has_calls([
                call("content1"),
                call("content2"),
                call("content3")
            ])


def test_fetch_content_recursively_is_resilient_to_parser_error():

    expected_urls = [
        "initialUrl",
        "https://mbasic.facebook.com/showMoreLink2",
        "https://mbasic.facebook.com/showMoreLink1"
    ]

    expected_content = OrderedDict(
        [
            ('Category 1', OrderedDict([('cat1Link1/', 'Category 1 - 1')])),
            ('Category 2',
                OrderedDict([
                    ('cat2Link1/', 'Category 2 - 1'),
                    ('cat2Link4/', 'Category 2 - 4')
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
            mock_parse = Mock(side_effect=[
                GenericResult(
                    content=OrderedDict([
                        ('Category 1',
                            OrderedDict([('cat1Link1/', 'Category 1 - 1')])),
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link1/', 'Category 2 - 1')
                            ]))
                    ]),
                    see_more_links=[
                        '/showMoreLink1', '/showMoreLink2']
                ),
                None,
                GenericResult(
                    content=OrderedDict([
                        ('Category 2',
                            OrderedDict([
                                ('cat2Link4/', 'Category 2 - 4')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ])

            res = fb_fetcher.fetch_content_recursively(
                "initialUrl", mock_parse)

            assert_equal(res, expected_content)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_parse.assert_has_calls([
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

            res = fb_fetcher.fetch_user_infos(user_ids, False, False, False)

            assert_equal(res, expected_results)

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
        ('username.1', OrderedDict([
            ('name', "Mutual friend 1")
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
            mock_fb_parser.parse_mutual_friends_page.return_value = \
                GenericResult(
                    content=OrderedDict([
                        ('mutual_friends',
                            OrderedDict([(
                                '/username.1?fref=fr_tab&refid=17',
                                'Mutual friend 1')]))
                    ]),
                    see_more_links=[]
                )

            res = fb_fetcher.fetch_user_infos(user_ids, False, False, True)

            assert_equal(res, expected_results)

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
        "https://mbasic.facebook.com/profile.php?v=likes&id=110"

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
                GenericResult(
                    content=OrderedDict([
                        ('Category',
                            OrderedDict([
                                ('/link/', 'Name')
                            ]))
                    ]),
                    see_more_links=[]
                )
            ]

            res = fb_fetcher.fetch_user_infos(user_ids, False, True, False)

            assert_equal(res, expected_results)

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

            res = fb_fetcher.fetch_user_infos([110, 111], False, False, False)

            assert_equal(res, expected_results)

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

            res = fb_fetcher.fetch_user_infos([110, 111], False, False, False)

            assert_equal(res, expected_results)

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

            res = fb_fetcher.fetch_user_infos([110, 111], False, False, False)

            assert_equal(res, expected_results)

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
            "https://mbasic.facebook.com/ShowMoreFromMainPage-Link1",
            "https://mbasic.facebook.com/ShowMoreFromMainPage-Link2",
            "https://mbasic.facebook.com/Link1FromMainPage",
            "https://mbasic.facebook.com/ShowMoreFromLink1-1",
            "https://mbasic.facebook.com/ShowMoreFromLink1-2",
            "https://mbasic.facebook.com/Link2FromMainPage"
        ]
    expected_results = OrderedDict([
        ("mark", OrderedDict([
            ("posts", OrderedDict([
                (100, OrderedDict([("someData", "1"), ('page', 'mark')])),
                (200, OrderedDict([("someData", "2"), ('page', 'mark')])),
                (300, OrderedDict([("someData", "3"), ('page', 'mark')])),
                (400, OrderedDict([("someData", "4"), ('page', 'mark')])),
                (500, OrderedDict([("someData", "5"), ('page', 'mark')])),
                (600, OrderedDict([("someData", "6"), ('page', 'mark')])),
                (700, OrderedDict([("someData", "7"), ('page', 'mark')])),
                (800, OrderedDict([("someData", "8"), ('page', 'mark')]))
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
                        (100, OrderedDict([("someData", "1")])),
                        (200, OrderedDict([("someData", "2")]))
                    ]),
                    show_more_link="/ShowMoreFromMainPage-Link1"),
                TimelineResult(
                    articles=OrderedDict([
                        (300, OrderedDict([("someData", "3")]))
                    ]),
                    show_more_link="/ShowMoreFromMainPage-Link2"),
                TimelineResult(
                    articles=OrderedDict([
                        (400, OrderedDict([("someData", "4")]))
                    ]),
                    show_more_link=""),
                TimelineResult(
                    articles=OrderedDict([
                        (500, OrderedDict([("someData", "5")]))
                    ]),
                    show_more_link="/ShowMoreFromLink1-1"),
                TimelineResult(
                    articles=OrderedDict([
                        (600, OrderedDict([("someData", "6")]))
                    ]),
                    show_more_link="/ShowMoreFromLink1-2"),
                TimelineResult(
                    articles=OrderedDict([
                        (700, OrderedDict([("someData", "7")]))
                    ]),
                    show_more_link=""),
                TimelineResult(
                    articles=OrderedDict([
                        (800, OrderedDict([("someData", "8")]))
                    ]),
                    show_more_link=""),
            ]

            res = fb_fetcher.fetch_articles_from_timeline(["mark"])

            assert_equal(res, expected_results)

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
            "https://mbasic.facebook.com/Link1FromMainPage",
            "https://mbasic.facebook.com/Link2FromMainPage"
        ]
    expected_results = OrderedDict([
        ("mark", OrderedDict([
            ("posts", OrderedDict([
                (300, OrderedDict([("someData", "3"), ('page', 'mark')]))
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
                        (300, OrderedDict([("someData", "3")]))
                    ]),
                    show_more_link=""),
            ]

            res = fb_fetcher.fetch_articles_from_timeline(["mark"])

            assert_equal(res, expected_results)

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

            assert_equal(sorted(res), sorted(expected_likers))

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

            assert_equal(sorted(res), sorted(expected_likers))

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

            assert_equal(sorted(res), sorted(expected_likers))

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

            assert_equal(sorted(res), sorted(expected_likers))

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

            assert_equal(sorted(res), sorted(expected_likers))

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

            assert_equal(sorted(res), sorted(expected_likers))

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

            assert_equal(sorted(res), sorted(expected_likers))

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

            assert_equal(res, expected_results)

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

            assert_equal(res, expected_results)

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)] * len(expected_urls))
