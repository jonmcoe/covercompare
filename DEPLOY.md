# Deploying CoverCompare

Assumes Amazon Linux 2 (or similar), Python 3.9+, nginx, and an existing
domain pointed at the server. The original `post_today.py` cron can keep
running in parallel — it shares the `downloads/` cache so there's no
duplication of fetches.

---

## 1. Pull the code

```bash
cd /srv/covercompare   # or wherever it lives
git pull
```

---

## 2. Install dependencies

```bash
source env/bin/activate
pip install -r requirements.txt
```

---

## 3. Initialize the database

Only needed on first deploy; safe to re-run (uses `CREATE TABLE IF NOT EXISTS`).

```bash
python db.py
```

---

## 4. Environment variables

The `.env` file is sourced by the existing cron wrapper scripts. The systemd
service (below) also loads it via `EnvironmentFile`.

```bash
# /srv/covercompare/.env  (already gitignored)
COVERCOMPARE_DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
```

---

## 5. systemd service for gunicorn

Create `/etc/systemd/system/covercompare.service`:

```ini
[Unit]
Description=CoverCompare webapp
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/srv/covercompare
EnvironmentFile=/srv/covercompare/.env
ExecStart=/srv/covercompare/env/bin/gunicorn app:app \
    --workers 1 \
    --bind 127.0.0.1:5000 \
    --access-logfile /var/log/covercompare-access.log \
    --error-logfile /var/log/covercompare-error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **Why 1 worker?** The rate limiter uses an in-process dict. Multiple workers
> each have their own bucket, so `-w 4` would effectively 4× the rate limit.
> A single gevent worker handles concurrent I/O fine if you want more throughput:
> `pip install gevent` and add `--worker-class gevent`.

```bash
sudo systemctl daemon-reload
sudo systemctl enable covercompare
sudo systemctl start covercompare
sudo systemctl status covercompare
```

---

## 6. nginx reverse proxy

```nginx
server {
    server_name covercompare.example.com;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # Covers can be a few MB; give fetches time on cache miss
        proxy_read_timeout 30s;
    }
}
```

Then add HTTPS via certbot:

```bash
sudo certbot --nginx -d covercompare.example.com
```

---

## 7. Crontab entries

Add to the user's crontab (`crontab -e`). Times are ET — adjust for server timezone.

```cron
# Warm the image cache before deliveries
30 6 * * * /srv/covercompare/env/bin/python /srv/covercompare/prefetch.py >> /var/log/covercompare-prefetch.log 2>&1

# Deliver to all active Discord subscriptions
0  7 * * * /srv/covercompare/env/bin/python /srv/covercompare/deliver.py  >> /var/log/covercompare-deliver.log 2>&1
```

The existing `post_today.py` cron entry can stay — it hits the same `downloads/`
cache so covers are never fetched twice.

---

## 8. Smoke test

```bash
# Confirm the app is up
curl -s http://localhost:5000/api/papers | python3 -m json.tool | head -20

# Test a paper fetch (will download if not cached)
curl -I http://localhost:5000/api/paper/nypost

# Manually run prefetch and deliver
python prefetch.py
python deliver.py
```

---

## Updating

```bash
git pull
sudo systemctl restart covercompare
```

No migration needed unless `db.py`'s schema changes (it uses `CREATE TABLE IF NOT EXISTS`).
