#!/usr/bin/env python3
import datetime
from get_mongo_client import get_mongo_client
from icalendar import Calendar, Event

cli = get_mongo_client()
c = cli.kinpri_goods_wiki.items

cal = Calendar()
cal['summary'] = 'プリリズ＆キンプリ グッズ発売日カレンダー'
cal['description'] = '''詳細はこちらのサイトをご覧ください！
https://skrm.ch/prettyrhythm/calendar/'''
for i in c.find():
    e = Event()
    if not i['date']:
        continue
    date = i['date'].date()

    # date_extra
    if i['date_extra']:
        if i['date_extra'] == '月':
            day = 1
            date_extra_description = '※この商品の発売日は、この日ではなく、{month}月中となっています。\n'.format(
                month=date.month,
                extra=i['date_extra'],
            )
        else:
            if i['date_extra'] == '上':
                day = 1
            elif i['date_extra'] == '中':
                day = 10
            elif i['date_extra'] == '下':
                day = 20
            date_extra_description = '※この商品の発売日は、この日ではなく、{month}月{extra}旬となっています。\n'.format(
                month=date.month,
                extra=i['date_extra'],
            )
    else:
        day = date.day
        date_extra_description = ''

    date = datetime.date(date.year, date.month, day)
    
    tags = ' '.join(i['tags'])
    summary = '[発売日]'
    if '雑誌' in tags:
        summary += '[雑誌]'
    elif 'コミックス' in tags or 'アンソロジー' in tags:
        summary += '[コミックス]'
    elif '映像' in tags:
        summary += '[DVD]'
    elif '円盤' in tags:
        summary += '[CD]'
    elif 'プリティーリズム' in tags:
        summary += '[プリティーリズム]'
    else:
        summary = ''
    summary += ' ' + i['name']
        
    description = '''{date_extra_description}発売元: {maker}
タグ: {tags}
Wiki: {url}'''.format(
    maker=i['maker'],
    tags=tags,
    url=i['url'],
    date_extra_description=date_extra_description,
)
    e.add('dtstart', date)
    e.add('summary', summary)
    e.add('description', description)
    cal.add_component(e)

with open('kinpri-goods-wiki.ics', 'wb') as f:
    f.write(cal.to_ical())

