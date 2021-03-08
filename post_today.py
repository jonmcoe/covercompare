import datetime

import combine
import fetch
import tweet

if __name__ == '__main__':
    daily = fetch.download_dailynews()
    post = fetch.download_nypost()
    combined = combine.combine(daily, post, f'./generated_images/{datetime.date.today().isoformat()}-combined.jpg')
    status = tweet.tweet_single_image(combined)
    print(status.text)
