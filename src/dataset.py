"""Build per-subject feature/target arrays from Hyser WFDB records.

Pipeline per record:
  256-ch EMG @2048 Hz  -> subsample to 8 "wrist band" channels
                       -> 20-450 Hz bandpass + 50 Hz notch, zero phase
                       -> 200 ms windows / 100 ms hop -> RMS,MAV,WL,ZC,SSC
  5-ch force @100 Hz   -> sampled at window ends -> normalised to %MVC per subject

Output: results/cache/subject_XX_sessionY.npz  with X (n_win, n_feat), y (n_win, 5)

Run `python -m src.dataset --check` FIRST. It loads one record, prints the true
channel count and signal names, and tells you whether the montage indices in
config.yaml are plausible. Do not trust the default montage until that passes.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import yaml
from tqdm import tqdm

from .features import align_force, preprocess, window_features

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config.yaml"


def load_cfg() -> dict:
    with open(CFG) as fh:
        return yaml.safe_load(fh)


def _wfdb():
    try:
        import wfdb
    except ImportError:
        print("ERROR: pip install wfdb", file=sys.stderr)
        raise
    return wfdb


def find_records(root: Path, subset: str) -> list[Path]:
    """Hyser lays records out as <subset>/subject_XX_sessionY/<task>_<kind>_<i>.hea"""
    hits = sorted((root / subset).rglob("*.hea"))
    return [h.with_suffix("") for h in hits]


_SS = re.compile(r"subject(\d+)_session(\d+)")


def parse_subject_session(p: Path) -> tuple[int, int]:
    """Hyser folders are named 'subject01_session1' (no underscore after 'subject')."""
    for part in p.parts[::-1]:
        m = _SS.fullmatch(part) or _SS.search(part)
        if m:
            return int(m.group(1)), int(m.group(2))
    raise ValueError(f"cannot parse subject/session from {p}")


def resolve_montage(sig_name: list[str], mont: dict) -> tuple[list[int], str]:
    """Pick the 8 band channels BY NAME where possible.

    Hyser names channels "XX-i-j": XX in {ED, EP, FD, FP} = extensor/flexor x distal/proximal,
    i,j = row/column in that 8x8 array (readme.txt). A wrist band sits distally, so we take
    only ED-* and FD-*. Name lookup means a change in channel ordering cannot silently
    corrupt the montage - which index-based selection would.
    """
    want = mont.get("channel_names") or []
    if want and sig_name:
        idx = [sig_name.index(w) for w in want if w in sig_name]
        if len(idx) == len(want):
            return idx, "by_name"
        missing = [w for w in want if w not in sig_name]
        print(f"  WARNING: montage names not found: {missing}", file=sys.stderr)
        print(f"  available (first 12): {sig_name[:12]}", file=sys.stderr)
    return list(mont["indices"]), "by_index_FALLBACK"


def load_record(stem: Path):
    wfdb = _wfdb()
    rec = wfdb.rdrecord(str(stem))
    return rec.p_signal, rec.fs, list(rec.sig_name or [])


def split_emg_force(sig: np.ndarray, n_force: int) -> tuple[np.ndarray, np.ndarray | None]:
    """Hyser stores EMG and force in separate files ('..._raw' vs '..._force').

    If a record has exactly n_force channels we treat it as a force file, otherwise
    as EMG. Verified by --check.
    """
    if sig.shape[1] == n_force:
        return None, sig
    return sig, None


def build_subject_arrays(cfg: dict, check_only: bool = False, limit: int | None = None) -> None:
    data, mont, sig_cfg = cfg["data"], cfg["montage"], cfg["signal"]
    root = Path(data["root"])
    out = ROOT / cfg["output"]["results_dir"] / "cache"
    out.mkdir(parents=True, exist_ok=True)

    stems = []
    for subset in data["subsets"]:
        stems += find_records(root, subset)
    if not stems:
        pass
    if not stems:
        print(f"ERROR: no .hea files under {root.resolve()}. Run `make fetch` first.", file=sys.stderr)
        sys.exit(1)

    if limit is not None:
        keep = set(range(1, limit + 1))
        kept = []
        for s in stems:
            try:
                subj, _ = parse_subject_session(s)
            except ValueError:
                continue
            if subj in keep:
                kept.append(s)
        stems = kept
        print(f"--limit {limit}: {len(stems)} records from subjects 1..{limit}")

    if check_only:
        print(f"found {len(stems)} records under {root}")
        emg_stem = next((s for s in stems if "force" not in s.name), stems[0])
        sig, fs, names = load_record(emg_stem)
        print(f"\nsample record : {emg_stem}")
        print(f"  shape       : {sig.shape}  (samples, channels)")
        print(f"  fs          : {fs} Hz")
        print(f"  sig_name[:8]: {names[:8]}")
        n_ch = sig.shape[1]
        idx, how = resolve_montage(names, mont)
        ok = all(0 <= i < n_ch for i in idx)
        print(f"\nmontage       : resolved {how}")
        print(f"  wanted      : {mont.get('channel_names')}")
        print(f"  -> indices  : {idx}")
        print(f"  in range    : {'YES' if ok else 'NO - FIX config.yaml'}")
        if how != "by_name":
            print("  !! Name lookup failed. Do NOT run the sweep until this resolves by_name.")
        if n_ch != 256:
            print("  NOTE: expected 256 EMG channels. If this record is a force file, that is fine;")
            print("        re-run --check once EMG records are present.")
        print("\nBefore trusting results, confirm from the Hyser docs which physical grid/row each")
        print("index maps to. The montage is meant to imitate a distal wrist band, 2 channels per grid.")
        return

    per_key: dict[tuple[int, int], dict[str, list]] = {}
    skipped: list[str] = []
    missing_mvc: list[str] = []
    for stem in tqdm(stems, desc="records"):
        try:
            subj, sess = parse_subject_session(stem)
        except ValueError:
            continue
        try:
            sig, fs, _names = load_record(stem)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{stem.parent.name}/{stem.name}: {exc}")
            continue

        emg, force = split_emg_force(sig, data["n_force_channels"])
        key = (subj, sess)
        per_key.setdefault(key, {"emg": [], "force": [], "mvc": []})
        is_mvc = "mvc" in str(stem).lower()

        if force is not None:
            per_key[key]["mvc" if is_mvc else "force"].append(force)
            continue
        if is_mvc:
            continue  # MVC EMG not needed; we only use MVC to scale the force target

        idx, _how = resolve_montage(_names, mont)
        emg = emg[:, idx]
        emg = preprocess(emg, fs, tuple(sig_cfg["bandpass"]), sig_cfg["notch_hz"], sig_cfg["notch_q"])
        X, ends = window_features(emg, fs, sig_cfg["window_ms"], sig_cfg["hop_ms"], sig_cfg["features"])
        per_key[key]["emg"].append((X, ends))

    tgt = cfg.get("target", {})
    pct = int(tgt.get("mvc_percentile", 95))

    for (subj, sess), d in per_key.items():
        if not d["emg"] or not d["force"]:
            continue

        # %MVC reference: per finger, the `pct`th percentile of |force| across this
        # subject-session's MVC trials (flexion AND extension). Force is stored in
        # amplifier volts with a per-finger gain, so this ratio is the only
        # cross-subject-comparable quantity the dataset supports.
        if d["mvc"]:
            mvc_ref = np.percentile(np.abs(np.concatenate(d["mvc"], axis=0)), pct, axis=0)
            ref_src = "mvc_trials"
        else:
            mvc_ref = np.percentile(np.abs(np.concatenate(d["force"], axis=0)), 99, axis=0)
            ref_src = "task_peak_FALLBACK"
            missing_mvc.append(f"subject{subj:02d}_session{sess}")
        mvc_ref = np.where(mvc_ref <= 0, 1.0, mvc_ref)

        units = tgt.get("units", "pct_mvc")
        Xs, ys = [], []
        for (X, ends), F in zip(d["emg"], d["force"]):
            y = align_force(F, data["force_fs"], ends, data["emg_fs"])
            Xs.append(X)
            # Raw force is amplifier VOLTS with a per-finger gain (see the /V in the .hea),
            # so it is meaningless across subjects until divided by that subject's MVC.
            ys.append(100.0 * y / mvc_ref if units == "pct_mvc" else y)
        np.savez_compressed(
            out / f"subject_{subj:02d}_session{sess}.npz",
            X=np.concatenate(Xs).astype(np.float32),
            y=np.concatenate(ys).astype(np.float32),
            mvc_ref=mvc_ref.astype(np.float32),
            ref_source=ref_src,
            units=units,
        )
    n_cached = len(list(out.glob("*.npz")))
    print(f"\ncached {n_cached} subject-sessions -> {out}")

    if missing_mvc:
        print(f"\nWARNING: {len(missing_mvc)} subject-session(s) had NO MVC trials and fell back to "
              f"task-peak normalisation:", file=sys.stderr)
        for m in missing_mvc[:6]:
            print(f"  {m}", file=sys.stderr)
        print("  Fetch mvc_dataset force records and rebuild for true %MVC.", file=sys.stderr)

    if skipped:
        print(f"\n{'!' * 72}", file=sys.stderr)
        print(f"WARNING: {len(skipped)} of {len(stems)} records failed to load and were SKIPPED.",
              file=sys.stderr)
        for s in skipped[:8]:
            print(f"  {s}", file=sys.stderr)
        if len(skipped) > 8:
            print(f"  ... and {len(skipped) - 8} more", file=sys.stderr)
        if any("reshape" in s for s in skipped):
            print("\n'cannot reshape array of size N into shape (256)' means a TRUNCATED .dat file.",
                  file=sys.stderr)
            print("The cache you just built is INCOMPLETE. Fix it, then rebuild:", file=sys.stderr)
            print("    python -m src.fetch --repair", file=sys.stderr)
            print("    rm -rf results/cache && make prepare", file=sys.stderr)
        print(f"{'!' * 72}\n", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--limit", type=int, default=None,
                    help="process only the first N subjects - use 2 or 3 for the first real run")
    args = ap.parse_args()
    build_subject_arrays(load_cfg(), check_only=args.check, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
