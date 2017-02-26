import datetime
from dateutil.parser import parse
from urllib.parse import unquote
from get_mongo_client import get_mongo_client

cli = get_mongo_client()
c = cli.kinpri_goods_wiki.items

for i in c.find({'date': {'$gte': parse('2015-1-1')}}).sort('date'):
    if i['date_extra']:
        date = i['date'].strftime('%m月{}旬'.format(i['date_extra']))
    else:
        date = i['date'].strftime('%m月%d日')
    name = i['name'].replace('KING OF PRISM by PrettyRhythm', '').replace('KING OF PRISM', '').strip()
    page = unquote(i['url'].split('/')[-1], encoding='euc-jp')
    print('| {} | [[{}>{}]] |  |'.format(date, name, page))
