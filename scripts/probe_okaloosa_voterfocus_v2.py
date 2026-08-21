#!/usr/bin/env python3
import json, requests
from pathlib import Path
from bs4 import BeautifulSoup

URL='https://www.voterfocus.com/enr_php/enrarchive.php?county=okaloosa&election='
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
r=s.get(URL,timeout=20); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
options=[{'text':' '.join(o.stripped_strings),'value':(o.get('value') or '').strip()} for o in soup.find_all('option')]
match=next((o for o in options if '2026' in o['text'] and 'primary' in o['text'].lower()),None)
forms=[]
for f in soup.find_all('form'):
    forms.append({
      'action':f.get('action'),'method':f.get('method'),
      'html':str(f)[:12000],
      'inputs':[{'name':i.get('name'),'value':i.get('value'),'type':i.get('type'),'onclick':i.get('onclick')} for i in f.find_all(['input','button','select'])]
    })
scripts=[]
for sc in soup.find_all('script'):
    txt=sc.get_text('\n',strip=True)
    if txt: scripts.append(txt[:15000])
result={'url':URL,'selected':match,'forms':forms,'scripts':scripts,'html':r.text[:30000]}
Path('okaloosa-voterfocus-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'selected':match,'forms':forms,'scripts':scripts},indent=2))
if not match: raise SystemExit('2026 Primary option missing')
