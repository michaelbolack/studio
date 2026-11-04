"""Independent General watch collector. Never mutates archived or legacy result files."""
import argparse,csv,hashlib,io,json,re,urllib.request
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STATE_URL='https://flelectionfiles.floridados.gov/enightfilespublic/20261103_ElecResultsFL.txt'
RELEASE=datetime(2026,11,4,1,tzinfo=timezone.utc)
IDENTITY=['ElectionDate','RaceCode','RaceName','CountyCode','CountyName','Juris1num','Juris2num','PartyCode','CanNameLast','CanNameFirst','CanNameMiddle']
STATE_CODES={'USS','GOV','ATG','CFO','AGR','AMD','SCJ'}

def rows_from(text):
 reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),delimiter='\t')
 if not set(IDENTITY+['Precincts','PrecinctsReporting','CanVotes']).issubset(reader.fieldnames or []):raise ValueError('Wrong state file header')
 rows=list(reader)
 if not rows:raise ValueError('Empty state file')
 for r in rows:
  if r['ElectionDate']!='11/03/2026' or None in r or any(r[k] is None for k in IDENTITY):raise ValueError('Wrong or truncated election file')
 return rows

def identity_digest(text):
 ids=[tuple(r[k].strip() for k in IDENTITY) for r in rows_from(text)]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate result row')
 return hashlib.sha256(json.dumps(sorted(ids),ensure_ascii=True).encode()).hexdigest()

def count(s):
 s=s.strip()
 if not re.fullmatch(r'\d+',s):raise ValueError('Invalid nonnegative integer')
 return int(s)

def candidate_name(r):
 return ' '.join(r[k].strip() for k in ['CanNameFirst','CanNameMiddle','CanNameLast'] if r[k].strip())

def build_state_snapshot(text,expected_digest,now):
 if identity_digest(text)!=expected_digest:raise ValueError('Candidate/county coverage changed or file incomplete')
 rows=rows_from(text);groups=defaultdict(list)
 for r in rows:
  r['_votes']=count(r['CanVotes']);r['_precincts']=count(r['Precincts']);r['_reporting']=count(r['PrecinctsReporting'])
  if r['_reporting']>r['_precincts']:raise ValueError('Invalid reporting count')
  key=(r['RaceCode'],r['RaceName'].strip(),r['Juris1num'].strip(),r['Juris2num'].strip())
  if r['RaceCode'] in STATE_CODES:groups[('florida',key)].append(r)
  if r['CountyCode']=='IND':groups[('indian-river',key)].append(r)
  if r['CountyCode']=='IND' and r['RaceCode'] not in STATE_CODES:groups[('district',key)] # populate below
 for (scope,key),g in list(groups.items()):
  if scope=='district':groups[(scope,key)]=[r for r in rows if (r['RaceCode'],r['RaceName'].strip(),r['Juris1num'].strip(),r['Juris2num'].strip())==key]
 races=[]
 for (scope,key),g in groups.items():
  candidates=defaultdict(int);precincts={}
  for r in g:
   candidates[(candidate_name(r),r['PartyCode'].strip())]+=r['_votes']
   counts=(r['_precincts'],r['_reporting'])
   if r['CountyCode'] in precincts and precincts[r['CountyCode']]!=counts:raise ValueError('Inconsistent precinct totals')
   precincts[r['CountyCode']]=counts
  total=sum(candidates.values());released=now>=RELEASE
  race_id=hashlib.sha256(json.dumps([scope,key]).encode()).hexdigest()[:16]
  races.append({'id':race_id,'scope':scope,'name':key[1],'status':'unofficial' if released and total else 'pending','totalVotes':total if released else None,
   'candidates':[{'name':n,'party':p,'votes':v if released else None,'percent':round(v/total*100,2) if released and total else None} for (n,p),v in candidates.items()],
   'precincts':sum(x[0] for x in precincts.values()),'precinctsReporting':sum(x[1] for x in precincts.values()) if released else None,'countiesIncluded':len(precincts),
   'sourceUrl':'https://floridaelectionwatch.gov/TrackCounty/IND' if scope=='indian-river' else 'https://floridaelectionwatch.gov/'})
 if not any(r['scope']=='indian-river' for r in races):raise ValueError('Indian River coverage missing')
 return {'electionId':'2026-fl-general','electionDate':'2026-11-03','fetchedAt':now.isoformat(),'status':'unofficial' if any(r['status']=='unofficial' for r in races) else 'pending','races':races}

def collect_source(fetch,previous,now):
 try:return fetch(),{'status':'ok','checkedAt':now.isoformat()}
 except Exception as e:return previous,{'status':'error','checkedAt':now.isoformat(),'message':str(e)[:240]}

def download(url):
 r=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'IRC-Media-Election-Center/1.0'}),timeout=30)
 if r.geturl()!=url:raise ValueError('Unexpected source redirect')
 return r.read().decode('utf-8-sig'),r.headers.get('Last-Modified')

def write_json(path,value):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)

COUNTY_URL='https://enr.electionsfl.org/IND/4096/Summary/'
LOCAL_RELEASE=datetime(2026,11,4,0,tzinfo=timezone.utc)
def clean_html(text):
 import html
 return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>',' ',text))).strip()

def parse_county(text):
 from zoneinfo import ZoneInfo
 if not re.search(r'Election Date:\s*11/3/2026',text) or 'Official General Election' not in text:raise ValueError('Wrong county election')
 m=re.search(r'Website last updated at:\s*([^<)]+)',text)
 if not m:raise ValueError('County update time missing')
 updated=datetime.strptime(m[1].strip(),'%m/%d/%Y %I:%M:%S %p').replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
 blocks=re.split(r'<div\s+id="(\d+)"\s+class="Race row">',text)
 races=[]
 for i in range(1,len(blocks),2):
  raceid,block=blocks[i:i+2]
  name=re.search(r'<label>(.*?)</label>',block,re.S)
  table=re.search(r'<table class="DetailResults"[^>]*>(.*?)</table>',block,re.S)
  if not name or not table:raise ValueError('County race structure incomplete')
  candidates=[]
  for row in re.findall(r'<tr[^>]*>(.*?)</tr>',table[1],re.S):
   choice=re.search(r'<td class="ChoiceColumn"[^>]*>(.*?)</td>',row,re.S)
   votes=re.search(r'<td class="[^"]*\bTotalVotes\b[^"]*"[^>]*>(.*?)</td>',row,re.S)
   if choice:
    if not votes:raise ValueError('County candidate votes missing')
    label=clean_html(choice[1]);party='NON'
    suffix=re.search(r'\s*\((REP|DEM|NPA|LPF|WRI|NON)\)\s*$',label)
    if suffix:party=suffix[1];label=label[:suffix.start()].strip()
    candidates.append({'name':label,'party':party,'votes':count(clean_html(votes[1]).replace(',',''))})
  if len(candidates)<2 or len({(c['name'],c['party']) for c in candidates})!=len(candidates):raise ValueError('Incomplete/duplicate county candidates')
  reported=re.search(r'class="numPrecinctsReported">(\d+)</span>',block)
  precincts=re.search(r'class="numPrecinctsParticipating">(\d+)</span>',block)
  if not reported or not precincts or int(reported[1])>int(precincts[1]):raise ValueError('County precinct counts invalid')
  vote_for=re.search(r'\(Vote For (\d+)\)',block)
  races.append({'id':'local-'+raceid,'scope':'local','name':clean_html(name[1]),'candidates':candidates,'precincts':int(precincts[1]),'precinctsReporting':int(reported[1]),'voteFor':int(vote_for[1]) if vote_for else 1,'sourceUrl':COUNTY_URL})
 if not races:raise ValueError('No county races')
 identity=[(r['id'],r['name'],r['voteFor'],[(c['name'],c['party']) for c in r['candidates']]) for r in races]
 return identity,races,updated

def build_county_snapshot(text,expected_identity,now):
 identity,races,updated=parse_county(text)
 # JSON roundtrip normalizes tuples for a stable stored contract.
 if json.loads(json.dumps(identity))!=json.loads(json.dumps(expected_identity)):raise ValueError('County candidate roster changed or missing races')
 if updated>now:raise ValueError('County update timestamp is in the future')
 released=now>=LOCAL_RELEASE and updated>=LOCAL_RELEASE
 for r in races:
  total=sum(c['votes'] for c in r['candidates'])
  r['totalVotes']=total if released else None;r['status']='unofficial' if released and total else 'pending'
  for c in r['candidates']:c['percent']=round(c['votes']/total*100,2) if total and released else None;c['votes']=c['votes'] if released else None
  if not released:r['precinctsReporting']=None
 return {'electionId':'2026-fl-general','electionDate':'2026-11-03','fetchedAt':now.isoformat(),'sourceModifiedAt':updated.isoformat(),'status':'unofficial' if any(r['status']=='unofficial' for r in races) else 'pending','races':races}


def overlay_official_headlines(races, now):
 path=ROOT/'data/official-headline-results.json'
 if not path.exists():
  return races
 try:
  data=json.loads(path.read_text())
 except Exception:
  return races
 if data.get('electionDate')!='2026-11-03' or not isinstance(data.get('races'),list):
  return races
 official=[r for r in data['races'] if r.get('status')=='unofficial' and int(r.get('totalVotes') or 0)>0]
 if not official:
  return races
 replace_keys={(r.get('scope'),r.get('name')) for r in official}
 kept=[r for r in races if (r.get('scope'),r.get('name')) not in replace_keys]
 normalized=[]
 for r in official:
  normalized.append({
   'id':'official-'+hashlib.sha256(json.dumps([r.get('scope'),r.get('name')]).encode()).hexdigest()[:12],
   'scope':r.get('scope'),
   'name':r.get('name'),
   'status':'unofficial',
   'totalVotes':int(r.get('totalVotes') or 0),
   'candidates':[{
    'name':c.get('name') or '',
    'party':c.get('party') or 'NON',
    'votes':int(c.get('votes') or 0),
    'percent':float(c.get('percent') or 0)
   } for c in (r.get('candidates') or [])],
   'precincts':None,
   'precinctsReporting':None,
   'countiesIncluded':r.get('countiesIncluded'),
   'sourceUrl':r.get('sourceUrl') or 'https://floridaelectionwatch.gov/',
   'sourceFetchedAt':r.get('sourceFetchedAt') or now.isoformat(),
   'sourceUpdatedAt':r.get('sourceFetchedAt') or now.isoformat(),
  })
 return kept+normalized

def overlay_live_district9(races, now):
 path=ROOT/'data/district-9.json'
 if not path.exists():
  return races
 try:
  data=json.loads(path.read_text())
 except Exception:
  return races
 if data.get('electionDate')!='2026-11-03' or not isinstance(data.get('races'),list) or not data['races']:
  return races
 race=data['races'][0]
 candidates=race.get('candidates') or []
 if len(candidates)<2:
  return races
 total=sum(int(c.get('votes') or 0) for c in candidates)
 if total<=0:
  return races
 replacement={
  'id':'live-cd9-general',
  'scope':'district',
  'name':'Representative in Congress, District 9',
  'status':'unofficial',
  'totalVotes':total,
  'candidates':[{
    'name':c.get('name') or '',
    'party':c.get('party') or 'NON',
    'votes':int(c.get('votes') or 0),
    'percent':round(int(c.get('votes') or 0)/total*100,2)
  } for c in candidates],
  'precincts':None,
  'precinctsReporting':None,
  'countiesIncluded':int(data.get('countiesIncluded') or 0),
  'sourceUrl':'https://floridaelectionwatch.gov/',
  'sourceFetchedAt':now.isoformat(),
  'sourceUpdatedAt':data.get('generatedAt') or data.get('lastUpdated') or now.isoformat(),
 }
 kept=[r for r in races if not (r.get('scope')=='district' and 'Representative in Congress' in str(r.get('name') or '') and 'District 9' in str(r.get('name') or ''))]
 kept.append(replacement)
 return kept

def main():
 from email.utils import parsedate_to_datetime
 parser=argparse.ArgumentParser();parser.add_argument('--output',default='data/general-watch.json');args=parser.parse_args()
 out=ROOT/args.output;out.parent.mkdir(parents=True,exist_ok=True)
 baseline=json.loads((ROOT/'data/general-watch-contract.json').read_text());now=datetime.now(timezone.utc)
 def state_fetch():
  text,modified=download(STATE_URL)
  result=build_state_snapshot(text,baseline['stateIdentityDigest'],now)
  if now>=RELEASE and any(r['totalVotes'] for r in result['races']):
   if not modified or parsedate_to_datetime(modified)<RELEASE:raise ValueError('State file has no verified post-release update')
  result['sourceModifiedAt']=modified
  return result
 def county_fetch():
  text,_=download(COUNTY_URL)
  return build_county_snapshot(text,baseline['countyIdentity'],now)
 snapshots={};health={}
 for name,fetch in [('state',state_fetch),('county',county_fetch)]:
  path=out.with_name('general-watch-'+name+'.json')
  previous=json.loads(path.read_text()) if path.exists() else None
  snapshot,status=collect_source(fetch,previous,now)
  health[name]=status
  if snapshot:
   snapshots[name]=snapshot
   if status['status']=='ok':write_json(path,snapshot)
 races=[]
 for name in ['county','state']:
  snap=snapshots.get(name)
  if snap:
   for race in snap['races']:
    races.append({**race,'sourceFetchedAt':snap['fetchedAt'],'sourceUpdatedAt':snap.get('sourceModifiedAt')})
 races=overlay_live_district9(races,now)
 races=overlay_official_headlines(races,now)
 live_district=[r for r in races if r.get('scope')=='district' and r.get('status')=='unofficial' and int(r.get('totalVotes') or 0)>0]
 if live_district:
  races=[r for r in races if r.get('scope')!='district']+live_district
 if races:
  combined={'electionId':'2026-fl-general','electionDate':'2026-11-03','fetchedAt':min(s['fetchedAt'] for s in snapshots.values()),'races':races,
   'status':'unofficial' if any(r['status']=='unofficial' for r in races) else 'pending',
   'coverage':{'countyConnected':'county' in snapshots,'stateConnected':'state' in snapshots}}
  write_json(out,combined)
 write_json(out.with_name('general-watch-health.json'),health)
 print(json.dumps({'sources':health,'races':len(races)}))
 if any(h['status']!='ok' for h in health.values()):raise SystemExit(1)
if __name__=='__main__':main()
