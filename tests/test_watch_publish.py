import unittest,tempfile,subprocess
from pathlib import Path
SCRIPT=Path('scripts/publish_general_watch.sh').resolve()
class PublishingTests(unittest.TestCase):
 def test_concurrent_unrelated_main_commit_is_preserved(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   def git(*args,cwd=root):return subprocess.run(['git',*args],cwd=cwd,check=True,capture_output=True,text=True).stdout.strip()
   git('init','--bare','--initial-branch=main','origin.git');git('clone',str(root/'origin.git'),'a')
   a=root/'a'
   for work in [a]:git('config','user.email','test@example.com',cwd=work);git('config','user.name','Test',cwd=work)
   (a/'base').write_text('base');git('add','.',cwd=a);git('commit','-m','base',cwd=a);git('push','origin','main',cwd=a)
   git('clone',str(root/'origin.git'),'b');b=root/'b';git('config','user.email','test@example.com',cwd=b);git('config','user.name','Test',cwd=b)
   (a/'watch').write_text('new results');git('add','.',cwd=a);git('commit','-m','results',cwd=a)
   (b/'other').write_text('independent update');git('add','.',cwd=b);git('commit','-m','other',cwd=b);git('push','origin','main',cwd=b)
   subprocess.run(['bash',str(SCRIPT)],cwd=a,check=True,capture_output=True,text=True)
   self.assertEqual(git('show','main:other',cwd=a),'independent update')
   self.assertEqual(git('show','main:watch',cwd=a),'new results')

class LegacyProtectionTests(unittest.TestCase):
 def test_legacy_publisher_preserves_newest_general_snapshot(self):
  import os,json
  from scripts.protect_v2_data import preserve_general_watch
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);subprocess.run(['git','init','--initial-branch=main',td],check=True,capture_output=True)
   for key,value in [('user.name','Test'),('user.email','test@example.com')]:subprocess.run(['git','-C',td,'config',key,value],check=True)
   (root/'data').mkdir();(root/'data/general-watch.json').write_text(json.dumps({'electionId':'2026-fl-general','races':[{'totalVotes':42}]}))
   subprocess.run(['git','-C',td,'add','.'],check=True);subprocess.run(['git','-C',td,'commit','-m','latest'],check=True,capture_output=True)
   generated=root/'generated';generated.mkdir();(generated/'general-watch.json').write_text('{}')
   old=Path.cwd()
   try:
    os.chdir(root);preserve_general_watch(generated,'HEAD')
   finally:os.chdir(old)
   self.assertEqual(json.loads((generated/'general-watch.json').read_text())['races'][0]['totalVotes'],42)
