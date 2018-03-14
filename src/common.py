import json
import logging
import os
from collections import namedtuple

CONFIG_FILENAME = "config/config.json"

CONFIG_KEYS = ['cookie_xs', 'user_id', 'client_id']
Config = namedtuple('Config', CONFIG_KEYS)

def prettify(decoded_json):
    return json.dumps(decoded_json, sort_keys=True, indent=4)

def parse_config(config_json):
    """
    >>> parse_config({ "cookie_xs" : "xs_val", "user_id": "uid_val", \
            "client_id": "client_val" })
    Config(cookie_xs='xs_val', user_id='uid_val', client_id='client_val')
    >>> parse_config({ "cookie_xs" : "", "user_id": "uid_val", \
            "client_id": "client_val" })
    Traceback (most recent call last):
    ...
    RuntimeError: Configuration file does not contain 'cookie_xs'
    >>> parse_config({ "cookie_xs" : "xs_val", "client_id": "client_val" })
    Traceback (most recent call last):
    ...
    RuntimeError: Configuration file does not contain 'user_id'
    """
    for key in CONFIG_KEYS:
        if key not in config_json or not config_json[key]:
            raise RuntimeError("Configuration file does not contain '{0}'".
                format(key))

    return Config(
        *[config_json[key] for key in CONFIG_KEYS])

def get_filepath(filename):
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        filename)

def load_config():
    config_filepath = get_filepath(CONFIG_FILENAME)
    if not os.path.exists(config_filepath):
        raise RuntimeError("Configuration file '{0}' does not exist".
            format(config_filepath))

    with open(config_filepath, "r") as f:
        config_json = json.load(f)

    return parse_config(config_json)

def build_cookie(config):
    return "c_user={0}; xs={1}; noscript=1;".format(
        config.user_id,
        config.cookie_xs
    )

def configure_logging(logging_level):
    logging.basicConfig(format='%(name)s: %(levelname)s: %(message)s',
        level=logging_level)