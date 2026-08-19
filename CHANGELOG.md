# Log

Reverse chronological. One entry per working session.

## 2026-08-19 (later) — the calibration-budget surface

**Turned the curve into a surface.** New module `src/budget.py`: corpus size N crossed with
calibration duration k, one test set throughout (held-out wearer's session 2, in full),
calibration drawn from that wearer's session 1. 1,000 population fits, each reused across
6 durations x 2 window-selection modes x 2 adaptation methods.

The surface contains the existing results as corners, which is how it was validated:
- N=0, k=120 s reproduces `calibrated_crossday`: **15.52** vs the published 15.17.
- N=16, k=0 reproduces zero-shot, re-scored on session 2 only: **12.40** (the published 11.22
  averages over both sessions; session 2 is the harder one).

Findings:
- **The value of calibration collapses as the corpus grows.** A full 120 s ritual is worth
  +9.31 %MVC at 1 wearer (19/20 helped, p < 0.0001) and +0.47 at 16 (10/20 helped, p = 0.841).
  By 16 wearers it is not distinguishable from skipping calibration.
- **Roughly the first 5 seconds does most of the work** at every corpus size.
- **The corpus buys out the ritual, not the re-donning penalty.** No cell reaches the
  same-session ceiling of 8.4 %MVC.
- **Fitting the scale beats fitting the weights.** Per-finger gain and offset (10 params)
  produces the whole surface. Prior-mean ridge on the residuals is worse than not calibrating
  at all (12.40 -> 14.95 at N=16, k=5 s) and stays worse with its penalty chosen ON the test
  set, so it is a method failure, not a tuning failure.
- **More calibration data can hurt.** With no corpus, 5 s sampled across the session beats 120 s
  of it (11.90 vs 15.75). Same mechanism: capacity to memorise session 1's donning is punished
  on session 2.

Two bugs in my own analysis, both found by cross-checking against the published numbers:
1. Grouped the summary by `lam` for every method. lambda is a *factor* for the oracle arm but an
   *outcome* for the honest arm (the inner split picks it per subject and per rep), so the honest
   finetune rows were split into subgroups and the pivot averaged subgroup means with equal
   weight. Fixed: `lam_key` is only meaningful for `finetune_grid`.
2. Bootstrapped over all 200 runs per cell. There are only 20 wearers; that reports a CI for a
   sample size we do not have. Fixed: collapse reps to a per-subject mean first, then bootstrap
   over subjects. CIs got appropriately wider.

Also added: `src/budget_tests.py` (paired tests, same shape as `paired.py`),
`src/plot_budget.py` (two-panel figure, same CVD-validated palette), Makefile targets.

**README rewritten** from open-question scaffold to findings. The old line 4 claimed "Nobody has
published the equivalent experiment for force", which the 19 Aug prior-art check had already
shown to be too strong. It now states the bounded claim: the power law is established for sEMG
kinematics and gestures, and this measures it for force.

## 2026-08-19 — first full result

**Ran the full sweep on all 20 Hyser subjects.** 1,000 zero-shot fits, 40 within-session,
20 cross-day.

Findings:
- Scaling law: `MAE = 18.3 · N^(-0.192)`, log-log R² = 0.966 (N = 1,2,4,8,16 subjects).
- Re-donning cost: same-session calibration 8.4 %MVC vs next-day 15.2 (median 11.8).
- Crossover: zero-shot beats next-day calibration from N ≈ 4–8; wins for 14/20 subjects at N=16.
- Extrapolation to the same-session ceiling: ~57 wearers (mean fit) to ~113 (median fit).

Four bugs found and fixed, all by reading the actual bytes rather than the docs:
1. `parse_subject_session` assumed `subject_01_session_1`; Hyser uses `subject01_session1`.
2. Downloads were silently truncated — urllib returns a short body without raising. Added
   Content-Length verification and a `--repair` mode. 366 records had to be re-fetched.
3. The montage was index-based; `readme.txt` gave the `ED/EP/FD/FP` naming, so it now resolves
   by channel name. Channels are stored in reverse column order, so index selection would have
   silently grabbed the wrong electrodes.
4. **Force is stored in amplifier VOLTS**, not Newtons. `equipment_info.pdf` gives the sensor
   range (±200 N) but no V→N constant ships with the dataset. This is why the Hyser literature
   reports %MVC — so we do too, normalising against each subject's own MVC trials.

Design change from the data: added a third arm. The original "calibrated" reference trained on
session 1 and tested on session 2, which is cross-day *and* re-donned — harder than ForceBand's
same-session calibration. Split into `calibrated_within` and `calibrated_crossday`; the gap
between them is the cost of taking the band off.

## 2026-08-18 — scaffold

Repo built, harness verified end to end on synthetic data. Pure-Python downloader (no wget /
awscli). Design fixed: leave-one-subject-out, training-set-size sweep, bootstrap CIs.

## 2026-08-17 — the commitment

Intro call with Julian Olschwang (Hemlock, YC F26). Full-time role closing; internship offered;
evaluation kit in ~6 weeks. His stated differentiator: *"we're trying to amass the data volume
needed to make these models actually useful and generalizable — there's this kind of a one-off
system off of 10 hours, there's only so much you can do."*

Committed by email: run the scaling question on public data and send the result within two
weeks, either way. **Due 31 Aug.**
