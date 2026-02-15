# import bs4
import datetime
import requests


def _save_image(url, papername):
    image_res = requests.get(url)
    path = f'./downloads/{datetime.date.today().isoformat()}-{papername}.jpg'
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
    # probably broken Feb 2026
    # TODO: try https://www.frontpages.com/daily-news --> https://www.frontpages.com/g/2026/02/14/daily-news-103321aw18n9j.webp
    #       but the hash changes each day!
    #       if we only need thumbnail, might be best to pull a *different* page and take thumbnail out of js section.
    #       https://www.frontpages.com/new-york-post/ --> https://www.frontpages.com//t/2026/02/14/daily-news-103321aw1.webp
    d = d or datetime.date.today()
    day = d.day
    # https://www.freedomforum.org/todaysfrontpages/?tfp_display=gallery&tfp_region=USA&tfp_sort_by=state&tfp_state_letter=N
    return _save_image(f'https://cdn.freedomforum.org/dfp/jpg{day}/lg/NY_DN.jpg', 'dailynews')

def download_newsday(d):
    d = d or datetime.date.today()
    day = d.isoformat()
    # https://www.freedomforum.org/todaysfrontpages/?tfp_display=gallery&tfp_region=USA&tfp_sort_by=state&tfp_state_letter=N
    return _save_image(f'https://d2dr22b2lm4tvw.cloudfront.net/ny_nd/{day}/front-page-large.jpg', 'newsday')


if __name__ == '__main__':
    d = datetime.date.today()
    download_nypost_direct(d)
    download_dailynews(d)
    download_newsday(d)
