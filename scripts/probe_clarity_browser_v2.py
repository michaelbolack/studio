#!/usr/bin/env python3
import json, re, time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

COUNTIES = {
    'Martin': 'https://results.enr.clarityelections.com/FL/Martin/126768/web.345435/#/summary',
    'Osceola': 'https://results.enr.clarityelections.com/FL/Osceola/126781/web.345435/#/summary',
    'Pinellas': 'https://enr.votepinellas.gov/FL/Pinellas/126780/web.345435/#/summary',
}

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--window-size=1600,1200')
opts.add_argument('--disable-gpu')
opts.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})

out = {}
for county, url in COUNTIES.items():
    d = None
    try:
        d = webdriver.Chrome(options=opts)
        d.set_page_load_timeout(45)
        d.get(url)
        time.sleep(8)
        title = d.title
        text = d.find_element('tag name', 'body').text
        logs = d.get_log('performance')
        urls = []
        for entry in logs:
            try:
                msg = json.loads(entry['message'])['message']
                if msg.get('method') != 'Network.responseReceived':
                    continue
                u = msg['params']['response']['url']
                if any(k in u.lower() for k in ('current_ver','/json/','detailxml','/reports/')) or re.search(r'/\d{5,12}/(?:json|reports)/', u, re.I):
                    urls.append({'url':u,'status':msg['params']['response'].get('status'),'mime':msg['params']['response'].get('mimeType')})
            except Exception:
                pass
        # capture all same-election URLs with a numeric publication segment as a secondary discovery signal
        allurls=[]
        for entry in logs:
            try:
                msg=json.loads(entry['message'])['message']
                if msg.get('method')=='Network.responseReceived':
                    u=msg['params']['response']['url']
                    if any(eid in u for eid in ('126768','126781','126780')):
                        allurls.append(u)
            except Exception: pass
        versions=sorted(set(re.findall(r'/(\d{5,12})/(?:json|reports|Web\d+|web\.)', '\n'.join(allurls), re.I)))
        out[county]={'ok':True,'title':title,'currentUrl':d.current_url,'bodySample':text[:5000],'interestingResponses':urls[:200],'publicationVersions':versions,'electionUrls':list(dict.fromkeys(allurls))[:300]}
    except Exception as e:
        out[county]={'ok':False,'error':repr(e)}
        if d:
            try:
                out[county]['title']=d.title
                out[county]['currentUrl']=d.current_url
                out[county]['bodySample']=d.find_element('tag name','body').text[:5000]
            except Exception: pass
    finally:
        if d:
            try:d.quit()
            except Exception:pass

Path('clarity-browser-probe.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
