# Low-Complexity Neural Network Equalization for Optical Fibre Communication on FPGA

MLEE (EEE G513) course project, BITS Pilani. It reproduces and extends Ney et al., *"CNN-Based Equalization for
Communications: Achieving Gigabit Throughput with a Flexible FPGA Hardware Architecture"*
([arXiv:2405.02323](https://arxiv.org/abs/2405.02323)), which releases no code or data. Everything here is built from
the paper's description: an IM/DD link simulator, the CNN equalizer and strong baselines, quantization-aware training,
and a hand-written SystemVerilog streaming engine on a PYNQ-Z2 (XC7Z020).

## Results

Fresh 4M-symbol test set, 40 GBd PAM2, 31.5 km SSMF, 24 dB SNR; hardware on the XC7Z020-1, DSP builds, power from
gate-level switching activity at 200 MHz.

| Design | Bits | BER | Fmax (MHz) | LUT | FF | DSP | Dyn. power (W) |
|---|---|---|---|---|---|---|---|
| Paper's CNN (V_p 8, L 3, K 9, C 5), MSE | 8 | 4.96e-4 | 187.9 | 7,056 | 11,543 | 42 | 0.302 |
| Ours: CNN (V_p 4, L 4, K 9, C 3), cross-entropy | 6 | 2.18e-5 | 207.2 | 3,957 | 6,393 | 45 | 0.259 |
| **Ours: CNN + 2 decision-feedback taps (deployed)** | 8 | **5.0e-7** | **202.4** | 5,430 | 8,919 | 43 | 0.318 |

- 16x lower BER than the paper's CNN at a similar multiplication count (2.7e-5 vs 4.4e-4, floating point).
- About 1000x lower BER at the same 8 bits with decision feedback (2 errors in 3,997,440 bits).
- The deployed core closes 200 MHz in the full PYNQ-Z2 system (PS7 + AXI DMA at 100 MHz, core at 200 MHz).
- All six routed builds are bit-exact against the integer golden model in gate-level simulation.

The full write-up is [report/MLEE_Report.pdf](report/MLEE_Report.pdf); the poster is
[poster/MLEE_Poster.pdf](poster/MLEE_Poster.pdf).

## Repository layout

```
equalizer/                 simulation, learning and hardware
  eqsim/                   Python package: channels, equalizers, training, DFE, quantization, integer golden model
  scripts/                 experiments (Proakis-B, IM/DD search, DFE stress test, quantization), RTL export,
                           board vectors, artefact freezing
  tests/                   pytest suite (incl. a simulated-PYNQ test of the board driver)
  results/                 experiment outputs (JSON, logs, figures)
  checkpoints/             frozen, read-only artefacts with SHA-256 manifests:
                           fp32_v1 (models + datasets), quant_v1, hw_v1 (CNN, r7b), hw_v2 (CNN + DFE, r8c, overlay)
  rtl/src/                 SystemVerilog engine: conv1d_stream, add_tree, dfe_stream, cnn_eq_core, cnn_eq_top
  rtl/gen/                 per-model packages, parameter images and test vectors (from scripts/export_rtl.py)
  rtl/sim/, rtl/syn/       xsim testbenches; out-of-context implementation scripts
  rtl/bd/                  PYNQ-Z2 block design (build_bd.tcl) and the IP Integrator wrapper
  rtl/power/               gate-level SAIF power flow
  rtl/history/             every RTL revision r2-r8c as a full snapshot
  board/                   PYNQ-Z2 driver (cnn_eq_pynq.py) and notebook for the on-board run
report/                    the project report (docx + pdf)
poster/                    A0 poster: LaTeX source on the course template, its figures (PDF) and the PDF
papers/                    the replicated paper and the cited demonstrator paper (PDF)
Project submission templates/   course templates
```

## Setup

Python 3.14 with numpy, scipy, matplotlib, pytest and torch (CPU). Hardware: AMD Vivado / xsim 2025.2 (XC7Z020 is covered by the free edition). Run the Python code from
`equalizer/` with `PYTHONPATH` set to that folder.

```bash
python -m pytest -q
```

## Reproducing

| Step | Command (from `equalizer/` unless noted) |
|---|---|
| Proakis-B reproduction | `python scripts/run_proakis.py --iters 10000 --seeds 3`; `python scripts/run_proakis_seeds.py --seeds 10` |
| IM/DD topology and loss search | `python scripts/run_imdd_dse.py --stage all`, then `--stage confirm --seeds 3` |
| Decision feedback | `python scripts/run_dfe_stress.py`; `python scripts/run_quant_dfe.py` |
| Quantization | `python scripts/run_quant.py --bits 8 6 5 4 3` |
| RTL export | `python scripts/export_rtl.py --model results/quant/<model>/integer_model.pkl --name <model>` |
| RTL simulation | `rtl/sim/run_sim.ps1 -Model <model> -Stall 30 -UseDsp 1`; `rtl/sim/run_unit.ps1` |
| Implementation | `vivado -mode batch -source rtl/syn/impl_ooc_opt.tcl -tclargs <model> 5.0 <dsp> ...` |
| PYNQ-Z2 system | `vivado -mode batch -source rtl/bd/build_bd.tcl -tclargs <model> 200 1 <tag> 100` |
| Power | `rtl/power/run_power.ps1 -Model <model>_short -OutDir <build>` |
| Poster (in `poster/`) | `pdflatex MLEE_Poster.tex` (twice) or `tectonic MLEE_Poster.tex` |

Git tags `v1.0-cnn-200mhz` and `v2.0-cnn-dfe-200mhz` mark the two hardware versions.

## On-board run (PYNQ-Z2)

1. Build the package: `python scripts/make_board_vectors.py` (from `equalizer/`). It writes `board/board_vectors.npz`
   (20 frames x 200,000 symbols of the fresh test set, golden outputs, true bits, the 336 parameter words) and copies
   the overlay `cnn_eq.bit` / `cnn_eq.hwh` from `checkpoints/hw_v2` into `board/`.
2. Copy `cnn_eq.bit`, `cnn_eq.hwh`, `board_vectors.npz`, `cnn_eq_pynq.py` and `cnn_eq_pynq.ipynb` into one folder on
   the board (Jupyter upload) and run the notebook, or `sudo python3 cnn_eq_pynq.py` in a terminal.
3. A good run reports the core ID `0x4E455131`, 0 output mismatches against the golden model, 2 bit errors in
   3,997,440 bits, exact frame and beat counters, and a core throughput near 97.5 MSym/s. Results are written to
   `board_results.json`.
