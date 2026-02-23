# covercompare

A bot that fetches New York newspaper front pages, combines them side-by-side, and posts the comparison image to Discord daily.

## Papers

| Key | Paper | Source |
|---|---|---|
| `nypost` | NY Post | Direct CDN at `nypost.com/wp-content/uploads/...` |
| `newsday` | Newsday | CloudFront CDN at `d2dr22b2lm4tvw.cloudfront.net/ny_nd/...` |
| `dailynews` | NY Daily News | `frontpages.com` (1200px) |
| `wsj` | Wall Street Journal | `kiosko.net` (750px; skips Sundays) |
| `nytimes` | NY Times | `frontpages.com` (1200px), `freedomforum` fallback |
| `washpost` | Washington Post | `frontpages.com` (1200px), `freedomforum` fallback |
| `boston-globe` | Boston Globe | `freedomforum` (700px), `frontpages.com` fallback |
| `miami-herald` | Miami Herald | `freedomforum` (700px), `frontpages.com` fallback |

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
| `post_today.py` | Main entry point: fetch, combine, post |
| `papers.yaml` | Paper definitions and named run configs |
| `fetch.py` | Downloads cover images from paper sources |
| `combine.py` | Tiles N images side-by-side with optional whitespace trimming |
| `discord.py` | Posts image to Discord via webhook |
| `flashback.py` | Re-posts a historical combined image |
