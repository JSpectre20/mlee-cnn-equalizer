"""QAT of the CNN+DFE2 equalizer (improvement I5) and its integer model.

Source: results/dfe_stress/models/<key>.pt (default: best 24 dB / 31.5 km CNN+DFE2 seed).
QAT as in run_quant.py (LSQ, Adam lr 2e-4, --iters, b bits for weights / activations / input),
with teacher-forced feedback taps; the integer model gets fb[v][k] = round(fb[k] / out_scale[v]).
Scored with the integer golden model (own-decision feedback) on the fresh 4M test set.
Writes results/quant/ours_bce_dfe_w<b>/{qat_model.pt, integer_model.pkl, metrics.json}.

Usage: python scripts/run_quant_dfe.py --bits 6 --iters 4000
"""
import argparse
import copy
import json
import pickle
import time
from pathlib import Path

import numpy as np
import torch

from eqsim.data import load_dataset
from eqsim.dfe import CNNDFE, train_cnn_dfe
from eqsim.quant import QuantCNNDFE, QuantNeyCNN, export_integer_dfe, integer_ber

CK = Path("checkpoints/fp32_v1/imdd_data")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="results/dfe_stress/models/snr24_L31.5_cnndfe_s1.pt")
    ap.add_argument("--bits", type=int, nargs="+", default=[6])
    ap.add_argument("--iters", type=int, default=4000)
    args = ap.parse_args()
    torch.set_num_threads(4)
    ck = torch.load(args.src)
    fp = CNNDFE(n_fb=2, **ck["cfg"])
    fp.load_state_dict(ck["state_dict"])
    fp.eval()
    tr = load_dataset(CK / "train.npz", 2, 2)
    te = load_dataset(CK / "test_fresh.npz", 2, 2)
    for bits in args.bits:
        torch.manual_seed(0)
        q = QuantNeyCNN(fp.cnn, bits, bits, bits)
        q.calibrate(torch.from_numpy(np.stack([tr.rx[0][:65536], tr.rx[1][:65536]])))
        qd = QuantCNNDFE(q, fp.fb.detach().numpy())
        ptq_ber, _ = integer_ber(export_integer_dfe(qd), te)
        t0 = time.time()
        train_cnn_dfe(qd, tr, iters=args.iters, lr=2e-4, seed=0)
        qd.eval()
        im = export_integer_dfe(qd)
        qat_ber, n = integer_ber(im, te)
        im_nofb = copy.deepcopy(im)
        im_nofb.fb = None
        nofb_ber, _ = integer_ber(im_nofb, te)
        d = Path("results/quant") / f"ours_bce_dfe_w{bits}"
        d.mkdir(parents=True, exist_ok=True)
        torch.save({"cfg": ck["cfg"], "bits": bits, "state_dict": qd.state_dict(), "source": args.src}, d / "qat_model.pt")
        with open(d / "integer_model.pkl", "wb") as f:
            pickle.dump(im, f)
        row = {"name": "ours_bce_dfe", "source": args.src, "bits": bits, "ptq_ber": ptq_ber, "qat_ber": qat_ber,
               "qat_ber_without_feedback": nofb_ber, "bits_tested": n, "fb_float": [float(v) for v in qd.fb.detach()],
               "fb_int": im.fb.tolist(), "out_scale": im.out_scale.tolist(), "qat_s": round(time.time() - t0, 1)}
        (d / "metrics.json").write_text(json.dumps(row, indent=2))
        print(json.dumps({k: row[k] for k in ("bits", "ptq_ber", "qat_ber", "qat_ber_without_feedback", "fb_int")}), flush=True)


if __name__ == "__main__":
    main()
