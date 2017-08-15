#!/usr/bin/env python3
from bs4 import BeautifulSoup; import requests
from urllib.parse import urljoin
import re
from jinja2 import Template

base_url = 'http://www.movic.jp/shop/genre/genre.aspx?genre=100727&utm_content=buffer1a28f&utm_medium=social&utm_source=tw&utm_campaign=mv'

template = Template('''*** {{name}}
発売元：ムービック
** 仕様
- 発売日：{{date}}
- 価格：{{price}}
- {{description}}
&twitter()

**関連ツイート

**登場キャラクター
|Over the Rainbow|コウジ、ヒロ、カヅキ|
|エーデルローズ生|シン、ユキノジョウ、カケル、タイガ、レオ、ユウ、ミナト|
|シュワルツローズ生|ルヰ、アレクサンダー|

**取り扱い店舗
|ムービック通販|{{url}}|
|アニメイト||
その他アニメグッズ店舗情報があれば追記お願いします。

**参照・関連情報

ムービック コウジ ヒロ カヅキ シン ユキノジョウ カケル タイガ レオ ユウ ミナト ルヰ アレクサンダー ジョージ
''')

def goods_wiki(url, s):
    return dict(
    name = s.select('.goods_name_')[0].text.replace('\u3000', ' '),
    price = re.search(r'([\d,]+円)', s.select('.price_')[0].text.strip()).group(1) + '＋税',
    date = (s.select('#spec_release_comment') or s.select('#spec_release_dt'))[0].text,
    description = s.select('.goodscomment4_')[0].text.replace('\u3000', ' '),
    url = url,
    )

r = requests.get(base_url)
soup = BeautifulSoup(r.text, 'lxml')
goods = soup.select('a.goods_name_')

for g in goods:
    url = urljoin(base_url, g['href'])
    r = requests.get(url)
    s = BeautifulSoup(r.text, 'lxml')
    d = goods_wiki(url, s)
    print('-' * 40)
    print(d['name'], url)
    input()
    print(template.render(d))
