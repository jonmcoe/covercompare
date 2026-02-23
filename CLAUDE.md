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

## Adding a new paper

Two generic fetchers are available in `fetch.py`:

**`_fetch_frontpages(slug, papername, d)`** — scrapes frontpages.com full-res image (1200px wide) via base64-obfuscated inline script. Higher quality, more papers available.
- Browse index: https://www.frontpages.com/ — click any paper, the URL slug is e.g. `the-new-york-times`
- Note: og:image/JSON-LD on these pages contains a *truncated* slug that 404s; the real one is only in the script tag

**`_fetch_freedomforum(code, papername, d)`** — hits freedomforum.org CDN directly (700px wide). Patchier coverage but no scraping needed.
- Browse index: https://www.freedomforum.org/todaysfrontpages/?tfp_display=gallery&tfp_region=USA&tfp_sort_by=state&tfp_state_letter=N
- Code format is `STATE_ABBREV` e.g. `NY_DN`, `MA_BG`, `DC_WP`
- Broken for Daily News as of Feb 2026; test before relying on it

To add a paper: add a function in `fetch.py`, register it in `FETCHERS` in `post_today.py`, add an entry in `papers.yaml`.

## Directory conventions

Both directories are auto-created on first run and fully gitignored.

- `downloads/` — individual fetched covers, named `YYYY-MM-DD-papername.ext`
- `generated_images/` — combined output, named `YYYY-MM-DD-{label}.jpg`

## Legacy

- `tweet.py` and `credentials.py` — old Twitter/X posting path, not used in current flow
