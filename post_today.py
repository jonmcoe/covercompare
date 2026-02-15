import datetime
import sys

import combine
import discord
import fetch

if __name__ == '__main__':
    if len(sys.argv) > 1:
        dt = datetime.date.fromisoformat(sys.argv[1])
    else:
        dt = datetime.date.today()
    newsday = fetch.download_newsday(dt)
    post = fetch.download_nypost_direct(dt)
    combined = combine.combine(newsday, post, f'./generated_images/{dt.isoformat()}-combined.jpg')
    status = discord.post(combined, dt)
    print(status.text)
