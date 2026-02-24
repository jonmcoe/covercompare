# covercompare

A webapp and bot that fetches US newspaper front pages, displays them side-by-side in a browser, and posts daily combined images to Discord.

## Papers

21 papers across 5 configs. See `papers.yaml` for the full list. A few highlights:

| Region | Papers |
|---|---|
| New York | NY Post, Newsday, NY Daily News |
| National | NY Times, Washington Post, USA Today, Wall Street Journal |
| Northeast | Boston Globe, Philadelphia Inquirer, NJ Star-Ledger, Pittsburgh Post-Gazette |
| Southeast | Miami Herald, Atlanta Journal-Constitution |
| Midwest | Chicago Tribune, Chicago Sun-Times, Dallas Morning News, Houston Chronicle |
| West | LA Times, SF Chronicle, Seattle Times, Denver Post |

Papers with multiple sources try them in order — first success wins. See `papers.yaml` and `CLAUDE.md` for adding more.

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3 and: `pillow`, `requests`, `pyyaml`

### Environment variables

| Variable | Description |
|---|---|
| `COVERCOMPARE_DISCORD_WEBHOOK` | Discord webhook URL to post images to |

## Usage

```bash
python post_today.py                           # default papers (newsday + nypost)
python post_today.py 2025-11-15                # specific date
python post_today.py --config new_york         # all 3 NY papers left-to-right
python post_today.py --papers nypost dailynews # explicit paper list
```

Named configs are defined in `papers.yaml`. The `new_york` config runs Daily News → Newsday → NY Post (left-to-right by political lean).

Generated images are saved to `generated_images/YYYY-MM-DD-{label}.jpg`.

### Flashback

Re-posts a previously generated image from `generated_images/`:

```bash
python flashback.py 2023-04-01
```

## File overview

| File | Purpose |
|---|---|
| `post_today.py` | CLI entry point: fetch, combine, post |
| `papers.yaml` | Paper definitions and named run configs |
| `fetch.py` | Downloads cover images from paper sources |
| `combine.py` | Tiles N images side-by-side with optional whitespace trimming |
| `discord.py` | Posts image to Discord via webhook |
| `flashback.py` | Re-posts a historical combined image |
| `app.py` | Flask webapp: viewer API + subscription endpoints |
| `db.py` | SQLite wrapper for subscriptions |
| `prefetch.py` | Cron script: warm image cache each morning |
| `deliver.py` | Cron script: deliver to all active subscriptions |
