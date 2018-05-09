# fb-scraping-tools

**A unit tested set of tools written in Python to scrape / collect data visible by a logged in user from Facebook.**

## Why ([![start with why](https://img.shields.io/badge/start%20with-why%3F-brightgreen.svg?style=flat)](http://www.ted.com/talks/simon_sinek_how_great_leaders_inspire_action))

To learn how to scrape non-interactive websites (with javascript disabled) using [requests](http://docs.python-requests.org/) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup).

To extract data not available easily via Facebook, e.g.:

- Find the most popular posts of any page, can be done with [fetch-timeline-posts](fetch-timeline-posts),
- Find the birthday dates of all your friends who make it available via Facebook, can be done with [tools/fetch-friend-list-with-details](tools/fetch-friend-list-with-details) and for the one that hid their birthday dates after a few years of using Facebook, it can still be deduced by looking for messages posted on their timeline using [fetch-timeline-posts](fetch-timeline-posts).

To check the potential privacy implications that modern social media have, e.g.:

- Find the list of all the public posts that a user ever liked by exploring all the posts of every single page he likes, can be done with [tools/fetch-all-liked-posts-from-liked-pages](tools/fetch-all-liked-posts-from-liked-pages) but it can take time,
- Compile a list of all users who like posts from any page / group / user timeline (e.g. find all users who liked posts from [Anonymous Facebook page](https://www.facebook.com/AnonSec/)) however they restricted their profiles, can be done with [tools/fetch-timeline-likes](tools/fetch-timeline-likes),
- Deduce a part of the friends of anyone even when they hide their friend list, can be done with [tools/fetch-timeline-likes](tools/fetch-timeline-likes) and [tools/fetch-tagged-users-in-timeline-posts](tools/fetch-tagged-users-in-timeline-posts),
- Find all users with who you have friends in common that liked a post from a page / group / user (e.g. who from your network like the same music band as you), can be done with [tools/fetch-timeline-likes](tools/fetch-timeline-likes),

To check the potential psychological implications that modern social media have, e.g.:

- "According to one Facebook executive, millennials look at their phones on average more than 150 times a day" (Smartphones and anxiety, The Economist, 26/11/2017), can be checked for your friends with [tools/create-visualisable-data-from-last-active-times](tools/create-visualisable-data-from-last-active-times),
- Find which of your friends is posting the most and the evolution over time, can be done with [tools/create-visualisable-data-from-timeline-posts-of-all-friends](tools/create-visualisable-data-from-timeline-posts-of-all-friends).

## Disclaimer

This project is a learning experiment and shall not be used to collect data from Facebook, see [Facebook Automated Data Collection Terms](https://www.facebook.com/apps/site_scraping_tos_terms.php).

Instead, Facebook Graph API can be used to collect data, even though it sometimes returns less information than is available through normal browsing (e.g. friend list), see [Facebook's Graph API v2.0 kills data mining](https://github.com/ptwobrussell/Mining-the-Social-Web-2nd-Edition/issues/205) and [Facebook Is Shutting Down Its API For Giving Your Friends’ Data To Apps](https://techcrunch.com/2015/04/28/facebook-api-shut-down/).

Therefore, I urge you to use this project for educational purpose only, and not to use it to access Facebook.

### Risks of having your profile restricted for 1 week

In case your are still not convinced, Facebook might also restrict your profile from seeing the profiles of anyone other than friends and friends of friends for a week if you use these tools. This is what you might see on [a Facebook notification](https://www.facebook.com/support/?notif_t=feature_limits):

> **You're restricted from seeing the profiles of anyone other than friends and friends of friends.**
> This restriction is a precaution we use to make sure only people are seeing profile posts, photos and activity.

> **Why you're seeing this**
> The restriction is typically used only for computers posing as real people, so you may have been restricted by mistake. If so, we're very sorry for the inconvenience and will work to lift the restriction as soon as possible.

> **The restriction has been lifted** (1 week later)
> You were temporarily restricted from seeing the profiles of anyone other than friends and friends of friends. Recent activity led us to believe that your profile was copying information from other profiles, so the restriction was put in place as a precaution. You may have been restricted by mistake. If so, we're very sorry for the inconvenience this caused.

## License

MIT (see [LICENSE](LICENSE))

## Installation

```bash
sudo apt install python3-pip
sudo apt install python3-venv
sudo apt install jq # required only by tools/ to post-process JSON
python3 -m venv fb-scraping-tools-env
source fb-scraping-tools-env/bin/activate
pip install -r requirements.txt
```

## Configuration

Change the [language of Facebook user interface](https://www.facebook.com/settings?tab=language) to English (UK),

Fill the file [config/config.json](config/config.json):

- specify your Facebook cookies: xs (**cookie_xs**) and c_user (**cookie_c_user**):
  - On Chrome, you can find them there: [chrome://settings/siteData](chrome://settings/siteData), or by pressing F12 and going to Application (tab) - Cookies (sidebar).

- optionally, change the logging level (**logging_level**) using one of these: "DEBUG", "INFO", "WARNING", "ERROR".

- optionally, enable caching (**caching_secs**) to avoid hitting Facebook repeatedly: 0 (cache does not expire), or x (cache expires after x seconds) or -1 (cache disabled).

## Usage

This repository contains a set of basic tools generating JSON. They can be combined using [jq](https://stedolan.github.io/jq/) to deal with more complex use cases, see example shell scripts in [tools/](tools/).

### Fetching friend list and details about users

- [fetch-friend-list](fetch-friend-list) returns your Facebook friend list (Facebook username + name) extracted from your Friends page:

```bash
./fetch-friend-list > friend-list.json
# {
#    "username1": {
#        "name": "Friend 1"
#    },
#    "username2": {
#        "name": "Friend 2"
#    },
#    "username3": {
#        "name": "Friend 3"
#    },
#    ...
# }
```

- [fetch-user-infos](fetch-user-infos) extracts all these fields from About Page if they are present:
  - 'AIM', 'Address', 'BBM', 'Birth Name', 'Birthday', 'Education', 'Facebook', 'Foursquare', 'Gadu-Gadu', 'Gender', 'ICQ', 'Instagram', 'Interested in', 'Languages', 'LinkedIn', 'Maiden Name', 'Mobile', 'Nickname', 'Political Views', 'Religious views', 'Relationship', 'Skype', 'Snapchat', 'Twitter', 'VK', 'Websites', 'Windows Live Messenger', 'Work', 'Year of birth'.
  - Birthday is treated specially and depending on the information available, only day and month of birth or year of birth are extracted,
  - Only the first work and education listed are extracted,
  - Also fetches friend list if -f is passed.
  - Also fetches pages liked if -l is passed.
  - Also fetches mutual friends if -m is passed.

```bash
./fetch-user-infos -u user -f -l -m > user-infos.json
# {
#     "user": {
#         "name": "User 1",
#         "id": 111111111,
#         "birthday": "1 January 1984",
#         "gender": "Male",
#         "languages": "English language",
#         "day_and_month_of_birth": "1 January",
#         "year_of_birth": 1984,
#         "work": "Workplace",
#         "education": "Some University",
#         "relationship": "Married",
#         "friends": {
#             "username1": {
#                 "name": "Friend 1"
#             },
#             "username2": {
#                 "name": "Friend 2"
#             },
#             ...
#         },
#         "friend_count": 200,
#         "liked_pages": {
#             "Music": {
#                 "bandLink/": "Band name",
#                 ...
#             },
#             "Television": {
#                 "filmLink/": "Film name",
#                 ...
#             },
#             ...
#         },
#         "liked_page_count": 200,
#         "mutual_friends": {
#             "username1": {
#                 "name": "Mutual friend 1"
#             },
#             "username2": {
#                 "name": "Mutual friend 2"
#             },
#             ...
#         },
#         "mutual_friend_count": 10
#     }
# }

echo '["user", 222222222]' | ./fetch-user-infos -i > user-infos.json
# {
#     "user": {
#         "name": "User 1",
#         "id": 111111111,
#         ...
#     },
#     "222222222": {
#         "name": "User 2",
#         "id": 222222222,
#         ...
#     }
# }
```

- [tools/fetch-friend-list-with-details](tools/fetch-friend-list-with-details), is a shell script combining [fetch-friend-list](fetch-friend-list) and [fetch-user-infos](fetch-user-infos) returning your Facebook friend list with details extracted from their About pages:

```bash
tools/fetch-friend-list-with-details > friend-list-with-details.json
#  {
#    "111111111": {
#        "name": "Friend 1",
#        "id": 111111111,
#        "address": "Address 1",
#        "facebook": " Facebook username",
#        "gender": "Male",
#        "day_and_month_of_birth": "1 January",
#        ...
#        "friends": {
#            ...
#        },
#        "friend_count": 200,
#        "liked_pages": {
#            ...
#        },
#        "liked_page_count": 200,
#        "mutual_friends": {
#            ...
#        },
#        "mutual_friend_count": 10
#    },
#    "222222222": {
#        "name": "Friend 2",
#        "id": 222222222,
#        "day_and_month_of_birth": "2 January",
#        "work": "Workplace",
#        "education": "University name",
#        "relationship": "In a relationship",
#        ...
#        "friends": {
#            ...
#        },
#        "friend_count": 200,
#        "liked_pages": {
#            ...
#        },
#        "liked_page_count": 200,
#        "mutual_friends": {
#            ...
#        },
#        "mutual_friend_count": 10
#    },
#  }
```

### Fetching timeline posts of users, groups or pages

- [fetch-timeline-posts](fetch-timeline-posts) returns all the posts from the timeline of a specified user id, username, group name, page name, or a list of usernames / user ids / group names / page names:

```bash
./fetch-timeline-posts -u username > posts.json
#  {
#    "username": {
#        "posts": {
#            "100000000000001": {
#                "post_id": 100000000000001,
#                "content": "User added a new photo",
#                "participants": [
#                    "username",
#                    "username2",
#                    "1000000000001",
#                    "1000000000002"
#                ],
#                "date": "2018-01-01 12:00:00",
#                "date_org": "1 January at 12:00",
#                "like_count": 3100,
#                "comment_count": 100,
#                "story_link": "https://mbasic.facebook.com/photo.php?fbid=100000000000001&id=someOtherId&...",
#                "page": "username"
#            },
#            "100000000000002": {
#                "post_id": 100000000000002,
#                "content": "User is with some other user",
#                "participants": [
#                    "username"
#                ],
#                "date": "2018-01-02 12:00:00",
#                "date_org": "2 January at 12:00",
#                "like_count": 0,
#                "comment_count": 0,
#                "story_link": "https://mbasic.facebook.com/story.php?story_fbid=100000000000002&id=someOtherId&...",
#                "page": "username"
#            },
#            ...
#        }
#    }
# }
```

```bash
./fetch-timeline-posts -u TheEconomist > posts.json
```

```bash
./fetch-timeline-posts -u groups/123456 > posts.json
```

```bash
echo '["username1", 1111111, "TheEconomist", "groups/123456"]' | ./fetch-timeline-posts -i > posts.json
```

```bash
echo '{"username1": "somedetail", 1111111: "somedetail", "TheEconomist": "somedetail", "groups/123456": "somedetail"}' | ./fetch-timeline-posts -i > posts.json
```

- [tools/fetch-tagged-users-in-timeline-posts](tools/fetch-tagged-users-in-timeline-posts) is a shell script that returns the list of all usernames and ids that appear in posts from the timeline of a specified user id, username, group name, page name, or a list of usernames / user ids / group names / page names:

```bash
tools/fetch-tagged-users-in-timeline-posts -u "username" > users.json
# [
#   "100000000000001",
#   "100000000000002",
#   "100000000000003",
#   ...
#   "username1",
#   "username2",
#   ...
# ]
```

Note that it is possible to then use [fetch-user-infos](fetch-user-infos) and [jq](https://stedolan.github.io/jq/) to query details about every single username / id and then remove duplicates (ids and usernames might link to the same users), e.g.:

```bash
tools/fetch-tagged-users-in-timeline-posts -u "username" | fetch-user-infos -i | jq '[.[]] | unique_by(.id)' > detailed-users.json
[
  {
    "name": "Name 1",
    "id": 100000000000001,
    ...
  },
  ...
  {
    "name": "Name 2",
    "id": 100000000000009,
    ...
  },
  ...
]
```

- [tools/create-visualisable-data-from-timeline-posts](tools/create-visualisable-data-from-timeline-posts) is a shell script that generates JSON viewable with [fb-scraping-tools-viewer](https://github.com/hubertlacote/fb-scraping-tools-viewer) - it makes it possible to see when users are posting and which user is posting the most, it doesn't use like_count or comment_count.

```bash
tools/create-visualisable-data-from-timeline-posts -u "username" > times.json

# or

echo '["username1", "username2", "username3"]' | tools/create-visualisable-data-from-timeline-posts -i > times.json
```

- [tools/create-visualisable-data-from-timeline-posts-of-all-friends](tools/create-visualisable-data-from-timeline-posts-of-all-friends) does the same but takes as input your friend list:

```bash
tools/create-visualisable-data-from-timeline-posts-of-all-friends > times.json 2>log
```

### Fetching timeline likes of users, groups or pages

- [tools/fetch-timeline-likes](tools/fetch-timeline-likes) is a shell script that returns the list of users who liked posts from a timeline (of a specified user id, username, group name, page name, or a list of usernames / user ids / group names / page names):

```bash
tools/fetch-timeline-likes -u "username" > likes.json
# {
#    "liker1": {
#        "likes": [
#            {
#                "post_id": 111111111111111,
#                ...
#            },
#            {
#                "post_id": 111111111111112,
#                ...
#            },
#            ...
#        ]
#    },
#    ...
# }

echo '["username1", "username2"]' | tools/fetch-timeline-likes -i > likes.json
```

**Note that Facebook servers do not seem to support to return more than ~5000 likers for any post**, the tool fetches as many likers as Facebook allows.

- [tools/fetch-all-liked-posts-from-liked-pages](tools/fetch-all-liked-posts-from-liked-pages) is a shell script that returns the list of all public posts that a user ever liked by exploring all the posts of every single page he likes (time consuming since there might be 1000 posts to explore for every page liked):

```bash
tools/fetch-all-liked-posts-from-liked-pages -u "username" > likes.json
# [
#   {
#     "post_id": 111111111111111,
#     ...
#     "story_link": "https://mbasic.facebook.com/...,
#     "page": "PageName1/"
#   },
#   {
#     "post_id": 111111111111112,
#     ...
#     "story_link": "https://mbasic.facebook.com/...,
#     "page": "PageName2/"
#   },
#   ...
# ]
```

- [tools/create-visualisable-data-from-timeline-likes](tools/create-visualisable-data-from-timeline-likes) is a shell script that generates JSON viewable with [fb-scraping-tools-viewer](https://github.com/hubertlacote/fb-scraping-tools-viewer) - it makes it possible to see the evolution of likes with time, and to see the biggest likers.

```bash
tools/create-visualisable-data-from-timeline-likes -u "username" > likes.json
```

```bash
echo '["username1", "username2"]' | ./create-visualisable-data-from-timeline-likes -i > likes.json
```

### Fetching last active times of your Facebook friends

- [fetch-last-active-times](fetch-last-active-times) uses an un-documented Facebook API to fetch the last time your Facebook friends were active on Facebook, as described in these articles: [How you can use Facebook to track your friends’ sleeping habits](https://medium.com/@sqrendk/how-you-can-use-facebook-to-track-your-friends-sleeping-habits-505ace7fffb6), [Graphing when your Facebook friends are awake](https://defaultnamehere.tumblr.com/post/139351766005/graphing-when-your-facebook-friends-are-awake):

```bash
./fetch-last-active-times > last_active_times.json
# {
#    "111111111": {
#        "times": [
#            "2018-04-18 11:20:30"
#        ]
#    },
#    "222222222": {
#        "times": [
#            "2018-04-18 11:10:06"
#        ]
#    }
# }
```

- [poll-last-active-times](poll-last-active-times) simply fetches this same Facebook API repeatedly:

```bash
# Press Ctrl-C to interrupt polling
./poll-last-active-times -t 0 -d 300 > last_active_times.json
# {
#    "111111111": {
#        "times": [
#            "2018-04-18 11:20:30",
#            "2018-04-18 11:22:30"
#        ]
#    },
#    "222222222": {
#        "times": [
#            "2018-04-18 11:10:06"
#        ]
#    },
#    "333333333": {
#        "times": []
#    },
# }
```

- [tools/create-visualisable-data-from-last-active-times](tools/create-visualisable-data-from-last-active-times) is a shell script that generates JSON viewable with [fb-scraping-tools-viewer](https://github.com/hubertlacote/fb-scraping-tools-viewer) - it executes [poll-last-active-times](poll-last-active-times) and when it finishes (or when Ctrl-C is pressed), it fetches user details using [fetch-user-infos](fetch-user-infos) and denormalizes data so that there is one time per JSON line:

```bash
# Press Ctrl-C to interrupt polling
./tools/create-visualisable-data-from-last-active-times -t 0 -d 300 > times.json
# Same as below but with compact output
# [
#   {
#     "id": 111111111,
#     "time": "2018-04-18 11:20:30",
#     "name": "User 1",
#     "education": "University name",
#     ...
#   },
#   {
#     "id": 111111111,
#     "time": "2018-04-18 11:22:30",
#     "name": "User 1",
#     "education": "University name",
#     ...
#   },
#   {
#     "id": 222222222,
#     "time": "2018-04-18 11:10:06",
#     "name": "User 2",
#     "education": "University name",
#     ...
#   }
# ]
```

## Contributing

```bash
./run-tests
```
