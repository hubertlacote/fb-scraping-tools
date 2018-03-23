from core.downloader import Downloader
from core.facebook_soup_parser import FacebookSoupParser

from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def create_mock_downloader():
    with patch(
        "core.downloader.Downloader", autospec=True) \
            as mock_downloader_class:

        yield mock_downloader_class.return_value


@contextmanager
def create_mock_facebook_parser():
    with patch(
        "core.facebook_soup_parser.FacebookSoupParser", autospec=True) \
            as mock_fb_parser_class:

        yield mock_fb_parser_class.return_value
