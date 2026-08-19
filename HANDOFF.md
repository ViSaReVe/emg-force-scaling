# Handoff — read this first

For a fresh session, or for me in three weeks. Everything needed to continue without
re-deriving anything. Written 19 Aug 2026.

---

## The situation

**17 Aug**, intro call with **Julian Olschwang**, founder of **Hemlock** (YC F26, Los Angeles,
one employee). Wrist sEMG band — "the Bracelet" — sold as force-labelled demonstration data for
training robot manipulation policies.

Outcome: the full-time founding-engineer role is **closing**. He offered "at best an
internship," rolling, revisit later. He committed to an **evaluation kit in ~6 weeks**
(≈ end of September). He said, unprompted, at the very end of the call:

> *"The main differentiator between what they're doing and what we're doing is we're trying to
> amass the data volume needed to make these models actually useful and generalizable. There's
> this kind of a one-off system off of 10 hours — there's only so much you can do."*

**That sentence is the whole project.** The follow-up email quoted it back and committed to:
*run the scaling question on public data and send the result within two weeks, either way.*

**Due 31 Aug.** Julian replied: *"I agree. This is good thinking. When I have a better idea of
when I can get an early kit in your hands, I'll let you know."*

---

## Where the project is

**The experiment is finished.** What remains is writing.

| | |
|---|---|
| Repo | `~/Documents/Projects/emg-force-scaling`, private, `github.com/ViSaReVe/emg-force-scaling` |
| Data | Hyser (PhysioNet hd-semg 2.0.0), 20 subjects × 2 sessions, ~5 GB, in `data/` (gitignored) |
| Done | fetch → prepare → sweep → paired → plot, all reproducible via `make` |
| Left | README rewrite · email to Julian · flip repo public · *optional* calibration-budget surface |

### The result

| Arm | MAE (%MVC) |
|---|---|
| Zero-shot, 1 training subject | 19.2 |
| Zero-shot, 16 training subjects | **11.2** |
| That subject's own calibration, **next day** | 15.2 (median 11.8) |
| That subject's own calibration, **same session** | 8.4 |

- Power law **`MAE = 18.3 · N^(−0.192)`**, log–log R² = **0.966**.
- Zero-shot overtakes next-day calibration at **N ≈ 4–8**; wins for **14/20** subjects at N=16.
  Paired **Wilcoxon p = 0.0027**, rank-biserial 0.733. Holds without the outlier (p = 0.0053).
- Zero-shot **loses 20/20** to same-session calibration — the honest limit of the claim.
- Extrapolating to that ceiling: **~57 wearers** (mean fit) to **~113** (median fit).

---

## Decisions already made — do not relitigate

| Decision | Why |
|---|---|
| **Ridge, not a neural net** | The variable under test is *subject count*. A big model confounds capacity with data volume. Ridge is the control. |
| **%MVC, not newtons** | Hyser stores **amplifier volts** with a per-finger gain and ships no V→N constant. Absolute newtons are not recoverable. |
| **Leave-one-subject-out only** | Never a random split — windows overlap 50%, a random split leaks. |
| **Temporal split for the within-session arm** | Same reason. First 60% / last 40%. |
| **Three arms, not two** | Train-sess1→test-sess2 is cross-day *and* re-donned — harder than ForceBand's same-session calibration. Splitting them isolates the cost of re-donning. |
| **8 channels from ED + FD only** | Distal arrays only, to imitate a wrist band. Selected **by channel name**, never index. |
| **`random_dataset` + `mvc_dataset` force only** | ~5 GB instead of 143. `raw` is a second copy of the EMG; MVC EMG is unused. |
| **Blue / burnt-orange / violet palette** | The obvious green failed a colourblind check against the orange (protan ΔE 6.0). Validated trio. |

---

## Gotchas — every one of these cost time

1. **Force is in volts, not newtons.** `equipment_info.pdf` advertises ±200 N sensors; the
   `.hea` headers say `/V` with a different gain per finger. Read the header, not the doc.
2. **Channels are stored in reverse column order** (`ED-8-8, ED-8-7, …`). Index-based montage
   selection silently grabs the wrong electrodes. Always resolve by name; `make check` must
   print `resolved by_name`.
3. **urllib returns truncated bodies without raising.** Downloads are now size-verified against
   `Content-Length`. If `prepare` reports `cannot reshape array of size N into shape (256)`,
   run `python -m src.fetch --repair`.
4. **Folder names are `subject01_session1`** — no underscore after "subject".
5. **Interactive zsh does not treat `#` as a comment.** Pasting `make fetch  # ~5 GB` fails with
   `not enough directory stack entries`. `setopt interactivecomments` is now in `~/.zshrc`.
6. **The Cowork bridge cannot delete files.** Never run `git` writes through it — it leaves
   `.git/HEAD.lock` behind and jams the repo. **Claude writes files; Vidya runs git.**
7. **PhysioNet is unreachable from the Cowork container.** All downloads happen on the Mac.

---

## Prior art — checked, claim survives

Meta's **Nature 2025** neuromotor-interface paper reports a power law in participant count —
but for **wrist angle, gestures and handwriting** (162 / 4,900 / 6,627 participants). **Force is
not among their tasks.** *Scaling and Distilling Transformer Models for sEMG* (arXiv:2507.22094)
scales **model parameters** on typing with a fixed 100-user set — no subject axis, no force.

So the claim is: *the power law is established for sEMG kinematics and gestures; this measures
it for **force**, and finds the same functional form.* Never "nobody has done EMG scaling laws."

Useful anchor: Meta's **wrist decoder used 162 participants** — their smallest task and the
nearest thing to continuous regression. The 57–113 extrapolation sits *below* that, so the
target is not exotic.

---

## ⚠️ Keep two lanes apart

- **This repo** — the research. Nothing about Julian personally. Public when the email goes out.
- **The Obsidian vault**, `Career/Applications/Hemlock/` — fit brief, risk read, call debrief,
  comp and visa notes, candid assessments of Julian. **Never goes in this repo, never public.**

---

## Bootstrapping a new chat

Point it at this file. A good opening:

> I'm continuing a project in `~/Documents/Projects/emg-force-scaling`. Read `HANDOFF.md`,
> `RESEARCH.md` and `CHANGELOG.md` in that folder, then tell me the state and what's next
> before doing anything.

Persistent memory already carries the relationship context — see `/areas/hemlock.md` and
`/people/julian-olschwang.md`. The vault holds the career side. This repo holds the work.

**Reading order for a cold start:** `HANDOFF.md` → `RESEARCH.md` (findings, limits, the three
paths) → `CHANGELOG.md` (what happened when) → `README.md` (how to run it).
