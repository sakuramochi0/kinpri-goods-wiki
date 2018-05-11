#!/usr/bin/env python3
import argparse
import datetime
import fcntl
import re
import time

import requests
import yaml
from bs4 import BeautifulSoup
from dateutil.parser import parse
from get_mongo_client import get_mongo_client
from get_tweepy import *

from save_items import print_item


def tweet_date_items(date):
    """
    指定した日付に発売される全アイテムをツイートする
    """
    # tweet item number of the date
    num_status = make_num_status(date=date)
    if args.debug_no_tweet:
        print('status:', num_status)
    else:
        tweet(num_status)

    # tweet items
    items = get_date_items(date)
    for item in items:
        try:
            item_status = make_item_status(date=date, item=item)
            if args.debug_no_tweet:
                print('status:', item_status)
                continue
            res = tweet(item_status)
        except tweepy.TweepError as e:
            if e.api_code == 186:
                if item['maker']:
                    item['maker'] = re.sub(
                        r'\s*?[\(（].+[\)）]',
                        '',
                        item['maker']
                    ).strip()
                try:
                    print(item_status)
                    res = tweet(item_status)
                except tweepy.TweepError as e:
                    if e.api_code == 186:
                        item['name'] = re.sub(
                            r'\s*?KING OF PRISM by PrettyRhythm\s*?',
                            '',
                            item['name']
                        ).strip()
                        item_status = make_item_status(date=date, item=item)
                        try:
                            res = tweet(item_status)
                        except tweepy.TweepError as e:
                            if e.api_code == 186:
                                item['name'] = re.sub(
                                    r'\s*?KING OF PRISM\s*?',
                                    '',
                                    item['name']
                                ).strip()
                                item_status = make_item_status(date=date, item=item)
                                res = tweet(item_status)

        try:
            print('res:', res)
            api.create_favorite(id=res.id)
        except tweepy.TweepError as e:
            if e.api_code == 139:
                pass


def tweet(status):
    """
    指定したツイートテキストで、アカウントからツイートする
    """
    print('-' * 4)
    print('tweeting:')
    print(status)
    print('({})'.format(status_len(status)))
    res = api.update_status(status=status, tweet_mode='extended')
    res = assign_full_text_to_text(res)
    if not args.debug:
        time.sleep(10)
    return res


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
        status = 'みんな〜、{date_description}{date}は{num}個のグッズが発売されるみたいだぞー。これから紹介するな〜。'.format(
            date_description=get_date_description(date), date=format_date(date), num=num
        )
    else:
        future_items = c.items.find({'date': {'$gt': date}, 'date_extra': None}).sort('date')
        if future_items.count():
            next_item = future_items[0]
            next_date = next_item['date']
            next_num = c.items.find({'date': next_date, 'date_extra': None}).count()
            status = '{date_description}{date}は、特にグッズは発売されないみたいだな〜。次は{next_date_description}{next_date}に、{next_num}個のグッズが発売されるようだ。'.format(
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
    status = '{date_description}{date}は{maker}「{name}」が発売されるようだ。詳しくはこれ見とけ〜 {quote}'.format(
        date_description=get_date_description(date),
        date=format_date(date),
        maker=maker,
        name=item['name'],
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
    # get all tweets without condition
    tweets = []
    try:
        ts = api.user_timeline(screen_name=screen_name, count=200, tweet_mode='extended')
        ts = assign_full_text_to_text_list(ts)
    except tweepy.TweepError as e:
        raise
    for t in reversed(ts):
        if retweet_filter(t, screen_name):
            tweets.append(t)
    retweet_tweets(tweets)


def retweet_tweets(tweets):
    for t in tweets:
        # if new tweet, insert to database
        doc = c.tweets.find_one(t.id)
        if not doc:
            doc = make_doc(t)
            if not args.debug:
                c.tweets.insert_one(doc)

        # if not retweeted, do it and record to database
        if not doc['meta']['retweeted'] and not is_retweeted(doc):
            if args.debug:
                print('would retweeted:')
                print_tweet(doc)
                if not args.debug_no_tweet:
                    api.retweet(doc['_id'])
            else:
                try:
                    api.retweet(doc['_id'])
                except tweepy.TweepError as e:
                    if e.api_code == 327:  # already retweeted
                        pass
                    else:
                        raise
                c.tweets.update_one({'_id': doc['_id']}, {'$set': {'meta.retweeted': True}})
                set_latest_retweet_date()
                time.sleep(1)


def retweet_ids(ids):
    ts = []
    for id in ids:
        try:
            ts.append(api.get_status(id=id, tweet_mode='extended'))
        except TweepError as e:
            if e.api_code == 144:  # not found status_id
                pass
            else:
                raise
    ts = assign_full_text_to_text_list(ts)
    retweet_tweets(ts)


def retweet_filter(tweet, screen_name):
    """Return True if the tweet should be retweeted, False if not."""
    if tweet.created_at.date() < latest_retweet_date - datetime.timedelta(days=1):
        return False
    if screen_name == 'PRR_music':
        return True
    elif in_kinpri_text(tweet) or in_pretty_text(tweet):
        # return True if the tweet should be retweeted
        if screen_name == 'magazine_pash':
            return not re.search('人気記事|人気ニュース|週間リツイートランキング|RT→', tweet.text)
        elif screen_name == 'hobby_stock':
            return '【再販】' not in tweet.text
        elif screen_name in ['animate_cafe', 'animatecafe_grt']:
            return '空席分のご予約' not in tweet.text
        elif screen_name == 'Kotobukiya_akb':
            return '在庫' not in tweet.text and '入荷' not in tweet.text
        elif screen_name == 'animegainfo':
            return '開催中' not in tweet.text
        elif screen_name == 'atelieraqua':
            return '定期' not in tweet.text
        elif screen_name == 'saku_moca':
            return 'cheese' in tweet.text
        elif screen_name == 'CafeReoInc':
            return 'オードトワレ' not in tweet.text
        elif screen_name == 'anime_tsutaya':
            return '販売中' not in tweet.text
        elif screen_name == 'amiamihobbynews':
            return '女性向け' not in tweet.text
        elif screen_name == 'aniaco_info':
            return '再掲' not in tweet.text and '女性向け' not in tweet.text
        elif screen_name == 'mantanotaku':
            return 'アニメ1週間' not in tweet.text
        elif screen_name == 'ufotablecinema':
            return '上映時間' not in tweet.text
        elif screen_name == 'news_mynavi_jp':
            urls = [url['expanded_url'] for url in tweet.entities['urls']]
            url = urls[0]
            r = requests.get(url)
            r.encoding = 'utf-8'
            s = BeautifulSoup(r.text, 'lxml')
            publisher = s.select('[itemprop="publisher"]')[0]['content']
            return 'まんたん' not in publisher
        elif screen_name == 'TOWER_Shinjuku':
            return 'prince' not in tweet.text.lower()
        else:
            return True
    elif in_prismstone_text(tweet):
        return in_kinpri_text(tweet) or in_pretty_text(tweet)
    else:
        return False


def run_command_from_tos():
    ts = api.search('from:{sn} @tos'.format(sn=api.auth.username), tweet_mode='extended')
    ts = assign_full_text_to_text_list(ts)
    for t in ts:
        if t.text.startswith('@tos'):
            raw_args = t.text.replace('@tos', '').strip().split()
            parser = argparse.ArgumentParser()
            parser.add_argument('command')
            parser.add_argument('targets', nargs='+')
            args = parser.parse_args(raw_args)
            args.command = args.command.lower()
            if args.command == 'rt':
                ids = []
                urls = [url['expanded_url'] for url in t.entities['urls']]
                for url in urls:
                    m = re.search(r'(?:https?://.+/)?(\d+)', url)
                    if m:
                        ids.append(m.group(1))
                if ids:
                    retweet_ids(ids)
                t.destroy()
            elif args.command == 'follow':
                for target in args.targets:
                    try:
                        u = api.get_user(screen_name=target)
                    except tweepy.TweepError as e:
                        print('Failed to follow account from tweet command')
                        print('\tTarget account:', target)
                        print('\tError:')
                        print(e)
                    add_retweet_target_account(target)
                    print('Success to add new account to retweet target account list')
                    print('\tTarget account:', target)
                t.destroy()


# utility functions

def make_doc(tweet, retweeted=False):
    doc = dict()
    doc['_id'] = tweet.id
    doc['meta'] = {'time': tweet.created_at, 'retweeted': retweeted}
    doc['data'] = tweet._json
    return doc


def add_collection(tweet, retweeted=False):
    doc = make_doc(tweet, retweeted)
    return c.tweets.replace_one({'_id': doc['_id']}, doc, upsert=True)


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
    with open('retweet_target_screen_names.yaml') as f:
        screen_names = yaml.load(f)
    return screen_names


def add_retweet_target_account(screen_name):
    with open('retweet_target_screen_names.yaml') as f:
        fcntl.flock(f)
        screen_names = yaml.load(f)
    screen_names.append(screen_name)

    with open('retweet_target_screen_names.yaml', 'w') as f:
        fcntl.flock(f)
        yaml.dump(screen_names, f, width=5)


def remove_retweet_target_account(screen_name):
    with open('retweet_target_screen_names.yaml') as f:
        fcntl.flock(f)
        screen_names = yaml.load(f)
    screen_names.remove(screen_name)

    with open('retweet_target_screen_names.yaml', 'w') as f:
        fcntl.flock(f)
        yaml.dump(screen_names, f, width=5)


def get_latest_retweet_date():
    with open('latest_retweet_date.yaml') as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        date = yaml.load(f)
    return date


def set_latest_retweet_date():
    date = datetime.date.today() - datetime.timedelta(days=1)
    with open('latest_retweet_date.yaml', 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yaml.dump(date, f)


def get_following_accounts():
    return [u.screen_name for u in api.me().friends()]


def follow_retweet_target_accounts():
    accounts = set(get_retweet_target_accounts()) - set(get_following_accounts())
    for account in accounts:
        try:
            api.create_friendship(screen_name=account)
        except tweepy.TweepError as e:
            print(e)


def get_all_tweets(screen_name):
    ts = []
    for t in tweepy.Cursor(api.user_timeline, screen_name=screen_name, count=200, tweet_mode='extended').items():
        ts.append(t)
    ts = assign_full_text_to_text_list(ts)
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
            text = tweet['data']['text'].lower()
        elif type(tweet) is tweepy.Status:
            text = tweet.text.lower()
        return regex.search(text)

    return in_text


in_kinpri_text = in_regex_text(r'king ?of ?prism|キンプリ|キング・?オブ・?プリズム\
|kinpri|エーデルローズ|シュワルツローズ')
in_pretty_text = in_regex_text(r'プリティーリズム|プリリズ|prettyrhythm|オーロラドリーム|ディアマイフューチャー|レインボーライブ|オールフレンズ|prettyall')
in_prismstone_text = in_regex_text(r'プリズムストーン|prismstone')


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


def remove_twitter_prefix(ids):
    """Remove 'https://twitter.com/...' if exists."""
    return map(lambda x: x.split('/')[-1], ids)


def assign_full_text_to_text_list(ts):
    """Copy full_text attribute to text for tweet list."""
    ts = list(map(assign_full_text_to_text, ts))
    return ts


def assign_full_text_to_text(t: tweepy.Status):
    """Copy full_text attribute to text."""
    t.text = t.full_text
    t._json['text'] = t._json['full_text']
    return t


if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser()

    # for debug
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--debug-no-tweet', action='store_true')

    parser.add_argument('command', type=str, choices=[
        'tweet_today', 'print_today',
        'tweet_tomorrow', 'print_tomorrow',
        'tweet_date', 'print_date',
        'retweet', 'follow',
        'run_command_from_tos',
    ])
    parser.add_argument('--date')
    parser.add_argument('--delta', type=int, default=1)
    parser.add_argument('--screen_names', nargs='+')  # for retweet
    parser.add_argument('--ids', nargs='+')  # for retweet

    args = parser.parse_args()

    # prepare database
    c = get_mongo_client().kinpri_goods_wiki

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
        latest_retweet_date = get_latest_retweet_date()
        if args.ids:
            ids = remove_twitter_prefix(args.ids)
            retweet_ids(ids)
        else:
            if args.screen_names:
                screen_names = args.screen_names
            else:
                screen_names = get_retweet_target_accounts()
            for screen_name in screen_names:
                try:
                    retweet_user(screen_name)
                except tweepy.TweepError as e:
                    if e.api_code == 88:  # Rate limit exceeds
                        print('Rate limit exceeds:')
                        print(api.rate_limit_status())
                        break
                except Exception as e:
                    print('failed to get tweets:', screen_name)
                    print(api.rate_limit_status())
                    print(e)

    elif args.command == 'follow':
        follow_retweet_target_accounts()

    elif args.command == 'run_command_from_tos':
        run_command_from_tos()
else:
    c = get_mongo_client().kinpri_goods_wiki
    api = get_api('sakuramochi_pre')
