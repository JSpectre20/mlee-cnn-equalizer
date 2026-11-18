"""Driver and on-board test for the CNN + DFE equalizer overlay on a PYNQ-Z2 (needs only pynq + numpy).

Files next to this script: cnn_eq.bit + cnn_eq.hwh (overlay), board_vectors.npz (scripts/make_board_vectors.py).
Run on the board (Jupyter terminal or notebook):   sudo python3 cnn_eq_pynq.py      -> board_results.json

Hardware contract (rtl/WEIGHT_FORMAT.md, checkpoints/hw_v2):
  eq  @ 0x4000_0000  AXI-Lite: 0x00 ID "NEQ1", 0x04 SHAPE {L,K,C,VP}, 0x08 NPARAM, 0x0C CTRL (bit 0 = datapath reset,
                     keeps the parameters), 0x10 FRAMES, 0x14 BUSY_CYC (200 MHz cycles), 0x18 IN_BEATS, 0x1C OUT_BEATS;
                     parameter word i at 0x4000 + 4 i (write only)
  dma @ 0x4040_0000  AXI DMA, simple mode, no interrupts (polling); one transfer = one frame (TLAST at its end)
  MM2S: int8 input codes, 2 per symbol (a 32-bit word carries 4 codes, lowest byte first)
  S2MM: int16 soft output per symbol (2 per 32-bit word, low half first); decision bit = (value > 0)
"""
import json
import time
from pathlib import Path

import numpy as np

REG = {"ID": 0x00, "SHAPE": 0x04, "NPARAM": 0x08, "CTRL": 0x0C, "FRAMES": 0x10, "BUSY_CYC": 0x14, "IN_BEATS": 0x18,
       "OUT_BEATS": 0x1C}
PMEM = 0x4000
ID_NEQ1 = 0x4E455131
F_CORE = 200e6
HERE = Path(__file__).resolve().parent


class Equalizer:
    """Thin wrapper around the overlay: registers, parameter load, one DMA frame."""

    def __init__(self, bitfile=HERE / "cnn_eq.bit", pynq=None):
        if pynq is None:
            import pynq
        self.pynq = pynq
        self.ol = pynq.Overlay(str(bitfile))
        self.eq, self.dma = self.ol.eq, self.ol.dma

    def reg(self, name):
        return int(self.eq.read(REG[name]))

    def check(self, shape_word, n_param):
        got = {k: self.reg(k) for k in ("ID", "SHAPE", "NPARAM")}
        exp = {"ID": ID_NEQ1, "SHAPE": int(shape_word), "NPARAM": int(n_param)}
        if got != exp:
            raise RuntimeError(f"wrong core: read {got}, expected {exp}")
        return got

    def load_params(self, words):
        for i, w in enumerate(words):
            self.eq.write(PMEM + 4 * i, int(w))

    def soft_reset(self):
        """Clear the datapath and the counters; the parameters stay loaded."""
        self.eq.write(REG["CTRL"], 1)
        self.eq.write(REG["CTRL"], 0)

    def counters(self):
        return {k: self.reg(k) for k in ("FRAMES", "BUSY_CYC", "IN_BEATS", "OUT_BEATS")}

    def run_frame(self, inbuf, outbuf):
        """One frame through the core: arm S2MM first, then send MM2S, then wait for both (polling)."""
        self.dma.recvchannel.transfer(outbuf)
        self.dma.sendchannel.transfer(inbuf)
        self.dma.sendchannel.wait()
        self.dma.recvchannel.wait()


def run_test(vectors=HERE / "board_vectors.npz", results=HERE / "board_results.json", pynq=None, repeats=3, log=print):
    v = np.load(vectors)
    x, u_gold, n_sym, crop = v["x"], v["u_gold"], int(v["n_sym"]), int(v["crop"])
    n_fr = x.shape[0]
    bits_true = np.unpackbits(v["bits_true"], axis=1)[:, :n_sym].astype(bool)

    eq = Equalizer(pynq=pynq)
    pynq = eq.pynq
    ids = eq.check(v["shape_word"], len(v["params"]))
    log(f"core found: ID 0x{ids['ID']:08X}, SHAPE 0x{ids['SHAPE']:08X}, {ids['NPARAM']} parameters")
    eq.load_params(v["params"])
    eq.soft_reset()

    inb = [pynq.allocate(shape=(x.shape[1],), dtype=np.int8) for _ in range(n_fr)]
    outb = [pynq.allocate(shape=(n_sym,), dtype=np.int16) for _ in range(n_fr)]
    for i in range(n_fr):
        inb[i][:] = x[i]
        if hasattr(inb[i], "flush"):
            inb[i].flush()

    # pass 1: correctness, frame by frame, against the golden integer model
    mismatches, errors, bits = 0, 0, 0
    for i in range(n_fr):
        outb[i][:] = 0                       # stale data cannot pass for a result ...
        if hasattr(outb[i], "flush"):
            outb[i].flush()                  # ... and no dirty cache line can be written over the DMA's data later
        eq.run_frame(inb[i], outb[i])
        if hasattr(outb[i], "invalidate"):
            outb[i].invalidate()
        out = np.array(outb[i])
        mismatches += int(np.count_nonzero(out != u_gold[i]))
        dec = out > 0
        errors += int(np.count_nonzero(dec[crop:-crop] != bits_true[i, crop:-crop]))
        bits += n_sym - 2 * crop
    c1 = eq.counters()
    log(f"pass 1: {n_fr} frames, {mismatches} output mismatches vs golden, {errors} bit errors in {bits} bits")

    # pass 2: throughput, all frames back to back (repeated), with the core's own cycle counter
    walls, cores = [], []
    for _ in range(repeats):
        eq.soft_reset()
        t0 = time.perf_counter()
        for i in range(n_fr):
            eq.run_frame(inb[i], outb[i])
        walls.append(time.perf_counter() - t0)
        c = eq.counters()
        cores.append(c)
    c2 = cores[-1]
    sym = n_fr * n_sym
    wall = min(walls)
    res = {
        "pynq_version": getattr(pynq, "__version__", "unknown"),
        "core": {"ID": f"0x{ids['ID']:08X}", "SHAPE": f"0x{ids['SHAPE']:08X}", "NPARAM": ids["NPARAM"]},
        "frames": n_fr, "symbols_per_frame": n_sym,
        "bit_exact": mismatches == 0, "output_mismatches": mismatches,
        "bit_errors": errors, "bits_counted": bits, "ber": errors / bits,
        "golden_bit_errors": int(v["golden_errors"]), "golden_bits": int(v["golden_bits"]),
        "counters_pass1": c1, "counters_pass2": c2,
        "counters_ok": c2["FRAMES"] == n_fr and c2["IN_BEATS"] == x.size and c2["OUT_BEATS"] == sym,
        "wall_s_per_pass": walls,
        "throughput_msym_s_wall": sym / wall / 1e6,
        "core_busy_s": c2["BUSY_CYC"] / F_CORE,
        "throughput_msym_s_core": sym / (c2["BUSY_CYC"] / F_CORE) / 1e6 if c2["BUSY_CYC"] else None,
        "samples_per_core_cycle": c2["IN_BEATS"] / c2["BUSY_CYC"] if c2["BUSY_CYC"] else None,
    }
    Path(results).write_text(json.dumps(res, indent=2))
    log(f"pass 2: {sym / 1e6:.1f} M symbols in {wall * 1e3:.1f} ms -> {res['throughput_msym_s_wall']:.1f} MSym/s "
        f"(wall clock); core busy {res['core_busy_s'] * 1e3:.1f} ms -> {res['throughput_msym_s_core'] or 0:.1f} MSym/s")
    verdict = "PASS" if res["bit_exact"] and res["counters_ok"] and errors == res["golden_bit_errors"] else "CHECK"
    log(f"{verdict}: bit-exact {res['bit_exact']}, BER {res['ber']:.2e} (golden {res['golden_bit_errors']} errors), "
        f"counters {'ok' if res['counters_ok'] else 'unexpected'}; results in {Path(results).name}")
    return res


if __name__ == "__main__":
    run_test()
