#!/usr/bin/env python3
import re
import time
import datetime
from dateutil.parser import parse
import argparse
from urllib.parse import unquote_plus
from bs4 import BeautifulSoup
import requests
from get_mongo_client import get_mongo_client

BASE_URL = 'http://kinprigoods.memo.wiki/'

IGNORE_URLS = [
    # トップページ
    'd/%a5%c8%a5%c3%a5%d7%a5%da%a1%bc%a5%b8',
    # メニューバー
    'd/MenuBar1',
    # タグ検索ページ
    't/',
    # 感謝祭前売り券
    'd/%a5%ad%a5%f3%a5%d7%a5%ea%a5%d5%a5%a1%a5%f3%b4%b6%bc%d5%ba%d7%c1%b0%c7%e4%a4%ea%a5%b0%a5%c3%a5%ba',
    # ぷりっしゅ
    'd/%a4%d7%a4%ea%a4%c3%a4%b7%a4%e5',
    # 発売日リスト
    'd/%c8%af%c7%e4%c6%fc%a5%ea%a5%b9%a5%c8',
    # キャンペーン・期間限定ショップ・イベント販売情報
    'd/%a5%ad%a5%e3%a5%f3%a5%da%a1%bc%a5%f3%a1%a6%b4%fc%b4%d6%b8%c2%c4%ea%a5%b7%a5%e7%a5%c3%a5%d7%a1%a6%a5%a4%a5%d9%a5%f3%a5%c8%c8%ce%c7%e4%be%f0%ca%f3',
    # 同・終了分
    'd/%a5%ad%a5%e3%a5%f3%a5%da%a1%bc%a5%f3%a1%a6%b4%fc%b4%d6%b8%c2%c4%ea%a5%b7%a5%e7%a5%c3%a5%d7%a1%a6%a5%a4%a5%d9%a5%f3%a5%c8%c8%ce%c7%e4%be%f0%ca%f3%a1%ca%bd%aa%ce%bb%ca%ac%a1%cb',
]
# prepend a base url
IGNORE_URLS = list(map(lambda ignore: BASE_URL + ignore, IGNORE_URLS))

def main():
    # get links from menubar
    if args.page == 'all':
        urls = get_urls_all()
    elif args.page == 'new':
        urls = get_urls_new()
    else:
        return
    for i, url in enumerate(urls):
        if url in IGNORE_URLS:
            continue
        item = parse_page(url)
        if not item:
            continue
        print_item(item, i=i)
        save_item(item)

def get_urls_all():
    url = BASE_URL + 'd/MenuBar1'
    soup = get_soup(url)
    urls = [a['href'] for a in soup.select('#content_block_2 li a')[2:]]
    return urls

def get_urls_new():
    url = BASE_URL + 'l/'
    soup = get_soup(url)
    urls = [a['href'] for a in soup.select('ul.page-list > li > a')]
    return urls

def print_item(item, i=None):
    """
    for debug: print key/value pairs of item.
    """
    print('-' * 4)
    if i is not None:
        print('#', i)
    for k, v in item.items():
        print('- {}: {}'.format(k,repr(v)))

def save_item(item):
    # use page url as id
    id = '/'.join(item['url'].split('/')[4:])
    db.update({'_id': id}, {'$set': item}, upsert=True)
        
def get_soup(url):
    """
    get BeautifulSoup object of the url page
    """
    r = requests.get(url)
    if not r.ok:
        return None
    return BeautifulSoup(r.text, 'lxml')

def parse_page(url):
    """
    analyze the url page and return informations
    """
    item = {}
    soup = get_soup(url)
    if not soup:
        return None

    # get page meta data
    item['url'] = url
    item['updated_time'] = parse(soup.select('meta[name=generated]')[0]['content'])
    
    soup = soup.select('#page-body')[0]

    # get name
    for div in soup.select('div'):
        if div.has_attr('class'):
            if re.search(r'title-\d', ' '.join(div['class'])):
                item['name'] = div.text.strip().replace('　', ' ')
                break

    # get maker name
    m = re.search(r'(?:発売元|出版社)(?::|：)(\S+)\s*?(?:販売元)?', soup.text)
    if m:
        item['maker'] = m.group(1).replace('株式会社', '').strip()
    else:
        item['maker'] = None

    # get tweet ids
    item['tweet_urls'] = [t.select('a')[-1]['href'] for t in soup.select('.embedded-tweet')]
        
    # remove embeded tweets
    for div in soup.select('.embedded-tweet'):
        div.extract() 

    # remove headers
    titles = [div for div in soup.select('div')
              if div.has_attr('class') and re.search(r'title-', ' '.join(div['class']))]
    for title in titles:
        title.extract()
    
    # get release_date
    m = re.search(r'((?:(?:(\d{4})年)?(\d{,2})月(?:(\d{,2})日)?.*?(?:(上|中|下)旬)?.*?)|発売.+?不明)', soup.text)
    if m:
        # if release date id '不明'
        if '不明' in m.group(1):
            item['date'] = None
            item['date_extra'] = None
        else:
            year, month, day = map(lambda x: x and int(x) or None, m.group(2, 3, 4))
            extra = m.group(5)
            if not year:
                year = datetime.date.today().year
            if not month:
                month = 1
            if not day:
                if not extra:
                    extra = '月'
                day = 1
            item['date'] = datetime.datetime(year=year, month=month, day=day)
            item['date_extra'] = extra
    else:
        item['date'] = None
        item['date_extra'] = None

    # get tags
    item['tags'] = [tag.text.strip() for tag in soup.select('#page-tags .tags')]
        
    return item

if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('page', choices=['all', 'new'])
    args = parser.parse_args()
     
    # prepare database
    c = get_mongo_client()
    db = c.kinpri_goods_wiki.items

    main()
