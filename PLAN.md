# Plan — EMG→force scaling study

**Commitment:** a plot to Julian Olschwang (Hemlock) by **Mon 31 Aug 2026**. Said in writing:
*"I am running it over the next two weeks and I will send you the result either way."*

**Today:** Tue 18 Aug. **13 days left.** Deadline is self-imposed, which is exactly why it will
slip if it is not defended.

---

## 1. Where we are

**Done**
- Repo scaffolded: fetch / features / dataset / sweep / plot, config-driven, `make` targets.
- Harness verified end to end on synthetic data (`make smoke`) — the sweep, the bootstrap CIs
  and the figure all execute. Nothing about EMG is validated by that; only that the code runs.
- Experiment design fixed: leave-one-subject-out, training-set-size sweep, plus a per-user
  calibrated reference line so the plot shows the calibration tax rather than a bare curve.

**Not done**
- No data downloaded. No real record has ever been opened.
- **The electrode montage is unresolved** — see §3. This is the only thing that can produce a
  confident wrong answer.

---

## 2. Hard facts established 18 Aug

| Fact | Consequence |
|---|---|
| Mac has **40 GB free (92% used)** | 18 GB for both subsets is tight. **Start with `random/` only (9.8 GB).** |
| **PhysioNet is unreachable from the Cowork container** (403 at the proxy) | Claude cannot download or run this. **You run it in your own Mac terminal.** |
| The Cowork VM has **no network** and lacks scipy/sklearn/wfdb | Same conclusion. The VM is only useful for editing files. |
| Hyser: 20 subjects × 2 sessions, 256 ch @ 2048 Hz, 5 force ch @ 100 Hz, WFDB | Matches the code's assumptions, to be confirmed by `make check`. |
| `random/` has a published comparable — Jiang 2021, ≈8.57 %MVC RMSE within-day | Sanity anchor for the calibrated arm. If we land wildly off that, something is wrong. |

### Division of labour

- **You:** venv, download, and every `make` run. Nothing else can do it.
- **Claude:** code, debugging from pasted errors, reviewing `results/*.csv`, the montage
  mapping once `equipment_info.pdf` is on disk, the figure, the write-up and the email.

---

## 3. The one open technical question

`config.yaml` picks 8 of 256 channels to imitate a wrist band. **Those indices are a
placeholder.** The real mapping — which channel index sits on which grid, row and forearm
compartment — lives in **`equipment_info.pdf`, shipped inside the dataset**, and could not be
read from outside (PhysioNet blocks the container; the paper is behind a captcha).

**Resolution:** after `make fetch`, open `equipment_info.pdf`, or point Claude at it, and fix
`config.yaml` before any sweep. `make check` confirms the indices are at least in range and
prints the real channel names.

**Why it matters:** a wrong montage still produces a smooth, plausible curve. It would be the
one failure mode that survives all the way into Julian's inbox.

---

## 4. Schedule

| When | Do | Done when |
|---|---|---|
| **Tue 18 (tonight)** | venv + `pip install -r requirements.txt`; `make smoke`; `make sweep plot`; delete `results/cache`. Then start `make fetch` and go to bed. | A synthetic curve rendered, download running |
| **Wed 19** | `make check`. Read `equipment_info.pdf`, fix the montage. `make prepare LIMIT=3`. Eyeball one subject: force trace vs EMG envelope, same plot. | You have *seen* real Hyser signal |
| **Thu 20 – Fri 21** | Full `make prepare`, first full `make sweep plot`. Ugly is fine. | **GATE: one curve on real data** |
| Sat 22 – Sun 24 | Buffer. Add `mvc/` if disk allows and rerun with true %MVC. | — |
| Mon 25 – Wed 27 | Real runs: per-finger breakdown, cross-day arm, full bootstrap. | Numbers you would defend |
| Thu 28 – Fri 29 | Figure polish, write-up, caveats section. | Draft email ready |
| **Sat 30 – Sun 31** | Send. | Sent |

### The gate, and the descope rule

**If there is no curve on real data by end of Friday 21 Aug, descope immediately** — one
finger (index), five held-out subjects, three repeats, `random/` only. Do not extend the
deadline. A small honest result on time beats a complete one that arrives in September, and
the entire point of this exercise is that the thing you said you would do actually lands.

---

## 5. Risks, in the order they will bite

1. **Wrong montage → confident wrong curve.** Mitigation: §3, resolved before the sweep.
2. **Disk.** 40 GB free, 9.8 GB download plus cache. Mitigation: `random/` only; check `df -h`
   before starting; `mvc/` is optional and the code already falls back to task-peak
   normalisation without it.
3. **Record structure differs from assumption** — how EMG and force files pair up, file naming.
   Mitigation: `make check` and `LIMIT=3` before committing to a full run.
4. **`prepare` runtime.** Filtering happens *after* the 256→8 subsample, so it is cheap, but the
   full `random/` subset is ~10 GB of WFDB. Measure with `LIMIT=3` and extrapolate before
   launching the full pass.
5. **Attention.** Qualcomm, NVIDIA and the rest of the pipeline are live. This has a hard date
   and a named person waiting; the others do not. Protect Wed–Fri.

---

## 6. What the deliverable actually is

Not just a plot. Three things, in one short email:

1. **The figure** — zero-shot MAE vs training subjects, bootstrap CIs, calibrated ceiling line.
2. **Three sentences of reading** — does the curve bend, and what that implies for how many
   wearers Hemlock needs before calibration stops being a bottleneck.
3. **The caveats, stated by you first** — %MVC is not Newtons; 20 subjects caps the sweep at
   N=16 while Meta's effect appeared at thousands; an 8-channel subsample of an HD grid is not
   a wristband; Hyser is clean lab data and says nothing about sweat or band migration.

The caveats are not throat-clearing. A flat curve reported honestly as *"not visible below 16
subjects"* is a credible result; the same curve reported as *"force does not scale"* is one an
investor's diligence takes apart, and it would take you with it.
