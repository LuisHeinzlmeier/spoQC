#!/usr/bin/env bash
# Move the fork onto the newest upstream dev: fork/base and every branch in fork/branches.txt are rebased onto it,
# then the integration branch is rebuilt.
#
#   fork/sync_upstream.sh
#
# Local only. It prints the push commands at the end; check the result (pytest, a short run) before pushing.
# Branches started from another listed branch (stacked) are not moved automatically: the script stops and says which.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git diff --quiet && git diff --cached --quiet || { echo "Working tree has changes; commit or set them aside first." >&2; exit 1; }
git config rerere.enabled true

git show-ref --verify --quiet refs/heads/fork/base || git branch fork/base origin/fork/base
old_upstream="$(git merge-base fork/base upstream/dev)"
old_base="$(git rev-parse fork/base)"
git fetch -q upstream
if [ "$(git rev-parse upstream/dev)" = "$old_upstream" ]; then
  echo "fork/base is already on the newest upstream dev ($(git rev-parse --short upstream/dev)). Nothing to do."
  exit 0
fi
echo "upstream dev: $(git rev-parse --short "$old_upstream") -> $(git rev-parse --short upstream/dev)"

branches=$(git show fork/base:fork/branches.txt | sed 's/#.*//' | awk 'NF {print $1}')
for b in $branches; do
  git show-ref --verify --quiet "refs/heads/$b" || git branch "$b" "origin/$b"
  for other in $branches; do
    if [ "$other" != "$b" ] && git merge-base --is-ancestor "$other" "$b" 2>/dev/null; then
      echo "$b is started from $other (stacked). Rebase stacked branches by hand; nothing was changed." >&2
      exit 1
    fi
  done
done

start="$(git rev-parse --abbrev-ref HEAD)"
git rebase -q --onto upstream/dev "$old_upstream" fork/base
echo "fork/base -> $(git rev-parse --short fork/base)"
for b in $branches; do
  mb="$(git merge-base "$b" "$old_base")"
  if ! git rebase -q --onto fork/base "$mb" "$b"; then
    echo "Conflict while moving $b. Resolve, 'git rebase --continue', then run fork/rebuild_integration.sh." >&2
    exit 1
  fi
  echo "$b -> $(git rev-parse --short "$b")"
done
git switch -q "$start" 2>/dev/null || true
fork/rebuild_integration.sh

echo
echo "Also fast-forward the copies of upstream:  git push origin upstream/dev:dev upstream/main:main"
echo "Push after checking:  git push --force-with-lease origin fork/base $(echo $branches) integration/fast-qc"
