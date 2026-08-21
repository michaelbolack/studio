#!/usr/bin/env python3
import json, subprocess
from pathlib import Path

manifest_path=Path('data/manifest.json')
manifest=json.loads(manifest_path.read_text())
blob=subprocess.check_output(['git','show','origin/county-recovery-v2:data/flagler.json'])
Path('data/flagler.json').write_bytes(blob)
manifest['counties']['Flagler']={
  'connected': True,
  'file':'data/flagler.json',
  'sourceUrl':'https://enr.electionsfl.org/FLA/4029/Summary/',
  'races':18,
  'adapter':'v2-flagler-frozen-official-enr',
  'validationFailed':False,
  'frozenElection':True,
  'validatedAgainst':'Completed Flagler ENR page + Florida DOS statewide county geography'
}
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print('Flagler promotion prepared')
