# EMG → force: does cross-subject accuracy improve with more wearers?

**The question.** Meta removed per-user calibration for *gesture* decoding by training on
6,500+ participants and described the result as a scaling law. Nobody has published the
equivalent experiment for *force*. Hemlock's whole strategy rests on the answer, and
ForceBand's own released checkpoint shows the problem exists: it zero-shots onto a new rig
at negative R², and their README says it "transfers in shape but not absolute scale."

**The test.** On public data, no hardware. Plot force error against the number of *training
subjects*, leave-one-subject-out, with a per-user-calibrated reference line for context.

---

## What comes out

One figure: `results/scaling_curve.png`

- **Blue** — zero-shot MAE on a wearer the model has never seen, vs. training-set size.
- **Orange dashed** — the per-user-calibrated ceiling (train on that subject's session 1,
  test on session 2). This is what a calibration ritual buys you.
- The gap between them is the calibration tax. **The question is whether the blue line bends
  toward the orange one as subjects are added.**

If it bends: the tax is a data problem, and the roadmap is "get to N wearers."
If it is flat out to N=16: the effect is not visible at this scale — which is a real finding,
and see the caveats before calling it a null.

---

## Data

[Hyser](https://physionet.org/content/hd-semg/2.0.0/) (PhysioNet, Jiang et al., IEEE TNSRE
2021). 20 subjects × 2 sessions on **separate days**, 256-channel HD-sEMG @ 2048 Hz, 5-channel
finger force @ 100 Hz.

**We download ~18 GB, not 143 GB** — only `mvc/` (7.8 GB, for %MVC normalisation) and
`random/` (9.8 GB, unscripted finger combinations, the closest thing to natural varied-force
manipulation). `random/` also has a published comparable: Jiang 2021 reports ≈8.57 %MVC RMSE
within-day, which is the sanity anchor for the calibrated arm.

---

## Run it

```bash
pip install -r requirements.txt

make smoke              # synthetic data, ~30 s - proves the harness runs before you download
make sweep plot         # look at results/scaling_curve.png, then delete results/cache

make fetch              # ~18 GB from PhysioNet (wget -c, resumable)
make check              # VERIFY THE MONTAGE - see below. Do this before trusting anything.
make prepare            # filter, window, featurise, %MVC-normalise -> results/cache/
make sweep              # LOSO × training-set-size sweep + bootstrap CIs
make plot
```

---

## Method

```
256-ch EMG @2048 Hz → subsample to 8 "wrist band" channels
                    → 20–450 Hz Butterworth + 50 Hz notch (Q=30), zero phase
                    → 200 ms windows / 100 ms hop
                    → RMS, MAV, WL, ZC, SSC per channel
5-ch force @100 Hz  → sampled at window ends → %MVC per subject (95th pct of MVC trials)
model               → RidgeCV on standardised features
```

**Why ridge and not a network.** The question is whether error falls with *subject count*.
A large model would confound that with capacity. Ridge isolates the variable. If the curve
bends under ridge, it will bend harder under a real model; if it does not bend under ridge,
that is the more interesting result and worth reporting before adding parameters.

**Why zero-phase filtering.** This is offline analysis, so `sosfiltfilt` is correct. A live
pipeline must use a causal single pass — the two give different onset timing, and mixing them
is a classic source of EMG results that do not reproduce.

---

## ⚠️ Do this before trusting any number

**Verify the montage.** `config.yaml` picks 8 of 256 channels to imitate a wrist band
(2 per grid, distal row). **Those indices are a placeholder.** `make check` prints the real
channel count and signal names from an actual record; confirm against the Hyser documentation
which physical grid and row each index maps to, then fix `config.yaml`. Everything downstream
depends on this and a wrong montage will produce a confident, wrong curve.

---

## Caveats that must ship with the result

These make the finding more credible, not less. Put them in the email.

1. **Hyser force is %MVC. ForceBand is Newtons. The two are not comparable in level.**
   The transferable claim is the *shape of the curve*, never the absolute number.
2. **20 subjects caps the sweep at N=16.** Meta's effect appeared at *thousands*. A flat curve
   here does **not** show that force fails to scale — it shows the effect is not visible below
   16 subjects. Stating this is the difference between a credible result and one an investor's
   technical diligence takes apart.
3. **An 8-channel subsample of an HD grid is not a wristband.** Different electrode size,
   spacing, contact impedance, and no donning variability. It is an approximation of the
   geometry, not of the product.
4. **Hyser is lab data.** Seated, scripted, clean. It says nothing about sweat, band migration
   or fatigue across a shift — which is the failure mode the product actually meets.
5. **The calibrated reference is cross-day within subject**, which is a friendlier setting than
   cross-day *and* re-donned. Treat it as an optimistic ceiling.

## Method commitments

- Leave-one-subject-out only. Never a random split over windows.
- Bootstrap CIs on every number.
- Fixed seed; every training subset logged in `results/raw_results.csv`.
- `make all` reproduces the figure from scratch.
- Report the negative result as loudly as the positive one.
