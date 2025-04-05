import datetime
import sys

import discord

if __name__ == '__main__':
    if len(sys.argv) > 1:
        dt = datetime.date.fromisoformat(sys.argv[1])
    else:
        print("need date positional arg")
        exit()
    expected_file = f"./generated_images/{dt.isoformat()}-combined.jpg"
    status = discord.post(expected_file, dt, extra_text="FLASHBACK: ")
    print(status.text)
