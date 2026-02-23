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
import fetch

app = Flask(__name__, static_folder='static', static_url_path='')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAPERS_YAML_PATH = os.path.join(os.path.dirname(__file__), 'papers.yaml')
_DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
_GENERATED_DIR = os.path.join(os.path.dirname(__file__), 'generated_images')

DISCORD_DOMAINS = {'discord.com', 'discordapp.com'}
AUTO_DEACTIVATE_THRESHOLD = 7


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

    # Check disk cache first
    cached = _cached_paper_path(key, d)
    if cached:
        path = cached
    else:
        try:
            path = fetch.fetch_paper(paper_cfg, key, d)
        except RuntimeError:
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


# ---------------------------------------------------------------------------
# Subscription routes
# ---------------------------------------------------------------------------

@app.route('/api/subscriptions', methods=['POST'])
def create_subscription():
    ip = _client_ip()
    if not _rate_limit(f'sub:{ip}', max_calls=5, window_seconds=86400):
        abort(429)

    body = request.get_json(force=True, silent=True) or {}
    webhook_url = (body.get('webhook_url') or '').strip()
    papers = body.get('papers') or []
    label = (body.get('label') or '').strip() or None

    # Validate
    if not webhook_url or not papers:
        return jsonify({'error': 'webhook_url and papers are required'}), 400

    # Webhook URL validation: HTTPS + domain allowlist
    from urllib.parse import urlparse
    parsed = urlparse(webhook_url)
    if parsed.scheme != 'https':
        return jsonify({'error': 'webhook_url must be HTTPS'}), 400
    if parsed.hostname not in DISCORD_DOMAINS:
        return jsonify({'error': 'webhook_url must be a Discord webhook'}), 400

    # Validate paper keys
    cfg = _load_yaml()
    invalid = [p for p in papers if p not in cfg['papers']]
    if invalid:
        return jsonify({'error': f'Unknown paper keys: {invalid}'}), 400

    # Test delivery — fetch+combine and post to webhook
    today = datetime.date.today()
    try:
        paths, trim_flags = _fetch_papers(papers, cfg, today)
        label_str = label or '-'.join(sorted(papers))
        combined_path = os.path.join(_GENERATED_DIR, f'{today.isoformat()}-test-{uuid.uuid4().hex[:8]}.jpg')
        os.makedirs(_GENERATED_DIR, exist_ok=True)
        combine.combine(paths, combined_path, trim_flags)
        resp = discord.post(combined_path, today, webhook_url=webhook_url)
        if not (200 <= resp.status_code < 300):
            return jsonify({'error': f'Test delivery failed: HTTP {resp.status_code}'}), 400
        # Clean up temp combined file
        try:
            os.remove(combined_path)
        except OSError:
            pass
    except Exception as e:
        return jsonify({'error': f'Test delivery error: {e}'}), 400

    secret_token = str(uuid.uuid4())
    sub = db.create_subscription(
        webhook_url=webhook_url,
        papers=papers,
        label=label,
        secret_token=secret_token,
        ip_address=ip,
    )

    return jsonify({
        'id': sub['id'],
        'secret_token': secret_token,
        'label': sub['label'],
        'papers': papers,
        'created_at': sub['created_at'],
    }), 201


@app.route('/api/subscriptions/<int:sub_id>', methods=['DELETE'])
def delete_subscription(sub_id):
    token = request.headers.get('X-Subscription-Token', '')
    sub = db.get_subscription(sub_id)
    if sub is None or sub['secret_token'] != token:
        abort(403)
    db.deactivate_subscription(sub_id)
    return '', 204


@app.route('/api/subscriptions/<int:sub_id>/preview')
def preview_subscription(sub_id):
    token = request.headers.get('X-Subscription-Token', '')
    sub = db.get_subscription(sub_id)
    if sub is None or sub['secret_token'] != token:
        abort(403)
    if not sub['active']:
        return jsonify({'error': 'Subscription is inactive'}), 400

    import json
    papers = json.loads(sub['papers'])
    today = datetime.date.today()
    cfg = _load_yaml()

    try:
        paths, trim_flags = _fetch_papers(papers, cfg, today)
        label = sub['label'] or '-'.join(sorted(papers))
        combined_path = os.path.join(_GENERATED_DIR, f'{today.isoformat()}-preview-{sub_id}.jpg')
        os.makedirs(_GENERATED_DIR, exist_ok=True)
        combine.combine(paths, combined_path, trim_flags)
        resp = discord.post(combined_path, today, webhook_url=sub['webhook_url'])
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
