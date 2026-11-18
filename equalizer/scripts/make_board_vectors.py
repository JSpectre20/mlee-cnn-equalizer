r"""Build the on-board test package for the PYNQ-Z2 run (equalizer/board/).

Everything comes from the frozen artefacts, so the board runs exactly the model that was measured in simulation:
  model   checkpoints/hw_v2/results/quant/ours_bce_dfe_w8/integer_model.pkl  (deployed CNN + DFE, 8 bit)
  params  checkpoints/hw_v2/rtl/gen/ours_bce_dfe_w8/params.mem              (336 words written over AXI-Lite)
  data    checkpoints/fp32_v1/imdd_data/test_fresh.npz                      (fresh 4M-symbol test set, 20 chunks)
  overlay checkpoints/hw_v2/rtl/bd/proj_ours_bce_dfe_w8_200_dsp1_2clk_r8c/overlay/cnn_eq.{bit,hwh}

Each 200,000-symbol chunk is one frame (400,000 input bytes, 200,000 int16 outputs), exactly as in
eqsim.quant.integer_ber, so the board must reproduce the reported BER (2 errors in 3,997,440 bits) and the golden
outputs bit for bit.

Checks before writing: the integer model reproduces the RTL test vectors (rtl/gen/ours_bce_dfe_w8/test_out.mem),
the parameter image equals params.mem, and the golden BER equals the recorded metrics.json.

Run from equalizer/:  $env:PYTHONPATH=(Get-Location).Path; D:\venvs\mlee-eq\Scripts\python.exe scripts\make_board_vectors.py
Writes board/board_vectors.npz (about 10 MB) and copies the overlay into board/.
"""
import json
import pickle
import shutil
from pathlib import Path

import numpy as np

from eqsim.data import load_dataset

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "checkpoints" / "hw_v2"
MODEL = HW / "results" / "quant" / "ours_bce_dfe_w8" / "integer_model.pkl"
METRICS = HW / "results" / "quant" / "ours_bce_dfe_w8" / "metrics.json"
GEN = HW / "rtl" / "gen" / "ours_bce_dfe_w8"
OVERLAY = HW / "rtl" / "bd" / "proj_ours_bce_dfe_w8_200_dsp1_2clk_r8c" / "overlay"
DATA = ROOT / "checkpoints" / "fp32_v1" / "imdd_data" / "test_fresh.npz"
OUT = ROOT / "board"
CROP = 64


def sat16(u):
    return np.clip(u, -32768, 32767).astype(np.int16)


def main():
    im = pickle.load(open(MODEL, "rb"))
    params = np.array([int(l, 16) for l in (GEN / "params.mem").read_text().split()], dtype=np.uint32)
    meta = json.loads((GEN / "meta.json").read_text())
    assert len(params) == meta["N_PARAM"] == 336

    # 1. the model is the one the RTL was verified against: reproduce its test vectors (3 frames x 1024 symbols)
    ds = load_dataset(DATA, 2, 2)
    n_s, nos = meta["frame_symbols"], im.nos
    exp = [int(l, 16) for l in (GEN / "test_out.mem").read_text().split()]
    got = []
    for fr in range(meta["test_frames"]):
        seg = ds.rx[0][fr * n_s * nos:(fr + 1) * n_s * nos].astype(np.float64)
        _, u = im.forward_int(im.quantize_input(seg))
        got += [int(v) & 0xFFFF for v in sat16(u)]
    assert got == exp, "integer model does not reproduce rtl/gen test_out.mem"
    print(f"check 1: integer model reproduces the RTL test vectors ({len(exp)} outputs)")

    # 2. golden outputs for the whole fresh set, one frame per chunk
    xs, us, bits_true, errs, total = [], [], [], 0, 0
    for rx, idx in zip(ds.rx, ds.idx):
        x = im.quantize_input(rx.astype(np.float64))
        assert x.min() >= -128 and x.max() <= 127 and len(x) % (2 * im.vp) == 0
        bits, u = im.forward_int(x)
        xs.append(x.astype(np.int8))
        us.append(sat16(u))
        assert np.array_equal(sat16(u) > 0, bits.astype(bool)), "saturation changed a decision"
        bits_true.append(np.packbits(idx.astype(np.uint8)))
        errs += int(np.sum(bits[CROP:-CROP] != idx[CROP:-CROP]))
        total += len(idx) - 2 * CROP
    ber = errs / total
    rec = json.loads(METRICS.read_text())
    assert total == rec["bits_tested"] and abs(ber - rec["qat_ber"]) < 1e-12, (ber, rec["qat_ber"])
    print(f"check 2: golden BER {ber:.3e} ({errs} errors in {total} bits) = recorded {rec['qat_ber']:.3e}")

    OUT.mkdir(exist_ok=True)
    np.savez_compressed(
        OUT / "board_vectors.npz",
        params=params, x=np.stack(xs), u_gold=np.stack(us), bits_true=np.stack(bits_true),
        n_sym=np.int64(len(ds.idx[0])), crop=np.int64(CROP), golden_errors=np.int64(errs), golden_bits=np.int64(total),
        shape_word=np.uint32((meta["L"] << 24) | (meta["K"] << 16) | (meta["C"] << 8) | meta["VP"]))
    for f in ("cnn_eq.bit", "cnn_eq.hwh"):
        shutil.copyfile(OVERLAY / f, OUT / f)
        (OUT / f).chmod(0o644)
    mb = (OUT / "board_vectors.npz").stat().st_size / 1e6
    print(f"wrote board/board_vectors.npz ({mb:.1f} MB: {len(xs)} frames x {len(ds.idx[0])} symbols) and the overlay")


if __name__ == "__main__":
    main()
