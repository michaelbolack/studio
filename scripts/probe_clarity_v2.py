#!/usr/bin/env python3
from __future__ import annotations
import json,re,time
from pathlib import Path
from urllib.parse import urljoin
import requests

TARGETS={
 'Martin':'https://results.enr.clarityelections.com/FL/Martin/126768/web.345435/#/summary',
 'Osceola':'https://results.enr.clarityelections.com/FL/Osceola/126781/web.345435/#/summary',
 'Pinellas':'https://enr.votepinellas.gov/FL/Pinellas/126780/web.345435/#/summary',
}
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)','Accept':'application/json,application/xml,text/xml,*/*'}

def bases(url):
    clean=url.split('#',1)[0]
    build=clean if clean.endswith('/') else clean+'/'
    m=re.search(r'^(.*?/\d{3,9}/)',clean)
    if not m: raise ValueError(f'cannot derive election root: {url}')
    return [('build',build),('root',m.group(1))]

def poll(url):
    attempts=[]
    s=requests.Session();s.headers.update(HEADERS)
    for i in range(5):
        r=s.get(url,timeout=25)
        attempts.append({'attempt':i+1,'status':r.status_code,'bytes':len(r.content),'contentType':r.headers.get('content-type',''),'location':r.headers.get('location'),'retryAfter':r.headers.get('retry-after')})
        if r.content:
            return attempts,r.content[:5000].decode('utf-8','replace')
        time.sleep(2)
    return attempts,''

def main():
    out=[]
    rels=['json/en/summary.json','reports/detailxml.zip']
    for county,url in TARGETS.items():
        checks=[]
        for kind,base in bases(url):
            for rel in rels:
                ep=urljoin(base,rel)
                try:
                    attempts,sample=poll(ep)
                    checks.append({'baseKind':kind,'url':ep,'attempts':attempts,'sample':sample})
                except Exception as e:
                    checks.append({'baseKind':kind,'url':ep,'error':str(e)})
        out.append({'county':county,'sourceUrl':url,'checks':checks})
    p=Path('validation-output/clarity-probe-v2.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'status':'complete','mode':'poll-202','counties':out},indent=2)+'\n')
    print('Polled',len(out),'Clarity counties')
if __name__=='__main__': main()
