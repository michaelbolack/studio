#!/usr/bin/env python3
# isolated source-structure diagnostic; no production writes
import json,requests,re
from pathlib import Path
from bs4 import BeautifulSoup
URL='https://www.livevoterturnout.com/ENR/semflenr/21/en/Index_21.html'
r=requests.get(URL,timeout=30,headers={'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
r.raise_for_status()
soup=BeautifulSoup(r.text,'html.parser')
out={'url':URL,'status':r.status_code,'bytes':len(r.content),'title':soup.title.get_text(' ',strip=True) if soup.title else None,'headings':[],'tables':[]}
for h in soup.find_all(re.compile('^h[1-6]$')):
    out['headings'].append({'tag':h.name,'text':' '.join(h.stripped_strings)})
for i,t in enumerate(soup.find_all('table')):
    prev=[]; node=t
    for _ in range(12):
        node=node.find_previous()
        if not node: break
        if node.name in ['h1','h2','h3','h4','h5','h6','div','span','strong']:
            txt=' '.join(node.stripped_strings)
            if txt and txt not in prev: prev.append(txt[:300])
        if len(prev)>=5: break
    rows=[]
    for tr in t.find_all('tr')[:12]:
        cells=[' '.join(c.stripped_strings) for c in tr.find_all(['th','td'])]
        if cells: rows.append(cells)
    out['tables'].append({'index':i,'id':t.get('id'),'class':t.get('class'),'previousText':prev,'rows':rows})
Path('seminole-html-probe.json').write_text(json.dumps(out,indent=2)+'\n')
print('status',r.status_code,'bytes',len(r.content),'headings',len(out['headings']),'tables',len(out['tables']))
