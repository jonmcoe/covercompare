"""deliver.py — daily cron script to post combined covers to all active subscriptions.

Runs after prefetch.py so downloads/ is already warm.

Crontab:
    0 7 * * * /path/to/env/bin/python /path/to/deliver.py >> /var/log/deliver.log 2>&1
"""

import datetime
import glob
import json
import os
import sys

import yaml

import combine
import db
import discord
import fetch


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
GENERATED_DIR = os.path.join(BASE_DIR, 'generated_images')


def _load_yaml():
    with open(os.path.join(BASE_DIR, 'papers.yaml')) as f:
        return yaml.safe_load(f)


def _cached_paper_path(papername, d):
    pattern = os.path.join(DOWNLOADS_DIR, f'{d.isoformat()}-{papername}.*')
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def _fetch_papers(paper_keys, cfg, d):
    paths = []
    trim_flags = []
    for key in paper_keys:
        paper_cfg = cfg['papers'][key]
        cached = _cached_paper_path(key, d)
        if cached:
            path = cached
        else:
            print(f'  [{key}] cache miss, fetching...')
            path = fetch.fetch_paper(paper_cfg, key, d)
        paths.append(path)
        trim_flags.append(paper_cfg.get('trim_whitespace', False))
    return paths, trim_flags


def deliver_subscription(sub, cfg, today):
    sub_id = sub['id']
    papers = json.loads(sub['papers'])
    label = sub['label'] or '-'.join(sorted(papers))

    print(f'[sub {sub_id}] delivering {papers} to webhook ...')

    combined_path = os.path.join(GENERATED_DIR, f'{today.isoformat()}-sub{sub_id}.jpg')
    os.makedirs(GENERATED_DIR, exist_ok=True)

    try:
        paths, trim_flags = _fetch_papers(papers, cfg, today)
        combine.combine(paths, combined_path, trim_flags)
        resp = discord.post(combined_path, today, webhook_url=sub['webhook_url'])
        if not (200 <= resp.status_code < 300):
            raise RuntimeError(f'Discord returned HTTP {resp.status_code}: {resp.text[:200]}')
        db.record_success(sub_id, today)
        print(f'[sub {sub_id}] OK (HTTP {resp.status_code})')
    except Exception as e:
        error_msg = str(e)
        db.record_error(sub_id, error_msg)
        print(f'[sub {sub_id}] FAILED: {error_msg}', file=sys.stderr)


def main():
    today = datetime.date.today()
    print(f'deliver.py starting — {today.isoformat()}')

    db.init()
    cfg = _load_yaml()
    subs = db.get_active_subscriptions()
    print(f'{len(subs)} active subscription(s)')

    for sub in subs:
        deliver_subscription(sub, cfg, today)

    print('deliver.py done')


if __name__ == '__main__':
    main()
