import datetime
import sys

import combine
import discord
import fetch

if __name__ == '__main__':
    if len(sys.argv) > 1:
        dt = datetime.date.fromisoformat(sys.argv[1])
    else:
        dt = None
    daily = fetch.download_dailynews(dt)
    post = fetch.download_nypost_direct(dt)
    combined = combine.combine(daily, post, f'./generated_images/{datetime.date.today().isoformat()}-combined.jpg')
    status = discord.post(combined)
    print(status.text)
