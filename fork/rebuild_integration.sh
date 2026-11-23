#!/usr/bin/env bash
# Rebuild the integration branch: fork/base plus every branch listed in fork/branches.txt, merged in order.
#
#   fork/rebuild_integration.sh [target-branch]      (default: integration/fast-qc)
#
# The list is read from the fork/base branch, so this works from any checkout. A local branch is used when it exists,
# otherwise origin/<branch>. Local only: push the result yourself with --force-with-lease.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
target="${1:-integration/fast-qc}"

git diff --quiet && git diff --cached --quiet || { echo "Working tree has changes; commit or set them aside first." >&2; exit 1; }
git config rerere.enabled true

ref_of() { if git show-ref --verify --quiet "refs/heads/$1"; then echo "$1"; else echo "origin/$1"; fi; }
base="$(ref_of fork/base)"
branches=$(git show "$base:fork/branches.txt" | sed 's/#.*//' | awk 'NF {print $1}')
[ -n "$branches" ] || { echo "No branches listed in fork/branches.txt on $base." >&2; exit 1; }

start="$(git rev-parse --abbrev-ref HEAD)"
git switch -q -C "$target" "$base"
echo "$target <- $base ($(git rev-parse --short "$base"))"
for b in $branches; do
  ref="$(ref_of "$b")"
  git rev-parse --verify --quiet "$ref" >/dev/null || { echo "Branch $b not found (locally or on origin)." >&2; exit 1; }
  echo "  merge $ref ($(git rev-parse --short "$ref"))"
  if ! git merge -q --no-ff --no-edit -m "Merge $b into $target" "$ref"; then
    echo "Merge conflict with $b. Resolve it, 'git commit', then run this script again (rerere remembers the fix)." >&2
    exit 1
  fi
done
echo "Done: $target at $(git rev-parse --short HEAD)."
echo "Check it (pytest, a short run), then: git push --force-with-lease origin $target"
if [ "$start" != "$target" ] && [ "$start" != "HEAD" ]; then
  git switch -q "$start"
  echo "(switched back to $start)"
fi
