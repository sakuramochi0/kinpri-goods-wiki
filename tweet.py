#!/usr/bin/env python3
import re
import datetime
import argparse
import time
from dateutil.parser import parse
from pymongo.mongo_client import MongoClient
from get_tweepy import *

from save_items import print_item

def tweet_date_items(date):
    """
    指定した日付に発売される全アイテムをツイートする
    """
    # tweet item number of the date
    num_status = make_num_status(date=date)
    tweet(num_status)

    # tweet items
    items = get_date_items(date)
    for item in items:
        item_status = make_item_status(date=date, item=item)
        tweet(item_status)

def tweet(status, imgs=[]):
    """
    指定したツイートテキストで、アカウントからツイートする
    """
    if args.debug:
        print('-' * 4)
        print('would tweet:')
        print(status)
    else:
        # TODO: imgs can be list?
        if imgs:
            pass
        #     api.update_with_media(status=status, filename=imgs)
        else:
            api.update_status(status=status)
            print('-' * 4)
            print('tweeted:')
            print(status)
            time.sleep(10)

def make_num_status(date=None):
    """
    ツイート用に、指定した日付に発売するアイテム数を知らせるツイートテキストを生成する
    """
    # parse date
    if type(date) is str:
        date = parse(date)
    elif not date:
        date = get_date()

    # tweet a number of items
    num = db.find({'date': date, 'date_extra': None}).count()
    if num:
        status = 'みんな〜、{date_description}{date}は{num}個のグッズが発売されるみたいだぞー。これから紹介するなー。'.format(
            date_description=get_date_description(date), date=format_date(date), num=num
        )
    else:
        future_items = db.find({'date': {'$gt': date}, 'date_extra': None}).sort('date')
        if future_items.count():
            next_item = future_items[0]
            next_date = next_item['date']
            next_num = db.find({'date': next_date, 'date_extra': None}).count()
            status = '{date_description}{date}は、特にグッズは発売されないみたいだなー。次は{next_date_description}{next_date}に、{next_num}個のグッズが発売されるようだ。'.format(
                date_description=get_date_description(date),
                date=format_date(date),
                next_date_description=get_date_description(next_date),
                next_date=format_date(next_date),
                next_num=next_num,
            )
        else:
            status = '今のところ、{date_description}{date}以降に発売する予定のグッズはないみたいだ。次を楽しみにしようなー。'.format(
                date_description=get_date_description(date),
                date=format_date(date),
            )

    return status

def make_item_status(item=None, date=None):
    """
    ツイート用に、指定したアイテムや日付から、アイテムの紹介ツイートテキストを生成する
    """
    # parse date
    if type(date) is str:
        date = parse(date)
    elif not date:
        date = get_date()

    # make quote text
    if item['tweet_urls']:
        quote = ' ' + item['tweet_urls'][0]
    else:
        quote = ''
        
    # make status text
    status = '{date_description}{date}は、{maker}さんから「{name}」が発売されるようだ。詳しくはこれ見とけ〜 {url}{quote}'.format(
        date_description=get_date_description(date),
        date=format_date(date),
        maker=item['maker'],
        name=item['name'],
        url=item['url'],
        quote=quote,
    )
    return status

def get_date_description(date):
    delta = (date.date() - datetime.date.today()).days
    if delta == 0:
        date_description = '今日'
    elif delta == 1:
        date_description = '明日'
    elif delta == 2:
        date_description = '明後日'
    elif delta == 3:
        date_description = 'あさって'
    else:
        date_description = ''
    return date_description

def format_date(date):
    """
    ツイート用に、日付を「1月1日(月)」のフォーマットに整形する
    """
    weekday = str(date.weekday()).translate(dict([(ord(n), day) for n, day in zip('0123456', '月火水木金土日')]))
    datestr = date.strftime('%m月%d日({weekday})'.format(weekday=weekday))
    # 月と日の0埋めを消す e.g.「01月」->「1月」
    datestr = re.sub(r'0(\d)(月|日)', r'\1\2', datestr)
    return datestr
    
def get_date(delta=0, date=''):
    """
    今日からの日数、または、文字列で指定した日付のdatetimeオブジェクトを返す
    """
    if date:
        date = parse(date)
    else:
        today = datetime.date.today()
        date = today + datetime.timedelta(days=delta)
    return parse(date.strftime('%Y-%m-%d'))

def print_date_items(date):
    """
    指定した日付のアイテムをプリントする
    """
    items = get_date_items(date)
    print('date:{} / item: {}'.format(date.date(), items.count()))
    for item in items:
        print_item(item)

# stub
def print_week_items(date):
    """
    指定した日付が含まれる週のアイテムをプリントする
    """
    items = get_date_items(date)
    print('{} item:'.format(date), items.count())
    for item in items:
        print_item(item)
        
def get_date_items(date):
    """
    指定した日付に発売するアイテムのCursorを返す
    """
    return get_dates_items(date, date)

def get_dates_items(start_date, end_date):
    """
    指定した日付の期間に発売するアイテムのCursorを返す
    """
    return db.find({'date': {'$gte': start_date, '$lte': end_date}, 'date_extra': None})

if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('command', type=str, choices=[
        'tweet_today', 'print_today',
        'tweet_tomorrow', 'print_tomorrow',
        'tweet_date', 'print_date',
    ])
    parser.add_argument('--date')
    parser.add_argument('--delta', type=int, default=1)
    args = parser.parse_args()
     
    # prepare database
    c = MongoClient()
    if args.debug:
        db = c.kinpri_goods_wiki_debug.items
    else:
        db = c.kinpri_goods_wiki.items
     
    # get tweepy api
    api = get_api('goods_yamada')

    # run command
    
    # today
    if args.command == 'tweet_today':
        tweet_date_items(get_date())

    elif args.command == 'print_today':
        print_date_items(get_date())

    # tomorrow
    if args.command == 'tweet_tomorrow':
        tweet_date_items(get_date(delta=1))

    elif args.command == 'print_tomorrow':
        print_date_items(get_date(delta=1))

    # specific date
    elif args.command == 'tweet_date' or args.command == 'print_date':
        # get date
        if args.date:
            date = get_date(date=args.date)
        elif args.delta is not None:
            date = get_date(delta=args.delta)

        # run command
        if args.command == 'tweet_date':
            tweet_date_items(date)
        elif args.command == 'print_date':
            print_date_items(date)
    
