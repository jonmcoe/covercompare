import tweepy

import credentials


def tweet_single_image(path):
    auth = tweepy.OAuthHandler(credentials.API_KEY, credentials.API_SECRET)
    auth.set_access_token(credentials.ACCESS_TOKEN, credentials.ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    api.update_with_media(path)