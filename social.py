import helpers
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import base64


def getTweets():
    """ Get list of tweets, with tweet ID and content, from configured Twitter account URL.

    This function relies on BeautifulSoup to extract the tweet IDs and content of all tweets on the specified page.

    The data is returned as a list of dictionaries that can be used by other functions.
    """

    all_tweets = []
    url = helpers._config("tweets.source_account_url")

    if not url:
        helpers._error(
            "getTweets() => The source Twitter account URL ({}) was incorrect. Could not retrieve tweets.".format(url)
        )
        return False

    headers = {}
    headers["accept-language"] = "en-US,en;q=0.9"
    headers["dnt"] = "1"
    headers["user-agent"] = helpers._config("gen.APP_NAME")

    data = requests.get(url)
    html = BeautifulSoup(data.text, "html.parser")
    timeline = html.select("#timeline li.stream-item")

    if timeline is None:
        helpers._error(
            "getTweets() => Could not retrieve tweets from the page. Please make sure the source Twitter account URL ({}) is correct.".format(url)
        )
        return False

    helpers._info("getTweets() => Fetched tweets for {}.".format(url))

    for tweet in timeline:

        try:

            tweet_id = tweet["data-item-id"]
            tweet_text = tweet.select("p.tweet-text")[0].get_text().encode("utf-8")
            tweet_time = int(tweet.select("span._timestamp")[0].attrs["data-time-ms"])

            all_tweets.append({"id": tweet_id, "text": tweet_text, "time": tweet_time})

        except Exception as e:

            helpers._error("getTweets() => No tweet text found.")
            helpers._error(e)
            continue

    return all_tweets if len(all_tweets) > 0 else None


def tootTheTweet(tweet):
    """ Receieve a dictionary containing Tweet ID and text... and TOOT!

    This function relies on the requests library to post the content to your Mastodon account (human or bot).

    A boolean success status is returned.

    Arguments:
        tweet {dictionary} -- Dictionary containing the "id" and "text" of a single tweet.
    """

    host_instance = helpers._config("toots.host_instance")
    token = helpers._config("toots.app_secure_token")
    timestamp_file = helpers._config("toots.cache_path") + "last_tweet_tooted"

    if not host_instance:
        helpers._error(
            "tootTheTweet() => Your host Mastodon instance URL ({}) was incorrect.".format(host_instance)
        )
        return False

    if not token:
        helpers._error("tootTheTweet() => Your Mastodon access token was incorrect.")
        return False

    last_timestamp = helpers._read_file(timestamp_file)
    if not last_timestamp:

        helpers._write_file(timestamp_file, str(tweet["time"]))

        return False

    last_timestamp = int(last_timestamp)

    headers = {}
    headers["Authorization"] = "Bearer {}".format(token)
    headers["Idempotency-Key"] = tweet["id"]

    data = {}
    data["status"] = tweet["text"]
    data["visibility"] = "public"

    if tweet["time"] <= last_timestamp:

        print("tootTheTweet() => No new tweets. Moving on.")

        return None

    last_timestamp = helpers._write_file(timestamp_file, str(tweet["time"]))

    helpers._info('tootTheTweet() => New tweet {} => "{}".'.format(tweet["id"], tweet["text"]))

    response = requests.post(
        url="{}/api/v1/statuses".format(host_instance), data=data, headers=headers
    )

    if response.status_code == 200:
        helpers._info("tootTheTweet() => OK. Posted tweet {} to Mastodon.".format(tweet['id']))
        helpers._info("tootTheTweet() => Response: {}".format(response.text))
        return True

    else:
        helpers._info(
            "tootTheTweet() => FAIL. Could not post tweet {} to Mastodon.".format(tweet['id'])
        )
        helpers._info("tootTheTweet() => Response: {}".format(response.text))
        return False
