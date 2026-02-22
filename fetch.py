import bs4
import datetime
import json
import os
import requests


def _save_image(url, papername):
    os.makedirs('./downloads', exist_ok=True)
    image_res = requests.get(url)
    ext = os.path.splitext(url.split('?')[0])[1] or '.jpg'
    path = f'./downloads/{datetime.date.today().isoformat()}-{papername}{ext}'
    with open(path, 'wb') as f:
        f.write(image_res.content)
    return path


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
    d = d or datetime.date.today()
    page_html = requests.get('https://www.frontpages.com/daily-news/').content
    soup = bs4.BeautifulSoup(page_html, features="html.parser")
    script_tag = soup.find('script', attrs={'type': 'application/ld+json'})
    data = json.loads(script_tag.string)
    if isinstance(data, list):
        data = data[0]
    # data['image'] is a list: [0] = /share/ JPEG, [1] = /g/ full-size webp (404s without auth)
    # /t/ thumbnail (same slug, different prefix) is publicly accessible
    g_url = data['image'][1]
    full_url = g_url.replace('/g/', '/t/', 1)
    return _save_image(full_url, 'dailynews')


def download_newsday(d):
    d = d or datetime.date.today()
    day = d.isoformat()
    return _save_image(f'https://d2dr22b2lm4tvw.cloudfront.net/ny_nd/{day}/front-page-large.jpg', 'newsday')


if __name__ == '__main__':
    d = datetime.date.today()
    download_nypost_direct(d)
    download_dailynews(d)
    download_newsday(d)
