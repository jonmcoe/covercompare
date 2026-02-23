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

Two generic fetchers are available in `fetch.py`. To add a paper, only `papers.yaml` needs to change (no Python edits needed for either generic source).

**`frontpages` source** — 1200px wide WebP, ~33 US dailies, scraped via base64-obfuscated inline script
- Browse index: https://www.frontpages.com/ — click any paper, the URL slug is the path component e.g. `the-new-york-times`
- Note: og:image/JSON-LD on these pages contains a *truncated* slug that 404s; the real one is only in the script tag
- Updates ~01:00–06:00 ET for major papers; `dateModified` in JSON-LD is in CET (shifts to CEST after late March European DST)
- Newsday edge case: frontpages labels Newsday's edition with the *next* calendar day

**`freedomforum` source** — 700px wide JPEG, ~19+ US dailies confirmed, direct CDN URL (no scraping)
- Browse index: https://www.freedomforum.org/todaysfrontpages/?tfp_display=gallery&tfp_region=USA&tfp_sort_by=state&tfp_state_letter=N (note: the website itself rate-limits bots but the CDN does not)
- Code format is `STATE_ABBREV` e.g. `MA_BG`, `DC_WP`, `NY_NYT`; day-of-month in URL is not zero-padded
- `Last-Modified` header on CDN responses gives reliable staleness check
- NY Post and NY Daily News are not available here; use frontpages for those
- Some papers have stale images on weekends — verify with a HEAD request before relying on it

**Choosing between them for a paper on both**: prefer frontpages for resolution; prefer freedomforum for stability (no scraping dependency). If frontpages changes its obfuscation scheme it will break all frontpages fetches simultaneously.

## Directory conventions

Both directories are auto-created on first run and fully gitignored.

- `downloads/` — individual fetched covers, named `YYYY-MM-DD-papername.ext`
- `generated_images/` — combined output, named `YYYY-MM-DD-{label}.jpg`

## Legacy

- `tweet.py` and `credentials.py` — old Twitter/X posting path, not used in current flow
