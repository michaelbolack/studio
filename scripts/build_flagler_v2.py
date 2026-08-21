#!/usr/bin/env python3
"""Freeze Flagler's completed 2026 primary result from its official ENR page.

GitHub Actions is served Flagler's stale pre-election shell, while the public
county ENR page currently exposes the completed 21/21 result. These values are
transcribed from that official completed page and are NOT trusted on their own:
all eight statewide contests must cross-check Florida DOS geography before the
county file may be written.
"""
import json,re
from pathlib import Path

COUNTY='Flagler'
URL='https://enr.electionsfl.org/FLA/4029/Summary/'

def C(name,party,votes,pct): return {'name':name,'party':party,'votes':votes,'percent':pct}
def R(name,*cands): return {'name':name,'candidates':list(cands)}
def norm(s): return re.sub(r'[^a-z0-9]','',str(s or '').lower()).replace('and','')

def office_key(name):
    s=name.lower()
    if 'united states senator' in s:return 'United States Senator'
    if 'governor' in s:return 'Governor and Lieutenant Governor'
    if 'chief financial officer' in s:return 'Chief Financial Officer'
    if 'commissioner of agriculture' in s:return 'Commissioner of Agriculture'

def party_for(race):
    if race.startswith('REP '):return 'REP'
    if race.startswith('DEM '):return 'DEM'
    return 'NON'

races=[
R('DEM United States Senator',C('Angie Nixon','DEM',4273,48.83),C('Alex Vindman','DEM',4478,51.17)),
R('DEM Representative in Congress, District 6',C('Robert David Cooper II','DEM',1235,14.69),C('Steve Morgan','DEM',1988,23.64),C('Ronnie "Ron" Murchinson-Rivera','DEM',2541,30.22),C('Eric Yonce','DEM',2644,31.45)),
R('DEM Governor and Lieutenant Governor',C('Evelyn Castillo-Bach','DEM',645,7.40),C('Thomas Eloy Fernandez','DEM',340,3.90),C('Dayna Marie Foster','DEM',1114,12.78),C('David Jolly','DEM',5800,66.54),C('Dotie Joseph','DEM',617,7.08),C('Stephann Norman','DEM',201,2.31)),
R('DEM Chief Financial Officer',C('Earle Ford','DEM',3153,37.68),C('Annette Taddeo','DEM',5215,62.32)),
R('DEM Commissioner of Agriculture',C('Joey Mendoza Atkins','DEM',5823,71.14),C('Donald A. "Don" Prichard','DEM',2362,28.86)),
R('REP United States Senator',C('Chris Gleason','REP',1967,11.73),C('Ashley Moody','REP',13934,83.08),C('Neelam Taneja Perry','REP',245,1.46),C('Ernest "Ernie" Rivera','REP',625,3.73)),
R('REP Representative in Congress, District 6',C('Aaron Baker','REP',1770,10.74),C('Dan Bilzerian','REP',3025,18.35),C('Randy Fine','REP',9425,57.17),C('Charles Gambaro','REP',2267,13.75)),
R('REP Governor and Lieutenant Governor',C('Jay Collins','REP',3826,22.23),C('Byron Donalds','REP',8379,48.68),C('James Fishback','REP',1325,7.70),C('Jim Holcomb','REP',96,.56),C('Arthur Joseph McCaffrey','REP',52,.30),C('Daniel Nokovich','REP',37,.21),C('Paul Renner','REP',2787,16.19),C('Rachel Rodriguez','REP',158,.92),C('James W. Shaw','REP',58,.34),C('Caneste Succe','REP',36,.21),C('Bobby Williams','REP',460,2.67)),
R('REP Chief Financial Officer',C('Frank William Collige','REP',5341,33.52),C('Blaise Ingoglia','REP',10594,66.48)),
R('REP Commissioner of Agriculture',C('Wilton Simpson','REP',11348,70.85),C('Matt Taylor','REP',4668,29.15)),
R('REP Board of County Commissioners, District 2',C('Greg Feldman','REP',7666,47.91),C('Theresa Pontieri','REP',8336,52.09)),
R('REP Board of County Commissioners, District 4',C('Anna Jones','REP',3242,20.77),C('Drew Moss','REP',3847,24.65),C('Leann Pennington','REP',8520,54.58)),
R('Circuit Judge, 7th Judicial Circuit, Group 26',C('Carleen Leffler','NON',9346,37.18),C('Jeanne Stratis','NON',15794,62.82)),
R('School Board, District 1',C('Cathy Moon','NON',15000,55.93),C('Jill R. Woolbright','NON',11818,44.07)),
R('School Board, District 2',C('Will Furry','NON',10866,40.95),C('Rob Wood','NON',15668,59.05)),
R('School Board, District 4',C('Christy Chong','NON',9831,37.20),C('Ron Long','NON',6156,23.29),C('Trevor Tucker','NON',10442,39.51)),
R('City of Palm Coast Council Member, District 2',C('Antonio "Tony" Amaral Jr.','NON',8903,45.00),C('Jeani Duarte','NON',5970,30.17),C('Jimmy Hengy','NON',4912,24.83)),
R('City of Palm Coast Council Member, District 4',C('Dylana "Dee" Galery','NON',5262,26.94),C('John Kvederis','NON',4580,23.45),C('Ramon Marrero','NON',3428,17.55),C('Darlene Shelley','NON',6262,32.06)),
]

# Eight statewide contests must agree with DOS. The county page can contain
# later provisional updates, but only tiny nonnegative deltas with same leader.
state=json.loads(Path('data/statewide.json').read_text()); checks=[]
assert len(state.get('races',[]))==8
for sr in state['races']:
    office,party=sr['office'],sr['party']
    lr=next((r for r in races if office_key(r['name'])==office and party_for(r['name'])==party),None)
    assert lr,(office,party)
    geo=next(g for g in sr['geography'] if g.get('county')==COUNTY)
    expected={norm(k):int(v) for k,v in geo['votes'].items()}
    actual={norm(c['name']):int(c['votes']) for c in lr['candidates']}
    # Governor ticket label differs between county page and DOS; compare its
    # candidate vote vector after sorting when normalized names don't align.
    if set(actual)==set(expected):
        deltas=[actual[k]-expected[k] for k in expected]
        leader_ok=max(actual,key=actual.get)==max(expected,key=expected.get)
    else:
        assert office=='Governor and Lieutenant Governor',(office,actual,expected)
        av=sorted(actual.values()); ev=sorted(expected.values())
        assert len(av)==len(ev)
        deltas=[a-e for a,e in zip(av,ev)]
        leader_ok=max(actual.values())>=max(expected.values())
    assert all(d>=0 for d in deltas),(office,party,deltas)
    st=sum(expected.values()); ct=sum(actual.values()); dp=((ct-st)/st*100) if st else 0
    assert dp<0.25,(office,party,dp)
    assert leader_ok,(office,party)
    checks.append({'office':office,'party':party,'dosVotes':st,'countyVotes':ct,'delta':ct-st,'deltaPct':round(dp,4),'leaderMatch':True})

out={'schemaVersion':2,'county':COUNTY,'election':'2026 Primary Election','electionDate':'2026-08-18','source':'Flagler County Elections Office - Election Night Reporting','sourceUrl':URL,'sourceStatus':'Unofficial Election Results - all vote methods completely reported','precinctsReporting':21,'precinctsTotal':21,'coverageComplete':True,'frozenElection':True,'races':races,'validation':{'allPrecinctsReported':True,'allVoteTypesCompletelyReported':True,'statewideOverlapChecks':checks,'fixtureSource':'Completed official Flagler ENR page captured 2026-08-21'}}
Path('data/flagler.json').write_text(json.dumps(out,indent=2)+'\n')
manifest=json.loads(Path('data/manifest.json').read_text()); ent=manifest['counties'].setdefault(COUNTY,{})
ent.update({'connected':True,'file':'data/flagler.json','sourceUrl':URL,'races':len(races),'adapter':'v2-flagler-frozen-official-enr','validationFailed':False,'frozenElection':True,'validatedAgainst':'Completed Flagler ENR page + Florida DOS statewide county geography'});ent.pop('error',None)
Path('data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('flagler-v2-report.json').write_text(json.dumps({'status':'passed','races':len(races),'precincts':'21/21','statewideChecks':len(checks)},indent=2)+'\n')
print('Flagler frozen v2 built:',len(races),'races; checks',len(checks))
