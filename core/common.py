import json
import logging
import os
import requests_cache
from collections import namedtuple
from collections import OrderedDict

CONFIG_FILENAME = "config/config.json"

CONFIG_KEYS = ['caching_secs', 'cookie_xs', 'cookie_c_user', 'logging_level']
Config = namedtuple('Config', CONFIG_KEYS)


def prettify(decoded_json, indent=4):
    return json.dumps(decoded_json, indent=indent)


def parse_config(config_json):
    """
    >>> parse_config({ "caching_secs": -1, "cookie_xs" : "xs_val",\
    "cookie_c_user": "uid_val", "logging_level": "INFO" })
    Config(caching_secs=-1, cookie_xs='xs_val', cookie_c_user='uid_val', \
logging_level=20)

    >>> parse_config({ "caching_secs": -1, "cookie_xs" : "",\
    "cookie_c_user": "uid_val", "logging_level": "INFO" })
    Traceback (most recent call last):
    ...
    RuntimeError: Configuration file does not contain 'cookie_xs'

    >>> parse_config({ "caching_secs": -1, "cookie_xs" : "xs_val",\
    "logging_level": "INFO" })
    Traceback (most recent call last):
    ...
    RuntimeError: Configuration file does not contain 'cookie_c_user'

    >>> parse_config({ "caching_secs": -1, "cookie_xs" : "xs_val",\
    "cookie_c_user": "uid_val", "logging_level": "HORROR" })
    Traceback (most recent call last):
    ...
    RuntimeError: Configuration file contains an invalid 'logging_level'

    >>> parse_config({ "caching_secs": "-10000", "cookie_xs" : "xs_val",\
    "cookie_c_user": "uid_val", "logging_level": "INFO" })
    Traceback (most recent call last):
    ...
    RuntimeError: Configuration file contains an invalid 'caching_secs' - \
allowed: -1: disabled - 0: cache forever - >0: cache for x seconds
    """
    for key in CONFIG_KEYS:
        if key not in config_json or config_json[key] == "":
            raise RuntimeError(
                "Configuration file does not contain '{0}'".format(key))

    try:
        config_json["logging_level"] = getattr(
            logging, config_json["logging_level"])
    except Exception:
        raise RuntimeError(
            "Configuration file contains an invalid 'logging_level'")

    is_int = True
    try:
        config_json["caching_secs"] = int(config_json["caching_secs"])
    except Exception:
        is_int = False
    finally:
        if not is_int or config_json["caching_secs"] < -1:
            raise RuntimeError(
                "Configuration file contains an invalid 'caching_secs' - " +
                "allowed: " +
                "-1: disabled - 0: cache forever - >0: cache for x seconds")

    return Config(
        *[config_json[key] for key in CONFIG_KEYS])


def get_filepath(filename):
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "..",
        filename)


def load_json_from_fd(fd):
    try:
        return json.load(fd, object_pairs_hook=OrderedDict)

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


def configure(caching_secs_override=None):

    logging.basicConfig(
        format='%(asctime)s %(filename)s:%(lineno)d:'
        ' %(levelname)s: %(message)s', level=logging.ERROR)

    config = load_config()

    logging.getLogger().setLevel(config.logging_level)

    caching_secs = config.caching_secs
    if caching_secs_override and \
       caching_secs_override != caching_secs:
        logging.info("Overriding configuration - Caching disabled.")
        caching_secs = caching_secs_override

    if caching_secs == 0:
        logging.info("Caching enabled: cache does not expîre")
        requests_cache.install_cache(expire_after=None)
    elif caching_secs > 0:
        logging.info("Caching enabled: cache expires after {0}s".format(
            caching_secs))
        requests_cache.install_cache(expire_after=caching_secs)

    return config


def build_cookie(config):
    return "c_user={0}; xs={1}; noscript=1;".format(
        config.cookie_c_user,
        config.cookie_xs
    )
