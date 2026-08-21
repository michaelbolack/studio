#!/usr/bin/env python3
# isolated source discovery; no production writes
import json,requests,time
from pathlib import Path
from bs4 import BeautifulSoup

s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0'})
results=[]
for eid in range(151,221):
    url=f'https://www.voterfocus.com/enr_php/enrstaticarchive.php?county=okaloosa&election={eid}&hideall=Y'
    try:
        r=s.get(url,timeout=12)
        soup=BeautifulSoup(r.text,'html.parser')
        text=' '.join(soup.stripped_strings)
        missing='parameters provided do not match' in text.lower()
        if not missing:
            results.append({'electionId':eid,'status':r.status_code,'bytes':len(r.content),'sample':text[:1800],'links':[{'text':' '.join(a.stripped_strings),'href':a.get('href')} for a in soup.find_all('a') if a.get('href')][:30]})
    except Exception as e:
        results.append({'electionId':eid,'error':repr(e)})
    time.sleep(.05)
Path('okaloosa-voterfocus-probe.json').write_text(json.dumps({'range':'151-220','matches':results},indent=2)+'\n')
print(json.dumps({'range':'151-220','matches':results},indent=2))
