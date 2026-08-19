"""The calibration-budget surface: given N wearers in the corpus, how many seconds
of per-user calibration do you still need?

`sweep.py` answers "do more wearers help?" — a curve. This answers the question a
product actually has to spec: **the trade between corpus size and the length of the
out-of-box calibration ritual.** That is a surface, not a curve.

Design
------
Everything here is evaluated on ONE test set, so every cell is comparable:

    test          : held-out subject's session 2, in full
    calibration   : k seconds drawn from that same subject's session 1
    corpus        : N other subjects, both sessions

So every number on this surface is **cross-day and re-donned** — the honest setting,
matching `calibrated_crossday` in sweep.py rather than the optimistic within-session one.
The surface contains the existing reference points as its corners:

    N=16, k=0     -> zero-shot (sweep.py's headline, re-scored on session 2 only)
    N=0,  k=124   -> calibrated_crossday (train on all of session 1, test on session 2)

How the k seconds are spent
---------------------------
    contiguous : the FIRST k seconds of session 1. A user sits down and does the
                 ritual once. This is the headline — it is what a product ships.
    spread     : k seconds' worth of windows sampled evenly across session 1. The user
                 cannot literally do this in k seconds; it stands for an idealised
                 protocol that covers the force range instead of whatever happens to
                 come first. Read it as "what a well-designed k-second protocol could
                 aim at", NOT as an achievable number and NOT as a bound.

How the k seconds are used
--------------------------
Naive pooling (concatenate k s of the target onto 40,000 population windows) is not
tested: 50 windows against 40,000 cannot move a ridge fit, so it would report "no
effect" as a property of the arithmetic rather than of the data. The two methods here
are the ones a product would actually ship:

    affine   : per-finger gain and offset on the population model's predictions.
               Ten free parameters. This is "calibration" in the sense a hardware
               person means it — fix the scale, keep the shape. ForceBand's own README
               says its model "transfers in shape but not absolute scale", which is
               exactly the failure this repairs.
    finetune : prior-mean ridge. Fit a ridge correction on the population model's
               RESIDUALS over the calibration window, in the population model's own
               standardised feature space. Equivalent to fine-tuning the weights with
               the population solution as the prior mean; lambda -> inf recovers the
               population model, lambda -> 0 recovers a per-user fit.

    peruser  : N=0 only. Plain ridge on the k seconds alone, no corpus. This is the
               status-quo column — what you get today with no data flywheel.

lambda is chosen by a TEMPORAL inner split of the calibration window (first 70% fit,
last 30% score), never by LOO-CV: windows overlap 50%, so any random inner split
leaks. Below `min_inner_windows` the split is not viable and the most conservative
lambda is used instead.

That selection has a blind spot worth stating out loud, because it turns out to
matter: the inner split lives entirely inside session 1, so it scores lambda on the
SAME donning it was fitted on. It cannot see the band come off. Every lambda on the
grid is therefore also scored directly on the test set and written out as
`finetune_grid` — an ORACLE, not a method, and never to be quoted as an achievable
result. Its only job is to separate "weight-level adaptation does not work here" from
"weight-level adaptation cannot be tuned without cross-day data", which are very
different sentences.

Rules inherited from sweep.py and not up for renegotiation:
  * leave-one-subject-out, never a random split over windows
  * bootstrap CIs on every reported number
  * fixed seed, subsets logged, reruns identically
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.linear_model import Ridge
from tqdm import tqdm

from .sweep import boot_ci, load_cache, load_cfg, make_model, stack, _mae

ROOT = Path(__file__).resolve().parents[1]

# Seconds of calibration to test. The cache is 1240 windows per session at a 100 ms
# hop = 124.0 s, so 120 s is 96.8% of the session and effectively "calibrate on
# everything" — which is why it should land on calibrated_crossday.
CAL_SECONDS = [0, 5, 15, 30, 60, 120]

# Prior-mean ridge penalty. Deliberately wide and deliberately biased high: with 50
# calibration windows and 40 features, the honest answer is usually "barely move".
LAMBDAS = [1.0, 10.0, 100.0, 1_000.0, 10_000.0, 100_000.0]

MIN_INNER_WINDOWS = 30  # below this the temporal inner split is not viable
HOP_MS = 100  # from config.signal.hop_ms; asserted against config at run time


def cal_index(n_windows: int, k_windows: int, selection: str) -> np.ndarray:
    """Which windows of session 1 the user's k seconds buy."""
    k_windows = min(k_windows, n_windows)
    if k_windows <= 0:
        return np.empty(0, dtype=int)
    if selection == "contiguous":
        return np.arange(k_windows)
    if selection == "spread":
        return np.unique(np.linspace(0, n_windows - 1, k_windows).round().astype(int))
    raise ValueError(selection)


def pick_lambda(Z: np.ndarray, r: np.ndarray) -> float:
    """Choose the prior-mean ridge penalty on a temporal inner split of the
    calibration window. First 70% fits, last 30% scores. Never a random split."""
    n = len(Z)
    cut = int(0.7 * n)
    if cut < MIN_INNER_WINDOWS or n - cut < 10:
        return max(LAMBDAS)
    best, best_mae = max(LAMBDAS), np.inf
    for lam in LAMBDAS:
        m = Ridge(alpha=lam).fit(Z[:cut], r[:cut])
        e = _mae(r[cut:], m.predict(Z[cut:]))
        if e < best_mae:
            best, best_mae = lam, e
    return best


def adapt_affine(yhat_cal, y_cal, yhat_te):
    """Per-finger gain and offset fitted on the calibration window.

    Ten parameters total. Robust at 5 s because it is asking almost nothing of the
    data: keep the population model's shape, fix its scale.
    """
    out = np.empty_like(yhat_te)
    for j in range(yhat_te.shape[1]):
        x, y = yhat_cal[:, j], y_cal[:, j]
        v = x.var()
        if v < 1e-12 or len(x) < 3:
            out[:, j] = yhat_te[:, j]
            continue
        a = float(np.cov(x, y, bias=True)[0, 1] / v)
        b = float(y.mean() - a * x.mean())
        out[:, j] = a * yhat_te[:, j] + b
    return out


def main() -> int:
    cfg = load_cfg()
    sw, out_cfg = cfg["sweep"], cfg["output"]
    results_dir = ROOT / out_cfg["results_dir"]
    rng = np.random.default_rng(sw["seed"])

    hop_ms = int(cfg["signal"]["hop_ms"])
    if hop_ms != HOP_MS:
        raise SystemExit(f"hop_ms is {hop_ms} in config but this module assumes {HOP_MS}")
    win_per_s = 1000 // hop_ms

    data = load_cache(results_dir)
    subjects = sorted(data)
    held_out = [s for s in subjects if 1 in data[s] and 2 in data[s]]
    print(f"{len(subjects)} subjects cached; {len(held_out)} have both sessions")

    n_win = {s: len(data[s][1][0]) for s in held_out}
    print(f"session-1 length: {min(n_win.values())}-{max(n_win.values())} windows "
          f"({min(n_win.values())/win_per_s:.0f}-{max(n_win.values())/win_per_s:.0f} s)")

    train_sizes = list(sw["train_sizes"])
    rows: list[dict] = []

    # ---- N = 0: no corpus at all. Plain ridge on the k seconds. The status quo. ----
    for s in tqdm(held_out, desc="N=0 per-user"):
        Xc_all, yc_all = data[s][1]
        Xte, yte = data[s][2]
        for sel in ("contiguous", "spread"):
            for ksec in CAL_SECONDS:
                if ksec == 0:
                    continue  # no corpus and no calibration is not a model
                idx = cal_index(len(Xc_all), ksec * win_per_s, sel)
                if len(idx) < 10:
                    continue
                Xc, yc = Xc_all[idx], yc_all[idx]
                m = make_model(sw["ridge_alphas"]).fit(Xc, yc)
                rows.append(dict(method="peruser", n_train_subjects=0, cal_seconds=ksec,
                                 selection=sel, held_out=s, rep=0,
                                 mae=_mae(yte, m.predict(Xte)), lam=np.nan))

    # ---- N >= 1: population model, then adapt it on k seconds ----
    total = len(held_out) * len(train_sizes) * sw["repeats"]
    with tqdm(total=total, desc="corpus x calibration") as bar:
        for s in held_out:
            pool = [t for t in subjects if t != s]
            Xc_all, yc_all = data[s][1]
            Xte, yte = data[s][2]

            for n in train_sizes:
                if n > len(pool):
                    bar.update(sw["repeats"])
                    continue
                for rep in range(sw["repeats"]):
                    pick = rng.choice(pool, size=n, replace=False)
                    Xtr = np.concatenate([stack(data[t])[0] for t in pick])
                    ytr = np.concatenate([stack(data[t])[1] for t in pick])
                    pop = make_model(sw["ridge_alphas"]).fit(Xtr, ytr)

                    # The population model's own standardised space — the fine-tune
                    # correction lives here, so it inherits the population scaler
                    # rather than re-deriving one from 50 windows.
                    scaler = pop.named_steps["standardscaler"]
                    yhat_te = pop.predict(Xte)
                    yhat_cal_all = pop.predict(Xc_all)
                    Z_all = scaler.transform(Xc_all)
                    resid_all = yc_all - yhat_cal_all
                    Z_te = scaler.transform(Xte)

                    base = dict(n_train_subjects=n, held_out=s, rep=rep,
                                train_subjects=",".join(map(str, sorted(pick))))

                    # k = 0: the zero-shot cell, scored on session 2 only.
                    zs = _mae(yte, yhat_te)
                    for sel in ("contiguous", "spread"):
                        for meth in ("affine", "finetune"):
                            rows.append(dict(method=meth, cal_seconds=0, selection=sel,
                                             mae=zs, lam=np.nan, **base))

                    for sel in ("contiguous", "spread"):
                        for ksec in CAL_SECONDS:
                            if ksec == 0:
                                continue
                            idx = cal_index(len(Xc_all), ksec * win_per_s, sel)
                            if len(idx) < 3:
                                continue
                            y_cal = yc_all[idx]

                            rows.append(dict(
                                method="affine", cal_seconds=ksec, selection=sel,
                                mae=_mae(yte, adapt_affine(yhat_cal_all[idx], y_cal, yhat_te)),
                                lam=np.nan, **base))

                            Z, r = Z_all[idx], resid_all[idx]
                            chosen = pick_lambda(Z, r)
                            for lam in LAMBDAS:
                                corr = Ridge(alpha=lam).fit(Z, r)
                                e = _mae(yte, yhat_te + corr.predict(Z_te))
                                # the honest arm: lambda picked without seeing session 2
                                if lam == chosen:
                                    rows.append(dict(method="finetune", cal_seconds=ksec,
                                                     selection=sel, mae=e, lam=lam, **base))
                                # the oracle arm: every lambda, scored on the test set
                                rows.append(dict(method="finetune_grid", cal_seconds=ksec,
                                                 selection=sel, mae=e, lam=lam, **base))
                    bar.update(1)

    df = pd.DataFrame(rows)
    df.to_csv(results_dir / "budget_raw.csv", index=False)

    # Collapse reps first: the unit of analysis is the SUBJECT, not the fit. Bootstrapping
    # over 200 runs when there are only 20 wearers would report a CI for a sample size we
    # do not have. Mean over reps per subject, then bootstrap over subjects.
    # lambda is a FACTOR for finetune_grid (we sweep it on purpose) but an OUTCOME for
    # finetune (the inner split picks it, and it differs per subject and per rep).
    # Grouping the honest arm by lambda would split it into subgroups and average the
    # subgroup means with equal weight — which is not the mean over subjects.
    df["lam_key"] = np.where(df["method"] == "finetune_grid", df["lam"].fillna(-1.0), -1.0)
    keys = ["method", "selection", "n_train_subjects", "cal_seconds", "lam_key"]
    per_subj = df.groupby(keys + ["held_out"], dropna=False)["mae"].mean().reset_index()

    # win rate answers "did spending k seconds help THIS wearer?" — so the baseline is
    # the k=0 cell at the same corpus size and the same held-out subject. At k=0 no
    # adaptation has happened, so that cell is identical across methods by construction;
    # take it once, from affine.
    base0 = (per_subj[(per_subj.cal_seconds == 0) & (per_subj.method == "affine")]
             .groupby(["selection", "n_train_subjects", "held_out"])["mae"]
             .mean().rename("mae0").reset_index())

    summ = []
    for k, g in per_subj.groupby(keys, dropna=False):
        meth, sel, n, ksec, lam = k
        mu, lo, hi = boot_ci(g["mae"].tolist(), sw["bootstrap"], rng)
        cmp = g.merge(base0, on=["selection", "n_train_subjects", "held_out"], how="left")
        wins = (float((cmp["mae"] < cmp["mae0"]).mean())
                if cmp["mae0"].notna().all() and ksec > 0 else np.nan)
        summ.append(dict(method=meth, selection=sel, n_train_subjects=int(n),
                         cal_seconds=int(ksec), lam=(None if lam < 0 else lam),
                         mae=mu, lo=lo, hi=hi, median=float(g["mae"].median()),
                         win_rate_vs_k0=wins, n_subjects=len(g)))
    sdf = pd.DataFrame(summ).sort_values(["method", "selection", "n_train_subjects", "cal_seconds", "lam"])
    sdf.to_csv(results_dir / "budget_summary.csv", index=False)

    (results_dir / "budget_config.json").write_text(json.dumps(
        dict(cal_seconds=CAL_SECONDS, lambdas=LAMBDAS, hop_ms=hop_ms,
             min_inner_windows=MIN_INNER_WINDOWS, seed=sw["seed"],
             repeats=sw["repeats"], train_sizes=train_sizes,
             test="held-out subject session 2, full",
             calibration="held-out subject session 1, first k s (contiguous) or "
                         "k s of windows evenly spaced (spread)"), indent=2))

    head = sdf[(sdf.selection == "contiguous") & (sdf.method.isin(["affine", "peruser"]))]
    print("\ncontiguous calibration, affine adaptation (peruser at N=0)")
    print(head.pivot_table(index="cal_seconds", columns="n_train_subjects",
                           values="mae").round(2).to_string())
    print(f"\nwrote {results_dir/'budget_raw.csv'} and {results_dir/'budget_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
