#!/usr/bin/env python3
# isolated source discovery; no production writes
import json, requests
from pathlib import Path
from bs4 import BeautifulSoup

ARCHIVE='https://www.voterfocus.com/enr_php/enrarchive.php?county=okaloosa&election='
STATIC='https://www.voterfocus.com/enr_php/enrstaticarchive.php?county=OKA&election=4026'
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})

r=s.get(ARCHIVE,timeout=20); r.raise_for_status()
soup=BeautifulSoup(r.text,'html.parser')
options=[{'text':' '.join(o.stripped_strings),'value':(o.get('value') or '').strip()} for o in soup.find_all('option')]
match=next((o for o in options if '2026' in o['text'] and 'primary' in o['text'].lower()),None)

rr=s.get(STATIC,timeout=20); rr.raise_for_status()
ss=BeautifulSoup(rr.text,'html.parser')
result={
  'archiveUrl':ARCHIVE,
  'selected':match,
  'staticUrl':STATIC,
  'staticStatus':rr.status_code,
  'staticBytes':len(rr.content),
  'staticText':' '.join(ss.stripped_strings)[:12000],
  'tables':[],
  'links':[{'text':' '.join(a.stripped_strings),'href':a.get('href')} for a in ss.find_all('a') if a.get('href')][:100]
}
for idx,t in enumerate(ss.find_all('table')):
    rows=[]
    for tr in t.find_all('tr'):
        cells=[' '.join(c.stripped_strings) for c in tr.find_all(['th','td'])]
        if cells: rows.append(cells)
    if rows: result['tables'].append({'index':idx,'rows':rows[:80]})
Path('okaloosa-voterfocus-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'selected':match,'staticStatus':rr.status_code,'staticBytes':len(rr.content),'tableCount':len(result['tables']),'sample':result['staticText'][:3000]},indent=2))
if not match or match.get('value')!='OKA|4026': raise SystemExit('Unexpected selector value')
if 'parameters provided do not match' in result['staticText'].lower(): raise SystemExit('Static archive rejected OKA/4026')
