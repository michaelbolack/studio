import unittest
from unittest.mock import patch
from scripts import collect_prediction_markets as markets
from scripts import collect_general_watch as watch

class MarketLifecycleTests(unittest.TestCase):
 def fetch(self,url):
  ticker=url.rsplit('/',1)[1]
  config=next((c for c in markets.EVENTS if c['eventTicker']==ticker),None)
  if config:
   return {'event':{'event_ticker':ticker},'markets':[{'ticker':t,'status':'finalized'} for t,_ in config['outcomes']]}
  return {'event':{'event_ticker':ticker},'markets':[{'ticker':ticker+'-'+s,'yes_sub_title':s,'status':'active','yes_bid':49,'yes_ask':51,'last_price':50,'volume':2000,'volume_24h':100,'open_interest':200} for s in ['A','B']]}
 def test_closed_core_markets_do_not_block_active_long_range(self):
  s=markets.build_snapshot(self.fetch)
  self.assertEqual(s['events'],[])
  self.assertEqual(len(s['closedEvents']),2)
  self.assertGreaterEqual(len(s['longRangeEvents']),6)
 def test_missing_core_market_is_still_an_error(self):
  def missing(url):
   payload=self.fetch(url)
   payload['markets']=[]
   return payload
  with self.assertRaises(ValueError):markets.build_snapshot(missing)

class OutageNotificationTests(unittest.TestCase):
 def test_repeated_outage_is_not_new(self):
  h={'state':{'status':'error','message':'TLS failed'},'county':{'status':'ok'}}
  self.assertFalse(watch.new_source_outages(h,h))
 def test_first_outage_and_changed_error_are_reported(self):
  h={'state':{'status':'error','message':'TLS failed'}}
  self.assertTrue(watch.new_source_outages(h,{}))
  self.assertTrue(watch.new_source_outages(h,{'state':{'status':'error','message':'timeout'}}))
 def test_outage_after_recovery_is_reported(self):
  self.assertTrue(watch.new_source_outages({'state':{'status':'error','message':'TLS failed'}},{'state':{'status':'ok'}}))
