import argparse
import datetime

import yaml

import combine
import discord
import fetch


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('date', nargs='?', default=None)
    parser.add_argument('--papers', nargs='+', default=None)
    parser.add_argument('--config', default=None)
    args = parser.parse_args()

    dt = datetime.date.fromisoformat(args.date) if args.date else datetime.date.today()

    with open('papers.yaml') as f:
        config = yaml.safe_load(f)

    if args.papers:
        paper_keys = args.papers
        run_label = '-'.join(args.papers)
    elif args.config:
        paper_keys = config['configs'][args.config]
        run_label = args.config
    else:
        paper_keys = config['default']
        run_label = 'combined'

    paths = []
    trim_flags = []
    for key in paper_keys:
        paper_cfg = config['papers'][key]
        path = fetch.fetch_paper(paper_cfg, key, dt)
        paths.append(path)
        trim_flags.append(paper_cfg.get('trim_whitespace', False))

    combined = combine.combine(paths, f'./generated_images/{dt.isoformat()}-{run_label}.jpg', trim_flags)
    status = discord.post(combined, dt)
    print(status.text)
