#!  #!/usr/bin/env python3

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

    def fetch_url(self, cookie, url, timeout_secs = 15):
        logging.info("Fetching {0}".format(url))
        headers = self.HEADERS
        headers["cookie"] = cookie

        response = requests.get(url, headers = headers,
            allow_redirects = True, timeout = timeout_secs)

        if response.status_code != 200 or not response.text:
            raise RuntimeError("Error while downloading page '{0}', "
                "status code: '{1}' - headers: '{2}'".format(
                    url, response.status_code, response.headers))

        return response
