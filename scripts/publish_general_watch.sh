#!/usr/bin/env bash
set -euo pipefail
# Rebase only our scoped snapshot commit over unrelated main updates. Never force push.
for attempt in 1 2 3; do
  git fetch origin main
  if ! git -c core.editor=true rebase origin/main; then
    git rebase --abort
    exit 1
  fi
  if git push origin HEAD:main; then
    exit 0
  fi
done
echo 'Main kept changing; refusing to overwrite newer work.' >&2
exit 1
