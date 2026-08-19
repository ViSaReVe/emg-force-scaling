"""Two panels: the scaling curve, and the paired head-to-head behind it.

Palette is CVD-validated (blue / burnt-orange / violet). The obvious green for the
"ceiling" line failed a colourblind-separation check against the orange, so it is
violet instead. Marker SHAPE carries identity in panel B as well as colour.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]

ZERO, NEXTDAY, CEIL = "#2f6f9f", "#c2410c", "#6d28d9"
INK, MUTED, GRID = "#1a1a1a", "#6b6b6b", "#d8d8d6"


def main() -> int:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    unit = "N" if cfg.get("target", {}).get("units", "pct_mvc") == "newtons" else "%MVC"
    rd = ROOT / cfg["output"]["results_dir"]
    df = pd.read_csv(rd / "summary.csv")
    raw = pd.read_csv(rd / "raw_results.csv")
    zs = df[df.arm == "zero_shot"].sort_values("n_train_subjects")

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12.6, 5.0), dpi=200,
                                 gridspec_kw={"width_ratios": [1.25, 1]})

    # ---------------- A: scaling curve ----------------
    ax.plot(zs.n_train_subjects, zs["mae"], "o-", color=ZERO, lw=2, ms=8, zorder=4,
            mec="white", mew=1.2)
    ax.fill_between(zs.n_train_subjects, zs.lo, zs.hi, color=ZERO, alpha=0.16, lw=0, zorder=1)

    xmax = zs.n_train_subjects.max()
    for arm, colour, style, label in (
            ("calibrated_crossday", NEXTDAY, (0, (6, 3)), "Calibrated,\nworn again next day"),
            ("calibrated_within", CEIL, (0, (2, 2.5)),
             "Calibrated, same session\n(ForceBand's setting)")):
        r = df[df.arm == arm]
        if not len(r):
            continue
        v = float(r["mae"].iloc[0])
        ax.axhline(v, color=colour, ls=style, lw=1.8, zorder=3)
        ax.annotate(f"{label} — {v:.1f}", xy=(xmax * 1.06, v), fontsize=8.5, color=colour,
                    va="center", ha="left", linespacing=1.35)

    lx, ly = np.log(zs.n_train_subjects.values), np.log(zs["mae"].values)
    b, la = np.polyfit(lx, ly, 1)
    r2 = 1 - np.sum((ly - (la + b * lx)) ** 2) / np.sum((ly - ly.mean()) ** 2)
    xs = np.linspace(lx.min(), lx.max(), 60)
    ax.plot(np.exp(xs), np.exp(la + b * xs), color=ZERO, lw=1, ls=":", alpha=0.65, zorder=2)
    ax.annotate("Zero-shot on a wearer\nthe model has never seen",
                xy=(1.15, zs["mae"].max() * 1.07), fontsize=8.5, color=ZERO,
                va="top", linespacing=1.35)
    ax.text(0.985, 0.03,
            f"MAE = {np.exp(la):.1f}·N$^{{{b:.3f}}}$   (log–log R²={r2:.3f})",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5, color=MUTED)

    ax.set_xscale("log", base=2)
    ax.set_xticks(zs.n_train_subjects)
    ax.set_xticklabels([str(int(v)) for v in zs.n_train_subjects])
    ax.set_xlim(0.85, xmax * 1.12)
    ax.set_ylim(zs["mae"].min() * 0.6, zs["mae"].max() * 1.17)
    ax.set_xlabel("Training subjects (log scale)")
    ax.set_ylabel(f"Force MAE ({unit})")
    ax.set_title("A · More wearers, less error", fontsize=11.5, color=INK, loc="left", pad=10)

    # ---------------- B: paired, one row per subject ----------------
    z16 = (raw[(raw.arm == "zero_shot") & (raw.n_train_subjects == 16)]
           .groupby("held_out")["mae"].mean())
    cd = raw[raw.arm == "calibrated_crossday"].set_index("held_out")["mae"]
    s = sorted(set(z16.index) & set(cd.index))
    a, c = z16.loc[s].values, cd.loc[s].values
    o = np.argsort(c)
    a, c, sid = a[o], c[o], np.array(s)[o]
    y = np.arange(len(s))
    clip = float(np.percentile(c, 90)) * 1.35   # keep the bulk legible; annotate what falls outside

    for i in range(len(s)):
        x2 = min(c[i], clip)
        bx.plot([a[i], x2], [y[i], y[i]], color=(ZERO if c[i] > a[i] else NEXTDAY),
                alpha=0.30, lw=1.6, zorder=1)
        if c[i] > clip:
            bx.annotate("", xy=(clip + 0.9, y[i]), xytext=(clip - 0.3, y[i]),
                        arrowprops=dict(arrowstyle="-|>", color=NEXTDAY, lw=1.4))
            bx.text(clip + 1.3, y[i], f"subject {sid[i]}: {c[i]:.0f}", fontsize=7.5,
                    color=NEXTDAY, va="center")
    bx.scatter(a, y, s=34, color=ZERO, zorder=4, ec="white", lw=0.9,
               label="Zero-shot (16 others)")
    bx.scatter(np.minimum(c, clip), y, s=34, color=NEXTDAY, marker="s", zorder=4, ec="white",
               lw=0.9, label="That subject's own calibration, next day")

    w = stats.wilcoxon(a, c)
    bx.set_yticks([])
    bx.set_xlim(min(a.min(), c.min()) * 0.8, clip + 7)
    bx.set_ylim(-1.2, len(s) + 0.4)
    bx.set_xlabel(f"Force MAE ({unit})")
    bx.set_title(f"B · Same subject, two methods — zero-shot wins {int((c > a).sum())}/{len(s)}",
                 fontsize=11.5, color=INK, loc="left", pad=10)
    bx.legend(frameon=False, fontsize=8.5, loc="lower right", bbox_to_anchor=(1.02, -0.01),
              handletextpad=0.5, borderpad=0, labelspacing=0.45)
    bx.text(0.015, 0.985,
            f"One row per subject, sorted by calibration error\n"
            f"Wilcoxon signed-rank  p = {w.pvalue:.3f}",
            transform=bx.transAxes, ha="left", va="top", fontsize=8.5, color=MUTED,
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
    bx.grid(axis="y", visible=False)

    fig.text(0.005, -0.045,
             "Hyser random task · 8 distal channels (ED/FD) · 200 ms windows · ridge on "
             "RMS/MAV/WL/ZC/SSC · leave-one-subject-out · shaded band = bootstrap 95% CI.\n"
             "Force is %MVC because Hyser stores amplifier volts, not newtons — comparable to "
             "ForceBand in the SHAPE of the curve, not in level. 20 subjects caps the sweep\n"
             "at N=16; Meta's calibration-free gesture result needed thousands of participants, "
             "so a flat curve here would mean \"not visible below 16\", not \"does not scale\".",
             fontsize=7.5, color=MUTED, linespacing=1.5)
    fig.tight_layout(w_pad=3.0)
    out = ROOT / cfg["output"]["figure"]
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
