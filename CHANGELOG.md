# Log

Reverse chronological. One entry per working session.

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
