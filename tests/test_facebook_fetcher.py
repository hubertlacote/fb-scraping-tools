from core import common
from core.facebook_fetcher import FacebookFetcher
from core.facebook_soup_parser import TimelineResult
from tests.mocks import create_mock_downloader, create_mock_facebook_parser
from tests.fakes import create_ok_return_value, create_fake_config

from collections import OrderedDict
from unittest.mock import call, ANY


def test_fetch_lat_calls_downloader_correctly():

    config = common.Config(
        cookie_xs="abc", user_id="123", client_id="456a")

    expected_cookie = "c_user=123; xs=abc; noscript=1;"
    expected_url = \
        "https://5-edge-chat.facebook.com/pull?channel=p_123&seq=1&" + \
        "partition=-2&clientid=456a&cb=ze0&idle=0&qp=yisq=129169&" + \
        "msgs_recv=0&uid=123&viewer_uid=123&sticky_token=1058&" + \
        "sticky_pool=lla1c22_chat-proxy&state=active"
    expected_timeout = 15
    expected_retries = 5

    with create_mock_downloader() as mock_downloader:

        with create_mock_facebook_parser() as mock_fb_parser:

            fb_fetcher = FacebookFetcher(
                mock_downloader, mock_fb_parser, config)
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

            res = fb_fetcher.fetch_user_infos(user_ids)

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

            res = fb_fetcher.fetch_user_infos([110, 111])

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

            res = fb_fetcher.fetch_user_infos([110, 111])

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

            res = fb_fetcher.fetch_user_infos([110, 111])

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
        (100, OrderedDict([
            ('id', 100),
            ('date', '2008-05-13 10:02:00'),
            ('date_org', '13 May 2008 at 10:02')])),
        (200, OrderedDict([
            ('id', 200),
            ('date', '2008-05-13 10:25:00'),
            ('date_org', '13 May 2008 at 10:25')])),
        (300, OrderedDict([
            ('id', 300),
            ('date', '2008-05-15 11:02:00'),
            ('date_org', '15 May 2008 at 11:02')])),
        (400, OrderedDict([
            ('id', 400),
            ('date', '2007-02-01 09:00:00'),
            ('date_org', '1 February 2007 at 09:00')])),
        (500, OrderedDict([
            ('id', 500),
            ('date', '2007-02-02 10:00:00'),
            ('date_org', '2 February 2007 at 10:00')])),
        (600, OrderedDict([
            ('id', 600),
            ('date', '2007-02-03 11:00:00'),
            ('date_org', '3 February 2007 at 11:00')])),
        (700, OrderedDict([
            ('id', 700),
            ('date', '2007-02-04 12:00:00'),
            ('date_org', '4 February 2007 at 12:00')]))
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
                        (100, '13 May 2008 at 10:02'),
                        (200, '13 May 2008 at 10:25')]),
                    show_more_link="/ShowMoreFromMainPage"),
                TimelineResult(
                    articles=OrderedDict([
                        (300, '15 May 2008 at 11:02')]),
                    show_more_link=""),
                TimelineResult(
                    articles=OrderedDict([
                        (400, '1 February 2007 at 09:00')]),
                    show_more_link=""),
                TimelineResult(
                    articles=OrderedDict([
                        (500, '2 February 2007 at 10:00')]),
                    show_more_link="/ShowMoreFromLink1-1"),
                TimelineResult(
                    articles=OrderedDict([
                        (600, '3 February 2007 at 11:00')]),
                    show_more_link="/ShowMoreFromLink1-2"),
                TimelineResult(
                    articles=OrderedDict([
                        (700, '4 February 2007 at 12:00')]),
                    show_more_link=""),
            ]

            res = fb_fetcher.fetch_articles_from_timeline("mark")

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


def test_fetch_articles_liked_per_user():

    expected_urls = [
        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=10000&total_count=10000&ft_ent_identifier=100",

        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=10000&total_count=10000&ft_ent_identifier=200",

        "https://mbasic.facebook.com/ufi/reaction/profile/browser/fetch/?" +
        "limit=10000&total_count=10000&ft_ent_identifier=300"
    ]

    expected_results = OrderedDict([
        ('username1', {100}),
        ('username2', {100, 200}),
        ('username3', {200})
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
                    ["username1", "username2"],
                    ["username2", "username3"],
                    []
                ]

            res = fb_fetcher.fetch_articles_liked_per_user([100, 200, 300])

            assert res == expected_results

            mock_downloader.fetch_url.assert_has_calls([
                call(
                    url=expected_urls[i],
                    cookie=ANY, timeout_secs=ANY, retries=ANY
                ) for i in range(0, len(expected_urls))
            ])
            mock_fb_parser.parse_reaction_page.assert_has_calls(
                [call(fake_return_value.text)] * len(expected_urls))
