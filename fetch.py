import base64
import datetime
import email.utils  # parsedate_to_datetime is stdlib's de facto HTTP date parser
import io
import os
import re
import requests
from PIL import Image, ImageOps
from zoneinfo import ZoneInfo


_DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')


def _save_image(url, papername, date=None, mirror=False):
    os.makedirs(_DOWNLOADS_DIR, exist_ok=True)
    image_res = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    image_res.raise_for_status()
    ext = os.path.splitext(url.split('?')[0])[1]
    if ext.lower() not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
        ext = '.jpg'
    if date is None:
        date = datetime.date.today()
    path = os.path.join(_DOWNLOADS_DIR, f'{date.isoformat()}-{papername}{ext}')
    if mirror:
        img = Image.open(io.BytesIO(image_res.content))
        ImageOps.mirror(img).save(path)
    else:
        with open(path, 'wb') as f:
            f.write(image_res.content)
    return path


def _parse_frontpages_date(html):
    """Extract the actual paper date from frontpages.com JSON-LD dateModified.

    dateModified is in CET/CEST (Europe/Paris). We take the date portion
    directly — it reflects the European calendar date at time of update, which
    matches the edition date for US papers published that morning.
    Returns a datetime.date, or None if not found.
    """
    m = re.search(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
    if m:
        return datetime.date.fromisoformat(m.group(1))
    return None


def _fetch_frontpages(slug, papername, d):
    """Fetch full-res cover from frontpages.com for any paper by its URL slug.

    frontpages.com base64-encodes the full-size image path in an obfuscated
    inline script to foil naive scrapers. The slug in og:image/JSON-LD is
    truncated and 404s; this extracts the real one.

    The image is saved under the actual paper date from dateModified, not the
    requested date, to avoid cache poisoning when frontpages hasn't updated yet.

    Find a paper's slug at https://www.frontpages.com/<slug>/
    e.g. 'daily-news', 'new-york-post', 'newsday'
    """
    r = requests.get(f'https://www.frontpages.com/{slug}/', headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    actual_date = _parse_frontpages_date(r.text) or (d or datetime.date.today())
    m = re.search(r"atob\('([A-Za-z0-9+/=]+)'\)", r.text)
    path = base64.b64decode(m.group(1)).decode('utf-8')
    full_url = 'https://www.frontpages.com' + path
    needs_mirror = bool(re.search(r'id="giornale-img"[^>]*class="[^"]*rttx', r.text) or
                        re.search(r'class="[^"]*rttx[^"]*"[^>]*id="giornale-img"', r.text))
    return _save_image(full_url, papername, date=actual_date, mirror=needs_mirror)


def _fetch_freedomforum(code, papername, d):
    """Fetch cover from freedomforum.org CDN by paper code.

    Was the original source for several papers; broken for Daily News as of
    Feb 2026 but may still work for others.

    Find a paper's code at https://www.freedomforum.org/todaysfrontpages/
    e.g. 'NY_DN' (Daily News), 'MA_BG' (Boston Globe)
    """
    d = d or datetime.date.today()
    url = f'https://cdn.freedomforum.org/dfp/jpg{d.day}/lg/{code}.jpg'
    return _save_image(url, papername, date=d)


def _fetch_kiosko(slug, papername, d, region='us'):
    """Fetch cover from kiosko.net by paper slug (750px JPEG).

    Scrapes the date from the page rather than using d directly, since some
    papers (e.g. WSJ) don't publish every day and the page always reflects
    the most recent available issue.

    Find a paper's slug at https://www.kiosko.net/{region}/ — URL is /{region}/np/{slug}.html
    e.g. 'wsj', 'nyt', 'usatoday' (region='us'), 'vocero' (region='pr')
    """
    r = requests.get(f'https://www.kiosko.net/{region}/np/{slug}.html', headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    m = re.search(r'img\.kiosko\.net/(\d{4}/\d{2}/\d{2})', r.text)
    if not m:
        raise RuntimeError(f'Could not find date in kiosko page for {slug}')
    date_path = m.group(1)
    actual_date = datetime.date.fromisoformat(date_path.replace('/', '-'))
    url = f'https://img.kiosko.net/{date_path}/{region}/{slug}.750.jpg'
    return _save_image(url, papername, date=actual_date)


def _fetch_nypost_scrape(papername, d):
    """NY Post cover page scrape — discovers the actual P1 image URL.

    The filename suffix (e.g. _LCF, _SX) varies day-to-day so we scrape the
    cover archive page to find it rather than constructing the URL directly.
    Supports historical dates since the archive goes back years.
    """
    d = d or datetime.date.today()
    date_str = d.strftime('%B-%d-%Y').lower().replace('-0', '-')
    r = requests.get(f'https://nypost.com/cover/{date_str}/', headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    r.raise_for_status()
    m = re.search(r'https://nypost\.com/wp-content/uploads/sites/2/\d{4}/\d{2}/\w+\.P1[^\s"\'<]+\.jpg', r.text)
    if not m:
        raise RuntimeError(f'Could not find P1 image URL in NY Post cover page for {date_str}')
    return _save_image(m.group(0), papername, date=d)


# Newsday CloudFront CDN — was the primary source until ~Mar 2026 when it started returning 403.
# Newsday migrated to PageSuite (paper.newsday.com → pagesuite redirect_url source). Kept for reference.
# def _fetch_newsday_cloudfront(papername, d):
#     d = d or datetime.date.today()
#     return _save_image(f'https://d2dr22b2lm4tvw.cloudfront.net/ny_nd/{d.isoformat()}/front-page-large.jpg', papername, date=d)


def _fetch_pagesuite(pbid, papername, d, redirect_url=None):
    """Fetch front page from PageSuite e-edition service by publication ID.

    Always returns today's edition — no historical date support.
    The pbid is a fixed UUID per publication, found in the paper's replica JS.

    Uses the Last-Modified response header (converted to ET) to determine the
    actual edition date, preventing cache poisoning if the new edition hasn't
    uploaded yet when we fetch.

    Two URL variants:
    - pbid (default): edition.pagesuite-professional.co.uk — e.g. Seattle Times, Boston Globe
    - redirect_url: follow a redirect to extract the current edid, then fetch from
      edition.pagesuite.com with pnum=1 — e.g. Newsday (paper.newsday.com)
    """
    d = d or datetime.date.today()
    if redirect_url:
        redir = requests.get(redirect_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        m = re.search(r'[?&]edid=([a-f0-9-]+)', redir.url)
        if not m:
            raise RuntimeError(f'Could not find edid in redirect URL: {redir.url}')
        eid = m.group(1)
        url = f'https://edition.pagesuite.com/get_image.aspx?w=1200&eid={eid}&pnum=1'
    else:
        url = f'https://edition.pagesuite-professional.co.uk/get_image.aspx?w=1200&pbid={pbid}'
    r = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    r.raise_for_status()
    last_mod = r.headers.get('Last-Modified')
    if last_mod:
        actual_date = email.utils.parsedate_to_datetime(last_mod).astimezone(ZoneInfo('America/New_York')).date()
    else:
        actual_date = d
    os.makedirs(_DOWNLOADS_DIR, exist_ok=True)
    path = os.path.join(_DOWNLOADS_DIR, f'{actual_date.isoformat()}-{papername}.jpg')
    with open(path, 'wb') as f:
        f.write(r.content)
    return path


def _fetch_source(source_cfg, papername, d):
    """Dispatch a single source config entry to the appropriate fetcher."""
    source = source_cfg['source']
    if source == 'frontpages':
        return _fetch_frontpages(source_cfg['slug'], papername, d)
    elif source == 'freedomforum':
        return _fetch_freedomforum(source_cfg['code'], papername, d)
    elif source == 'kiosko':
        return _fetch_kiosko(source_cfg['slug'], papername, d, region=source_cfg.get('region', 'us'))
    elif source == 'nypost_scrape':
        return _fetch_nypost_scrape(papername, d)
    elif source == 'pagesuite':
        return _fetch_pagesuite(source_cfg.get('pbid'), papername, d, redirect_url=source_cfg.get('redirect_url'))
    else:
        raise ValueError(f'Unknown source: {source}')


def fetch_paper(cfg, papername, d):
    """Try each source in order, returning the first success.

    Raises RuntimeError only if all sources fail.
    """
    errors = []
    for source_cfg in cfg['sources']:
        try:
            return _fetch_source(source_cfg, papername, d)
        except Exception as e:
            print(f'[{papername}] {source_cfg["source"]} failed: {e}, trying next source')
            errors.append(f'{source_cfg["source"]}: {e}')
    raise RuntimeError(f'All sources failed for {papername}: {"; ".join(errors)}')


if __name__ == '__main__':
    d = datetime.date.today()
    _fetch_nypost_scrape('nypost', d)
    _fetch_frontpages('daily-news', 'dailynews', d)
    _fetch_newsday_cloudfront('newsday', d)
