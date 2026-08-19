"""Sanity-check the cache before committing to the full download and sweep.

Three questions, in order of how badly a wrong answer would hurt:
  1. Did %MVC normalisation actually happen, and are the numbers physiological?
  2. Is EMG amplitude related to force at all? (alignment / montage sanity)
  3. Within one subject, cross-day, can ridge predict force? If not, nothing downstream works.

Run: make inspect
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import yaml
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
FINGERS = ["thumb", "index", "middle", "ring", "little"]


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    files = sorted(glob.glob(str(ROOT / cfg["output"]["results_dir"] / "cache" / "*.npz")))
    if not files:
        print("no cache. Run: make prepare LIMIT=2")
        return 1

    print(f"{len(files)} cached subject-session(s)\n")
    print("=" * 78)
    print("1. CACHE + NORMALISATION")
    print("=" * 78)
    subs: dict[int, dict[int, tuple]] = {}
    bad_ref = 0
    for f in files:
        d = np.load(f, allow_pickle=True)
        X, y = d["X"], d["y"]
        units = str(d["units"]) if "units" in d else "?"
        src = str(d["ref_source"]) if "ref_source" in d else "?"
        if src != "mvc_trials":
            bad_ref += 1
        stem = Path(f).stem
        subj = int(stem.split("_")[1]); sess = int(stem.split("session")[1])
        subs.setdefault(subj, {})[sess] = (X, y)
        print(f"{stem}   X{X.shape}  y{y.shape}  units={units}  ref={src}")
        print(f"    mvc_ref (V) : {np.round(d['mvc_ref'], 4)}")
        p1, p99 = np.percentile(y, [1, 99], axis=0)
        print(f"    y  1st pct  : {np.round(p1, 1)}")
        print(f"    y 99th pct  : {np.round(p99, 1)}")
        print(f"    |y| > 100%  : {100 * np.mean(np.abs(y) > 100):.1f}% of samples")

    print()
    if bad_ref:
        print(f"!! {bad_ref} file(s) not normalised from MVC trials - fetch mvc_dataset and rebuild.")
    else:
        print("OK  every file normalised from real MVC trials.")
    print("    Expect most |y| under 100 %MVC. A few percent over is normal (random task can")
    print("    briefly exceed the MVC reference). Tens of percent over means the reference is wrong.")

    print("\n" + "=" * 78)
    print("2. IS EMG RELATED TO FORCE AT ALL?")
    print("=" * 78)
    X0, y0 = next(iter(subs.values()))[1]
    # Feature layout is FEATURE-MAJOR: [rms(nch), mav(nch), wl(nch), zc(nch), ssc(nch)].
    # So RMS is the FIRST nch columns - not every k-th column.
    nch = cfg["montage"]["n_channels"]
    names = cfg["signal"]["features"]
    i_rms = names.index("rms")
    rms = X0[:, i_rms * nch:(i_rms + 1) * nch].mean(axis=1)
    ext = X0[:, i_rms * nch:i_rms * nch + nch // 2].mean(axis=1)   # ED-* channels
    flx = X0[:, i_rms * nch + nch // 2:(i_rms + 1) * nch].mean(axis=1)  # FD-* channels
    print(f"    {'finger':8s} {'all 8ch':>9s} {'extensor':>9s} {'flexor':>9s}")
    for i, fg in enumerate(FINGERS):
        a = np.corrcoef(rms, np.abs(y0[:, i]))[0, 1]
        e = np.corrcoef(ext, np.abs(y0[:, i]))[0, 1]
        f_ = np.corrcoef(flx, np.abs(y0[:, i]))[0, 1]
        print(f"    {fg:8s} {a:+9.3f} {e:+9.3f} {f_:+9.3f}")
    print("    Correlations vs |force|, split by array. Extensor and flexor pulling in")
    print("    opposite directions is normal antagonist behaviour, not a bug. All three")
    print("    columns near 0.00 for every finger would mean alignment or montage is broken.")

    print("\n" + "=" * 78)
    print("3. WITHIN-SUBJECT, CROSS-DAY RIDGE  (the go / no-go)")
    print("=" * 78)
    alphas = cfg["sweep"]["ridge_alphas"]
    any_ok = False
    for subj, d in sorted(subs.items()):
        if 1 not in d or 2 not in d:
            continue
        Xtr, ytr = d[1]
        Xte, yte = d[2]
        m = make_pipeline(StandardScaler(), RidgeCV(alphas=alphas)).fit(Xtr, ytr)
        pred = m.predict(Xte)
        mae = np.mean(np.abs(yte - pred), axis=0)
        r2 = [r2_score(yte[:, i], pred[:, i]) for i in range(yte.shape[1])]
        print(f"\n  subject {subj:02d}  (train session1 -> test session2)")
        print(f"    {'finger':8s} {'MAE %MVC':>10s} {'R2':>8s}")
        for i, fg in enumerate(FINGERS):
            print(f"    {fg:8s} {mae[i]:10.2f} {r2[i]:8.3f}")
        print(f"    {'MEAN':8s} {mae.mean():10.2f} {np.mean(r2):8.3f}")
        if np.mean(r2[:3]) > 0.1:
            any_ok = True

    print("\n" + "-" * 78)
    if any_ok:
        print("GO. Thumb/index/middle R2 is positive - the pipeline extracts real signal.")
        print("    Jiang 2021 reports ~8.6 %MVC RMSE within-day on 256 channels; we use 8, so a")
        print("    larger error here is expected and fine. Proceed to the full download.")
    else:
        print("NO-GO. Ridge cannot predict force even within one subject across days.")
        print("    Do not download 5 GB yet. Suspects, in order: force/EMG time alignment,")
        print("    the montage, or window/hop settings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
