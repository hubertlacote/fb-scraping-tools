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

def load_json_from_fd(fd):
    try:
        return json.load(fd)

    except Exception as e:
        logging.error("Error parsing JSON, got exception: '{0}'".format(e))

    return {}

def load_json_from_file(filepath):
    if not os.path.exists(filepath):
        filepath_org = filepath
        filepath = get_filepath(filepath)

        if not os.path.exists(filepath):
            logging.error("Couldn't find file '{0}' or '{1}'".format(
                filepath_org, filepath))
            return {}

    logging.info("Loading JSON file '{0}'".format(filepath))
    with open(filepath, "r") as f:
        return load_json_from_fd(f)

def load_config():
    return parse_config(
        load_json_from_file(CONFIG_FILENAME))

def build_cookie(config):
    return "c_user={0}; xs={1}; noscript=1;".format(
        config.user_id,
        config.cookie_xs
    )

def configure_logging(logging_level):
    logging.basicConfig(format='%(asctime)s %(filename)s:%(lineno)d:'
        ' %(levelname)s: %(message)s', level=logging_level)