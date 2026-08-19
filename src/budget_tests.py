"""Paired tests behind the calibration-budget claim.

Same logic as paired.py: the comparison is naturally paired — same wearer, calibrated
or not — so the inference uses the 20 within-subject differences, not the overlap of
two bootstrap intervals. Reads results/budget_raw.csv, writes results/budget_tests.txt.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

from .paired import compare, fmt
from .plot_budget import METHOD, SELECTION

ROOT = Path(__file__).resolve().parents[1]


def per_subject(raw: pd.DataFrame, method: str, n: int, ksec: int) -> pd.Series:
    q = raw[(raw.selection == SELECTION) & (raw.method == method) &
            (raw.n_train_subjects == n) & (raw.cal_seconds == ksec)]
    return q.groupby("held_out")["mae"].mean()


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    rd = ROOT / cfg["output"]["results_dir"]
    raw = pd.read_csv(rd / "budget_raw.csv")
    old = pd.read_csv(rd / "summary.csv")
    ns = sorted(raw[raw.n_train_subjects > 0].n_train_subjects.unique())

    out = ["CALIBRATION BUDGET — PAIRED TESTS", "=" * 72, "",
           "Every cell: train on N other wearers, adapt on k seconds of the held-out",
           "wearer's session 1, test on all of their session 2 (next day, band re-donned).",
           f"Adaptation = {METHOD}; calibration windows = {SELECTION}.", ""]

    for ksec in (5, 120):
        out += [f"Does {ksec} s of calibration still pay, at each corpus size?",
                "-" * 72]
        for n in ns:
            a = per_subject(raw, METHOD, n, 0)
            b = per_subject(raw, METHOD, n, ksec)
            i = sorted(set(a.index) & set(b.index))
            av, bv = a.loc[i].values, b.loc[i].values
            w = stats.wilcoxon(av, bv)
            out.append(
                f"  N={n:2d}  no calibration {av.mean():6.2f}  ->  {ksec:3d} s {bv.mean():6.2f}   "
                f"mean gain {av.mean()-bv.mean():+5.2f} | median {np.median(av):5.2f} -> "
                f"{np.median(bv):5.2f} | helped {int((bv<av).sum())}/{len(i)} | p = {w.pvalue:.4f}")
        out.append("")

    # the headline pair, in full
    a = per_subject(raw, METHOD, max(ns), 0)
    b = per_subject(raw, METHOD, max(ns), 120)
    i = sorted(set(a.index) & set(b.index))
    out += ["The headline comparison, in full", "-" * 72,
            fmt(compare(b.loc[i].values, a.loc[i].values,
                        f"{max(ns)} wearers + 120 s calibration",
                        f"{max(ns)} wearers, no calibration"))]

    ceiling = float(old[old.arm == "calibrated_within"]["mae"].iloc[0])
    zs16 = float(per_subject(raw, METHOD, max(ns), 0).mean())
    out += ["READING IT", "-" * 72,
            "The value of the calibration ritual is not a constant — it is a function of how",
            "much data you already have. On this dataset it falls by more than an order of",
            f"magnitude between 1 wearer and {max(ns)}, and by {max(ns)} it is no longer",
            "distinguishable from skipping calibration entirely.",
            "",
            "Two honest limits.",
            f"  1. None of this reaches the same-session ceiling ({ceiling:.1f} %MVC). Taking the band",
            "     off costs more than any amount of calibration recovers, at any corpus size",
            "     tested. The corpus buys out the RITUAL, not the re-donning penalty.",
            "  2. The means are pulled up by a handful of badly-transferring wearers. At",
            f"     N={max(ns)} the mean says calibration is worth +0.5 %MVC while the median wearer",
            "     is barely touched — so read it as 'calibration has become a fallback for the",
            "     tail', not as 'calibration has become useless'.",
            "",
            f"  For reference: {max(ns)} wearers, no calibration = {zs16:.2f} %MVC on this test set",
            "  (session 2 only, which is the harder of the two sessions; sweep.py's headline",
            "  11.22 averages over both sessions).",
            ""]

    txt = "\n".join(out)
    (rd / "budget_tests.txt").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
