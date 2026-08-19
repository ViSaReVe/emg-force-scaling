"""Generate synthetic cached arrays so the sweep/plot code can be exercised
end-to-end without the 18 GB download. Proves the harness runs; proves nothing
about EMG. `make smoke` then `make sweep plot`.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cfg = yaml.safe_load(open(ROOT / "config.yaml"))
    out = ROOT / cfg["output"]["results_dir"] / "cache"
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)

    n_feat = cfg["montage"]["n_channels"] * len(cfg["signal"]["features"])
    W = rng.normal(size=(n_feat, 5))  # shared "physiology" all subjects have in common

    for subj in range(1, cfg["data"]["subjects"] + 1):
        gain = rng.uniform(0.6, 1.6, size=(1, 5))      # per-subject force scale
        offs = rng.normal(0, 3.0, size=(1, 5))          # per-subject offset
        Wsub = W + rng.normal(0, 0.25, size=W.shape)    # per-subject deviation
        for sess in cfg["data"]["sessions"]:
            n = 1200
            X = rng.normal(size=(n, n_feat)).astype(np.float32)
            y = (X @ Wsub) * gain + offs + rng.normal(0, 1.5, size=(n, 5))
            np.savez_compressed(out / f"subject_{subj:02d}_session{sess}.npz",
                                X=X, y=y.astype(np.float32),
                                mvc_ref=np.ones(5, np.float32), used_mvc_files=False)
    print(f"wrote {cfg['data']['subjects'] * 2} synthetic subject-sessions -> {out}")
    print("NOTE: synthetic. Delete results/cache before running on real Hyser data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
