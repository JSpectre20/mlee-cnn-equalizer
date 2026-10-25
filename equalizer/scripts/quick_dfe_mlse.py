"""Quick evidence: does decision feedback or a short Viterbi stage help on the simulated IM/DD link?

Linear baselines only (closed-form LS), so the numbers isolate the *structural* gain:
  FFE      N-tap FIR at nos=2, target s[n]
  FFE+DFE  same FIR plus B feedback taps on past *decisions* (fitted with true symbols,
           evaluated with the equalizer's own decisions, i.e. error propagation included)
  FFE+VA   FIR fitted to a partial-response target s[n] + a1 s[n-1] (+ a2 s[n-2]),
           followed by a 2-state (4-state) Viterbi detector on that target

PAM2 symbols s = 2*idx - 1. Fit on the first CHUNKS chunks of train.npz, test on the
first CHUNKS chunks of test_fresh.npz (each chunk = 200k symbols, edges cropped).

Usage: python scripts/quick_dfe_mlse.py [--chunks 3]
"""
import argparse
import json
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import as_strided

from eqsim.data import load_dataset

DATA = Path("checkpoints/fp32_v1/imdd_data")
CROP = 64


def windows(rx, taps, nos=2):
    """(N, taps) centred windows at every symbol, as a strided view (no copy)."""
    pad = taps // 2
    xp = np.pad(rx.astype(np.float64), (pad, pad + nos))
    n_sym = len(rx) // nos
    return as_strided(xp, shape=(n_sym, taps), strides=(xp.strides[0] * nos, xp.strides[0]))


def fit_ls(ds, taps, n_fb, target_taps, step=50_000):
    """Normal equations for [window, 1, s[n-1..n-n_fb]] -> sum_j target_taps[j] * s[n-j]."""
    d = taps + 1 + n_fb
    A, b = np.zeros((d, d)), np.zeros(d)
    for rx, idx in zip(ds.rx, ds.idx):
        s = 2.0 * idx - 1.0
        W = windows(rx, taps)
        for a in range(CROP, len(s) - CROP, step):
            e = min(a + step, len(s) - CROP)
            n = np.arange(a, e)
            X = np.empty((e - a, d))
            X[:, :taps] = W[a:e]
            X[:, taps] = 1.0
            for k in range(1, n_fb + 1):
                X[:, taps + k] = s[n - k]
            y = sum(c * s[n - j] for j, c in enumerate(target_taps))
            A += X.T @ X
            b += X.T @ y
    return np.linalg.solve(A + 1e-6 * np.eye(d), b)


def ffe_out(rx, w, taps):
    return windows(rx, taps) @ w[:taps] + w[taps]


def ber_ffe(ds, w, taps):
    errs = tot = 0
    for rx, idx in zip(ds.rx, ds.idx):
        y = ffe_out(rx, w, taps)[CROP:-CROP]
        errs += int(np.sum((y > 0) != (idx[CROP:-CROP] == 1)))
        tot += len(y)
    return errs / tot


def ber_dfe(ds, w, taps, n_fb):
    fb = w[taps + 1:]
    errs = tot = 0
    for rx, idx in zip(ds.rx, ds.idx):
        y = ffe_out(rx, w, taps)
        d = np.zeros(len(y))
        d[:CROP] = 2.0 * idx[:CROP] - 1.0              # start from known symbols (training preamble)
        for n in range(CROP, len(y)):
            v = y[n]
            for k in range(n_fb):
                v += fb[k] * d[n - 1 - k]
            d[n] = 1.0 if v > 0 else -1.0
        dec = d[CROP:-CROP] > 0
        errs += int(np.sum(dec != (idx[CROP:-CROP] == 1)))
        tot += len(dec)
    return errs / tot


def ber_viterbi(ds, w, taps, target_taps):
    """Viterbi on y[n] ~ sum_j c_j s[n-j]; state = last (len(c)-1) symbols."""
    c = np.asarray(target_taps)
    mem = len(c) - 1
    n_states = 2 ** mem
    # state bits: bit k = s[n-1-k] > 0
    st_sym = np.array([[1.0 if (st >> k) & 1 else -1.0 for k in range(mem)] for st in range(n_states)])
    errs = tot = 0
    for rx, idx in zip(ds.rx, ds.idx):
        y = ffe_out(rx, w, taps)
        N = len(y)
        # expected outputs for (state, new symbol)
        exp = np.zeros((n_states, 2))
        for st in range(n_states):
            for u, su in enumerate((-1.0, 1.0)):
                exp[st, u] = c[0] * su + (st_sym[st] @ c[1:])
        nxt = np.array([[((st << 1) | u) & (n_states - 1) for u in (0, 1)] for st in range(n_states)])
        pm = np.zeros(n_states)
        surv = np.zeros((N, n_states), dtype=np.int16)    # previous state for each new state
        for n in range(N):
            cand = pm[:, None] + (y[n] - exp) ** 2        # (state, u)
            new_pm = np.full(n_states, np.inf)
            prev = np.zeros(n_states, dtype=np.int16)
            for st in range(n_states):
                for u in (0, 1):
                    ns = nxt[st, u]
                    if cand[st, u] < new_pm[ns]:
                        new_pm[ns] = cand[st, u]
                        prev[ns] = st
            pm = new_pm - new_pm.min()
            surv[n] = prev
        st = int(np.argmin(pm))
        dec = np.zeros(N, dtype=bool)
        for n in range(N - 1, -1, -1):
            dec[n] = bool(st & 1)                          # newest symbol of state at time n
            st = surv[n, st]
        errs += int(np.sum(dec[CROP:-CROP] != (idx[CROP:-CROP] == 1)))
        tot += N - 2 * CROP
    return errs / tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", type=int, default=3)
    args = ap.parse_args()
    tr = load_dataset(DATA / "train.npz", 2, 2)
    te = load_dataset(DATA / "test_fresh.npz", 2, 2)
    tr.rx, tr.idx = tr.rx[:args.chunks], tr.idx[:args.chunks]
    te.rx, te.idx = te.rx[:args.chunks], te.idx[:args.chunks]
    res = {}
    for taps in (57, 121):
        w = fit_ls(tr, taps, 0, [1.0])
        res[f"FFE{taps}"] = ber_ffe(te, w, taps)
        for n_fb in (1, 2, 4):
            w = fit_ls(tr, taps, n_fb, [1.0])
            res[f"FFE{taps}+DFE{n_fb}"] = ber_dfe(te, w, taps, n_fb)
        best = None
        for a1 in (0.25, 0.5, 0.75, 1.0):
            w = fit_ls(tr, taps, 0, [1.0, a1])
            b = ber_viterbi(te, w, taps, [1.0, a1])
            res[f"FFE{taps}+VA2(1,{a1})"] = b
            best = b if best is None else min(best, b)
        for a1, a2 in ((0.5, 0.25), (0.75, 0.25), (1.0, 0.5)):
            w = fit_ls(tr, taps, 0, [1.0, a1, a2])
            res[f"FFE{taps}+VA4(1,{a1},{a2})"] = ber_viterbi(te, w, taps, [1.0, a1, a2])
        print(json.dumps({k: v for k, v in res.items() if k.startswith(f"FFE{taps}")}), flush=True)
    n_test = sum(len(i) - 2 * CROP for i in te.idx)
    out = Path("results/quick_dfe_mlse")
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({"test_symbols": n_test, "ber": res}, indent=2))
    print("test symbols", n_test)


if __name__ == "__main__":
    main()
