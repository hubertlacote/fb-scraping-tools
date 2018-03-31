from collections import OrderedDict
from datetime import datetime
import logging


def append_times(new_times, times):
    """ Add times from new_times that are not in times.

    >>> append_times(OrderedDict([('1', [150000])]), {})
    True
    >>> append_times(OrderedDict([('1', [150000])]), {'1': [150000]})
    False
    >>> append_times(OrderedDict([('2', [150000])]), {'1': [150000]})
    True
    >>> append_times(OrderedDict([('1', [150099])]), {'1': [150000]})
    True
    """
    changes = False
    for user in new_times.keys():

        new_lats = new_times[user]
        if not new_lats:
            logging.warn("No times found for user '{O}'".format(user))
            continue

        if user not in times:
            times[user] = []

        for new_lat in new_lats:
            if not times[user]:
                logging.info("User {0}: {1}".format(user, new_lat))
                times[user].append(new_lat)
                changes = True
            elif new_lat > times[user][-1]:
                logging.info("User {0}: {1} > {2}".format(
                    user, new_lat, times[user][-1]))
                times[user].append(new_lat)
                changes = True

    return changes


def process_data(times, user_infos, set_optional_fields=False):
    """ Parse names using user_infos and times.

    >>> process_data(OrderedDict([('mark.123', [1500])]), \
{'mark.123': {"id": 36, "Name": "John"}})
    [OrderedDict([('username', 'mark.123'), ('id', 36), ('name', 'John'), \
('times', ['1970-01-01 01:25:00'])])]

    >>> process_data(OrderedDict([('mark.123', [1500])]), \
{'mark.123': {"id": 36, "Year of birth": 1984}})
    [OrderedDict([('username', 'mark.123'), ('id', 36), \
('year_of_birth', 1984), ('times', ['1970-01-01 01:25:00'])])]

    >>> process_data(OrderedDict([('1', None)]), {'1': {"Name": "John"}})
    []

    >>> process_data(OrderedDict([('1', [])]), {'1': {"Name": "John"}})
    []

    >>> process_data(OrderedDict([('1', [1500])]), {})
    [OrderedDict([('id', 1), ('times', ['1970-01-01 01:25:00'])])]

    >>> process_data(OrderedDict([('1', [1500])]), {'1': {}})
    [OrderedDict([('id', 1), ('times', ['1970-01-01 01:25:00'])])]

    >>> process_data(OrderedDict([('1', [1500])]), {'1': {"Name": ""}})
    [OrderedDict([('id', 1), ('name', ''), \
('times', ['1970-01-01 01:25:00'])])]
    """

    parsed = []
    for user_id in times:

        parsed_user = OrderedDict()

        current_times = times[user_id]
        if not current_times:
            logging.warn(
                "Skipping user '{0}'".format(user_id))
            continue

        if user_id in user_infos and "id" in user_infos[user_id]:
            parsed_user["username"] = user_id
            parsed_user["id"] = user_infos[user_id]["id"]
        else:
            # Without user_infos, we need an id, not an username
            try:
                parsed_user["id"] = int(user_id)
            except Exception:
                logging.warn(
                    "Skipping user '{0}' with invalid id".format(user_id))
                continue

        tags = [
            'Name', 'Birthday', 'Education', 'Gender',
            'Relationship', 'Work', 'Year of birth']
        for tag in tags:
            escaped_tag = tag.replace(" ", "_").lower()
            if user_id in user_infos and tag in user_infos[user_id]:
                parsed_user[escaped_tag] = user_infos[user_id][tag]
            elif set_optional_fields:
                parsed_user[escaped_tag] = ""

        parsed_times = [
            str(datetime.fromtimestamp(int(time)))
            for time in current_times if int(time) != -1]

        parsed_user["times"] = parsed_times
        parsed.append(parsed_user)

    return parsed
