#!/usr/bin/env python3
from __future__ import annotations
import io,json,re,zipfile
from pathlib import Path
from urllib.parse import urljoin
import requests

TARGETS={
 'Martin':'https://results.enr.clarityelections.com/FL/Martin/126768/web.345435/#/summary',
 'Osceola':'https://results.enr.clarityelections.com/FL/Osceola/126781/web.345435/#/summary',
 'Pinellas':'https://enr.votepinellas.gov/FL/Pinellas/126780/web.345435/#/summary',
}
HEADERS={'User-Agent':'Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)'}

def root(url):
    clean=url.split('#',1)[0]
    m=re.search(r'^(.*?/\d{3,9}/)',clean)
    if not m: raise ValueError(f'cannot derive election root: {url}')
    return m.group(1)

def main():
    out=[]
    for county,url in TARGETS.items():
        base=root(url)
        checks=[]
        for rel in ['json/en/summary.json','json/en/election.json','json/en/contests.json','json/en/results.json','reports/detailxml.zip','reports/detailxml.xml','detailxml.zip']:
            ep=urljoin(base,rel)
            try:
                r=requests.get(ep,headers=HEADERS,timeout=25)
                item={'url':ep,'status':r.status_code,'contentType':r.headers.get('content-type',''),'bytes':len(r.content)}
                if r.ok:
                    if r.content[:2]==b'PK':
                        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                            item['zipMembers']=[{'name':i.filename,'bytes':i.file_size} for i in z.infolist()[:20]]
                    else:
                        item['sample']=r.text[:5000]
                checks.append(item)
            except Exception as e:
                checks.append({'url':ep,'error':str(e)})
        out.append({'county':county,'sourceUrl':url,'root':base,'checks':checks})
    payload={'status':'complete','counties':out}
    p=Path('validation-output/clarity-probe-v2.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(payload,indent=2)+'\n')
    print('Probed',len(out),'Clarity counties')
if __name__=='__main__': main()

# trigger v2
