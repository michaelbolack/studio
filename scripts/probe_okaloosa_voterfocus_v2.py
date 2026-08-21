#!/usr/bin/env python3
# isolated source discovery; no production writes
import json, requests
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE='https://www.voterfocus.com/enr_php/enrarchive.php?county=okaloosa&election='
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
r=s.get(BASE,timeout=20); r.raise_for_status()
soup=BeautifulSoup(r.text,'html.parser')
options=[]
for opt in soup.find_all('option'):
    text=' '.join(opt.stripped_strings)
    value=(opt.get('value') or '').strip()
    options.append({'text':text,'value':value})

match=next((o for o in options if '2026' in o['text'] and 'primary' in o['text'].lower()),None)
result={'archiveUrl':BASE,'options':options,'selected':match}
if match and match['value']:
    selected_url=urljoin(BASE, match['value']) if match['value'].startswith(('http://','https://','/')) else f'https://www.voterfocus.com/enr_php/enrarchive.php?county=okaloosa&election={match["value"]}'
    rr=s.get(selected_url,timeout=20); rr.raise_for_status()
    ss=BeautifulSoup(rr.text,'html.parser')
    result['selectedUrl']=selected_url
    result['status']=rr.status_code
    result['bytes']=len(rr.content)
    result['textSample']=' '.join(ss.stripped_strings)[:5000]
    result['iframes']=[{'src':i.get('src')} for i in ss.find_all('iframe') if i.get('src')]
    result['links']=[{'text':' '.join(a.stripped_strings),'href':a.get('href')} for a in ss.find_all('a') if a.get('href')][:100]
Path('okaloosa-voterfocus-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not match:
    raise SystemExit('2026 Primary Election option not found')
