"""deliver.py — post combined covers to all active subscriptions not yet delivered today.

Safe to run multiple times per day — skips subscriptions already successfully
delivered today. Run hourly during the morning delivery window so transient
failures (paper not yet available) are retried automatically.

On the final run of the day, pass --tolerate-miss: any papers that still fail
are omitted from the combined image and an apology note is prepended to the
Discord message. Earlier runs fail fast so the next hourly attempt can retry.

Crontab (final run at 16:00 UTC = 11 AM ET gets --tolerate-miss):
    0 12-15 * * * /path/to/env/bin/python /path/to/deliver.py >> /path/to/deliver.log 2>&1
    0 16    * * * /path/to/env/bin/python /path/to/deliver.py --tolerate-miss >> /path/to/deliver.log 2>&1
"""

import argparse
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


def _fetch_papers(sub_id, paper_keys, cfg, d):
    """Fetch all papers, returning (paths, trim_flags, failed_keys).

    Never raises — per-paper failures are collected in failed_keys so the
    caller can decide whether to abort or send a partial delivery.
    """
    paths = []
    trim_flags = []
    failed = []
    for key in paper_keys:
        try:
            paper_cfg = cfg['papers'][key]
            cached = _cached_paper_path(key, d)
            if cached:
                path = cached
            else:
                print(f'[sub {sub_id}/{key}] cache miss, fetching...')
                path = fetch.fetch_paper(paper_cfg, key, d)
            paths.append(path)
            trim_flags.append(paper_cfg.get('trim_whitespace', False))
        except Exception as e:
            print(f'[sub {sub_id}/{key}] fetch failed: {e}', file=sys.stderr)
            failed.append(key)
    return paths, trim_flags, failed


def _already_delivered(sub, today):
    """Return True if this subscription was successfully delivered today."""
    last = sub.get('last_posted_at')
    if not last:
        return False
    return last.startswith(today.isoformat())


def deliver_subscription(sub, cfg, today, tolerate_miss=False):
    sub_id = sub['id']
    papers = json.loads(sub['papers'])

    print(f'[sub {sub_id}] delivering {papers}')

    combined_path = os.path.join(GENERATED_DIR, f'{today.isoformat()}-sub{sub_id}.jpg')
    os.makedirs(GENERATED_DIR, exist_ok=True)

    paths, trim_flags, failed = _fetch_papers(sub_id, papers, cfg, today)

    if failed and not tolerate_miss:
        error_msg = f"fetch failed for: {', '.join(failed)}"
        db.record_error(sub_id, error_msg)
        print(f'[sub {sub_id}] FAILED (fetch): {error_msg}', file=sys.stderr)
        return

    if not paths:
        error_msg = f"all papers failed to fetch: {', '.join(failed)}"
        db.record_error(sub_id, error_msg)
        print(f'[sub {sub_id}] FAILED (fetch): {error_msg}', file=sys.stderr)
        return

    extra_text = ""
    if failed:
        names = [cfg['papers'][k]['name'] if k in cfg['papers'] else k for k in failed]
        extra_text = f"⚠️ Sorry! Couldn't fetch: {', '.join(names)}\n\n"
        print(f'[sub {sub_id}] partial delivery, missing: {failed}')

    try:
        combine.combine(paths, combined_path, trim_flags)
        resp = discord.post(combined_path, today, extra_text=extra_text, webhook_url=sub['webhook_url'], username=sub['label'] or None)
        if not (200 <= resp.status_code < 300):
            raise RuntimeError(f'Discord returned HTTP {resp.status_code}: {resp.text[:200]}')
        db.record_success(sub_id, today)
        print(f'[sub {sub_id}] OK (HTTP {resp.status_code})')
    except Exception as e:
        error_msg = str(e)
        db.record_error(sub_id, error_msg)
        print(f'[sub {sub_id}] FAILED (post): {error_msg}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tolerate-miss', action='store_true',
                        help='Send partial delivery if some papers fail (use on final daily run)')
    args = parser.parse_args()

    today = datetime.date.today()
    print(f'deliver.py starting — {today.isoformat()} (tolerate_miss={args.tolerate_miss})')

    db.init()
    cfg = _load_yaml()
    subs = db.get_active_subscriptions()
    print(f'{len(subs)} active subscription(s)')

    pending = [s for s in subs if not _already_delivered(s, today)]
    print(f'{len(pending)} pending, {len(subs) - len(pending)} already delivered today')

    for sub in pending:
        deliver_subscription(sub, cfg, today, tolerate_miss=args.tolerate_miss)

    print('deliver.py done')


if __name__ == '__main__':
    main()
