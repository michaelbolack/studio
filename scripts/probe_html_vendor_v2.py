#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

TARGETS={
 'Broward':'https://results.browardvotes.gov/ENR/browardflenr/239/en/Index_239.html',
 'Seminole':'https://www.livevoterturnout.com/ENR/semflenr/21/en/Index_21.html',
}
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)'}
def clean(x): return re.sub(r'\s+',' ',x or '').strip()
def main():
    counties=[]
    for county,url in TARGETS.items():
        r=requests.get(url,headers=HEADERS,timeout=35);r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser')
        races=[]
        for table in soup.find_all('table'):
            txt=clean(table.get_text(' ',strip=True));low=txt.lower()
            if 'candidate name' not in low or 'total percentage' not in low: continue
            rows=[]
            for tr in table.find_all('tr')[:12]:
                cells=[clean(c.get_text(' ',strip=True)) for c in tr.find_all(['th','td'])]
                if cells: rows.append(cells)
            prev=table.find_previous(['h1','h2','h3','h4','h5','h6'])
            heading=clean(prev.get_text(' ',strip=True)) if prev else ''
            races.append({'heading':heading,'rows':rows,'tableText':txt[:2500]})
            if len(races)>=40: break
        page=clean(soup.get_text(' ',strip=True))
        counties.append({'county':county,'url':url,'status':r.status_code,'bytes':len(r.content),'raceTables':len(races),'pageSignals':page[:4000],'races':races[:25]})
    p=Path('validation-output/html-vendor-probe-v2.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'status':'complete','counties':counties},indent=2)+'\n')
    print('HTML vendor probe complete')
if __name__=='__main__':main()

# trigger v2
