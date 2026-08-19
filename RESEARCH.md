# Where this stands, and where it could go

Written 19 Aug 2026, after the first full sweep.

---

## 1. What we actually have

Three findings, graded honestly.

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
CI is 11.1–21.4 and overlaps the zero-shot band. The claim is *suggestive*, not established,
until a paired test is run. And 57–113 is an extrapolation 4–7× beyond the last data point.

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
is the **axis** (force), the **head-to-head against per-user calibration**, and the
**re-donning cost**, which Meta sidesteps by training across placements rather than measuring
what it costs.

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

---

## 3. The one experiment that would multiply the value

Right now the result says *more wearers help*. The product question is sharper:

> **Given N wearers already in the corpus, how many seconds of per-user calibration do you
> still need?**

That is a **2-D surface**, not a curve — subjects on one axis, calibration seconds on the
other — and it turns the finding from an observation into a **decision tool**. It is exactly
the spec for Hemlock's out-of-box experience, and the machinery already exists: add a few-shot
arm that trains on N subjects **plus k seconds** of the held-out wearer, sweeping
k ∈ {0, 5, 15, 30, 60, 120}.

Output: *"At 50 wearers, 15 seconds of calibration gets you what 5 minutes buys today."*
Or whatever it actually says.

**Cost: about a day.** Highest value-per-hour of anything on this list, by a wide margin.

---

## 4. Three paths

### Path 1 — Ship what exists  (2–3 days)  ← **do this regardless**
Paired test, write-up, public repo, send to Julian. Closes the commitment with 10 days spare.

### Path 2 — Add the calibration-budget surface  (+1–2 days)
Path 1 plus §3. Turns a plot into a tool. **Recommended.**

### Path 3 — Make it a preprint  (3–6 weeks)
Path 2 plus: a second dataset (**HD-FW KIN** — 21 subjects and it has genuine *wrist* arrays,
which fixes the montage objection), a 1-D CNN to show the law is not a ridge artifact, a
channel-count ablation, and pooling across datasets to push N past 16.

**Do not decide Path 3 now.** Decide it after seeing whether Julian engages, and against the
OPT clock. It is real work with a real payoff — first-author preprint, live topic, exactly the
sensor/signal-ML lane — but it is also precisely the shape of thing the 15 Aug audit says
starts and does not finish.

---

## 5. What NOT to do

- **Do not chase a better model.** Ridge is the control. A CNN raises accuracy and answers a
  question nobody asked.
- **Do not claim anything about sweat, drift, or a full shift.** Hyser cannot support it.
- **Do not extrapolate past ~100 wearers** without saying loudly that it is extrapolation.
- **Do not fold in Ninapro or a third dataset before Path 1 ships.**

---

## 6. Next steps

| # | Step | State |
|---|---|---|
| 1 | Wilcoxon signed-rank + paired-dots panel | ✅ done — p = 0.0027, holds without the outlier |
| 2 | Two-panel figure, CVD-validated palette | ✅ done |
| 3 | Private GitHub repo + changelog | ✅ done |
| 4 | Prior-art check | ✅ done — see §1b, claim survives and is now precisely bounded |
| 5 | **README rewritten as findings, not scaffolding** | next, ~2 h |
| 6 | **Email to Julian** — figure, three sentences, caveats | next, ~1 h |
| 7 | Calibration-budget surface (§3) | optional, ~1 day |
| 8 | Flip repo public when the email goes out | 5 min |

**Path 1 is steps 5, 6, 8 — about half a day.** Step 7 is the only real decision left.

**Deadline is 31 Aug. Today is the 19th. This finishes early or it does not finish at all.**
