import datetime
import glob
import io
import os
import uuid

import yaml
from flask import Flask, jsonify, request, send_file, abort
from PIL import Image

import combine
import db
import discord
import email_delivery
import fetch

app = Flask(__name__, static_folder='static', static_url_path='')

# Trust one level of X-Forwarded-For (set by nginx); prevents IP spoofing
# for rate limiting. x_proto needed so url_for() generates https:// links.
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAPERS_YAML_PATH = os.path.join(os.path.dirname(__file__), 'papers.yaml')
_DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
_GENERATED_DIR = os.path.join(os.path.dirname(__file__), 'generated_images')

import re

DISCORD_DOMAINS = {'discord.com', 'discordapp.com'}
AUTO_DEACTIVATE_THRESHOLD = 7
_DISCORD_RE = re.compile(r'^https://(discord\.com|discordapp\.com)/api/webhooks/')
_EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def _infer_destination_type(destination):
    """Return 'discord', 'email', or None if unrecognized."""
    if _DISCORD_RE.match(destination):
        return 'discord'
    if _EMAIL_RE.match(destination):
        return 'email'
    return None


def _load_yaml():
    with open(_PAPERS_YAML_PATH) as f:
        return yaml.safe_load(f)


def _cached_paper_path(papername, d):
    """Return existing downloaded file path for papername+date, or None."""
    pattern = os.path.join(_DOWNLOADS_DIR, f'{d.isoformat()}-{papername}.*')
    matches = glob.glob(pattern)
    return matches[0] if matches else None


def _cached_combined_path(paper_keys, d):
    label = '-'.join(sorted(paper_keys))
    path = os.path.join(_GENERATED_DIR, f'{d.isoformat()}-{label}.jpg')
    return path if os.path.exists(path) else None


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter
# ---------------------------------------------------------------------------

import time
import collections

_rate_buckets = collections.defaultdict(list)

def _rate_limit(key, max_calls, window_seconds):
    """Returns True if the call should be allowed, False if rate-limited."""
    now = time.time()
    bucket = _rate_buckets[key]
    # remove old entries
    _rate_buckets[key] = [t for t in bucket if now - t < window_seconds]
    if len(_rate_buckets[key]) >= max_calls:
        return False
    _rate_buckets[key].append(now)
    return True


def _client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.route('/api/papers')
def api_papers():
    cfg = _load_yaml()
    papers = [
        {'key': k, 'name': v['name'], 'format': v.get('format', 'unknown')}
        for k, v in cfg['papers'].items()
    ]
    configs = cfg.get('configs', {})
    default = cfg.get('default', [])
    return jsonify({'papers': papers, 'configs': configs, 'default': default})


@app.route('/api/paper/<key>')
def api_paper(key):
    ip = _client_ip()
    if not _rate_limit(f'paper:{ip}', max_calls=20, window_seconds=60):
        abort(429)

    date_str = request.args.get('date')
    try:
        d = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
    except ValueError:
        abort(400)

    cfg = _load_yaml()
    if key not in cfg['papers']:
        abort(404)

    paper_cfg = cfg['papers'][key]

    # Check disk cache first; fall back to yesterday if today unavailable
    cached = _cached_paper_path(key, d)
    if cached:
        path = cached
    else:
        try:
            path = fetch.fetch_paper(paper_cfg, key, d)
        except RuntimeError:
            yesterday = d - datetime.timedelta(days=1)
            path = _cached_paper_path(key, yesterday)
            if not path:
                abort(502)
        path = os.path.abspath(path)

    if paper_cfg.get('trim_whitespace'):
        img = combine._trim_whitespace(Image.open(path).convert('RGB'))
        buf = io.BytesIO()
        img.save(buf, 'JPEG')
        buf.seek(0)
        return send_file(buf, mimetype='image/jpeg')

    return send_file(path)


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/unsubscribe')
def unsubscribe():
    sub_id_str = request.args.get('id', '').strip()
    try:
        sub_id = int(sub_id_str)
    except (ValueError, TypeError):
        return _unsubscribe_page('Invalid unsubscribe link.'), 400

    sub = db.get_subscription(sub_id)
    if sub is None or not sub['active']:
        # Already unsubscribed or never existed — still show a graceful message
        return _unsubscribe_page("You're already unsubscribed (or this link has expired)."), 200

    db.deactivate_subscription(sub_id)
    return _unsubscribe_page("You've been unsubscribed from CoverCompare. No more daily covers will be sent."), 200


def _unsubscribe_page(message):
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CoverCompare — Unsubscribe</title>
  <style>
    body {{ margin: 0; background: #111; color: #eee; font-family: sans-serif;
           display: flex; align-items: center; justify-content: center; min-height: 100vh; }}
    .box {{ text-align: center; padding: 40px 24px; max-width: 480px; }}
    h1 {{ font-size: 20px; margin: 0 0 16px; }}
    p {{ color: #aaa; margin: 0 0 24px; line-height: 1.5; }}
    a {{ color: #888; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>CoverCompare</h1>
    <p>{message}</p>
    <a href="/">Back to CoverCompare</a>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Subscription routes
# ---------------------------------------------------------------------------

@app.route('/api/subscriptions', methods=['POST'])
def create_subscription():
    ip = _client_ip()
    if not _rate_limit(f'sub:{ip}', max_calls=5, window_seconds=86400):
        abort(429)

    body = request.get_json(force=True, silent=True) or {}
    destination = (body.get('destination') or '').strip()
    papers = body.get('papers') or []
    label = (body.get('label') or '').strip() or None

    if not destination or not papers:
        return jsonify({'error': 'destination and papers are required'}), 400

    sub_type = _infer_destination_type(destination)
    if sub_type is None:
        return jsonify({'error': 'destination must be a Discord webhook URL or email address'}), 400

    cfg = _load_yaml()
    invalid = [p for p in papers if p not in cfg['papers']]
    if invalid:
        return jsonify({'error': f'Unknown paper keys: {invalid}'}), 400

    today = datetime.date.today()
    combined_path = os.path.join(_GENERATED_DIR, f'{today.isoformat()}-test-{uuid.uuid4().hex[:8]}.jpg')
    os.makedirs(_GENERATED_DIR, exist_ok=True)
    try:
        paths, trim_flags = _fetch_papers(papers, cfg, today)
        combine.combine(paths, combined_path, trim_flags)
        if sub_type == 'email':
            # Use sub_id=0 as placeholder for the test delivery unsubscribe link
            email_delivery.send(combined_path, today, to_email=destination, label=label, sub_id=0)
        else:
            resp = discord.post(combined_path, today, webhook_url=destination, username=label or None)
            if not (200 <= resp.status_code < 300):
                return jsonify({'error': f'Test delivery failed: HTTP {resp.status_code}'}), 400
    except Exception as e:
        return jsonify({'error': f'Test delivery error: {e}'}), 400
    finally:
        try:
            os.remove(combined_path)
        except OSError:
            pass

    sub = db.create_subscription(
        destination=destination,
        papers=papers,
        label=label,
        ip_address=ip,
        subscription_type=sub_type,
    )

    return jsonify({
        'id': sub['id'],
        'label': sub['label'],
        'papers': papers,
        'created_at': sub['created_at'],
    }), 201


@app.route('/api/subscriptions', methods=['DELETE'])
def delete_subscription():
    destination = request.headers.get('X-Destination', '').strip()
    if not destination or not db.deactivate_by_destination(destination):
        abort(403)
    return '', 204


@app.route('/api/subscriptions/<int:sub_id>/preview')
def preview_subscription(sub_id):
    destination = request.headers.get('X-Destination', '')
    sub = db.get_subscription(sub_id)
    if sub is None or sub['destination'] != destination:
        abort(403)
    if not sub['active']:
        return jsonify({'error': 'Subscription is inactive'}), 400

    import json
    papers = json.loads(sub['papers'])
    today = datetime.date.today()
    cfg = _load_yaml()

    try:
        paths, trim_flags = _fetch_papers(papers, cfg, today)
        combined_path = os.path.join(_GENERATED_DIR, f'{today.isoformat()}-preview-{sub_id}.jpg')
        os.makedirs(_GENERATED_DIR, exist_ok=True)
        combine.combine(paths, combined_path, trim_flags)
        sub_type = sub.get('subscription_type', 'discord')
        if sub_type == 'email':
            email_delivery.send(combined_path, today, to_email=sub['destination'], label=sub['label'] or None, sub_id=sub_id)
            db.record_success(sub_id, today)
            return jsonify({'status': 'delivered'})
        else:
            resp = discord.post(combined_path, today, webhook_url=sub['destination'], username=sub['label'] or None)
            db.record_success(sub_id, today)
            return jsonify({'status': 'delivered', 'discord_status': resp.status_code})
    except Exception as e:
        db.record_error(sub_id, str(e))
        return jsonify({'error': str(e)}), 502


# ---------------------------------------------------------------------------
# Shared helper for fetching a list of papers
# ---------------------------------------------------------------------------

def _fetch_papers(paper_keys, cfg, d):
    paths = []
    trim_flags = []
    for key in paper_keys:
        paper_cfg = cfg['papers'][key]
        cached = _cached_paper_path(key, d)
        if cached:
            path = cached
        else:
            path = fetch.fetch_paper(paper_cfg, key, d)
        paths.append(path)
        trim_flags.append(paper_cfg.get('trim_whitespace', False))
    return paths, trim_flags


if __name__ == '__main__':
    db.init()
    app.run(debug=True)
