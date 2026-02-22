# covercompare

A bot that fetches New York newspaper front pages, combines them side-by-side, and posts the comparison image to Discord daily.

## Papers

| Key | Paper | Source |
|---|---|---|
| `nypost` | NY Post | Direct CDN at `nypost.com/wp-content/uploads/...` |
| `newsday` | Newsday | CloudFront CDN at `d2dr22b2lm4tvw.cloudfront.net/ny_nd/...` |
| `dailynews` | NY Daily News | Scraped from `frontpages.com/daily-news/` (thumbnail-quality) |

## Setup

### Dependencies

```bash
pip install -r requirements.txt
```

Requires Python 3 and: `pillow`, `requests`, `beautifulsoup4`, `pyyaml`, `tweepy`

### Environment variables

| Variable | Description |
|---|---|
| `COVERCOMPARE_DISCORD_WEBHOOK` | Discord webhook URL to post images to |

### Directories

Create these if they don't exist:

```
downloads/          # individual fetched cover images
generated_images/   # combined output images
```

## Usage

### Post today's covers

```bash
python post_today.py                           # default papers (newsday + nypost)
python post_today.py 2025-11-15                # specific date
python post_today.py --config new_york         # named config (all 3 NY papers)
python post_today.py --papers nypost dailynews # explicit paper list
```

Named configs are defined in `papers.yaml`. The `new_york` config runs all three papers left-to-right by political lean: Daily News → Newsday → NY Post.

Generated images are saved to `generated_images/YYYY-MM-DD-{label}.jpg` where label is the config name, hyphenated paper list, or `combined` for the default.

### Post a flashback

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
| `tweet.py` | Legacy Twitter posting (not used) |
