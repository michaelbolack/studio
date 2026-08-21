#!/usr/bin/env python3
import json, requests, re
from pathlib import Path
from bs4 import BeautifulSoup
URL='https://enrarchive.electionsfl.org/OKA/4026/Summary/'
r=requests.get(URL,timeout=35,headers={'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
text=' '.join(soup.stripped_strings)
tables=[]
for t in soup.find_all('table'):
    headers=[' '.join(x.stripped_strings) for x in t.find_all('th')]
    rows=[]
    for tr in t.find_all('tr')[:8]:
        cells=[' '.join(c.stripped_strings) for c in tr.find_all(['th','td'])]
        if cells: rows.append(cells)
    tables.append({'headers':headers,'rows':rows})
result={
  'url':URL,'status':r.status_code,'bytes':len(r.content),
  'textSample':text[:8000],
  'precinctMatches':re.findall(r'Precincts Reporting:\s*\d+\s*/\s*\d+',text,re.I),
  'tableCount':len(tables),'tables':tables[:20]
}
Path('okaloosa-voterfocus-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
