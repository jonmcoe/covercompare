import bs4
import datetime
import requests


def _save_image(url, papername):
    image_res = requests.get(url)
    path = f'./downloads/{datetime.date.today().isoformat()}-{papername}.jpg'
    with open(path, 'wb') as f:
        f.write(image_res.content)
    return path


def download_nypost():
    today = datetime.date.today()
    today_string = today.strftime('%B-%d-%Y').lower().replace('-0', '-')
    page_html = requests.get(f'https://nypost.com/cover/{today_string}/').content
    soup = bs4.BeautifulSoup(page_html, features="html.parser")
    image_url = soup.find('source').attrs['data-srcset'].split('?')[0]
    return _save_image(image_url, 'nypost')


def download_dailynews():
    day = datetime.date.today().day
    # https://www.freedomforum.org/todaysfrontpages/?tfp_display=gallery&tfp_region=USA&tfp_sort_by=state&tfp_state_letter=N
    return _save_image(f'https://cdn.freedomforum.org/dfp/jpg{day}/lg/NY_DN.jpg', 'dailynews')


if __name__ == '__main__':
    download_nypost()
    download_dailynews()
