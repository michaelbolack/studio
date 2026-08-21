#!/usr/bin/env python3
import json,re,requests
from pathlib import Path
from bs4 import BeautifulSoup

urls=[
 'https://www.voterfocus.com/enr_php/enrstaticarchive.php?county=okaloosa&election=192&hideall=Y',
 'https://www.voterfocus.com/enr_php/enrstaticarchive.php?county=okaloosa&election=192',
]
out=[]
for url in urls:
    try:
        r=requests.get(url,timeout=25,headers={'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
        soup=BeautifulSoup(r.text,'html.parser')
        text=' '.join(soup.stripped_strings)
        links=[{'text':' '.join(a.stripped_strings),'href':a.get('href')} for a in soup.find_all('a') if a.get('href')]
        out.append({'url':url,'status':r.status_code,'bytes':len(r.content),'title':soup.title.get_text(' ',strip=True) if soup.title else None,'sample':text[:3000],'links':links[:100]})
    except Exception as e:
        out.append({'url':url,'error':repr(e)})
Path('okaloosa-voterfocus-probe.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
