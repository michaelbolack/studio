#!/usr/bin/env python3
import json, requests
from pathlib import Path
base='https://results.enr.clarityelections.com/FL/Martin/126768/current_ver/'
paths=['reports/summary.csv','reports/detailxml.zip','reports/detailxls.zip','reports/detailtxt.zip','json/en/summary.json']
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 IRC-Media-Election-Center/2.0','Referer':'https://www.martinvotes.gov/'})
out=[]
for p in paths:
    url=base+p
    try:
        r=s.get(url,timeout=25,allow_redirects=True)
        out.append({'path':p,'status':r.status_code,'finalUrl':r.url,'contentType':r.headers.get('content-type'),'bytes':len(r.content),'sample':r.text[:500] if 'text' in (r.headers.get('content-type') or '') or 'json' in (r.headers.get('content-type') or '') else None})
    except Exception as e:
        out.append({'path':p,'error':repr(e)})
Path('martin-current-ver-probe.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
