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
        try:
            item_status = make_item_status(date=date, item=item)
            tweet(item_status)
        except tweepy.TweepError as e:
            if e.api_code == 186:
                if item['maker']:
                    item['maker'] = re.sub(r'\s*?[\(（].+[\)）]', '', item['maker'])
                    item_status = make_item_status(date=date, item=item)
                    try:
                        tweet(item_status)
                    except tweepy.TweepError as e:
                        if e.api_code == 186:
                            item['name'] = re.sub(r'KING OF PRISM by PrettyRhythm', '', item['name'])
                            item_status = make_item_status(date=date, item=item)
                            tweet(item_status)

def tweet(status, imgs=[]):
    """
    指定したツイートテキストで、アカウントからツイートする
    """
    # TODO: imgs can be list?
    if imgs:
        pass
    #     api.update_with_media(status=status, filename=imgs)
    else:
        print('-' * 4)
        print('tweeting:')
        print(status)
        print('({})'.format(status_len(status)))
        api.update_status(status=status)
        if not args.debug:
            time.sleep(10)

def status_len(status):
    dummy_url = 'https://t.co/xxxxxxxxxx'
    url_regex = re.compile(r'http\S+')
    status = re.sub(url_regex, dummy_url, status)
    return len(status)
            
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
    num = c.items.find({'date': date, 'date_extra': None}).count()
    print([i['name'] for i in c.items.find({'date': date, 'date_extra': None})])
    if num:
        status = 'みんな〜、{date_description}{date}は{num}個のグッズが発売されるみたいだぞー。これから紹介するなー。'.format(
            date_description=get_date_description(date), date=format_date(date), num=num
        )
    else:
        future_items = c.items.find({'date': {'$gt': date}, 'date_extra': None}).sort('date')
        if future_items.count():
            next_item = future_items[0]
            next_date = next_item['date']
            next_num = c.items.find({'date': next_date, 'date_extra': None}).count()
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

    # make maker text
    if item['maker']:
        maker = item['maker'] + 'さんから'
    else:
        maker = ''
        
    # make status text
    status = '{date_description}{date}は、{maker}「{name}」が発売されるようだ。詳しくはこれ見とけ〜 {url}{quote}'.format(
        date_description=get_date_description(date),
        date=format_date(date),
        maker=maker,
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

# retweet functions
def retweet_user(screen_name):
    tweets = []
    for t in api.user_timeline(screen_name=screen_name, count=50):
        if in_kinpri_text(t) or in_pretty_text(t):
            tweets.append(t)

    for t in reversed(tweets):

        # if new tweet, insert to database
        if not c.tweets.find_one(t.id):
            doc = make_doc(t)
            c.tweets.insert(doc)
        
        # if not retweeted, do it and record to database
        doc = c.tweets.find_one(t.id)
        if not doc['meta']['retweeted'] and not is_retweeted(doc):
            if args.debug:
                print('would retweeted:')
                print_tweet(doc)
                if args.debug_retweet:
                    api.retweet(doc['_id'])
            else:
                api.retweet(doc['_id'])
                c.tweets.update({'_id': doc['_id']}, {'$set': {'meta.retweeted': True}})
                time.sleep(1)

# utility functions

def make_doc(tweet, retweeted=False):
    doc = dict()
    doc['_id'] = tweet.id
    doc['meta'] = {'time': tweet.created_at, 'retweeted': retweeted}
    doc['data'] = tweet._json
    return doc

def add_collection(tweet, retweeted=False):
    doc = make_doc(tweet, retweeted)
    return c.tweets.update({'_id': doc['_id']}, doc, upsert=True)
    
def print_tweet(t):
    if type(t) is dict:
        tweet_url = 'https://twitter.com/{name}/status/{id}'.format(
            name=t['data']['user']['screen_name'],
            id=t['_id'],
        )
        if t['meta']['retweeted']:
            retweeted = ' *'
        else:
            retweeted = ''
        print(t['meta']['time'], '/ ♡ {} ↻ {}{retweeted} / {}'.format(
            t['data']['favorite_count'],
            t['data']['retweet_count'],
            tweet_url,
            retweeted=retweeted,
        ))
        print('{}(@{})'.format(t['data']['user']['name'], t['data']['user']['screen_name']))
        print(t['data']['text'])
        print('-' * 8)
    else:
        tweet_url = 'https://twitter.com/{name}/status/{id}'.format(
            name=t.user.screen_name,
            id=t.id,
        )
        print(t.created_at, '/ ♡ {} ↻ {} /'.format(t.favorite_count, t.retweet_count), tweet_url)
        print('{}(@{})'.format(t.user.name, t.user.screen_name))
        print(t.text)
        print('-' * 8)

def get_retweet_target_accounts():
    return sorted(c.tweets.distinct('data.user.screen_name'))

def get_following_accounts():
    return [u.screen_name for u in api.me().friends()]

def follow_retweet_target_accounts():
    accounts = set(get_retweet_target_accounts()) - set(get_following_accounts())
    for account in accounts:
        api.create_friendship(screen_name=account)        

def get_all_tweets(screen_name):
    ts = []
    for t in tweepy.Cursor(api.user_timeline, screen_name=screen_name, count=200).items():
        ts.append(t)
    return ts

def get_all_tweets_from_collection(screen_name):
    return [t for t in c.tweets.find({'data.user.screen_name': screen_name}).sort('_id')]

def is_retweeted(tweet):
    if type(tweet) is tweepy.Status:
        return 'retweeted_status' in tweet._json
    elif type(tweet) is dict:
        return 'retweeted_status' in tweet['data']

def in_regex_text(regex_text):
    def in_text(tweet):
        regex = re.compile(regex_text)
        if type(tweet) is dict:
            return regex.search(tweet['data']['text'])
        elif type(tweet) is tweepy.Status:
            return regex.search(tweet.text)
    return in_text

in_kinpri_text = in_regex_text(r'KING OF PRISM|キンプリ|キング・?オブ・?プリズム|#kinpri')
in_pretty_text = in_regex_text(r'プリティーリズム|プリリズ')

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
    return c.items.find({'date': {'$gte': start_date, '$lte': end_date}, 'date_extra': None})

if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser()

    # for debug
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--debug_retweet', action='store_true')
    
    parser.add_argument('command', type=str, choices=[
        'tweet_today', 'print_today',
        'tweet_tomorrow', 'print_tomorrow',
        'tweet_date', 'print_date',
        'retweet', 'follow',
    ])
    parser.add_argument('--date')
    parser.add_argument('--delta', type=int, default=1)
    parser.add_argument('--screen_names', nargs='+')    # for retweet

    args = parser.parse_args()
     
    # prepare database
    c = MongoClient().kinpri_goods_wiki
     
    # get tweepy api
    if args.debug:
        api = get_api('sakuramochi_pre')
    else:
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
    
    elif args.command == 'retweet':
        if args.screen_names:
            screen_names = args.screen_names
        else:
            with open('retweet_target_screen_names.txt') as f:
                screen_names = f.read().strip().split()

        for screen_name in screen_names:
            retweet_user(screen_name)

    elif args.command == 'follow':
        follow_retweet_target_accounts()

else:
    c = MongoClient().kinpri_goods_wiki
    api = get_api('sakuramochi_pre')
