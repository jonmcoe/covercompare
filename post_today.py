import argparse
import datetime

import yaml

import combine
import discord
import fetch

FETCHERS = {
    'nypost': fetch.download_nypost_direct,
    'newsday': fetch.download_newsday,
    'dailynews': fetch.download_dailynews,
    'nytimes': fetch.download_nytimes,
    'washpost': fetch.download_washpost,
    'boston-globe': fetch.download_boston_globe,
    'miami-herald': fetch.download_miami_herald,
}

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
        path = FETCHERS[paper_cfg['fetcher']](dt)
        paths.append(path)
        trim_flags.append(paper_cfg.get('trim_whitespace', False))

    combined = combine.combine(paths, f'./generated_images/{dt.isoformat()}-{run_label}.jpg', trim_flags)
    status = discord.post(combined, dt)
    print(status.text)
