"""The one figure: zero-shot force error vs number of training subjects."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]

ACCENT = "#2f6f9f"
REF = "#b8562f"
CEIL = "#3f7d54"
INK = "#1a1a1a"


def main() -> int:
    cfg = yaml.safe_load(open(ROOT / "config.yaml"))
    unit = "N" if cfg.get("target", {}).get("units", "pct_mvc") == "newtons" else "%MVC"
    rd = ROOT / cfg["output"]["results_dir"]
    df = pd.read_csv(rd / "summary.csv")

    zs = df[df.arm == "zero_shot"].sort_values("n_train_subjects")

    fig, ax = plt.subplots(figsize=(7.6, 4.8), dpi=200)
    ax.plot(zs.n_train_subjects, zs["mae"], "o-", color=ACCENT, lw=2, ms=6,
            label="Zero-shot on an unseen wearer")
    ax.fill_between(zs.n_train_subjects, zs.lo, zs.hi, color=ACCENT, alpha=0.18, lw=0)

    refs = [("calibrated_crossday", REF, "-.", "Calibrated, worn again next day"),
            ("calibrated_within", CEIL, "--", "Calibrated, same session (ForceBand's setting)")]
    for arm, colour, style, label in refs:
        row = df[df.arm == arm]
        if not len(row):
            continue
        v = float(row["mae"].iloc[0])
        ax.axhline(v, color=colour, ls=style, lw=1.6, label=f"{label} — {v:.1f} {unit}")
        ax.fill_between(zs.n_train_subjects, float(row.lo.iloc[0]), float(row.hi.iloc[0]),
                        color=colour, alpha=0.10, lw=0)

    ax.set_xscale("log", base=2)
    ax.set_xticks(zs.n_train_subjects)
    ax.set_xticklabels([str(int(v)) for v in zs.n_train_subjects])
    ax.set_xlabel("Training subjects (log scale)")
    ax.set_ylabel(f"Force MAE ({unit})")
    ax.set_title("Does EMG-to-force generalisation improve with more wearers?\n"
                 "Hyser random task, 8-channel distal montage, leave-one-subject-out",
                 fontsize=11, color=INK, loc="left")
    ax.grid(alpha=0.25, lw=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    fig.text(0.01, -0.055,
             "Shaded bands = bootstrap 95% CI. Ridge on RMS/MAV/WL/ZC/SSC, 8 distal channels, "
             "200 ms windows, leave-one-subject-out.\n"
             "The gap between the two calibrated lines is the cost of re-donning the band. "
             "20 subjects caps the sweep at N=16; Meta's calibration-free\nresult needed thousands, "
             "so a flat curve here means 'not visible below 16', not 'does not scale'.",
             fontsize=7.5, color="#666")
    fig.tight_layout()
    out = ROOT / cfg["output"]["figure"]
    fig.savefig(out, bbox_inches="tight")
    print(f"wrote {out}  (units: {unit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
