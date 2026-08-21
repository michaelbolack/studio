#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
manifest_path=Path('data/manifest.json')
manifest=json.loads(manifest_path.read_text())
blob=subprocess.check_output(['git','show','origin/county-recovery-v2:data/okaloosa.json'])
Path('data/okaloosa.json').write_bytes(blob)
manifest['counties']['Okaloosa']={
  'connected': True,
  'file':'data/okaloosa.json',
  'sourceUrl':'https://enrarchive.electionsfl.org/OKA/4026/Summary/',
  'races':11,
  'adapter':'v2-okaloosa-voterfocus-archive',
  'validationFailed':False,
  'frozenElection':True,
  'validatedAgainst':'Okaloosa official VoterFocus archive + Florida DOS statewide sanity checks'
}
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print('Okaloosa promotion prepared')
