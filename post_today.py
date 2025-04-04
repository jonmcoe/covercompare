import datetime
import sys

import combine
import fetch
import tweet

if __name__ == '__main__':
    if len(sys.argv) > 1:
        dt = datetime.date.fromisoformat(sys.argv[1])
    else:
        dt = None
    daily = fetch.download_dailynews(dt)
    post = fetch.download_nypost(dt)
    combined = combine.combine(daily, post, f'./generated_images/{datetime.date.today().isoformat()}-combined.jpg')
    status = tweet.tweet_single_image(combined)
    print(status.text)
