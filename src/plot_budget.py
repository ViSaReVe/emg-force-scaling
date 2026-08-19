"""The calibration-budget figure: what a second of calibration is worth, and how
fast that value collapses as the corpus grows.

Panel A is the surface, sliced into one curve per corpus size — more honest than a
smoothed heatmap when the grid is 5 corpus sizes by 6 durations.
Panel B is the thing a product manager actually needs: the marginal value of the
ritual, against the number of wearers already in the corpus.

Palette follows plot.py: blue for the corpus, burnt orange for per-user calibration,
violet for the same-session ceiling. Corpus size is a blue ramp (sequential ramps are
CVD-safe by construction); the two non-blue lines keep the validated separation.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

ZERO, NEXTDAY, CEIL = "#2f6f9f", "#c2410c", "#6d28d9"
INK, MUTED, GRID = "#1a1a1a", "#6b6b6b", "#d8d8d6"
RAMP = ["#bcd4e6", "#8fb8d6", "#5f95c4", "#3a76ab", "#1e5081"]  # N = 1,2,4,8,16

SELECTION = "contiguous"   # the headline: the first k seconds, as a product would ship
METHOD = "affine"          # per-finger gain + offset; see budget.py for why not finetune


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    unit = "N" if cfg.get("target", {}).get("units", "pct_mvc") == "newtons" else "%MVC"
    rd = ROOT / cfg["output"]["results_dir"]
    s = pd.read_csv(rd / "budget_summary.csv")
    raw = pd.read_csv(rd / "budget_raw.csv")
    old = pd.read_csv(rd / "summary.csv")

    ceiling = float(old[old.arm == "calibrated_within"]["mae"].iloc[0])

    sel = s[s.selection == SELECTION]
    aff = sel[sel.method == METHOD].sort_values(["n_train_subjects", "cal_seconds"])
    per = sel[sel.method == "peruser"].sort_values("cal_seconds")
    ks = sorted(aff.cal_seconds.unique())
    ns = sorted(aff.n_train_subjects.unique())
    xpos = {k: i for i, k in enumerate(ks)}

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12.8, 5.1), dpi=200,
                                 gridspec_kw={"width_ratios": [1.15, 1]})

    # ---------------- A: one curve per corpus size ----------------
    ax.axhline(ceiling, color=CEIL, ls=(0, (2, 2.5)), lw=1.7, zorder=2)
    ax.annotate(f"Same-session calibration — {ceiling:.1f}   (the ceiling; band never removed)",
                xy=(0.30, ceiling + 0.22), fontsize=8.5, color=CEIL, va="bottom", ha="left")

    ax.plot([xpos[k] for k in per.cal_seconds], per["mae"], "s--", color=NEXTDAY, lw=1.8,
            ms=6, mec="white", mew=1.0, zorder=4)
    ax.annotate("No corpus at all — calibration only", color=NEXTDAY, fontsize=8.5,
                xy=(xpos[5], float(per[per.cal_seconds == 5]["mae"].iloc[0]) + 0.45),
                va="bottom", ha="left")

    # Label each curve at its LEFT end: at k=0 the corpus sizes are cleanly separated,
    # whereas by k=120 they have converged into a 1 %MVC band and the labels collide.
    for i, n in enumerate(ns):
        g = aff[aff.n_train_subjects == n]
        ax.plot([xpos[k] for k in g.cal_seconds], g["mae"], "o-", color=RAMP[i], lw=2,
                ms=6, mec="white", mew=1.0, zorder=5)
        first = g[g.cal_seconds == 0]
        ax.annotate(f"{int(n)}", xy=(-0.13, float(first["mae"].iloc[0])),
                    color=RAMP[i], fontsize=9.5, va="center", ha="right", weight="bold")
    ax.annotate("wearers in\nthe corpus", xy=(-0.13, 23.15), color=MUTED,
                fontsize=8.5, va="center", ha="right", linespacing=1.35)

    ax.set_xticks(list(xpos.values()))
    ax.set_xticklabels([f"{k}" for k in ks])
    ax.set_xlim(-0.78, len(ks) - 0.72)
    ax.set_ylim(7.6, 24.0)
    ax.set_xlabel("Seconds of that wearer's own calibration")
    ax.set_ylabel(f"Force MAE on the next day, band re-donned ({unit})")
    ax.set_title("A · The curves flatten as the corpus grows", fontsize=11.5, color=INK,
                 loc="left", pad=10)

    # ---------------- B: what the ritual is worth, vs corpus size ----------------
    ps = (raw[raw.selection == SELECTION]
          .groupby(["method", "n_train_subjects", "cal_seconds", "held_out"])["mae"]
          .mean().reset_index())

    gains5, gains120, win5, win120 = [], [], [], []
    for n in ns:
        base = ps[(ps.method == METHOD) & (ps.n_train_subjects == n) &
                  (ps.cal_seconds == 0)].set_index("held_out")["mae"]
        for ksec, gains, wins in ((5, gains5, win5), (120, gains120, win120)):
            cal = ps[(ps.method == METHOD) & (ps.n_train_subjects == n) &
                     (ps.cal_seconds == ksec)].set_index("held_out")["mae"]
            idx = sorted(set(base.index) & set(cal.index))
            a, b = base.loc[idx].values, cal.loc[idx].values
            gains.append(a.mean() - b.mean())
            wins.append(float((b < a).mean()))

    x = np.arange(len(ns))
    w = 0.36
    bx.bar(x - w / 2, gains5, w, color=RAMP[1], label="5 s of calibration", zorder=3)
    bx.bar(x + w / 2, gains120, w, color=RAMP[4], label="120 s of calibration", zorder=3)
    bx.axhline(0, color="#b9b9b6", lw=1)

    for i in range(len(ns)):
        for gx, gv, wv in ((x[i] - w / 2, gains5[i], win5[i]), (x[i] + w / 2, gains120[i], win120[i])):
            bx.text(gx, gv + 0.22, f"{gv:+.1f}", ha="center", va="bottom", fontsize=8.5,
                    color=INK)
            bx.text(gx, -0.62, f"{wv*100:.0f}%", ha="center", va="top", fontsize=8,
                    color=MUTED)
    bx.text(x[0] - w / 2 - 0.42, -0.62, "helped:", ha="right", va="top", fontsize=8, color=MUTED)

    bx.set_xticks(x)
    bx.set_xticklabels([str(int(n)) for n in ns])
    bx.set_xlabel("Wearers already in the corpus")
    bx.set_ylabel(f"MAE saved by calibrating ({unit})")
    bx.set_ylim(-1.9, max(gains120) * 1.22)
    bx.set_xlim(-0.72, len(ns) - 0.28)
    bx.set_title("B · What the calibration ritual buys you", fontsize=11.5, color=INK,
                 loc="left", pad=10)
    bx.legend(frameon=False, fontsize=8.5, loc="upper right", handletextpad=0.6,
              borderpad=0, labelspacing=0.45)
    bx.text(0.985, 0.60,
            "At 1 wearer the ritual is worth 9.3 %MVC.\n"
            "At 16 it is worth 0.5 and helps half the\n"
            "wearers — indistinguishable from skipping it\n"
            "(Wilcoxon p = 0.84).",
            transform=bx.transAxes, ha="right", va="top", fontsize=8.5, color=MUTED,
            linespacing=1.5)

    for axis in (ax, bx):
        axis.grid(alpha=0.55, lw=0.6, color=GRID)
        axis.set_axisbelow(True)
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            axis.spines[side].set_color("#b9b9b6")
        axis.tick_params(colors=MUTED, labelsize=9)
        axis.xaxis.label.set_color(MUTED)
        axis.yaxis.label.set_color(MUTED)
    bx.grid(axis="x", visible=False)

    fig.text(0.005, -0.10,
             "Hyser · 20 wearers · calibration = the FIRST k seconds of that wearer's session 1; "
             "test = all of their session 2, a different day with the band re-donned.\n"
             "Adaptation is a per-finger gain and offset on the population model's predictions "
             "(10 parameters). Fitting the weights themselves instead — prior-mean ridge on the\n"
             "residuals — is worse than not calibrating at all here, and stays worse even when "
             "its penalty is chosen on the test set, so it is not shown. Points are means over\n"
             "20 held-out wearers x 10 corpus draws; the mean is pulled up by a few badly-"
             "transferring wearers, so panel B also reports the share of wearers actually helped.",
             fontsize=7.5, color=MUTED, linespacing=1.5)
    fig.tight_layout(w_pad=3.2)
    out = rd / "calibration_budget.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
