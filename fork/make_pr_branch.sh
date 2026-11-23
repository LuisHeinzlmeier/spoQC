#!/usr/bin/env bash
# Make a clean branch for an upstream pull request: the change branch's own commits replayed on upstream/dev,
# without the fork tooling from fork/base.
#
#   fork/make_pr_branch.sh <change-branch>           e.g. fork/make_pr_branch.sh perf/ac-gene-lookup
#
# Creates (or resets) the local branch pr/<change-branch>. A branch started from another change branch brings that
# branch's commits along, as upstream needs them too. Local only: push it yourself.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
src="${1:?usage: fork/make_pr_branch.sh <change-branch>}"
dst="pr/$src"

git diff --quiet && git diff --cached --quiet || { echo "Working tree has changes; commit or set them aside first." >&2; exit 1; }
git fetch -q upstream
base_ref=$(git show-ref --verify --quiet refs/heads/fork/base && echo fork/base || echo origin/fork/base)
fork_point="$(git merge-base "$src" "$base_ref")"

tooling=$(git diff --name-only "$fork_point" "$src" -- AGENTS.md CLAUDE.md fork .claude)
if [ -n "$tooling" ]; then
  echo "$src changes fork tooling files, which must not go upstream:" >&2
  echo "$tooling" >&2
  echo "Move those changes to fork/base first." >&2
  exit 1
fi

git branch -f "$dst" "$src"
start="$(git rev-parse --abbrev-ref HEAD)"; [ "$start" = HEAD ] && start="$(git rev-parse HEAD)"
if ! git rebase -q --onto upstream/dev "$fork_point" "$dst"; then
  echo "Conflict while moving $src onto upstream/dev. Resolve, 'git rebase --continue', then push $dst." >&2
  exit 1
fi
git switch -q "$start" 2>/dev/null || git switch -q --detach "$start"
echo "$dst: $(git rev-list --count upstream/dev.."$dst") commit(s) on upstream/dev:"
git log --oneline upstream/dev.."$dst"
echo
echo "Next: git push -u origin $dst"
echo "      gh pr create --repo heylf/spoQC --base dev --head LuisHeinzlmeier:$dst"
