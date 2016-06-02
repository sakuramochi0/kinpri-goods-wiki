#!/usr/bin/env python3
import datetime
from pymongo.mongo_client import MongoClient
from icalendar import Calendar, Event

cli = MongoClient()
c = cli.kinpri_goods_wiki.items

cal = Calendar()
for i in c.find():
    e = Event()
    if i['date']:
        date = i['date'].date()

        # date_extra
        if i['date_extra']:
            if i['date_extra'] == '月':
                day = 1
                date_extra_description = '※この商品の発売日は{month}月となっています。\n'.format(
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
                    date_extra_description = '※この商品の発売日は{month}月{extra}旬となっています。\n'.format(
                        month=date.month,
                        extra=i['date_extra'],
                    )
        else:
            day = date.day
            date_extra_description = ''

        date = datetime.date(date.year, date.month, day)
        
        e.add('dtstart', date)
        e.add('summary', '[発売日] ' + i['name'])
        e.add('description', '{date_extra_description}発売元: {maker}\nWiki: {url}'.format(
            maker=i['maker'],
            url=i['url'],
            date_extra_description=date_extra_description,
        ))
        cal.add_component(e)

with open('calendar.ics', 'wb') as f:
    f.write(cal.to_ical())

