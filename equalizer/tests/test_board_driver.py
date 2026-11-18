"""Offline test of board/cnn_eq_pynq.py against a simulated PYNQ (no board needed).

A fake `pynq` module provides Overlay / allocate; its core holds the AXI-Lite registers and the parameter memory,
and its DMA computes each frame with the frozen integer golden model, but only if the driver loaded exactly the
336 parameter words of params.mem. This checks the driver's register use, parameter load, buffer handling, byte
and int16 interpretation, BER bookkeeping and the results file. It does not test the hardware itself.
Needs board/board_vectors.npz (scripts/make_board_vectors.py); skipped otherwise.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
VEC = ROOT / "board" / "board_vectors.npz"
MODEL = ROOT / "checkpoints" / "hw_v2" / "results" / "quant" / "ours_bce_dfe_w8" / "integer_model.pkl"
sys.path.insert(0, str(ROOT / "board"))
import cnn_eq_pynq as drv  # noqa: E402

pytestmark = pytest.mark.skipif(not VEC.exists(), reason="run scripts/make_board_vectors.py first")


class FakeCore:
    def __init__(self, im, params, shape_word, corrupt=False):
        self.im, self.params, self.shape, self.corrupt = im, [int(p) for p in params], int(shape_word), corrupt
        self.pmem, self.ctrl = {}, 0
        self.cnt = dict.fromkeys(("FRAMES", "BUSY_CYC", "IN_BEATS", "OUT_BEATS"), 0)

    def read(self, off):
        fixed = {0x00: drv.ID_NEQ1, 0x04: self.shape, 0x08: len(self.params), 0x0C: self.ctrl}
        if off in fixed:
            return fixed[off]
        name = {v: k for k, v in drv.REG.items()}[off]
        return self.cnt[name]

    def write(self, off, val):
        if off >= drv.PMEM:
            self.pmem[(off - drv.PMEM) // 4] = int(val)
        elif off == drv.REG["CTRL"]:
            self.ctrl = int(val)
            if val & 1:
                self.cnt = dict.fromkeys(self.cnt, 0)

    def process(self, codes):
        assert self.ctrl == 0, "datapath held in reset"
        assert [self.pmem.get(i) for i in range(len(self.params))] == self.params, "parameters not loaded as in params.mem"
        _, u = self.im.forward_int(np.asarray(codes, dtype=np.int8).astype(np.int64))
        out = np.clip(u, -32768, 32767).astype(np.int16)
        if self.corrupt:
            out[1000] += 1
        n = len(codes)
        self.cnt["IN_BEATS"] += n
        self.cnt["OUT_BEATS"] += len(out)
        self.cnt["FRAMES"] += 1
        self.cnt["BUSY_CYC"] += int(n / 0.975)
        return out


class FakeChannel:
    def __init__(self, dma, kind):
        self.dma, self.kind, self.buf = dma, kind, None

    def transfer(self, buf):
        if self.kind == "recv":
            self.buf = buf
        else:
            assert self.dma.recvchannel.buf is not None, "S2MM must be armed before MM2S"
            self.dma.recvchannel.buf[:] = self.dma.core.process(buf)
            self.dma.recvchannel.buf = None

    def wait(self):
        pass


class FakeDMA:
    def __init__(self, core):
        self.core = core
        self.recvchannel = FakeChannel(self, "recv")
        self.sendchannel = FakeChannel(self, "send")


def fake_pynq(core):
    class Overlay:
        def __init__(self, path):
            assert Path(path).name == "cnn_eq.bit"
            self.eq, self.dma = core, FakeDMA(core)

    mod = type(sys)("pynq")
    mod.Overlay, mod.__version__ = Overlay, "fake"
    mod.allocate = lambda shape, dtype: np.zeros(shape, dtype=dtype)
    return mod


@pytest.fixture(scope="module")
def small(tmp_path_factory):
    """The first two frames of the real board vectors (keeps the test fast)."""
    v = dict(np.load(VEC))
    im = pickle.load(open(MODEL, "rb"))
    for k in ("x", "u_gold", "bits_true"):
        v[k] = v[k][:2]
    crop, n = int(v["crop"]), int(v["n_sym"])
    bits = np.unpackbits(v["bits_true"], axis=1)[:, :n]
    v["golden_errors"] = np.int64(sum(int(np.sum((v["u_gold"][i] > 0)[crop:-crop] != bits[i, crop:-crop])) for i in range(2)))
    p = tmp_path_factory.mktemp("board") / "small.npz"
    np.savez(p, **v)
    return p, v, im


def test_driver_bit_exact(small, tmp_path):
    p, v, im = small
    core = FakeCore(im, v["params"], v["shape_word"])
    res = drv.run_test(vectors=p, results=tmp_path / "r.json", pynq=fake_pynq(core), repeats=1, log=lambda *_: None)
    assert res["bit_exact"] and res["output_mismatches"] == 0 and res["counters_ok"]
    assert res["bit_errors"] == int(v["golden_errors"]) and res["bits_counted"] == 2 * (int(v["n_sym"]) - 128)
    assert json.loads((tmp_path / "r.json").read_text())["frames"] == 2


def test_driver_reports_a_wrong_output(small, tmp_path):
    p, v, im = small
    core = FakeCore(im, v["params"], v["shape_word"], corrupt=True)
    res = drv.run_test(vectors=p, results=tmp_path / "r.json", pynq=fake_pynq(core), repeats=1, log=lambda *_: None)
    assert not res["bit_exact"] and res["output_mismatches"] == 2     # one corrupted value per frame


def test_driver_rejects_a_wrong_core(small, tmp_path):
    p, v, im = small
    core = FakeCore(im, v["params"], 0x03090508)                     # the paper's shape, not the deployed one
    with pytest.raises(RuntimeError):
        drv.run_test(vectors=p, results=tmp_path / "r.json", pynq=fake_pynq(core), repeats=1, log=lambda *_: None)
