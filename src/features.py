"""Filtering, windowing and classic sEMG features.

Deliberately boring. The question under test is whether force error falls as the
number of training SUBJECTS rises. A big model would confound that with capacity,
so the baseline is ridge regression on standard time-domain features.
"""
from __future__ import annotations

import numpy as np
from scipy import signal as sps


def design_filters(fs: int, band: tuple[float, float], notch_hz: float, notch_q: float):
    sos_bp = sps.butter(4, band, btype="bandpass", fs=fs, output="sos")
    b_n, a_n = sps.iirnotch(notch_hz, notch_q, fs=fs)
    return sos_bp, (b_n, a_n)


def preprocess(emg: np.ndarray, fs: int, band, notch_hz, notch_q) -> np.ndarray:
    """emg: (n_samples, n_channels) raw -> filtered, zero-phase.

    Zero-phase is correct here because this is offline analysis. A live pipeline
    must use a causal single pass; the two give different onset timing and mixing
    them is a classic source of irreproducible EMG results.
    """
    sos_bp, (b_n, a_n) = design_filters(fs, band, notch_hz, notch_q)
    x = sps.sosfiltfilt(sos_bp, emg, axis=0)
    x = sps.filtfilt(b_n, a_n, x, axis=0)
    return np.ascontiguousarray(x)


def _zc(w: np.ndarray, thr: float) -> np.ndarray:
    s = np.sign(w)
    changes = (s[:-1] * s[1:]) < 0
    big = np.abs(np.diff(w, axis=0)) > thr
    return np.sum(changes & big, axis=0).astype(float)


def _ssc(w: np.ndarray, thr: float) -> np.ndarray:
    d = np.diff(w, axis=0)
    changes = (d[:-1] * d[1:]) < 0
    big = np.maximum(np.abs(d[:-1]), np.abs(d[1:])) > thr
    return np.sum(changes & big, axis=0).astype(float)


def window_features(
    emg: np.ndarray, fs: int, window_ms: int, hop_ms: int, names: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    """-> (features (n_windows, n_channels*n_features), window_end_sample_index)"""
    win = int(round(fs * window_ms / 1000))
    hop = int(round(fs * hop_ms / 1000))
    n, c = emg.shape
    if n < win:
        return np.empty((0, c * len(names))), np.empty((0,), dtype=int)

    starts = np.arange(0, n - win + 1, hop)
    feats, ends = [], []
    for s0 in starts:
        w = emg[s0 : s0 + win]
        thr = 0.01 * np.std(w) + 1e-12
        cols = []
        for nm in names:
            if nm == "rms":
                cols.append(np.sqrt(np.mean(w**2, axis=0)))
            elif nm == "mav":
                cols.append(np.mean(np.abs(w), axis=0))
            elif nm == "wl":
                cols.append(np.sum(np.abs(np.diff(w, axis=0)), axis=0))
            elif nm == "zc":
                cols.append(_zc(w, thr))
            elif nm == "ssc":
                cols.append(_ssc(w, thr))
            else:
                raise ValueError(f"unknown feature: {nm}")
        feats.append(np.concatenate(cols))
        ends.append(s0 + win - 1)
    return np.asarray(feats, dtype=np.float32), np.asarray(ends, dtype=int)


def align_force(force: np.ndarray, force_fs: int, emg_idx: np.ndarray, emg_fs: int) -> np.ndarray:
    """Sample the 100 Hz force signal at the EMG window-end timestamps."""
    t = emg_idx / emg_fs
    f_idx = np.clip(np.round(t * force_fs).astype(int), 0, force.shape[0] - 1)
    return force[f_idx]
