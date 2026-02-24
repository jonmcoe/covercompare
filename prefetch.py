"""prefetch.py — eagerly fetch all paper covers into downloads/ cache.

Run before deliver.py so webhook deliveries are instant cache hits.

Crontab (11:30 UTC = 6:30 AM ET):
    30 11 * * * /path/to/env/bin/python /path/to/prefetch.py >> /path/to/prefetch.log 2>&1
"""

import datetime
import glob
import os
import sys

import yaml

import fetch


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')


def _load_yaml():
    with open(os.path.join(BASE_DIR, 'papers.yaml')) as f:
        return yaml.safe_load(f)


def _cached_paper_path(papername, d):
    pattern = os.path.join(DOWNLOADS_DIR, f'{d.isoformat()}-{papername}.*')
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def main():
    today = datetime.date.today()
    print(f'prefetch.py starting — {today.isoformat()}')

    cfg = _load_yaml()
    papers = cfg['papers']
    ok = 0
    skipped = 0
    failed = 0

    for key, paper_cfg in papers.items():
        cached = _cached_paper_path(key, today)
        if cached:
            print(f'[{key}] cached ({cached})')
            skipped += 1
            continue
        try:
            path = fetch.fetch_paper(paper_cfg, key, today)
            print(f'[{key}] fetched -> {path}')
            ok += 1
        except Exception as e:
            print(f'[{key}] FAILED: {e}', file=sys.stderr)
            failed += 1

    print(f'prefetch.py done — {ok} fetched, {skipped} skipped, {failed} failed')


if __name__ == '__main__':
    main()
