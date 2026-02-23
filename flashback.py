import argparse
import datetime

import yaml

import discord

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('date')
    parser.add_argument('--papers', nargs='+', default=None)
    parser.add_argument('--config', default=None)
    args = parser.parse_args()

    dt = datetime.date.fromisoformat(args.date)

    if args.papers:
        run_label = '-'.join(args.papers)
    elif args.config:
        with open('papers.yaml') as f:
            config = yaml.safe_load(f)
        run_label = args.config
    else:
        run_label = 'combined'

    path = f'./generated_images/{dt.isoformat()}-{run_label}.jpg'
    status = discord.post(path, dt, extra_text="FLASHBACK: ")
    print(status.text)
