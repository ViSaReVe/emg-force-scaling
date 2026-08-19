# Runbook — run these in order

You are in `~/Documents/Projects/emg-force-scaling`. Each step says what "good" looks like.
**If a step's check fails, stop there and paste the output — do not run the next one.**

---

## 1 · Environment  (2 min, once)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

✅ **Good:** `wfdb`, `scipy`, `scikit-learn` install without errors.
Your prompt should now start with `(.venv)` instead of `(base)`.

> Every step below assumes `.venv` is active. New terminal? `source .venv/bin/activate` first.

---

## 2 · Smoke test — prove the harness runs before downloading anything  (1 min)

```bash
python -m src.smoke
python -m src.sweep
python -m src.plot
open results/scaling_curve.png
```

✅ **Good:** a summary table prints, a figure opens, MAE falls as `n_train_subjects` rises.
This is **synthetic data** — it proves the code runs and nothing else.

### Then delete it, or it will contaminate the real run

```bash
rm -rf results/cache results/*.csv results/*.png results/run_config.json
```

---

## 3 · Plan the download  (10 s)

```bash
python -m src.fetch --check
```

✅ **Good:** `records : 400 -> 800 files`, a real per-file size probe, and an estimated total
around **4–6 GB**. If the probe says 0.00 MB you have no network to PhysioNet.

```bash
df -h .
```

---

## 4 · Download two subjects first  (~2 min, ~250 MB)

Never start a 5 GB transfer before proving one file parses.

```bash
python -m src.fetch --limit-subjects 2
```

✅ **Good:** `done. N downloaded, 0 failed.`
Re-run the same command if it drops — completed files are skipped.

---

## 5 · ⚠️ THE GATE — does the montage resolve?  (5 s)

```bash
make check
```

✅ **Good — you must see this:**
```
montage       : resolved by_name
  -> indices  : [...]
  in range    : YES
```

❌ **If it says `by_index_FALLBACK`**, the channel names did not match. **Stop.** Paste the
whole output, including the `available (first 12)` line. Everything downstream is wrong if
this is wrong, and a bad montage still draws a smooth, believable curve.

Also check the printed `shape` is `(n_samples, 256)` for an EMG record and `fs` is `2048`.

---

## 6 · Build features for those two subjects  (~2 min)

```bash
make prepare LIMIT=2
ls -la results/cache/
```

✅ **Good:** four `.npz` files (2 subjects × 2 sessions), each a few MB.

### Actually look at the data before trusting any of it

```bash
python - <<'PY'
import numpy as np, glob
f = sorted(glob.glob("results/cache/*.npz"))[0]
d = np.load(f); X, y = d["X"], d["y"]
print(f"{f}\n  X {X.shape}   y {y.shape}")
print(f"  force per finger (N):  min {y.min(0).round(2)}   max {y.max(0).round(2)}")
print(f"  feature range: {X.min():.3g} .. {X.max():.3g}")
print(f"  NaNs -> X:{np.isnan(X).sum()}  y:{np.isnan(y).sum()}")
PY
```

✅ **Good:** force maxima are plausible finger forces in Newtons (single digits to a few tens,
not 0.001 and not 5000). No NaNs. If forces look like 0–1 or 0–100 with no unit sense, say so —
the `.hea` scaling may need checking before anything else runs.

---

## 7 · Download the rest  (~5 GB — start it and walk away)

```bash
make fetch
```

Resumable. If it stops, run it again.

---

## 8 · Full prepare  (slow — time it on 2 subjects first)

```bash
rm -rf results/cache
time make prepare
```

✅ **Good:** 40 `.npz` files in `results/cache/`.
If step 6 took ~2 min for 2 subjects, expect roughly 20 min for 20.

---

## 9 · The sweep  (the actual experiment)

```bash
time make sweep
```

Full settings: 20 held-out subjects × 5 training sizes × 10 repeats = 1000 ridge fits.
**Do a short version first** if you want a number tonight — edit `config.yaml`:
`repeats: 3`, `held_out_subjects: [1,2,3,4,5]`, then rerun with full settings later.

✅ **Good:** a summary table with `mae`, `lo`, `hi` per training size, plus a `calibrated` row.

---

## 10 · The figure

```bash
make plot
open results/scaling_curve.png
```

Then send me `results/summary.csv` and the PNG and we read it together.

---

## ⚠️ zsh and `#` comments

Interactive zsh does **not** treat `#` as a comment by default. Pasting
`make fetch   # ~5 GB` runs `make fetch`, then tries to run `#` and `~5`, and you get
`zsh: not enough directory stack entries`. Either paste commands without the trailing
comments, or turn comments on once:

```bash
echo 'setopt interactivecomments' >> ~/.zshrc && source ~/.zshrc
```

---

## Quick reference

| | |
|---|---|
| New terminal | `source .venv/bin/activate` |
| Everything from scratch | `make clean && make prepare sweep plot` |
| Resume a failed download | re-run the same `fetch` command |
| Faster download | `python -m src.fetch --jobs 12` |
| Unfiltered EMG instead | `python -m src.fetch --types force raw` |
