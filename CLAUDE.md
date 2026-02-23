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
- **NY Daily News** (`dailynews`): scraped from `frontpages.com/daily-news/` via base64-obfuscated script tag

## papers.yaml

Defines paper sources and named run configs. The `new_york` config runs all three papers ordered left-to-right by political lean.

Each paper has a `sources` list tried in order — first success wins, error only if all fail. This supports silent fallback between sources for papers available in multiple places.

## Paper formats

Papers have a `format` field in `papers.yaml`: `tabloid` (NY Post, Daily News, Newsday — roughly square-ish aspect ratio) or `broadsheet` (NYT, WSJ, WaPo, Globe etc — tall and narrow). Mixing formats in a single run works but looks awkward: broadsheets will dominate height and tabloids will appear wide and stubby by comparison. The `new_york` config is all-tabloid; most national paper combos are all-broadsheet.

The `format` field is metadata only — `combine.py` doesn't use it. A future enhancement could warn or auto-group by format.

## Adding a new paper

To add a paper, only `papers.yaml` needs to change (no Python edits needed for `frontpages` or `freedomforum` sources). Add an entry with a `sources` list:

```yaml
my-paper:
  name: "My Paper"
  sources:
    - source: frontpages
      slug: my-paper-slug
    - source: freedomforum
      code: ST_CODE
```

**`frontpages` source** — 1200px wide WebP, ~33 US dailies, scraped via base64-obfuscated inline script
- Browse index: https://www.frontpages.com/ — click any paper, the URL slug is the path component e.g. `the-new-york-times`
- Note: og:image/JSON-LD on these pages contains a *truncated* slug that 404s; the real one is only in the script tag
- Updates ~01:00–06:00 ET for major papers; `dateModified` in JSON-LD is in CET (shifts to CEST after late March European DST)
- Newsday edge case: frontpages labels Newsday's edition with the *next* calendar day

**`freedomforum` source** — 700px wide JPEG, ~19+ US dailies confirmed, direct CDN URL (no scraping)
- Browse index: https://www.freedomforum.org/todaysfrontpages/?tfp_display=gallery&tfp_region=USA&tfp_sort_by=state&tfp_state_letter=N (note: the website rate-limits bots but the CDN at `cdn.freedomforum.org` does not)
- Code format is `STATE_ABBREV` e.g. `MA_BG`, `DC_WP`, `NY_NYT`; day-of-month in URL is **not zero-padded** (`jpg5` not `jpg05`)
- NY Post and NY Daily News are not on freedomforum; use frontpages for those
- **Weekend staleness risk**: some papers (Miami Herald, Star Tribune, Arizona Republic) have been observed returning the previous day's image on weekends with a 200 response — no error raised, just silently stale content
- **Known working codes** (swept 2026-02-22, 46 found from 2360 probes — freshness as of that Sunday):

  | Code | Paper | Fresh? |
  |---|---|---|
  | NY_NYT | NY Times | ✓ |
  | NY_ND | Newsday | ✓ |
  | DC_WP | Washington Post | ✓ |
  | MA_BG | Boston Globe | ✓ |
  | CA_LAT | LA Times | ✓ |
  | CA_SFC | SF Chronicle | ✓ |
  | CA_MN | Mercury News | ✓ |
  | CA_DN | Daily News (CA) | ✓ |
  | TX_DMN | Dallas Morning News | ✓ |
  | TX_HC | Houston Chronicle | ✓ |
  | IL_CST | Chicago Sun-Times | ✓ |
  | IL_JG | Joliet Herald-News | ✓ |
  | PA_PI | Pittsburgh Post-Gazette | ✓ |
  | OH_TB | Toledo Blade | ✓ |
  | OH_DDN | Dayton Daily News | ✓ |
  | GA_AJC | Atlanta Journal-Constitution | ✓ |
  | WA_ST | Seattle Times | ✓ |
  | CO_DH | Denver Post | ✓ |
  | NJ_SL | Star-Ledger (NJ) | ✓ |
  | MN_PP | Pioneer Press | ✓ |
  | VA_DP | Daily Progress | ✓ |
  | NE_CT | Omaha World-Herald | ✓ |
  | SC_MN | The State (SC) | ✓ |
  | FL_MH | Miami Herald | stale weekends |
  | MI_DFP | Detroit Free Press | stale weekends |
  | MN_ST | Star Tribune | stale weekends |
  | OR_RG | Oregonian | stale weekends |
  | MA_ST | Springfield Republican | stale weekends |
  | NV_SUN | Las Vegas Sun | stale weekends |
  | TX_ST | San Antonio Express | frequently stale |
  | IL_JS | Journal Star (IL) | frequently stale |
  | IL_PDT | Peoria Journal Star | frequently stale |
  | OH_CD | Columbus Dispatch | frequently stale |
  | MI_HS | Holland Sentinel | frequently stale |
  | GA_AC | Augusta Chronicle | frequently stale |
  | AZ_AR | Arizona Republic | frequently stale |
  | WA_SUN | Spokesman-Review | frequently stale |
  | IN_PI | Indianapolis Star | frequently stale |
  | IN_JC | Journal & Courier (IN) | frequently stale |
  | IN_IS | Indiana State Journal | frequently stale |
  | IN_SP | South Bend Tribune | frequently stale |
  | KY_CJ | Courier-Journal (KY) | frequently stale |
  | KY_DN | Daily News (KY) | frequently stale |
  | TN_DH | Daily Herald (TN) | frequently stale |
  | TN_JS | Jackson Sun | frequently stale |
  | WI_SP | Wisconsin State Journal | frequently stale |

**`kiosko` source** — 750px wide JPEG, good for papers not on frontpages/freedomforum (e.g. WSJ)
- Browse index: https://www.kiosko.net/us/ — URL slug is from `/us/np/{slug}.html`
- Date is scraped from the page rather than passed as a parameter — always reflects the most recent available issue, handling publication gaps (e.g. WSJ skips Sundays) automatically
- **Historical dates**: supported via direct URL (`img.kiosko.net/YYYY/MM/DD/us/{slug}.750.jpg`) but `_fetch_kiosko` ignores the `d` parameter and always fetches the latest

**Historical date support by source** (relevant for flashback runs and `post_today.py YYYY-MM-DD`):

| Source | Historical dates? | Notes |
|---|---|---|
| `nypost_direct` | Yes | Full date in CDN URL |
| `newsday_cloudfront` | Yes | Full ISO date in CDN URL |
| `kiosko` | No — always latest | Scrapes page date; ignores `d` |
| `frontpages` | No — always latest | Scrapes live page; ignores `d` |
| `freedomforum` | No — today only | URL uses day-of-month only, no year/month |

**Choosing between sources for a paper on multiple**: prefer frontpages for resolution; prefer freedomforum for stability (no scraping). If frontpages changes its obfuscation scheme it will break all frontpages fetches at once.

## Directory conventions

Both directories are auto-created on first run and fully gitignored.

- `downloads/` — individual fetched covers, named `YYYY-MM-DD-papername.ext`
- `generated_images/` — combined output, named `YYYY-MM-DD-{label}.jpg`
