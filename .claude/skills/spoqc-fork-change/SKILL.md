---
name: spoqc-fork-change
description: Make, check, integrate or send upstream a change in the SpoQC fork. Use for any speed-up or fix to SpoQC code in this repository, for rebuilding the integration branch, for syncing with upstream, and for preparing an upstream pull request.
---

# Changing SpoQC in this fork

The rules are in `AGENTS.md` at the repository root; read it first. This skill is the same procedure as a checklist.

## A new speed-up or fix

1. `git fetch --all --prune`, then `git switch -c perf/<topic> origin/fork/base` (or `fix/<topic>`). Never start from `dev`, `main` or `integration/fast-qc`.
2. Change only what the topic needs. No reformatting, renaming or clean-ups. Don't touch `AGENTS.md`, `CLAUDE.md`, `fork/` or `.claude/`.
3. Run `pytest`.
4. Measure the speed on one section: the step's run time before (upstream `dev`) and after, with the same CPUs.
5. Check equivalence: run upstream `dev` and the branch on the same input into two folders, then
   `python fork/equivalence/compare_outputs.py <upstream>/spoQC_tmp <branch>/spoQC_tmp` (add `--exact` when the change should not alter results). Decide: exact or approximate, and note the numbers.
6. Commit with the template in `AGENTS.md` (Speed, Equivalence, Tests lines). Push the branch.
7. On `fork/base`, add the branch to `fork/branches.txt` with its kind and equivalence result, commit, push.
8. `fork/rebuild_integration.sh`, run the tests on the result, then `git push --force-with-lease origin integration/fast-qc`.

## Before a pipeline run

Tag the integration commit: `git tag run/<YYYY-MM-DD>[-<what>] integration/fast-qc && git push origin <tag>`.

## Upstream changed

`fork/sync_upstream.sh`, check the rebuilt integration branch, then push with the commands it prints.

## Sending a change upstream

`fork/make_pr_branch.sh <branch>` makes `pr/<branch>` without the fork tooling. Push it and open the PR against `heylf/spoQC` `dev`, with the speed and equivalence numbers. One change at a time, smallest first. Ask the user before opening a pull request.

## Stop and ask the user when

- an equivalence check shows differences in a change that should be exact,
- a merge or rebase conflict touches SpoQC logic you don't fully understand,
- a step would push to `dev`, `main`, or anywhere in `heylf/spoQC`.
