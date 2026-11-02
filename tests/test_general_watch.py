import unittest,gzip
from pathlib import Path
from datetime import datetime, timezone
from scripts.collect_general_watch import build_state_snapshot, identity_digest, collect_source
TEXT=gzip.open('tests/fixtures/florida-general-zero.tsv.gz','rt').read()
NOW=datetime(2026,11,4,2,tzinfo=timezone.utc)
class WatchTests(unittest.TestCase):
 def test_official_zero_file_is_pending_and_has_county_and_state_scopes(self):
  s=build_state_snapshot(TEXT,identity_digest(TEXT),NOW)
  self.assertEqual(s['status'],'pending')
  self.assertTrue(any(r['scope']=='florida' and r['name']=='United States Senator' for r in s['races']))
  self.assertTrue(any(r['scope']=='indian-river' and 'District 34' in r['name'] for r in s['races']))
 def test_state_totals_sum_counties_not_county_totals(self):
  lines=TEXT.splitlines();lines[1]=lines[1].rsplit('\t',1)[0]+'\t123'
  s=build_state_snapshot('\n'.join(lines),identity_digest(TEXT),NOW)
  race=next(r for r in s['races'] if r['scope']=='florida' and r['name']=='United States Senator')
  self.assertEqual(race['totalVotes'],123)
  local=next(r for r in s['races'] if r['scope']=='indian-river' and r['name']=='United States Senator')
  self.assertEqual(local['totalVotes'],0)
 def test_missing_candidate_row_is_withheld(self):
  with self.assertRaises(ValueError):build_state_snapshot('\n'.join(TEXT.splitlines()[:-1]),identity_digest(TEXT),NOW)
 def test_wrong_election_rejected(self):
  with self.assertRaises(ValueError):build_state_snapshot(TEXT.replace('11/03/2026','08/18/2026'),identity_digest(TEXT),NOW)
 def test_negative_or_noninteger_votes_rejected(self):
  for v in ['-1','1.5','bad']:
   lines=TEXT.splitlines();lines[1]=lines[1].rsplit('\t',1)[0]+'\t'+v
   with self.assertRaises(ValueError):build_state_snapshot('\n'.join(lines),identity_digest(TEXT),NOW)
 def test_state_results_held_until_eight_eastern(self):
  lines=TEXT.splitlines();lines[1]=lines[1].rsplit('\t',1)[0]+'\t123'
  s=build_state_snapshot('\n'.join(lines),identity_digest(TEXT),datetime(2026,11,4,0,59,tzinfo=timezone.utc))
  self.assertTrue(all(r['totalVotes'] is None for r in s['races']))
 def test_failed_fetch_preserves_previous_snapshot(self):
  old={'races':[{'totalVotes':42}],'fetchedAt':'2026-11-04T01:00:00+00:00'}
  def fail():raise OSError('offline')
  s,h=collect_source(fail,old,NOW)
  self.assertEqual(s,old);self.assertEqual(h['status'],'error')
if __name__=='__main__':unittest.main()

class CountyTests(unittest.TestCase):
 def test_pre_election_nonzero_vendor_data_never_becomes_results(self):
  from scripts.collect_general_watch import parse_county,build_county_snapshot
  text=gzip.open('tests/fixtures/indian-river-general.html.gz','rt').read()
  contract=parse_county(text)[0]
  s=build_county_snapshot(text,contract,NOW)
  self.assertTrue(all(r['totalVotes'] is None and r['status']=='pending' for r in s['races']))
 def test_changed_roster_rejected(self):
  from scripts.collect_general_watch import parse_county,build_county_snapshot
  text=gzip.open('tests/fixtures/indian-river-general.html.gz','rt').read();contract=parse_county(text)[0]
  with self.assertRaises(ValueError):build_county_snapshot(text.replace('Jennifer Pippin','Altered Candidate'),contract,NOW)

class CountyReleaseTests(unittest.TestCase):
 def test_updated_county_page_can_publish_after_seven_before_state_release(self):
  from scripts.collect_general_watch import parse_county,build_county_snapshot
  text=gzip.open('tests/fixtures/indian-river-general.html.gz','rt').read();contract=parse_county(text)[0]
  text=text.replace('10/27/2026 1:41:53 pm','11/3/2026 7:15:00 pm')
  s=build_county_snapshot(text,contract,datetime(2026,11,4,0,30,tzinfo=timezone.utc))
  self.assertTrue(any(r['status']=='unofficial' and r['totalVotes']>0 for r in s['races']))
