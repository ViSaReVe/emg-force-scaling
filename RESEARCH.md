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

| # | Step | Cost |
|---|---|---|
| 1 | Wilcoxon signed-rank on the 20 paired differences; add a paired-dots panel | 1 h |
| 2 | Calibration-budget sweep (§3) | 1 day |
| 3 | README rewritten as findings, not scaffolding; results committed | 2 h |
| 4 | Push public to GitHub | 30 min |
| 5 | Email to Julian: figure + three sentences + caveats | 1 h |

Steps 1, 3, 4, 5 are Path 1. Step 2 decides itself once you see how long step 1 takes.

**Deadline is 31 Aug. Today is the 19th. This finishes early or it does not finish at all.**
