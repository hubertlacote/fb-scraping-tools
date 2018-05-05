#!  #!/usr/bin/env python3

from core import common
import logging
import requests


class Downloader:
    """Downloading URLs with headers set"""

    def __init__(self):
        self.HEADERS = {
            "accept": "*/*",
            # Removed br (Brotli) so that requests can decode content
            "accept-encoding": "gzip, deflate",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36",
        }

    def fetch_url(self, cookie, url, timeout_secs=15, retries=1):
        headers = self.HEADERS
        headers["cookie"] = cookie

        for attempt_no in range(1, retries + 1):
            logging.info("Fetching {0} - Attempt {1}".format(
                common.truncate_text(url, 200), attempt_no))

            try:
                response = requests.get(
                    url=url, headers=headers,
                    allow_redirects=True, timeout=timeout_secs)

                # Treat server errors as timeout so that retries are performed
                if response.status_code >= 500:
                    raise requests.exceptions.Timeout()

                if response.status_code != 200 or not response.text:
                    raise RuntimeError(
                        "Error while downloading page '{0}', "
                        "status code: '{1}' - headers: '{2}'".format(
                            common.truncate_text(url, 200),
                            response.status_code, response.headers))

                return response

            except requests.exceptions.Timeout:
                logging.warn("Request to '{0}' timed out".format(
                    common.truncate_text(url, 200)))
                if attempt_no == retries:
                    raise

        assert False, "Downloader.fetch_url - Should never reach this point"
        return None
