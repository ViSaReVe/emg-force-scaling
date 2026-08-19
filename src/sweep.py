"""The experiment: does cross-subject force error fall as training subjects rise?

Design
------
PRIMARY (zero-shot):   hold out subject S entirely. Train on a random subset of N
                       other subjects (both sessions). Evaluate on S. Sweep N.
REFERENCE (calibrated): train on S's own session 1, test on S's session 2.
                       This is the per-user-calibration ceiling and it is what the
                       scaling curve has to approach for calibration to become optional.

Rules, non-negotiable:
  * leave-one-subject-out only, never a random split over windows
  * bootstrap CIs on every reported number
  * fixed seed, subsets logged, so the whole thing reruns identically
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config.yaml"


def load_cfg() -> dict:
    with open(CFG) as fh:
        return yaml.safe_load(fh)


def load_cache(results_dir: Path) -> dict[int, dict[int, tuple[np.ndarray, np.ndarray]]]:
    cache = results_dir / "cache"
    out: dict[int, dict[int, tuple[np.ndarray, np.ndarray]]] = {}
    for f in sorted(cache.glob("subject_*_session*.npz")):
        subj = int(f.stem.split("_")[1])
        sess = int(f.stem.split("session")[1])
        d = np.load(f)
        out.setdefault(subj, {})[sess] = (d["X"], d["y"])
    if not out:
        raise SystemExit(f"no cached arrays in {cache}. Run `make prepare` first.")
    return out


def make_model(alphas):
    # RidgeCV over a small grid, standardised features. Boring on purpose.
    from sklearn.linear_model import RidgeCV

    return make_pipeline(StandardScaler(), RidgeCV(alphas=alphas))


def stack(sub: dict[int, tuple[np.ndarray, np.ndarray]], sessions=None):
    sessions = sessions or sorted(sub)
    Xs = [sub[s][0] for s in sessions if s in sub]
    ys = [sub[s][1] for s in sessions if s in sub]
    return np.concatenate(Xs), np.concatenate(ys)


def _mae(y, yhat) -> float:
    return float(np.mean(np.abs(y - yhat)))


def boot_ci(vals: list[float], n: int, rng: np.random.Generator, lo=2.5, hi=97.5):
    a = np.asarray(vals, dtype=float)
    if a.size == 0:
        return (np.nan, np.nan, np.nan)
    draws = rng.choice(a, size=(n, a.size), replace=True).mean(axis=1)
    return float(a.mean()), float(np.percentile(draws, lo)), float(np.percentile(draws, hi))


def main() -> int:
    cfg = load_cfg()
    sw, out_cfg = cfg["sweep"], cfg["output"]
    results_dir = ROOT / out_cfg["results_dir"]
    rng = np.random.default_rng(sw["seed"])

    data = load_cache(results_dir)
    subjects = sorted(data)
    held_out = subjects if sw["held_out_subjects"] == "all" else list(sw["held_out_subjects"])
    print(f"{len(subjects)} subjects cached; holding out {len(held_out)}")

    rows = []

    # --- reference arms: what per-user calibration actually buys ---
    #  calibrated_within  : train on the first 60% of a session, test on the last 40% of the
    #                       SAME session. This is ForceBand's setting - calibrate and use
    #                       immediately, band never removed. The optimistic ceiling.
    #  calibrated_crossday: train on session 1, test on session 2 - a different day and a
    #                       re-donned band. What a product actually faces every morning.
    #  The gap between them is the cost of taking the band off and putting it back on.
    #  Split is temporal, never random: windows overlap by 50%, so a random split leaks.
    for s in tqdm(held_out, desc="reference arms"):
        for sess in sorted(data[s]):
            X, y = data[s][sess]
            cut = int(0.6 * len(X))
            if cut < 50 or len(X) - cut < 50:
                continue
            m = make_model(sw["ridge_alphas"]).fit(X[:cut], y[:cut])
            rows.append(dict(arm="calibrated_within", n_train_subjects=0, held_out=s,
                             rep=sess, mae=_mae(y[cut:], m.predict(X[cut:]))))

        if 1 in data[s] and 2 in data[s]:
            Xtr, ytr = data[s][1]
            Xte, yte = data[s][2]
            m = make_model(sw["ridge_alphas"]).fit(Xtr, ytr)
            rows.append(dict(arm="calibrated_crossday", n_train_subjects=0, held_out=s, rep=0,
                             mae=_mae(yte, m.predict(Xte))))

    # --- primary: zero-shot vs number of training subjects ---
    total = len(held_out) * len(sw["train_sizes"]) * sw["repeats"]
    with tqdm(total=total, desc="zero-shot sweep") as bar:
        for s in held_out:
            pool = [t for t in subjects if t != s]
            Xte, yte = stack(data[s])
            for n in sw["train_sizes"]:
                if n > len(pool):
                    bar.update(sw["repeats"])
                    continue
                for rep in range(sw["repeats"]):
                    pick = rng.choice(pool, size=n, replace=False)
                    Xtr = np.concatenate([stack(data[t])[0] for t in pick])
                    ytr = np.concatenate([stack(data[t])[1] for t in pick])
                    m = make_model(sw["ridge_alphas"]).fit(Xtr, ytr)
                    rows.append(dict(arm="zero_shot", n_train_subjects=n, held_out=s, rep=rep,
                                     mae=_mae(yte, m.predict(Xte)),
                                     train_subjects=",".join(map(str, sorted(pick)))))
                    bar.update(1)

    df = pd.DataFrame(rows)
    df.to_csv(results_dir / "raw_results.csv", index=False)

    summ = []
    for n, g in df[df.arm == "zero_shot"].groupby("n_train_subjects"):
        mu, lo, hi = boot_ci(g["mae"].tolist(), sw["bootstrap"], rng)
        summ.append(dict(arm="zero_shot", n_train_subjects=int(n), mae=mu, lo=lo, hi=hi, n_runs=len(g)))
    for arm in ("calibrated_within", "calibrated_crossday"):
        cal = df[df.arm == arm]
        if len(cal):
            mu, lo, hi = boot_ci(cal["mae"].tolist(), sw["bootstrap"], rng)
            summ.append(dict(arm=arm, n_train_subjects=0, mae=mu, lo=lo, hi=hi, n_runs=len(cal)))
    sdf = pd.DataFrame(summ)
    sdf.to_csv(results_dir / "summary.csv", index=False)

    (results_dir / "run_config.json").write_text(json.dumps(cfg, indent=2))
    print("\n" + sdf.to_string(index=False))
    print(f"\nwrote {results_dir/'raw_results.csv'} and {results_dir/'summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
