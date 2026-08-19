# Where this stands, and where it could go

Written 19 Aug 2026, after the first full sweep. Updated 19 Aug after the calibration-budget run.

---

## 1. What we actually have

Four findings, graded honestly.

### A. A scaling law for EMG→force  ⭐ genuinely new

`MAE = 18.3 · N^(−0.192)`, log-log R² = 0.966 across N = 1, 2, 4, 8, 16 training subjects.

Meta published a scaling law for gesture and pose decoding. **Nobody has published one for
force regression.** It is a small result on one dataset with a weak model, but the claim
"cross-user force error follows a power law in wearer count" appears to be unmade in public.

### B. The cost of taking the band off  ⭐ the most product-relevant thing here

| Calibration setting | MAE |
|---|---|
| Same session, band never removed (ForceBand's setting) | **8.4 %MVC** |
| Same subject, next day, band re-donned | **15.2 %MVC** (median 11.8) |

**Per-user calibration loses roughly half its value the moment the band comes off.** Nobody
has published this for force. Every calibration claim in this literature — including
ForceBand's 15-minute protocol — is measured *within* a session, which is the friendly case.

### C. The crossover  ⭐ the headline, with a caveat

Zero-shot on an unseen wearer overtakes that wearer's own next-day calibration at **N ≈ 4–8**
training subjects, and wins for **14 of 20 subjects** individually at N = 16.

Extrapolating the power law to the same-session ceiling: **≈57 wearers** (mean fit) to
**≈113** (median fit).

**Caveat that must ship with it:** the cross-day arm has n = 20 (one pair per subject), so its
CI is 11.1–21.4 and overlaps the zero-shot band. The paired tests carry the claim, not the
error bars. And 57–113 is an extrapolation 4–7× beyond the last data point.

### D. The calibration budget  ⭐ the decision tool — see §3, now done

The value of per-user calibration is **not a constant**. It is a function of corpus size, and it
collapses fast.

| Wearers in corpus | What 120 s of calibration saves | Wearers helped | Paired p |
|---|---|---|---|
| 1 | +9.31 %MVC | 19/20 | 0.0000 |
| 2 | +5.02 | 18/20 | 0.0001 |
| 4 | +2.98 | 15/20 | 0.0083 |
| 8 | +1.22 | 13/20 | 0.114 |
| 16 | **+0.47** | **10/20** | **0.841** |

Roughly the first 5 seconds does most of the work at every corpus size. Two sub-findings that
matter as much as the headline:

- **The corpus buys out the ritual, not the re-donning penalty.** No cell on the surface reaches
  the same-session ceiling of 8.4 %MVC. Adding wearers substitutes for calibration, not for the
  band having moved. Meta handles re-donning by *training across placements*, not by adding
  participants, and this is evidence that the distinction is load-bearing.
- **Fitting the scale beats fitting the weights.** A per-finger gain and offset (10 parameters)
  produces the whole surface. Prior-mean ridge on the population model's residuals is worse than
  not calibrating at all, and stays worse when its penalty is chosen on the test set — a method
  failure, not a tuning failure. Anything with the capacity to memorise session 1's donning gets
  punished on session 2.

---

## 1b. Prior art — checked 19 Aug, and the claim survives

Before writing "nobody has published this," I went and looked.

**Meta, *A generic non-invasive neuromotor interface*, Nature 2025** (Kaifosh, Reardon et al.)
is the closest prior work and it is close:

> *"Across all tasks, we observed reliable performance improvements as a function of the
> increasing number of participants in the training corpus. Consistent with other domains,
> empirical performance follows a power law both as a function of parameters and data quantity."*

- Tasks: **wrist angle velocity, discrete gestures, handwriting.**
- Participants: 162 (wrist) · 4,900 (gesture) · 6,627 (handwriting); 11,236 unique overall.
- They handle re-donning by *training across* multiple band placements.
- **Force estimation is not among their tasks.**

**Scaling and Distilling Transformer Models for sEMG** (arXiv:2507.22094) scales **model
parameters** — 2.2M → 109M — on emg2qwerty typing. Fixed 100-user training set. **No
subject-count axis, no force.**

### So the precise claim is

> The power law in participant count is established for sEMG **kinematics and discrete
> gestures**. This measures it for **force regression** — the modality ForceBand and Hemlock
> are built on — and finds the same functional form.

Not "nobody has done scaling laws in EMG." That would be wrong and checkable. The contribution
is the **axis** (force), the **head-to-head against per-user calibration**, the
**re-donning cost**, and the **corpus-vs-calibration trade**.

### One number that makes the extrapolation less wild

Meta's **wrist decoder used 162 participants** — their smallest task, and the one closest to a
continuous regression problem. Our extrapolation to the same-session ceiling lands at
**57–113 wearers**, comfortably *below* that. So the target is not exotic; it is smaller than
what Meta already collected for the nearest comparable decoder.

---

## 2. What limits it

| Limit | Does it threaten the claim? |
|---|---|
| Ridge on hand-crafted features | **No — this is deliberate.** A big model would confound capacity with data volume. It does mean absolute MAE is weak; the *shape* is the result. |
| N capped at 16 (20 subjects exist) | **Yes, for the extrapolation.** Fine for the crossover, which happens inside the data. |
| One dataset | **Yes.** A single-dataset scaling law is a hypothesis, not a law. |
| 8 channels we chose ourselves | Moderate. It imitates a band; it is not one. |
| %MVC not Newtons | Presentational. Forced by the dataset — force is stored in amplifier volts. |
| Hyser is clean lab data | **Yes, for anything about sweat, fatigue or a real shift.** Say nothing about those. |
| Budget surface scored on session 2 only | Presentational, but state it. Session 2 is the harder session (12.4 at N=16 vs 11.2 averaged over both), so budget cells are comparable to each other but not to the scaling curve. |

---

## 3. ~~The one experiment that would multiply the value~~ — done 19 Aug

> **Given N wearers already in the corpus, how many seconds of per-user calibration do you
> still need?**

Built as `src/budget.py`. Result in §1D. It cost about half a day rather than the estimated
full day, because the expensive part (the population fit) is shared across every duration and
adaptation method, so 1,000 fits covered the whole 2-D grid.

The answer, in the shape §3 originally asked for: *"At 16 wearers, calibration is worth 0.5 %MVC
and helps half your wearers — so stop shipping it as a default ritual and keep it as a rescue
path for the tail."*

Validated against the existing results by construction: the surface's corners reproduce
`calibrated_crossday` (15.52 vs 15.17) and zero-shot (12.40 on session 2 only).

---

## 4. Three paths

### Path 1 — Ship what exists  (2–3 days)  ← **done, bar the send**
Paired test, write-up, public repo, send to Julian.

### Path 2 — Add the calibration-budget surface  (+1–2 days)  ← **done 19 Aug**
Path 1 plus §3. Turned the plot into a tool.

### Path 3 — Make it a preprint  (3–6 weeks)
Path 2 plus: a second dataset (**HD-FW KIN** — 21 subjects and it has genuine *wrist* arrays,
which fixes the montage objection), a 1-D CNN to show the law is not a ridge artifact, a
channel-count ablation, and pooling across datasets to push N past 16.

The budget surface strengthens the case for Path 3: there are now **four** findings rather than
two, and finding D is the one with no obvious prior art at all. The re-donning result in
particular suggests an experiment nobody appears to have run — *how many donnings per wearer is
a new wearer worth?* — which Hyser cannot answer with 2 sessions but a multi-donning dataset
could.

**Still do not decide Path 3 now.** Decide it after seeing whether Julian engages, and against
the OPT clock. It is precisely the shape of thing the 15 Aug audit says starts and does not
finish.

---

## 5. What NOT to do

- **Do not chase a better model.** Ridge is the control. A CNN raises accuracy and answers a
  question nobody asked.
- **Do not claim anything about sweat, drift, or a full shift.** Hyser cannot support it.
- **Do not extrapolate past ~100 wearers** without saying loudly that it is extrapolation.
- **Do not quote the `finetune_grid` numbers as a result.** They are an oracle, chosen on the
  test set, and exist only to prove the finetune failure is not a tuning artifact.
- **Do not quote the `spread` calibration numbers as achievable.** Sampling k seconds of windows
  across a whole session is not something a wearer can do in k seconds.
- **Do not fold in Ninapro or a third dataset before the email goes out.**

---

## 6. Next steps

| # | Step | State |
|---|---|---|
| 1 | Wilcoxon signed-rank + paired-dots panel | ✅ done — p = 0.0027, holds without the outlier |
| 2 | Two-panel figure, CVD-validated palette | ✅ done |
| 3 | Private GitHub repo + changelog | ✅ done |
| 4 | Prior-art check | ✅ done — see §1b, claim survives and is now precisely bounded |
| 5 | README rewritten as findings, not scaffolding | ✅ done — and the "nobody has published" overclaim on old line 4 is gone |
| 6 | Calibration-budget surface (§3) | ✅ done — `budget.py`, `budget_tests.py`, `plot_budget.py` |
| 7 | **Email to Julian** — figure, the trade, caveats | drafted, needs Vidya's pass and the repo link |
| 8 | **Commit the new work** (Claude writes files, Vidya runs git) | next |
| 9 | **Flip repo public when the email goes out** | 5 min |

**Deadline is 31 Aug. Today is the 19th.** What remains is a read-through, a git commit, and a
send.
