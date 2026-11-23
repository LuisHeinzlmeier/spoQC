# Working in this fork of SpoQC

This is a fork of [heylf/spoQC](https://github.com/heylf/spoQC) (`upstream`) for making SpoQC faster.
Every change is kept on its own branch, so it can be used here right away and sent upstream later as its own pull request.
These instructions are for people and coding agents (Codex, Claude Code, Cursor, …) alike. Read all of it before changing anything.

## Branches

| Branch | What it is | Rules |
|---|---|---|
| `dev`, `main` | Exact copies of upstream | Never commit here. Only fast-forward from `upstream`. |
| `fork/base` | Upstream `dev` + the fork's tooling (this file, `CLAUDE.md`, `fork/`, `.claude/`) | The default branch of the fork. Tooling changes only, never SpoQC code. Nothing in it goes upstream. |
| `fix/<topic>`, `perf/<topic>` | One change each, started from `fork/base` | One topic per branch, no unrelated edits. Becomes one upstream pull request. |
| `pr/<branch>` | A change branch replayed on upstream `dev` without the fork tooling | Made by `fork/make_pr_branch.sh`; the head of an upstream pull request. |
| `integration/fast-qc` | `fork/base` with every branch in `fork/branches.txt` merged in | What the pipeline runs. Rebuilt by script, never edited or committed to by hand. |

Tags `run/<date>[-<what>]` mark the exact integration commit used for a pipeline run, so results can be traced back to code.

## Rules

1. Never commit to `dev`, `main` or `integration/fast-qc`.
2. One change per branch, started from `fork/base`. If a change needs another one, start it from that branch and say so in `fork/branches.txt`.
3. Don't touch files under `fork/`, `.claude/`, `AGENTS.md` or `CLAUDE.md` on a change branch. Tooling changes go on `fork/base`.
4. No reformatting, renaming or clean-ups mixed into a change. They make the upstream review harder and cause merge conflicts.
5. A speed-up is only done when it has a measured speed-up **and** an equivalence check against upstream (see below), both written in its commit message.
6. Keep `fork/branches.txt` up to date: every change branch that should be in the integration build is listed there, with its status.
7. Push with `--force-with-lease`, never `--force`, and only to your own change branches or after a rebuild.

## Making a change

```bash
git fetch --all --prune
git switch -c perf/<topic> origin/fork/base     # or fix/<topic>
# ... edit, test ...
pytest                                          # SpoQC's own tests
# run old and new on the reference data and compare (see Correctness)
git commit                                      # message: see the template below
git push -u origin perf/<topic>
```

Then add the branch to `fork/branches.txt` (a commit on `fork/base`) and rebuild the integration branch:

```bash
fork/rebuild_integration.sh                     # merges every listed branch onto fork/base
git push --force-with-lease origin integration/fast-qc
```

`git config rerere.enabled true` is set by the script, so a merge conflict you resolve once is resolved the same way next time.

## Correctness

The faster code must give the same results as upstream. Two kinds of change:

- **Exact**: the same calculation, done faster (vectorising a loop, limiting threads, caching). The outputs must be identical. Any difference is a bug.
- **Approximate**: a different algorithm or sampling (another Leiden implementation, a sampled silhouette score). Outputs may differ slightly. Measure how much and write it down.

How to check:

1. Run upstream `dev` and your branch on the same input (a small section or a crop of one), with the same settings, into two output folders.
2. Compare the two `spoQC_tmp` folders:
   ```bash
   python fork/equivalence/compare_outputs.py <upstream>/spoQC_tmp <branch>/spoQC_tmp [--exact]
   ```
   It reports, per output file and column, how many values are identical, the largest difference, the correlation, and for masks the share of pixels that agree. With `--exact` it fails on any difference.
3. Where you can, also add a unit test that gives the old and the new function the same random input and checks the outputs agree.

Commit message template for a speed-up:

```
<What changed, in one line>

<Why it is faster, two or three sentences.>

Speed: <step> <old> -> <new> on <section> (<cells> cells, <cpus> CPUs)
Equivalence: exact | approximate (<metrics>) vs upstream dev <commit> on <reference data>
Tests: pytest passed
```

## Running the pipeline

The pipeline (the spatialaxe fork) runs SpoQC from `integration/fast-qc`. Before a run, tag the commit it uses:

```bash
git tag run/<YYYY-MM-DD>[-<what>] integration/fast-qc
git push origin run/<YYYY-MM-DD>[-<what>]
```

## Sending a change upstream

Send changes one at a time, smallest and least controversial first. For each one:

```bash
fork/make_pr_branch.sh perf/<topic>             # creates pr/perf/<topic>: the same commits on upstream dev, without the fork tooling
git push -u origin pr/perf/<topic>
gh pr create --repo heylf/spoQC --base dev --head LuisHeinzlmeier:pr/perf/<topic>
```

Put the speed and equivalence numbers from the commit message in the pull request. Agents: ask the user before opening a pull request upstream. Once it is merged upstream, remove the branch from `fork/branches.txt`; the change then arrives through `dev`.

## When upstream changes

```bash
fork/sync_upstream.sh                           # moves fork/base and every listed branch onto the new upstream dev, then rebuilds integration
```

It changes local branches only and prints the push commands. Check the rebuilt integration branch (tests, a short run) before pushing.

## Files

| Path | Purpose |
|---|---|
| `AGENTS.md` | These instructions (read by Codex and most agents) |
| `CLAUDE.md` | Points Claude Code at this file |
| `fork/branches.txt` | Change branches in the integration build, in merge order, with status |
| `fork/rebuild_integration.sh` | Rebuilds `integration/fast-qc` from `fork/base` and the listed branches |
| `fork/make_pr_branch.sh` | Makes a clean upstream branch from a change branch |
| `fork/sync_upstream.sh` | Moves the fork onto a new upstream `dev` |
| `fork/equivalence/compare_outputs.py` | Compares two SpoQC output folders |
| `.claude/skills/spoqc-fork-change/` | Step-by-step skill for Claude Code (same procedure as above) |
