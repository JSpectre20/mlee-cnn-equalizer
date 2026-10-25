"""Confirm the FFE+DFE result of quick_dfe_mlse.py on the full fresh test set, with sanity checks.

  - FFE sizes 9..57 with 0/1/2 feedback taps, fitted on 3 train chunks, tested on all test_fresh chunks
  - sanity: genie feedback (true past symbols) and random feedback (must collapse)
Writes results/quick_dfe_mlse/confirm.json.
"""
import json
from pathlib import Path

import numpy as np

from eqsim.data import load_dataset
from scripts.quick_dfe_mlse import CROP, DATA, ber_dfe, ber_ffe, ffe_out, fit_ls


def ber_dfe_feedback(ds, w, taps, n_fb, mode, rng):
    """mode 'genie': feed true past symbols; 'random': feed random symbols."""
    fb = w[taps + 1:]
    errs = tot = 0
    for rx, idx in zip(ds.rx, ds.idx):
        s = 2.0 * idx - 1.0
        y = ffe_out(rx, w, taps)
        src = s if mode == "genie" else rng.choice([-1.0, 1.0], size=len(s))
        v = y.copy()
        for k in range(1, n_fb + 1):
            v[k:] += fb[k - 1] * src[:-k]
        dec = v[CROP:-CROP] > 0
        errs += int(np.sum(dec != (idx[CROP:-CROP] == 1)))
        tot += len(dec)
    return errs / tot


def main():
    tr = load_dataset(DATA / "train.npz", 2, 2)
    te = load_dataset(DATA / "test_fresh.npz", 2, 2)
    tr.rx, tr.idx = tr.rx[:3], tr.idx[:3]
    n_test = sum(len(i) - 2 * CROP for i in te.idx)
    rng = np.random.default_rng(0)
    res = {"test_symbols": n_test}
    for taps in (9, 17, 25, 33, 41, 57):
        res[f"FFE{taps}"] = ber_ffe(te, fit_ls(tr, taps, 0, [1.0]), taps)
        for n_fb in (1, 2):
            w = fit_ls(tr, taps, n_fb, [1.0])
            res[f"FFE{taps}+DFE{n_fb}"] = ber_dfe(te, w, taps, n_fb)
            if n_fb == 2 and taps in (17, 57):
                res[f"FFE{taps}+DFE2 genie"] = ber_dfe_feedback(te, w, taps, 2, "genie", rng)
                res[f"FFE{taps}+DFE2 random-fb"] = ber_dfe_feedback(te, w, taps, 2, "random", rng)
        print(json.dumps({k: v for k, v in res.items() if k.startswith(f"FFE{taps}")}), flush=True)
    out = Path("results/quick_dfe_mlse")
    out.mkdir(parents=True, exist_ok=True)
    (out / "confirm.json").write_text(json.dumps(res, indent=2))
    print("test symbols", n_test)


if __name__ == "__main__":
    main()
