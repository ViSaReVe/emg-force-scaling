# Links & downloads

Everything needed for the study, in the order you will want it.

---

## 1. The data — Hyser (PhysioNet)

**Landing page (read the "Files" tab):** https://physionet.org/content/hd-semg/2.0.0/
**File browser:** https://physionet.org/files/hd-semg/2.0.0/

Open access, no login. Cite as: Jiang X, Liu X, Fan J, Ye X, Dai C, Clancy EA, Akay M, Chen W.
*Open Access Dataset, Toolbox and Benchmark Processing Results of High-Density Surface
Electromyogram Recordings.* IEEE TNSRE, 2021.

### Step 0 — grab the three small metadata files FIRST (< 2 MB, 5 seconds)

Do this **before** the 10 GB download. It unblocks the montage and the file-naming questions
immediately, and if something is wrong with our assumptions we find out now rather than
after an overnight transfer.

```bash
cd ~/Documents/Projects/emg-force-scaling
mkdir -p data/hd-semg/2.0.0 && cd data/hd-semg/2.0.0
# no trailing comments on these lines - curl treats extra words as more URLs
curl -O https://physionet.org/files/hd-semg/2.0.0/equipment_info.pdf
curl -O https://physionet.org/files/hd-semg/2.0.0/readme.txt
curl -O https://physionet.org/files/hd-semg/2.0.0/RECORDS
```

`RECORDS` alone lets us verify the folder/file naming for all 40 subject-sessions without
downloading a single signal file.

### Step 1 — the actual data (start it and go to bed)

**Exact directory names on the server** (note the `_dataset` suffix — the config now matches):

| Directory | Size | Take it? |
|---|---|---|
| `random_dataset/` | **9.8 GB** | **Yes** — unscripted finger combinations, closest to natural varied-force manipulation, and the subset with a published comparable |
| `mvc_dataset/` | 7.8 GB | Optional — true %MVC normalisation. Skip on first pass; the code falls back to task-peak |
| `1dof_dataset/` | 29.3 GB | No |
| `ndof_dataset/` | 58.6 GB | No |
| `pr_dataset/` | 37.1 GB | No — gestures, not force |

`src/fetch.py` is now **pure Python** - no wget, no awscli. It reads the `RECORDS`
manifest you already downloaded and fetches exactly the records we need, in parallel,
resumably.

```bash
cd ~/Documents/Projects/emg-force-scaling
source .venv/bin/activate
python -m src.fetch --check              # plan + real size probe, downloads nothing
python -m src.fetch --limit-subjects 2   # ~250 MB first slice, proves it works
make fetch                               # the rest (~5 GB)
```

**Each session ships three record types** - `force`, `preprocess`, `raw`. `raw` is a
second full copy of the EMG, so we skip it: **~5 GB instead of 9.8 GB.** Switch with
`--types force raw` if you ever want to own the filtering yourself.

**Disk check before you start:** `df -h .` — you had 40 GB free at 92% used.

---

## 2. Documentation that answers our open questions

| Question | Where |
|---|---|
| Electrode array geometry, IED, placement | `equipment_info.pdf` (in the download above) |
| Channel naming | `readme.txt` — **already resolved:** channels are `XX-i-j`, `XX` ∈ ED / EP / FD / FP (extensor-distal, extensor-proximal, flexor-distal, flexor-proximal), `i`,`j` = row/col in an 8×8 array. Force channels: `thumb`, `index`, `middle`, `ring`, `little`. |
| Benchmark numbers to sanity-check against | IEEE TNSRE 2021 paper below |

**Hyser paper:** https://pubmed.ncbi.nlm.nih.gov/34018935/ ·
https://www.embs.org/tnsre/articles/open-access-dataset-toolbox-and-benchmark-processing-results-of-high-density-surface-electromyogram-recordings/
**Semantic Scholar (often has a free PDF):** https://www.semanticscholar.org/paper/ed8bc4a3028136dbe3af6f2f18f7087369962df3
**WFDB Python docs:** https://wfdb.readthedocs.io/ · https://github.com/MIT-LCP/wfdb-python

---

## 3. The work this is aimed at

**ForceBand** — the benchmark, and the source of the "shape but not scale" finding
- Paper: https://arxiv.org/abs/2606.26093
- Project page: https://forceband-emg.github.io/
- Code + checkpoint + the README with the zero-shot numbers: https://github.com/Bottle101/ForceBand

**Meta / CTRL-labs — the scaling-law evidence**
- emg2pose (NeurIPS 2024 D&B): https://arxiv.org/abs/2412.02725
- Meta blog + dataset release: https://ai.meta.com/blog/open-sourcing-surface-electromyography-datasets-neurips-2024/
- Code: https://github.com/facebookresearch/emg2pose
- Neural Band product page (the 16-ch, 2 kHz band that ships): https://about.fb.com/news/2025/09/meta-ray-ban-display-ai-glasses-emg-wristband/

**Why MVIC normalisation is not the answer** — the counter-evidence to cite in the write-up
- CEDE consensus on EMG normalisation: https://research.vu.nl/ws/portalfiles/portal/122516008/
- Norcross et al., 61–118% intersubject CV after MVIC normalisation:
  https://exss.unc.edu/wp-content/uploads/sites/779/2013/01/JJEK_1048_Published_Version_Norcross.pdf

**Hemlock** — https://hemlock.info · https://www.ycombinator.com/companies/hemlock

---

## 4. Backup / extension datasets (only if Hyser disappoints)

- **HD-FW KIN** — 448-ch HD-sEMG incl. wrist "far-field" grids, 21 subjects, finger force at
  20/40% MVC. Notably, wrist-position arrays performed about as well as forearm arrays.
  Paper: https://www.nature.com/articles/s41597-025-04749-8 ·
  Data: https://physionet.org/content/hand-kinematics-semg/
- **Ninapro DB2** (Exercise 3 has finger force): https://ninapro.hevs.ch/instructions/DB2.html

---

## 5. Environment setup (your Mac, your terminal)

```bash
cd ~/Documents/Projects/emg-force-scaling
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make smoke && make sweep plot     # ~1 min, synthetic - proves the harness runs
rm -rf results/cache results/*.csv results/*.png
```

`wget` if you do not have it: `brew install wget` (or use the `aws s3 sync` line above).
