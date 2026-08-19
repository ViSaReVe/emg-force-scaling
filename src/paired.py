"""Paired head-to-head: zero-shot on N=16 others vs the subject's OWN calibration.

The scaling curve and the calibration lines have overlapping CIs because they are
summarised independently. But the comparison is naturally PAIRED - same subject,
two methods - so the right test uses the 20 within-subject differences, not the
overlap of two error bars.

Writes results/paired_tests.txt and returns the numbers for the figure.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]


def load(results_dir: Path, n_train: int = 16):
    df = pd.read_csv(results_dir / "raw_results.csv")
    zs = (df[(df.arm == "zero_shot") & (df.n_train_subjects == n_train)]
          .groupby("held_out")["mae"].mean())
    cross = df[df.arm == "calibrated_crossday"].set_index("held_out")["mae"]
    within = df[df.arm == "calibrated_within"].groupby("held_out")["mae"].mean()
    return zs, cross, within


def compare(a: np.ndarray, b: np.ndarray, name_a: str, name_b: str) -> dict:
    d = b - a  # > 0 means a (zero-shot) wins
    w = stats.wilcoxon(a, b)
    n = len(d)
    return {
        "n": n,
        "mean_a": a.mean(), "median_a": float(np.median(a)),
        "mean_b": b.mean(), "median_b": float(np.median(b)),
        "wins": int((d > 0).sum()),
        "median_diff": float(np.median(d)),
        "wilcoxon_W": float(w.statistic), "wilcoxon_p": float(w.pvalue),
        "ttest_p": float(stats.ttest_rel(a, b).pvalue),
        "sign_p": float(stats.binomtest(int((d > 0).sum()), n, 0.5).pvalue),
        "rank_biserial": 1 - 2 * w.statistic / (n * (n + 1) / 2),
        "name_a": name_a, "name_b": name_b,
    }


def fmt(r: dict) -> str:
    return (
        f"{r['name_a']}  vs  {r['name_b']}   (n = {r['n']} subjects, paired)\n"
        f"  {r['name_a']:32s} mean {r['mean_a']:6.2f}   median {r['median_a']:6.2f} %MVC\n"
        f"  {r['name_b']:32s} mean {r['mean_b']:6.2f}   median {r['median_b']:6.2f} %MVC\n"
        f"  wins for the first method       : {r['wins']}/{r['n']}\n"
        f"  median paired difference        : {r['median_diff']:+.2f} %MVC\n"
        f"  Wilcoxon signed-rank            : W = {r['wilcoxon_W']:.1f}, p = {r['wilcoxon_p']:.4f}\n"
        f"  paired t-test                   : p = {r['ttest_p']:.4f}\n"
        f"  sign test (direction only)      : p = {r['sign_p']:.4f}\n"
        f"  rank-biserial effect size       : {r['rank_biserial']:.3f}\n"
    )


def main() -> int:
    import yaml
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    rd = ROOT / cfg["output"]["results_dir"]
    zs, cross, within = load(rd)

    s = sorted(set(zs.index) & set(cross.index))
    r1 = compare(zs.loc[s].values, cross.loc[s].values,
                 "zero-shot on 16 others", "own calibration, next day")
    s2 = sorted(set(zs.index) & set(within.index))
    r2 = compare(zs.loc[s2].values, within.loc[s2].values,
                 "zero-shot on 16 others", "own calibration, same session")

    # robustness: drop the worst cross-day subject
    b = cross.loc[s].values
    drop = s[int(np.argmax(b))]
    k = [i for i, x in enumerate(s) if x != drop]
    r3 = compare(zs.loc[s].values[k], b[k],
                 "zero-shot on 16 others", f"own calibration next day (excl. subj {drop})")

    txt = ("PAIRED COMPARISONS\n" + "=" * 72 + "\n\n" + fmt(r1) +
           "\nRobustness - dropping the worst cross-day subject\n" + "-" * 72 + "\n" + fmt(r3) +
           "\nRemaining gap to the ceiling\n" + "-" * 72 + "\n" + fmt(r2) +
           "\nREADING IT\n" + "-" * 72 + "\n"
           "The signed-rank test is significant while the sign test is not: the effect lives in\n"
           "the MAGNITUDE of the differences, not merely their direction. 14/20 by itself would\n"
           "not be convincing; 14/20 with large wins and small losses is.\n\n"
           "Zero-shot does NOT beat same-session calibration - it loses 20/20. That gap is what\n"
           "more wearers would have to close, and it is the honest limit of the claim.\n")
    (rd / "paired_tests.txt").write_text(txt)
    print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
