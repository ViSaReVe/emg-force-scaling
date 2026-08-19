"""Download exactly the Hyser records this study needs. Pure Python - no wget, no awscli.

Why this exists: `wget` is not installed on macOS by default and awscli is another
dependency. PhysioNet ships a `RECORDS` manifest listing every record path, so we can
build the download list exactly instead of crawling HTML.

Each WFDB record is two files: <record>.hea (header) and <record>.dat (signal).

What we take from random_dataset (per subject-session, 5 samples each):
    random_force_sampleK       5 force channels @ 100 Hz     - tiny
    random_preprocess_sampleK  256 EMG channels @ 2048 Hz    - the bulk
and we SKIP random_raw_sampleK, which is a second full copy of the EMG at ~5 GB.
That halves the download. Set --types raw if you ever want the unfiltered version.

Usage:
    python -m src.fetch --check      # plan only: counts, bytes, nothing downloaded
    python -m src.fetch              # download (resumable - rerun after any interruption)
    python -m src.fetch --jobs 8     # more parallelism
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

BASE = "https://physionet.org/files/hd-semg/2.0.0"
ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config.yaml"
UA = {"User-Agent": "emg-force-scaling/0.1 (research; python-urllib)"}


def load_cfg() -> dict:
    return yaml.safe_load(CFG.read_text())


def read_records(root: Path) -> list[str]:
    f = root / "RECORDS"
    if not f.exists():
        print(f"ERROR: {f} not found. Fetch it first:\n"
              f"  curl -o {f} {BASE}/RECORDS", file=sys.stderr)
        sys.exit(1)
    return [ln.strip() for ln in f.read_text().splitlines() if ln.strip()]


def select(records: list[str], subset_types: dict[str, list[str]]) -> list[str]:
    """subset_types maps a subset dir to the record types wanted from it.

    e.g. {"random_dataset": ["force", "preprocess"], "mvc_dataset": ["force"]}
    The MVC EMG is never needed - only the MVC force, to build the %MVC reference.
    """
    out = []
    for r in records:
        subset = r.split("/", 1)[0]
        types = subset_types.get(subset)
        if not types:
            continue
        name = r.rsplit("/", 1)[-1]
        if any(f"_{t}_" in name for t in types):
            out.append(r)
    return sorted(out)


def head_size(url: str) -> int:
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.headers.get("Content-Length", 0))
    except Exception:  # noqa: BLE001
        return 0


def download(url: str, dest: Path, retries: int = 4) -> tuple[str, bool, str]:
    """Resumable, SIZE-VERIFIED single-file download.

    urllib will happily hand back a truncated body if the connection drops mid-stream,
    and a truncated .dat makes wfdb fail with "cannot reshape array of size N into
    shape (256)". So every write is checked against Content-Length before it is
    allowed to become the final file.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    remote = head_size(url)

    if dest.exists() and dest.stat().st_size > 0:
        if remote and dest.stat().st_size == remote:
            return (dest.name, False, "already complete")
        if remote:
            dest.unlink()  # wrong size -> truncated from an earlier run, redo it

    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as resp, open(tmp, "wb") as fh:
                expect = int(resp.headers.get("Content-Length", 0)) or remote
                shutil.copyfileobj(resp, fh, length=1 << 20)
            got = tmp.stat().st_size
            if expect and got != expect:
                if attempt == retries:
                    tmp.unlink(missing_ok=True)
                    return (dest.name, False, f"FAILED truncated {got}/{expect} bytes")
                time.sleep(1.5 * attempt)
                continue
            tmp.replace(dest)
            return (dest.name, True, "ok")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == retries:
                tmp.unlink(missing_ok=True)
                return (dest.name, False, f"FAILED after {retries}: {exc}")
            time.sleep(1.5 * attempt)
    return (dest.name, False, "unreachable")


def verify_local(records: list[str], root: Path, jobs: int) -> list[str]:
    """HEAD every expected file; return the record paths whose local size is wrong."""
    bad: set[str] = set()

    def one(rec: str) -> tuple[str, bool]:
        for ext in (".hea", ".dat"):
            f = root / f"{rec}{ext}"
            if not f.exists():
                return rec, False
            remote = head_size(f"{BASE}/{rec}{ext}")
            if remote and f.stat().st_size != remote:
                return rec, False
        return rec, True

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for fut in as_completed([pool.submit(one, r) for r in records]):
            rec, ok = fut.result()
            if not ok:
                bad.add(rec)
    return sorted(bad)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="plan only, download nothing")
    ap.add_argument("--jobs", type=int, default=6, help="parallel downloads (default 6)")
    ap.add_argument("--types", nargs="+", default=None,
                    help="record types to take (default: force preprocess). Use 'raw' for unfiltered EMG.")
    ap.add_argument("--repair", action="store_true",
                    help="check every local file against its remote size and re-download mismatches")
    ap.add_argument("--limit-subjects", type=int, default=None,
                    help="only subjects 1..N - use 2 for a fast first slice")
    args = ap.parse_args()

    cfg = load_cfg()
    root = ROOT / cfg["data"]["root"]
    subset_types = dict(cfg["data"]["subset_record_types"])
    if args.types:
        subset_types = {s: list(args.types) for s in subset_types}

    records = select(read_records(root), subset_types)
    if args.limit_subjects:
        keep = {f"subject{n:02d}_" for n in range(1, args.limit_subjects + 1)}
        records = [r for r in records if any(k in r for k in keep)]

    if not records:
        print(f"ERROR: no records matched {subset_types}", file=sys.stderr)
        return 1

    for s, ts in subset_types.items():
        n = sum(1 for r in records if r.startswith(s + "/"))
        print(f"{s:16s}: {', '.join(ts):22s} -> {n} records")
    print(f"records      : {len(records)}  ->  {len(records) * 2} files (.hea + .dat)")
    print(f"destination  : {root}")

    if args.check:
        sample = [r for r in records if "force" not in r][:1] + [r for r in records if "force" in r][:1]
        est = 0.0
        for r in sample:
            sz = head_size(f"{BASE}/{r}.dat")
            kind = "force" if "force" in r else "emg  "
            print(f"  probe {kind}: {sz/1e6:8.2f} MB  ({r})")
            n = sum(1 for x in records if ("force" in x) == ("force" in r))
            est += sz * n
        print(f"\nestimated total: ~{est/1e9:.1f} GB")
        print("\n--check: nothing downloaded. Drop --check to run.")
        return 0

    if args.repair:
        print("\nverifying local files against remote sizes ...")
        bad = verify_local(records, root, args.jobs)
        if not bad:
            print("all files present and the right size. Nothing to repair.")
            return 0
        print(f"{len(bad)} record(s) incomplete or missing - re-downloading:")
        for r in bad[:10]:
            print(f"  {r}")
        if len(bad) > 10:
            print(f"  ... and {len(bad) - 10} more")
        records = bad

    root.mkdir(parents=True, exist_ok=True)
    jobs = []
    for r in records:
        for ext in (".hea", ".dat"):
            jobs.append((f"{BASE}/{r}{ext}", root / f"{r}{ext}"))

    done = new = failed = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(download, u, d): d for u, d in jobs}
        for fut in as_completed(futs):
            name, got, msg = fut.result()
            done += 1
            if msg.startswith("FAILED"):
                failed += 1
                print(f"  !! {name}: {msg}", file=sys.stderr)
            elif got:
                new += 1
            if done % 25 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)} files  ({new} new, {failed} failed)", flush=True)

    print(f"\ndone. {new} downloaded, {done - new - failed} already present, {failed} failed.")
    if failed:
        print("Re-run the same command - completed files are skipped.", file=sys.stderr)
        return 1
    print("Next: make check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
