# covercompare

Daily NY newspaper front page comparison bot. Fetches covers, combines them side-by-side, posts to Discord.

## Running the bot

```bash
python post_today.py                           # default papers (newsday + nypost)
python post_today.py 2025-11-15                # specific date
python post_today.py --config new_york         # all 3 NY papers left-to-right
python post_today.py --papers nypost dailynews # explicit paper list
```

## Flashback posts

Re-posts a previously generated image from `generated_images/`:

```bash
python flashback.py 2023-04-01
```

## Environment variables

- `COVERCOMPARE_DISCORD_WEBHOOK` — Discord webhook URL (required for posting)

## Paper sources

- **NY Post** (`nypost`): direct CDN URL at `nypost.com/wp-content/uploads/...`
- **Newsday** (`newsday`): CloudFront CDN at `d2dr22b2lm4tvw.cloudfront.net/ny_nd/...`; has extra whitespace, trimmed automatically
- **NY Daily News** (`dailynews`): scraped from `frontpages.com/daily-news/` JSON-LD; thumbnail-quality only (`/t/` path, full-size `/g/` requires auth)

## papers.yaml

Defines paper fetcher mappings and named run configs. The `new_york` config runs all three papers ordered left-to-right by political lean.

## Directory conventions

- `downloads/` — individual fetched covers, named `YYYY-MM-DD-papername.ext`
- `generated_images/` — combined output, named `YYYY-MM-DD-{label}.jpg`

## Legacy

- `tweet.py` and `credentials.py` — old Twitter/X posting path, not used in current flow
