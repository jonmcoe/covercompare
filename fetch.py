import base64
import datetime
import os
import re
import requests


def _save_image(url, papername):
    os.makedirs('./downloads', exist_ok=True)
    image_res = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    ext = os.path.splitext(url.split('?')[0])[1] or '.jpg'
    path = f'./downloads/{datetime.date.today().isoformat()}-{papername}{ext}'
    with open(path, 'wb') as f:
        f.write(image_res.content)
    return path


def _fetch_frontpages(slug, papername, d):
    """Fetch full-res cover from frontpages.com for any paper by its URL slug.

    frontpages.com base64-encodes the full-size image path in an obfuscated
    inline script to foil naive scrapers. The slug in og:image/JSON-LD is
    truncated and 404s; this extracts the real one.

    Find a paper's slug at https://www.frontpages.com/<slug>/
    e.g. 'daily-news', 'new-york-post', 'newsday'
    """
    r = requests.get(f'https://www.frontpages.com/{slug}/', headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    m = re.search(r"atob\('([A-Za-z0-9+/=]+)'\)", r.text)
    path = base64.b64decode(m.group(1)).decode('utf-8')
    full_url = 'https://www.frontpages.com' + path
    return _save_image(full_url, papername)


def _fetch_freedomforum(code, papername, d):
    """Fetch cover from freedomforum.org CDN by paper code.

    Was the original source for several papers; broken for Daily News as of
    Feb 2026 but may still work for others.

    Find a paper's code at https://www.freedomforum.org/todaysfrontpages/
    e.g. 'NY_DN' (Daily News), 'NY_NWS' (Newsday)
    """
    d = d or datetime.date.today()
    url = f'https://cdn.freedomforum.org/dfp/jpg{d.day}/lg/{code}.jpg'
    return _save_image(url, papername)


# def download_nypost(d):
#     today = d or datetime.date.today()
#     today_string = today.strftime('%B-%d-%Y').lower().replace('-0', '-')
#     page_html = requests.get(f'https://nypost.com/cover/{today_string}/').content
#     soup = bs4.BeautifulSoup(page_html, features="html.parser")
#     image_element = soup.find('img', attrs={'class': 'cover-swap__image cover-swap__image--front'})
#     image_url = image_element.attrs['srcset'].split('?')[0]
#     return _save_image(image_url, 'nypost')


def download_nypost_direct(d):
    today = d or datetime.date.today()
    template = "https://nypost.com/wp-content/uploads/sites/2/{0}/{1}/{2}.P1_LCF.jpg?resize=1393,1536&quality=90&strip=all"
    year = today.strftime('%Y')
    month_num = today.strftime('%m')
    capmonth_with_daynum = today.strftime('%B').upper() + today.strftime('%d')
    url = template.format(year, month_num, capmonth_with_daynum)
    print(url)
    return _save_image(url, 'nypost')


def download_dailynews(d):
    return _fetch_frontpages('daily-news', 'dailynews', d)


def download_nytimes(d):
    return _fetch_frontpages('the-new-york-times', 'nytimes', d)


def download_washpost(d):
    return _fetch_frontpages('the-washington-post', 'washpost', d)


def download_boston_globe(d):
    return _fetch_freedomforum('MA_BG', 'boston-globe', d)


def download_miami_herald(d):
    return _fetch_freedomforum('FL_MH', 'miami-herald', d)


def download_newsday(d):
    d = d or datetime.date.today()
    return _save_image(f'https://d2dr22b2lm4tvw.cloudfront.net/ny_nd/{d.isoformat()}/front-page-large.jpg', 'newsday')


if __name__ == '__main__':
    d = datetime.date.today()
    download_nypost_direct(d)
    download_dailynews(d)
    download_newsday(d)
