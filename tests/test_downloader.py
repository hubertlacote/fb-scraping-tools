from collections import namedtuple
from core.downloader import Downloader

from unittest.mock import call, patch, ANY

import requests

FAKE_URL = "http://fake.url"
FAKE_COOKIE = "fake cookie"

Fake_Return_Value = namedtuple(
    'FakeReturnValue', ['status_code', 'text', 'headers'])

def create_ok_return_value():
    return Fake_Return_Value(
        status_code=200,
        text="not empty",
        headers="Some headers"
    )
def create_ok_return_value_without_text():
    return Fake_Return_Value(
        status_code=200,
        text="",
        headers="Some headers"
    )
def create_not_found_return_value():
    return Fake_Return_Value(
        status_code=404,
        text="Page not found",
        headers="Some headers"
    )

@patch("core.downloader.requests.get")
def test_url_is_passed(mock_requests):
    downloader = Downloader()

    mock_requests.return_value = create_ok_return_value()
    downloader.fetch_url(FAKE_COOKIE, FAKE_URL)

    mock_requests.assert_called_once_with(
        url=FAKE_URL, headers=ANY, allow_redirects=ANY, timeout=ANY)

@patch("core.downloader.requests.get")
def test_cookie_is_passed_in_headers(mock_requests):
    downloader = Downloader()

    mock_requests.return_value = create_ok_return_value()
    downloader.fetch_url(FAKE_COOKIE, FAKE_URL)

    expected_headers = {
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ' +
            '(KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36',
        'cookie': FAKE_COOKIE
    }

    mock_requests.assert_called_once_with(
        headers=expected_headers, url=ANY,
        allow_redirects=ANY, timeout=ANY)

@patch("core.downloader.requests.get")
def test_redirect_is_enabled(mock_requests):
    downloader = Downloader()

    mock_requests.return_value = create_ok_return_value()
    downloader.fetch_url(FAKE_COOKIE, FAKE_URL)

    mock_requests.assert_called_once_with(
        allow_redirects=True, url=ANY, headers=ANY, timeout=ANY)

@patch("core.downloader.requests.get")
def test_default_timeout_is_passed(mock_requests):
    downloader = Downloader()

    mock_requests.return_value = create_ok_return_value()
    downloader.fetch_url(FAKE_COOKIE, FAKE_URL)

    mock_requests.assert_called_once_with(
        timeout=15, url=ANY, headers=ANY, allow_redirects=ANY)

@patch("core.downloader.requests.get")
def test_timeout_is_passed(mock_requests):
    downloader = Downloader()

    mock_requests.return_value = create_ok_return_value()
    downloader.fetch_url(FAKE_COOKIE, FAKE_URL, timeout_secs=3600)

    mock_requests.assert_called_once_with(
        timeout=3600, url=ANY, headers=ANY, allow_redirects=ANY)

@patch("core.downloader.requests.get")
def test_response_is_returned(mock_requests):
    downloader = Downloader()

    mock_requests.return_value = create_ok_return_value()
    res = downloader.fetch_url(FAKE_COOKIE, FAKE_URL)

    assert res == create_ok_return_value()

    mock_requests.assert_called_once_with(
        url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY)

@patch("core.downloader.requests.get")
def test_status_code_different_from_200_causes_exception(mock_requests):
    downloader = Downloader()

    mock_requests.return_value = create_not_found_return_value()
    got_ex = False
    try:
        downloader.fetch_url(FAKE_COOKIE, FAKE_URL)
    except RuntimeError:
        got_ex = True

    mock_requests.assert_called_once_with(
        url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY)
    assert got_ex

@patch("core.downloader.requests.get")
def test_empty_returned_text_causes_exception(mock_requests):
    downloader = Downloader()

    mock_requests.return_value = create_ok_return_value_without_text()
    got_ex = False
    try:
        downloader.fetch_url(FAKE_COOKIE, FAKE_URL)
    except RuntimeError:
        got_ex = True

    mock_requests.assert_called_once_with(
        url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY)
    assert got_ex

@patch("core.downloader.requests.get")
def test_exceptions_from_get_are_propagated(mock_requests):
    downloader = Downloader()

    mock_requests.side_effect = RuntimeError('Boom')
    got_ex = False
    try:
        downloader.fetch_url(FAKE_COOKIE, FAKE_URL)

    except RuntimeError:
        got_ex = True

    mock_requests.assert_called_once_with(
        url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY)
    assert got_ex

@patch("core.downloader.requests.get")
def test_timeout_is_propagated_when_retries_are_disabled(mock_requests):
    downloader = Downloader()

    mock_requests.side_effect = requests.exceptions.Timeout()
    got_ex = False
    try:
        downloader.fetch_url(FAKE_COOKIE, FAKE_URL)

    except requests.exceptions.Timeout:
        got_ex = True

    mock_requests.assert_called_once_with(
        url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY)
    assert got_ex

@patch("core.downloader.requests.get")
def test_retries_when_timeout_then_ok(mock_requests):
    downloader = Downloader()

    mock_requests.side_effect = [
        requests.exceptions.Timeout(),
        create_ok_return_value()
    ]

    res = downloader.fetch_url(FAKE_COOKIE, FAKE_URL, retries=3)

    assert res == create_ok_return_value()

    mock_requests.assert_has_calls([
        call(url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY),
        call(url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY)
    ])

@patch("core.downloader.requests.get")
def test_timeout_is_propagated_after_last_retry_failed(mock_requests):
    downloader = Downloader()

    mock_requests.side_effect = [
        requests.exceptions.Timeout(),
        requests.exceptions.Timeout()
    ]

    got_ex = False
    try:
        downloader.fetch_url(FAKE_COOKIE, FAKE_URL, retries=2)

    except requests.exceptions.Timeout:
        got_ex = True

    mock_requests.assert_has_calls([
        call(url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY),
        call(url=ANY, headers=ANY, allow_redirects=ANY, timeout=ANY)
    ])
    assert got_ex
