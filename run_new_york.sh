#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAX_ATTEMPTS=4
RETRY_INTERVAL=3600  # seconds

cd "$SCRIPT_DIR"
[ -f .env ] && source .env

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Attempt $attempt of $MAX_ATTEMPTS"
    if env/bin/python post_today.py --config new_york; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Success"
        exit 0
    fi
    if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Failed, retrying in ${RETRY_INTERVAL}s"
        sleep "$RETRY_INTERVAL"
    fi
done

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] All $MAX_ATTEMPTS attempts failed" >&2
exit 1
