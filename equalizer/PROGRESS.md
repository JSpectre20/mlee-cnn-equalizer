# PROGRESS: Low-Complexity Neural Network Equalization for Optical Fibre Communication on FPGA

This is the single source of truth for project state. Every milestone appends to the log at the bottom, and the sections above it are kept current. If a chat context is lost, reading this file (plus `../MLEE_paper_shortlist_and_ideas.md` for the research history) must be enough to continue.

---

## 0. Resume here (state as of 2026-10-25, early morning)
- **Done:**
  - simulator + reproduction (Proakis-B and IM/DD);
  - the 135-config DSE with MSE vs CE;
  - fresh-test confirmation;
  - frozen FP32 checkpoints;
  - QAT + integer golden model;
  - SystemVerilog engine + bit-exact full-model testbench (all 5 models PASS, LUT and DSP multipliers) + conv1d_stream unit testbench (16 configurations PASS);
  - Vivado P&R rounds 1-3 on XC7Z020 (best so far 182.3 MHz, ours_bce_w6 LUT, round 2).
- **Running at the time of writing:** nothing. Agreed order DFE -> paper model -> power is complete. Final engine RTL r8c; deployed design ours_bce_dfe_w8 (tag `v2.0-cnn-dfe-200mhz`, `checkpoints/hw_v2`). Next: PYNQ driver notebook + on-board BER/throughput run (needs the user at the board), then report and poster.
- **Backups (2026-10-25):** `checkpoints/fp32_v1` (FP32 models + datasets), `checkpoints/quant_v1` (results/quant + rtl/gen, 92 files), `checkpoints/hw_v1` (r7b RTL, sim/syn/bd scripts, overlay .bit/.hwh, final reports, 31 files); all read-only with SHA-256 MANIFEST.json, made by `scripts/freeze_checkpoints.py` / `scripts/freeze_artifacts.py` (refuse to overwrite a tag). Full source + results archive: `../backups/equalizer_src_2026-10-25_1224.zip` (362 files, excludes datasets / Vivado projects / sim work dirs). Version control: the whole `Project/` folder is a git repository, pushed to the **private** GitHub repo https://github.com/JSpectre20/mlee-cnn-equalizer (branch `main`, GitHub account JSpectre20, `gh` CLI at `C:\Program Files\GitHub CLI\gh.exe`, logged in). Ignored (see `../.gitignore`): Vivado projects `rtl/bd/proj_*`, `*.dcp`, sim work dirs, Vivado logs, datasets written under `results/` (the reported ones are frozen in `checkpoints/fp32_v1`), `backups/`. Commit and push at every milestone, and record the commit id in the log below.
- **Next:**
  1. Record round-4 P&R results (§5.6). Any config within ~0.5 ns of 200 MHz gets one pass with stronger Vivado directives (opt Explore, place ExtraTimingOpt, phys_opt AggressiveExplore post-place and post-route, route AggressiveExplore) as an optional impl_ooc.tcl argument; otherwise lock in the best passing clock. 200 MHz is the paper's clock (on an UltraScale+ VU13P), not a requirement; a PYNQ DMA design typically runs 100-150 MHz.
  2. ~~Freeze the quantized models into `checkpoints/quant_v1`~~ (done 2026-10-25).
  3. Block design (Zynq PS + AXI DMA + engine) for the PYNQ board, then a PYNQ driver notebook and on-board BER/throughput.
  4. Improvements I1 (KAN-LUT) and I2 (ADC co-design).
  5. Audio-loopback real data.
  6. Report and poster.

## 1. Project at a glance
- **Course:** MLEE (EEE G513), BITS Pilani, Dr. Ritesh Vyas.
  - Team of at most 3; no paper may be reused by another group.
  - Deliverables: report (docx template), A3 colour poster (LaTeX template), running code/prototype. The report must state each member's role.
  - Templates are in `../Project submission templates/Project submission templates/`. Course handout: `../Project submission templates/handout_mlee.pdf`.
  - Title form was due 20 Oct 2026 (submitted). **Final submission 20 Nov 2026 (firm).**
- **Submitted title:** "Low-Complexity Neural Network Equalization for Optical Fibre Communication on FPGA".
- **Base paper:** Ney, Füllner, Lauinger, Schmalen, Randel, Wehn, *"CNN-Based Equalization for Communications: Achieving Gigabit Throughput with a Flexible FPGA Hardware Architecture"*, arXiv:2405.02323 (PDF + extracted text in `../papers/`). No public code or data; the fiber data are their lab captures.
- **Paper facts used:**
  - 40 GBd PAM2 IM/DD, 31.5 km SSMF, 40 GHz PD, N_os = 2.
  - CNN template with L layers, kernel K, C channels, V_p symbols/pass; selected L=3, K=9, C=5, V_p=8.
  - MSE loss + nearest-symbol decision.
  - Learned bit widths end at about 13-bit weights / 10-bit activations.
  - Vitis HLS + Vivado 2022.2. High-throughput build on XCVU13P: 64 instances, 200 MHz, 9,648 DSP (78.5%), 68% LUT, 79% BRAM (BRAM mainly for stream split/merge). Low-power build on XC7S25: DOP 1–225, 4–110 Mbit/s, 0.1–0.2 W (Vivado estimates).
  - Proakis-B channel h = [0.407, 0.815, 0.407] at 20 dB: CNN 8.4e-3 vs FIR 9.6e-3.
- **Why this paper was chosen:** see the shortlist history in §9. The user wanted something simpler than idea A, with no ready-made code (so the project isn't trivial), and a genuine improvement.
- **Plan:** reproduce (simulator + CNN/FIR/Volterra + quantization + FPGA), then improve (roadmap in §10).

## 2. Environment
- Python venv: `D:\venvs\mlee-eq` (Python 3.14, torch 2.14.1+cpu, numpy 2.5, scipy 1.18, matplotlib 3.11, pytest). Pip cache on `D:\pip-cache`. pypdf is installed in the *system* Python user site (for reading papers).
- Run scripts from `equalizer/` with `PYTHONPATH` set to that folder. Example: `$env:PYTHONPATH='...\equalizer'; D:\venvs\mlee-eq\Scripts\python.exe scripts\<x>.py`.
- Machine: 6 physical cores / 12 threads, 8 GB RAM, GTX 1650 4 GB (unused; the CPU torch build is enough for these tiny models), C: about 18 GB free, D: about 880 GB free.
  - Sweeps use 6 worker processes, 1 torch thread each.
  - Vivado peaks at about 2.1 GB RAM per run, so run them sequentially.
- **Vivado/Vitis 2025.2** at `D:\AMD\2025.2` (free ML Standard edition; XC7Z020 is covered). xsim via `rtl/sim/run_sim.ps1`; OOC implementation via `rtl/syn/impl_ooc.tcl`.
- **Hardware the user has:**
  - a **PYNQ board** (assumed PYNQ-Z2, XC7Z020-1CLG400; *exact model and PYNQ image version not confirmed*);
  - possibly a Zynq UltraScale+ board via the professor (unconfirmed);
  - **Cadence** (exact tools/PDK/licence count not confirmed);
  - no Vivado Enterprise licence, hence **no RFSoC**.
  - The old Zybo Z7-10 is retired: don't plan around it.
- The app's keep-awake hold ends about 5 min after the session goes idle, so long runs need the laptop plugged in and the lid open.

## 3. Code map (`equalizer/`)
| Path | What |
|---|---|
| `eqsim/pulses.py` | RC / RRC filters |
| `eqsim/channels.py` | `ProakisBChannel` (paper Sec. 2.2), `IMDDChannel` (physics model of Sec. 2.1) |
| `eqsim/equalizers.py` | `FIREqualizer`, `VolterraEqualizer` (unique-term kernels), `NeyCNN` (Fig. 1 template; `macs_per_symbol` exact, `macs_paper_formula`), LS (chunked normal equations) and logistic (LBFGS + L2) fits |
| `eqsim/detectors.py` | Viterbi MLSE reference for known linear ISI |
| `eqsim/metrics.py` | PAM decisions, Gray BER, Wilson CI |
| `eqsim/train.py` | Adam training on fresh or fixed data (`loss_type` = `mse` or `bce`), BER evaluation |
| `eqsim/data.py` | Fixed cached datasets (independent 200k-symbol chunks), `DatasetChannel`, dataset BER eval |
| `eqsim/quant.py` | QAT (BN folding, LSQ fake-quant, round-half-up), `export_integer()` → `IntegerModel` (W, bias, per-channel M/S, out_scale), integer golden model `forward_int()` = exact RTL arithmetic, `integer_ber()` |
| `eqsim/dfe.py` | Decision feedback: strided FFE windows, closed-form FFE+DFE fit (`fit_ffe_dfe`), sequential own-decision DFE (`dfe_decide`, `ber_ffe_dfe`), `CNNDFE` (NeyCNN + n_fb linear feedback taps on its output, teacher-forced BCE training `train_cnn_dfe`, `ber_cnn_dfe`) |
| `scripts/run_proakis.py` | Proakis-B reproduction: FIR/Volterra MSE+CE, CNN MSE+BCE, MLSE |
| `scripts/run_proakis_seeds.py` | 10-seed CNN variance study (parallel) |
| `scripts/run_imdd_sanity.py` | Fading null, eyes, FIR floor |
| `scripts/run_imdd_dse.py` | 135-config DSE; stages data / baselines / screen / refine / confirm (resumable JSONL) |
| `scripts/plot_imdd_dse.py` | DSE plot + `summary.json` |
| `scripts/freeze_checkpoints.py` | Freezes FP32 models into read-only `checkpoints/<tag>/` with a SHA-256 manifest (refuses to overwrite) |
| `scripts/run_quant.py` | Bit-width sweep (PTQ + QAT) of frozen FP32 models, integer-model BER on the fresh test set → `results/quant/` |
| `scripts/export_rtl.py` | IntegerModel → `rtl/gen/<model>/` (cnn_eq_pkg.sv, params.mem, test vectors, tb_cfg.svh, meta.json); checks worst-case accumulator width |
| `scripts/quick_dfe_mlse.py`, `scripts/quick_dfe_confirm.py` | First FFE+DFE / FFE+Viterbi evidence (results/quick_dfe_mlse) |
| `scripts/run_dfe_stress.py` | I5 stress test: SNR 14-24 dB at 31.5 km and 20/40/50 km at 20 dB; FFE57/121, FFE25/57+DFE2, CNN and CNN+DFE2 (vp4 L4 K9 C3, BCE, 3 seeds) |
| `scripts/freeze_artifacts.py` | Freeze any files/dirs into read-only `checkpoints/<tag>/` with a SHA-256 manifest |
| `tests/test_basics.py` | 8 tests (pulses, alignment, fading null, MLSE, logistic fit, shapes/MACs) |
| `tests/test_quant.py` | 3 tests (BN-fold exactness, integer vs fake-quant agreement, integer conv semantics vs torch) |
| `checkpoints/fp32_v1/` | **Frozen FP32 models + datasets (read-only, MANIFEST.json with SHA-256). Never modify.** |
| `results/` | All generated figures/JSON/logs (not hand-edited) |
| `rtl/README.md` | RTL flow and architecture summary |
| `rtl/WEIGHT_FORMAT.md` | Contract: arithmetic, parameter-memory layout, AXI-Lite register map, stream formats |
| `rtl/src/sync_fifo.sv` | FWFT FIFO |
| `rtl/src/conv1d_stream.sv` | Streaming Conv1D layer (see §5.5) |
| `rtl/src/add_tree.sv` | Registered adder tree (widths grow per level, capped at ACC_W), used per lane by conv1d_stream |
| `rtl/history/` | Full RTL snapshots r2, r4 (single files), r5, r6, r7, r7b (directories) + `CHANGES.md` (every change itemised, P&R results per revision) |
| `rtl/bd/cnn_eq_axi.v`, `rtl/bd/build_bd.tcl` | Verilog wrapper for IP Integrator; script that builds and implements the PYNQ-Z2 system (PS7 + AXI DMA + stream clock/width converters + equalizer), writes reports and the PYNQ overlay (`.bit` + `.hwh`). Args: `<model> [fclk 200] [use_dsp 1] [tag] [dma_mhz 100]` |
| `rtl/syn/impl_ooc_opt.tcl` | OOC P&R with timing directives; `conv_src` may be a snapshot directory |
| `rtl/src/cnn_eq_core.sv` | Layer chain + symbol serializer (int16-saturated z); parameter `USE_DSP` |
| `rtl/src/cnn_eq_top.sv` | AXI-Lite (params + control/counters) + AXI-Stream in (8-bit samples) / out (16-bit symbols); parameter `USE_DSP` |
| `rtl/gen/<model>/` | Generated per model: `paper_mse_w8`, `ours_bce_w6`, `ours_bce_w8`, plus `*_short` (8 × 64-symbol frames) test sets |
| `rtl/sim/tb_cnn_eq.sv`, `rtl/sim/run_sim.ps1` | Self-checking xsim TB (AXI-Lite param load, ID/SHAPE check, random stalls via `+stallN`, bit-exact compare, TLAST and frame-counter checks, throughput, state dump on timeout) |
| `rtl/sim/tb_conv1d_unit.sv`, `rtl/sim/run_unit.ps1` | Unit TB for one conv1d_stream layer vs a direct reference convolution: 16 instances (8 shapes incl. K=1, K=15, STRIDE=3, odd widths, hidden + last layer, each with LUT and DSP multipliers), 80 random frames each (length 1..120, incl. lengths shorter than PAD and not multiples of STRIDE), random input gaps and output back-pressure. Goes beyond the stream contract on purpose (robustness of the frame logic). `run_sim.ps1 -UseDsp 1` simulates the DSP multiplier path (via a generated `tb_dsp.svh` in the run dir) |
| `rtl/syn/impl_ooc.tcl` | Vivado OOC synth + P&R + reports. Args: `<model> <period_ns> [use_dsp] [part]` |

All 11 unit tests pass (8 basics + 3 quant).

## 4. Modeling choices and deviations from the paper
- **Proakis-B:** RC β = 0.25 (not given in the paper), per-sample SNR at N_os = 2, symbol-spaced h, BPSK/PAM2.
- **IM/DD simulator:** 40 GBd PAM2, RRC β = 0.2, simulation at 8 samples/symbol, zero-chirp push-pull MZM at quadrature (field = cos(π/4 − π/4·m·v), m = 0.8), CD all-pass H(ω) = exp(jβ₂Lω²/2) for 31.5 km SSMF with D = 16 ps/nm/km at 1550 nm, square-law PD with a 4th-order Bessel 40 GHz response, in-band thermal noise at **24 dB electrical SNR**, resample to N_os = 2, AC coupling + unit-std normalization, cross-correlation alignment, 64 guard symbols per chunk, optional ADC (`adc_bits`, ±3σ clip, mid-rise; not used yet).
  - The first power-fading null at **11.1 GHz** (second at 19.3 GHz) matches theory (unit test + `results/imdd_sanity/power_fading.png`).
- **FIR/Volterra:** fitted in closed form (LS) or by logistic regression (LBFGS from LS, L2 = 1e-4), not by Adam, so they are the strongest possible baselines.
  - Volterra keeps unique symmetric terms; its MAC count = M1 + 2·P2 + 3·P3.
- **Data/seeds:**
  - Proakis-B: LS fit data seed 7; test seed 12345 (10⁶ symbols); CNN trains on fresh data every batch.
  - IM/DD: fixed datasets (simulation costs about 0.4 s per batch, too slow on the fly) — train 2M symbols (seed 1), test 2M (seed 2), **fresh test 4M (seed 3)** for selection-bias-free confirmation. All are in `checkpoints/fp32_v1/imdd_data/`.
- **CNN training:** Adam lr 1e-3, 10k iterations, batch 32 × 512 symbols (1024 for V_p = 16), crop 32 symbols per edge. BCE treats the output as a logit, so the test-time sign decision is unchanged.
  - Weight init is seeded with `torch.manual_seed(seed)` (the very first Proakis-B CNN runs lacked this).
- **MAC count:** exact per output symbol. The paper's printed MAC_sym formula equals exact / N_os, i.e. per input sample.
- **Paper's 40 GBd budget:** DSP / (T_req / f_clk) · 1.2 = 12288 / 200 · 1.2 = 73.7 in the paper's units, i.e. **147 exact MAC/sym**.

## 5. Results
### 5.1 Proakis-B (20 dB), `results/proakis/`
- **FIR (LS)**: 3 taps 5.67e-2, 5 → 3.30e-2, 9 → 1.65e-2, 17 → 1.17e-2, 25 → 1.03e-2, 41 → 9.07e-3, **57 → 8.96e-3** (paper's FIR at similar complexity: 9.6e-3), 89/121 → about 8.96e-3. The CE fit is about 2% better.
- **Volterra, MSE fit vs CE fit (MAC):**
  - (9,3,3) at 51 MAC: 2.54e-2 → 8.7e-3
  - (13,5,3) at 73 MAC: 2.16e-2 → 5.7e-3
  - (15,5,5) at 150 MAC: 2.16e-2 → 3.2e-3
  - (25,9,5) at 220 MAC: 1.94e-2 → 2.6e-3
  - (25,9,9) at 610 MAC: 1.02e-2 → 8.3e-4
  - (35,15,9) at 770 MAC: 9.9e-3 → 8.5e-4

  The MSE-fit Volterra is *worse than FIR* (the cubic terms lower MSE but raise BER).
- **Paper's CNN, 10 seeds (`seeds.json`):**
  - MSE: 6.71e-3 … 1.42e-2, median 1.13e-2, **expected best-of-3 8.5e-3 (paper 8.4e-3)**.
  - BCE: 4.61e-3 … 9.43e-3 plus one diverged run at 3.81e-2, median 6.7e-3, expected best-of-3 5.2e-3.
  - **BCE < MSE, Mann-Whitney one-sided p = 0.011.**
- **MLSE (4-state Viterbi on symbol-spaced samples):** 0 errors in 9.9e5 symbols at 20 dB; 9.8e-2 at 6 dB, 2.6e-2 at 9 dB, 1.6e-3 at 12 dB. So it beats the CNN with about 8 dB less SNR.

### 5.2 IM/DD (24 dB). Sanity, then DSE, then fresh-test confirmation
- **FIR floor (LS)** at SNR 10/14/18/22/26/30/40 dB:
  - FIR-17: 5.2e-2 … 2.1e-2
  - FIR-57: 2.2e-2 → 6.7e-4
  - FIR-121: 2.1e-2 → **4.1e-4 at 40 dB**

  That's a nonlinear floor, as in the paper (which reports a FIR floor near 1e-4 with up to 1017 taps).
- **DSE** (`results/imdd_dse/`, `dse.png`, `summary.json`): 135 configs × {MSE, BCE}, 1 seed, then Pareto configs with 3 seeds.
  - BCE won in 81/121 configs (screen).
  - In-budget Pareto (best of 3): MSE best 1.25e-4 at 135 MAC; BCE best 2.9e-5 at 121.5 MAC.
  - CNNs at 400–2400 MAC reach 0 errors in 2M bits.
  - V_p = 16 configs train badly (BER 0.1–0.25).
- **Volterra on fiber (2M test), MSE → CE:**
  - (25,9,9) at 610 MAC: 5.7e-3 → 2.7e-3
  - (35,15,9) at 770 MAC: 1.6e-3 → 5.4e-4
  - (55,25,9) at 1200 MAC: 1.6e-4 → 5.5e-5
  - Best in budget, (13,5,3) at 73 MAC: about 3.9e-2
- **Fresh 4M-symbol test, best / median of 3 seeds:**

| Model | MAC/sym | MSE | CE |
|---|---|---|---|
| FIR 57 / 121 | 57 / 121 | 8.3e-4 / 4.5e-4 | 7.8e-4 / 3.8e-4 |
| Paper's CNN (vp8, L3, K9, C5) | 112.5 | 4.4e-4 / 5.7e-4 | 4.5e-4 / 5.1e-4 |
| (vp4, L3, K15, C3) | 135 | 1.3e-4 / 1.9e-4 | 1.2e-4 / 1.7e-4 |
| **(vp4, L4, K9, C3)** | 121.5 | 9.4e-4 / 1.3e-3 | **2.7e-5 / 4.2e-5** |

- **Headline:** our CE-trained (vp4, L4, K9, C3) gives **about 16× lower BER than the paper's CNN at the same cost** (2.7e-5 vs 4.4e-4).
  - The 4-layer net trains badly with MSE but best with CE (about 30× apart at the median).
  - The paper's central claim (CNN about 3.5–4× better than FIR in budget) reproduces, but with a different topology than the paper's pick.
  - Seed variance is large (2.7e-5 to 2.6e-4 for the same config).
  - Fresh-test numbers are selection-bias-free. The quantization step later used the best seed per config on that same fresh set (a minor bias; note it in the report).

### 5.3 Paper issues found
1. The MAC formula undercounts the CNN by N_os = 2.
2. MSE training handicaps nonlinear and deeper models (Volterra worse than FIR; the 4-layer CNN fails).
3. No MLSE / optimal-detector baseline (MLSE is error-free at their Proakis-B 20 dB point).
4. Large seed variance; best-of-3 selection matters.
5. The selected topology only ties FIR on our simulated link (plausibly a channel difference, not an error).
6. Power is a Vivado estimate only; Proakis-B is a weak showcase (linear, known channel).
7. **No decision-feedback baseline, and on our simulated link a tiny FFE+DFE beats every CNN.** `scripts/quick_dfe_mlse.py` / `quick_dfe_confirm.py` → `results/quick_dfe_mlse/{results,confirm}.json`. Closed-form LS FFE at N_os = 2 plus B feedback taps on the equalizer's *own* decisions (error propagation included), fitted on 600k train symbols, tested on the full 4M fresh test set (24 dB):
   - FFE17: 2.2e-2 → +DFE2 **6.0e-5** (19 MAC)
   - FFE25: 8.5e-3 → +DFE2 **5.0e-7** (2 errors in 4M; 27 MAC)
   - FFE33: 4.0e-3 → +DFE2 7.5e-7 (35 MAC)
   - FFE41 / FFE57 +DFE2: **0 errors in 4M** (BER < 7.5e-7 at 95%)
   - DFE1 helps little (e.g. FFE57 8.3e-4 → 5.4e-4), so two feedback taps matter.
   - Sanity: genie feedback (true symbols) FFE17+DFE2 1.5e-5, FFE57 0; random feedback collapses to 0.22-0.28, so the gain really comes from feedback.
   - Short Viterbi (partial-response target + 2/4-state VA, 600k test): FFE57+VA4(1,0.5,0.25) 1.0e-5; FFE121+VA4 0 errors; FFE121+VA2(1,0.25) 1.1e-4. Works, but costs more than a 2-tap DFE.
   - For comparison: the paper's CNN 4.4e-4 at 112.5 MAC; our best CE CNN 2.7e-5 at 121.5 MAC.
   - Physics: the CD power-fading null at 11.1 GHz sits inside the band; feed-forward equalizers can't fill a spectral null, decision feedback can (standard result).
   - Caveats: one simulated link at 24 dB with an ideal MZM and no laser chirp; real lab data (the paper's) may have impairments that feedback can't cancel. A DFE's recursion also limits parallelism: the paper's 40 GBd build runs 200 symbols per clock, which needs a look-ahead/unrolled parallel DFE.
   - **Full stress test** (`scripts/run_dfe_stress.py`, `results/dfe_stress/`; 1M train / 2M test symbols per condition; CNN = vp4 L4 K9 C3 BCE, best (median) of 3 seeds; all DFE with own decisions):

| Condition | FFE121 | FFE57+DFE2 | CNN | CNN+DFE2 |
|---|---|---|---|---|
| 20 km, 20 dB | 2.6e-4 | **0** | 1.8e-5 (5.1e-5) | 6.5e-6 (9.0e-6) |
| 31.5 km, 14 dB | 2.5e-3 | 2.0e-4 | 5.4e-4 (5.5e-4) | **1.3e-4** (1.6e-4) |
| 31.5 km, 16 dB | 1.5e-3 | **2.4e-5** | 2.3e-4 (2.4e-4) | 4.6e-5 (7.3e-5) |
| 31.5 km, 18 dB | 9.1e-4 | **1.0e-6** | 9.9e-5 (1.2e-4) | 1.7e-5 (2.0e-5) |
| 31.5 km, 20 dB | 6.6e-4 | **0** | 5.7e-5 (6.4e-5) | 1.2e-5 (1.4e-5) |
| 31.5 km, 22 dB | 5.2e-4 | **0** | 4.2e-5 (4.2e-5) | 8.0e-6 (9.0e-6) |
| 31.5 km, 24 dB | 4.5e-4 | **0** | 2.9e-5 (6.9e-5) | 3.5e-6 (6.3e-6) |
| 40 km, 20 dB | 1.7e-3 | 2.0e-3 | 1.5e-3 (1.9e-3) | **5.2e-4** (7.0e-4) |
| 50 km, 20 dB | 3.3e-3 | 5.7e-3 | 4.7e-3 (4.9e-3) | **3.1e-3** (3.2e-3) |

   - Findings: (1) CNN+DFE2 beats the CNN alone everywhere (1.5-8x). (2) At the paper's operating region (31.5 km, >= 16 dB) and at 20 km a 59-MAC FFE57+DFE2 beats every CNN. (3) The CNN wins where the channel is hard: 40 km (3.3x over the best linear option), 14 dB; at 40-50 km FFE+DFE suffers error propagation and is worse than FFE121 alone. (4) 50 km is beyond this complexity budget for every equalizer. Report framing: the best equalizer depends on the channel; CNN+DFE is the robust choice.

### 5.4 Quantization (`results/quant/`, `ber_vs_bits.png`)
- **Setup:** W = A = input bits. PTQ = calibration only. QAT = LSQ, Adam lr 2e-4, 4000 iterations from the frozen FP32 best seed (paper_mse = `vp8_L3_K9_C5_mse_s1`, paper_bce = `..._bce_s1`, ours_mse = `vp4_L4_K9_C3_mse_s2`, ours_bce = `..._bce_s2`). Integer-model BER on the fresh 4M test set.

| Model | FP32 | W8 | W6 | W5 | W4 | W3 |
|---|---|---|---|---|---|---|
| paper_mse (paper recipe) | 4.39e-4 | 4.96e-4 | 3.09e-3 | 1.69e-2 | 6.39e-2 | 1.80e-1 |
| paper_bce | 4.55e-4 | 3.45e-4 | 5.63e-4 | 1.96e-3 | 1.20e-2 | 7.43e-2 |
| ours_mse | 9.38e-4 | 8.57e-4 | 1.26e-3 | 3.77e-3 | 2.96e-2 | 1.67e-1 |
| **ours_bce** | 2.70e-5 | **1.13e-5** | **2.18e-5** | 1.72e-4 | 3.70e-3 | 9.10e-2 |

- PTQ alone is much worse at ≤6 bits (e.g. paper_mse W6 PTQ 2.25e-3, ours_bce W6 PTQ 5.5e-5); QAT is needed.
- Our CE model holds FP32 accuracy at 6 bits. The paper-recipe model needs 8 (consistent with the paper's ~13b/10b).
- **Ours W6 (2.2e-5) vs the paper's W8 (5.0e-4): about 23× lower BER with fewer bits.**
- Hardware targets: **paper_mse W8** (reproduction) and **ours_bce W6** (proposal), plus ours_bce W8.
- **Accumulators:**
  - measured on data: 17–19 bits at W8;
  - guaranteed worst case (used for ACC_W): paper_mse_w8 = 21, ours_bce_w6 = 16, ours_bce_w8 = 20.
- **Integer contract** (also `rtl/WEIGHT_FORMAT.md`):
  - input `x_q = clamp(round_half_up(rx/s_in))`, signed B_IN bits;
  - per-channel symmetric weights;
  - hidden `a' = clamp(((acc+bias)·M + 2^(S−1)) >>> S, 0, 2^B_A−1)`, with M u16 and S ≤ 40;
  - last `z = acc + bias`, decision = (z > 0);
  - BN folded first.
- The integer model matches fake-quant decisions above 99.9%. About 0.6% of logits differ by one requant LSB (float32 ties); the integer model is the RTL reference.
- Files per run: `results/quant/<name>_w<b>/{qat_model.pt, integer_model.pkl, metrics.json}`. **TODO:** freeze the chosen ones into `checkpoints/quant_v1/` (not done yet).
- **CNN+DFE2 quantization** (`scripts/run_quant_dfe.py`, source `results/dfe_stress/models/snr24_L31.5_cnndfe_s1.pt` (FP32 3.5e-6), QAT 4000 it, teacher-forced feedback; integer taps fb[v][k] = round(fb[k]/out_scale[v]); integer BER with own-decision feedback, frame start d = -1, fresh 4M set): **W6 2.8e-5** (9.5e-4 without feedback), **W7 3.5e-6**, **W8 5.0e-7** (2 errors in 4M; 2.1e-4 without feedback). Feedback needs a precise CNN: at 6 bits the gain is lost. **Chosen for hardware: ours_bce_dfe_w8** = same 8 bits as the paper's CNN, ~1000x lower BER (5.0e-7 vs 4.96e-4) and 44x below our W6 CNN (2.18e-5). Integer taps (W8): [[-1864, -3978], [-1835, -3916], [-1763, -3763], [-1905, -4065]].

### 5.5 RTL (hand-written SystemVerilog) and verification
- **Architecture (`conv1d_stream.sv`, per layer):**
  - K×IC sliding window with per-frame zero padding / flush identical to torch Conv1d(padding = K/2); `n_out = ceil(n_in/stride)`.
  - Jobs are held back one step so the frame's last job carries TLAST.
  - A job FIFO of depth 2; the engine issues **one output channel per cycle** into IC·K multipliers, then a registered adder tree, then bias.
  - Requant pipeline (now: multiply, round-add, coarse shift by S[5:3]·8, fine shift by S[2:0], registered clamp).
  - A collector assembles the OC results into an output FIFO (depth 16), with credit-based start so it never overflows.
  - The pipeline tag valid bits are reset.
- **Sizing:**
  - At 1 sample/clk every layer needs only 1 output channel per cycle, so the multipliers are: ours 9+27+27+27 = **90**, the paper's 9+45+45 = **99**.
  - Throughput is 1 sample/clk, i.e. f_clk / N_os symbols/s per instance.
- **Weights:** an AXI-Lite parameter memory `pmem` (write-only words at 0x4000 + 4i), stored in flip-flops. Shape is fixed per bitstream via the generated `cnn_eq_pkg`.
- **Registers:**
  - 0x0 ID "NEQ1"
  - 0x4 SHAPE
  - 0x8 NPARAM
  - 0xC CTRL (bit 0 = datapath soft reset)
  - 0x10 FRAMES
  - 0x14 BUSY_CYC
  - 0x18 IN_BEATS
  - 0x1C OUT_BEATS
- **Streams:**
  - in: 8-bit samples, TLAST at frame end; frame = n_sym·N_os samples with n_sym a multiple of V_p;
  - out: 16-bit saturated z per symbol, TLAST at frame end.
- **Verification:** xsim, bit-exact vs the integer golden model, TLAST and frame counter checked.
  - 3 models × 0/30/70% random stalls = 9/9 PASS.
  - Short frames (8 × 64 symbols) at 0/50% stalls PASS.
  - **Re-run after the requant pipeline change: 11/11 PASS.**
  - After rounds 3-4 (2-stage multipliers, registered credit, jobs-owed counter): all 5 models x stall 0/30 PASS (LUT), 3 models PASS with `-UseDsp 1`, unit TB 16/16 PASS. A deliberately broken copy (owed counter ignoring the stride phase) is caught by the unit TB (TLAST and value mismatches).
  - Throughput 0.981–0.983 samples/cycle unstalled (1024-symbol frames); 0.89 with 64-symbol frames (per-frame flush overhead).
  - r8 (decision feedback, `dfe_stream.sv`): ours_bce_dfe_w8 + _short x LUT/DSP x stall 0/30 = 8/8 PASS bit-exact; existing models still PASS; deliberately broken copies (no per-frame history reset; swapped tap order) are caught.
- **Bugs and gotchas:**
  1. Tag valid bits weren't reset; with 11 stages the X outlived the 10-cycle reset and deadlocked the paper's topology. Fixed.
  2. `until` is an SV keyword (renamed `to_next`).
  3. PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM, which xvlog rejects (use .NET `UTF8Encoding($false)`).
  4. xsim `.bat` wrappers split arguments at `=`, so the TB uses `+stallN` and reads .mem files from the run directory.
  5. xsim does not support seeding via `$urandom(seed)`; use `process::self().srandom(seed)`. The `.bat` '=' splitting also breaks `xelab -generic_top`, hence the generated `tb_dsp.svh`.
  6. Netlist (gate-level) simulation: wait for `glbl.GSR` to fall before releasing reset; xelab / xsim write their own `xelab.log` / `xsim.log`, so scripts must not tee into those names.

### 5.6 Vivado implementation, XC7Z020-1CLG400, OOC
- **First pass** (old requant pipeline, LUT multipliers, 200 MHz target; `rtl/syn/out_<model>_5.0ns/`). Timing not met:

| Model | LUT | (LUT as mem) | FF | DSP | BRAM | WNS | Fmax | Power total / dyn |
|---|---|---|---|---|---|---|---|---|
| paper_mse_w8 | 13,431 (25.3%) | 794 | 14,702 | 2 | 0 | −1.84 ns | 146 MHz | 0.310 / 0.205 W |
| ours_bce_w8 | 11,377 (21.4%) | 680 | 11,188 | 3 | 0 | −2.09 ns | 141 MHz | 0.308 / 0.202 W |
| **ours_bce_w6** | **8,176 (15.4%)** | 536 | **8,898** | 3 | 0 | −2.21 ns | 139 MHz | **0.263 / 0.159 W** |

  - Ours W6 uses about 39% fewer LUTs and FFs than the paper's CNN at about 23× lower BER.
  - Vivado put the conv multipliers into LUTs (the 2–3 DSPs are the requant multipliers).
  - Critical path: p_r → variable >>> S (up to 40) → clamp → collector, 9 logic levels.
- **Fix:** split the requant into coarse/fine shift + registered clamp stages (now done, 11/11 PASS). Added the `USE_DSP` parameter (attribute `use_dsp` on the product registers; synth `-generic USE_DSP=<0|1>`).
- **Round 2 (split requant shift + registered clamp), 5 ns target:** Fmax MHz (LUT mult / DSP mult): ours_bce_w6 182.3 / 174.0; ours_bce_w8 161.0 / 171.4; paper_mse_w8 156.9 / 169.2. Still short of 200 MHz. New critical paths: (a) control: 32-bit `created != n_out_total` compare in FLUSH -> `push` -> job-FIFO write enable (fanout 256-544 LUTRAM cells, since the job FIFO holds the whole packed window); (b) w8 LUT builds: single-cycle 9x8 LUT multiplier (6.4 ns, 8 logic levels).
- **Round 3 fixes (conv1d_stream.sv):** FLUSH uses a small registered `rem` jobs-remaining counter + `rem_nz` flag (computed at the s_last beat) instead of the 32-bit compare; multipliers are two register stages (LUT: a = a_hi*2^H + a_lo, two half-width products then one registered add; DSP: MREG + PREG); `credit_ok` is registered and one slot conservative (occupancy + in-flight grows by at most 1 per cycle). Pipeline is 1 cycle longer. Regression 10/10 bit-exact (5 models x stall 0/30); throughput unchanged at 0.981 samples/cycle (long frames), 0.88 (short). Testbench timeout dump now prints `rem` instead of `n_out_total`.
- **Round 3 results (5 ns target)** - Fmax / LUT / FF / DSP / power total (dyn):
  - ours_bce_w6 LUT: opt_design failed with an empty `[Synth 20-411]` error (probably transient; reports in the folder are still round 2's). DSP: 156.1 MHz / 3,950 / 5,312 / 136 / 0.209 W (0.104).
  - ours_bce_w8 LUT: 158.9 MHz / 12,847 / 13,530 / 3 / 0.390 W (0.283). DSP: 157.7 MHz / 4,580 / 6,686 / 136 / 0.266 W (0.161).
  - paper_mse_w8 LUT: 147.0 MHz / 14,717 / 17,258 / 2 / 0.379 W (0.272). DSP: 151.1 MHz / 5,574 / 9,622 / 149 / 0.341 W (0.235).
  - Worse than round 2: the new critical path was the round-3 `rem`/`rem_nz` computation itself (32-bit ceil-div/subtract at the s_last beat, chained after `job_now`, 14 logic levels). The fix moved the long arithmetic instead of removing it.
  - DSP builds use ~136 DSP instead of ~93: Vivado also packs the first adder-tree level into DSPs (layer 0: 9 + 5, 27-tap layers: 27 + 13/14). Fixable (e.g. `use_dsp = "no"` on the tree, or real DSP post-adder packing).
- **Round 4 fix:** jobs owed = ceil(n_in/STRIDE) - created is kept as a small running counter `rem` (width clog2(PAD+3)): +1 on an input beat with `phase == 0` (phase = n_in mod STRIDE), -1 per job created; FLUSH pushes while `rem != 0`, goes to FINAL when `rem == 0`. No wide arithmetic left on the push / job-FIFO write path. Snapshots of r2 and r4 and the full change list: `rtl/history/` (`CHANGES.md`).
- **Round 4 results (default flow, 5 ns), Fmax MHz LUT / DSP:** ours_bce_w6 199.2 / 198.7 (WNS -19 / -32 ps; worst path now the AXI-Lite pmem write decode -> pmem CE, 78% routing); ours_bce_w8 174.2 / (run died in opt_design, empty `[Synth 20-411]`); paper_mse_w8 169.9 / 184.1. w8 LUT builds are limited by the half-width LUT multiplier (5.9 ns, 7 levels).
- **Directive flow** (`rtl/syn/impl_ooc_opt.tcl`: opt Explore, place ExtraTimingOpt, phys_opt AggressiveExplore post-place and post-route, route AggressiveExplore, optional `-retiming`; outputs `out_<model>_5.0ns_dsp<d>_<tag>/`) on r4:
  - **ours_bce_w6 LUT: 200.3 MHz (WNS +0.008 ns), 200 MHz met.**
  - **ours_bce_w6 DSP: 201.4 MHz (WNS +0.071 ns), 200 MHz met.** Vivado exited while writing routed.dcp (reports complete, no dcp).
  - paper_mse_w8 DSP: 198.7 MHz (WNS -0.032 ns).
  - ours_bce_w8 DSP: Vivado died during post-route phys_opt (WNS -0.082 at that point); rerun queued.
  - Remaining runs (ours_bce_w8 DSP rerun, paper_mse_w8 DSP with retiming = tag `optrt`, ours_bce_w8 LUT, paper_mse_w8 LUT) running. _Results to be filled in here._
  - Vivado has died silently 4 times on this 8 GB machine (twice in opt_design, once writing routed.dcp, once in phys_opt); likely memory. Never run xsim or other heavy jobs alongside Vivado.
- **Decision (user, 2026-10-24):** if round 4 + directives had not reached 200 MHz, roll back to r2 (182 MHz) and apply the directives there. Not needed: r4 + directives meets 200 MHz for ours_bce_w6. Always record every RTL change in detail (`rtl/history/CHANGES.md`).
- **Optimisation passes (2026-10-25), ours_bce_w6, directive flow, 5 ns, all bit-exact (unit TB 16/16 + all 5 models, LUT and DSP, stall 0/30):**

| Rev | Change | LUT build: LUT / FF / MHz | DSP build: LUT / FF / DSP / MHz |
|---|---|---|---|
| r4 | baseline | 8,592 / 10,414 / 200.3 | 3,572 / 5,474 / 136 / 201.4 |
| r5 | no job FIFO; DW-bit datapath (unsigned activations); growing adder tree | 7,316 / 9,812 / 201.7 | 3,019 / 5,336 / 136 / 200.4 |
| r6 | last layer shares multipliers (FOLD 2); 1-stage LUT multipliers for products < 14 bits | 6,464 / 7,624 / 200.0 | 2,962 / 5,089 / 117 / 200.3 |
| r7b | 2 channels per DSP (pre-adder packing + borrow count); `add_tree` module | 6,580 / 7,620 / 200.0 | **3,957 / 6,393 / 45 / 207.2** |

  - Total: LUT build -23% LUT / -27% FF; DSP build -67% DSP (136 -> 45; fits an XC7Z010 with 80 DSP). Throughput 0.975-0.977 samples/cycle (was 0.981).
  - r7 (before the attribute fix) used 83 DSP: `use_dsp="yes"` on the pre-adder register put the pre-add in its own DSP. Details in `rtl/history/CHANGES.md`.
  - Decision: P&R only ours_bce_w6 in intermediate passes; paper_mse_w8 is measured once on the final engine (all models still simulated every pass). Only ours_bce_w6 must meet 200 MHz; the paper's model is compared at a common clock.
- **PYNQ-Z2 system (in context), ours_bce_w6 DSP build r7b:** two clocks (equalizer FCLK1 200 MHz, DMA/interconnect FCLK0 100 MHz, 32-bit DMA streams via axis clock + width converters). **Timing met: WNS +0.119 ns (200 MHz), +1.693 ns (100 MHz).** System 6,857 LUT / 10,726 FF / 45 DSP / 3 BRAM; equalizer 3,865 LUT / 6,306 FF / 45 DSP / 0.155 W; total 1.58 W (PS7 1.26 W). A single 200 MHz clock failed (WNS -0.948) only in the AXI DMA / interconnect IP. Overlay: `rtl/bd/proj_ours_bce_w6_200_dsp1_2clk/overlay/cnn_eq.{bit,hwh}`.
- **Power numbers are vectorless estimates**; re-measure with simulation activity (SAIF) on the final engine for the report.
- **Final-engine comparison** (OOC, directive flow, 5 ns target, XC7Z020-1; power = vectorless estimate; BER = integer model on the fresh 4M set). paper_mse_w8 and the ours_bce_dfe_w8 LUT build ran on r8b (identical to r8c for them; post-route phys_opt off for paper_mse_w8 because of a reproducible Vivado crash):

| Model | Bits | BER | Build | MHz | LUT | FF | DSP | Power total (dyn) |
|---|---|---|---|---|---|---|---|---|
| paper_mse_w8 | 8 | 4.96e-4 | DSP | 187.9 | 7,056 | 11,543 | 42 | 0.356 W (0.250) |
| paper_mse_w8 | 8 | 4.96e-4 | LUT | 196.3 | 10,907 | 14,840 | 2 | 0.358 W (0.252) |
| ours_bce_w6 (r7b) | 6 | 2.18e-5 | DSP | 207.2 | 3,957 | 6,393 | 45 | 0.262 W (0.158) |
| ours_bce_w6 (r7b) | 6 | 2.18e-5 | LUT | 200.0 | 6,580 | 7,620 | 3 | 0.245 W (0.141) |
| **ours_bce_dfe_w8 (r8c)** | 8 | **5.0e-7** | DSP | **202.4** | 5,430 | 8,919 | 43 | 0.326 W (0.220) |
| ours_bce_dfe_w8 (r8b) | 8 | 5.0e-7 | LUT | 195.8 | 10,331 | 12,383 | 3 | 0.366 W (0.259) |

  - vs the paper's CNN on the same engine: ours_bce_w6 = 23x lower BER with -44% LUT / -45% FF (DSP builds); ours_bce_dfe_w8 = ~1000x lower BER at the same 8 bits with -23% LUT / -23% FF and the same DSP count.
- **PYNQ-Z2 system with ours_bce_dfe_w8 (r8c, deployed):** core FCLK1 200 MHz **WNS +0.160 ns**, DMA FCLK0 100 MHz WNS +1.778; system 8,416 LUT / 13,148 FF / 43 DSP / 4 BRAM-equivalents (2 RAMB36 + 2 RAMB18); equalizer 5,421 LUT / 8,718 FF / 43 DSP / 0.213 W; system 1.64 W (PS7 1.26 W). r8 reached only 153 MHz (DFE input not registered), r8b 195.6 MHz OOC / zero slack in context (lane mux before the candidate adder), r8c fixes both (details in `rtl/history/CHANGES.md`).
- **Power with simulated switching activity (SAIF)** (`rtl/power/run_power.ps1`: post-route funcsim netlist simulated with tb_cnn_eq in NETLIST mode at 200 MHz on the `_short` vectors, no stalls, activity logged after the parameter load; `report_power` with the SAIF, 59-68% of nets annotated, the rest propagated; confidence **High**; reports `rtl/power/power_<out_dir>.rpt`). **Every routed netlist is also bit-exact in this gate-level simulation (512/512 outputs).**

| Model | Bits | BER | Build | Total | Dynamic | Dynamic vs paper |
|---|---|---|---|---|---|---|
| paper_mse_w8 | 8 | 4.96e-4 | DSP | 0.409 W | 0.302 W | - |
| paper_mse_w8 | 8 | 4.96e-4 | LUT | 0.495 W | 0.387 W | - |
| ours_bce_w6 | 6 | 2.18e-5 | DSP | 0.365 W | 0.259 W | -14% |
| ours_bce_w6 | 6 | 2.18e-5 | LUT | 0.349 W | 0.243 W | -37% |
| ours_bce_dfe_w8 (r8c, deployed) | 8 | 5.0e-7 | DSP | 0.426 W | 0.318 W | +5% |
| ours_bce_dfe_w8 (r8b) | 8 | 5.0e-7 | LUT | 0.499 W | 0.390 W | +1% |

  - The vectorless estimates were optimistic (e.g. deployed core 0.220 W -> 0.318 W dynamic); use these SAIF numbers in the report.
  - Throughput per instance: 200 MHz x ~0.975 samples/cycle / 2 samples/symbol = ~97.5 MBd = ~97.5 Mb/s (PAM2), so dynamic energy per bit = ~2.5 nJ/bit (ours_bce_w6 LUT), ~3.1 nJ/bit (paper_mse_w8 DSP), ~3.3 nJ/bit (ours_bce_dfe_w8 DSP). All builds evaluated at the same 200 MHz clock (paper_mse_w8 itself closes at 187.9 / 196.3 MHz).
  - Testbench gotcha: in netlist simulation all flip-flops ignore inputs during glbl.GSR (first 100 ns); the TB now waits for GSR before releasing reset (NETLIST mode only). Full-length vectors are too slow at gate level (DSP48E1 models); the `_short` sets are used.
- **Why BRAM = 0 (by design):**
  1. The parameters are tiny (328 words ours, 668 the paper's), and each cycle a layer needs **all IC·K weights of one output channel at once** (27–45 values in parallel). A BRAM has only 2 read ports, so it would need heavy banking. Flip-flops give full parallel access for about 2–4k bits.
  2. The FIFOs are shallow (job FIFO depth 2, output FIFO depth 16), so Vivado maps them to LUTRAM ("LUT as memory", 536–794).
  3. The window shift registers must be flip-flops anyway.
  4. The paper's 79% BRAM came mainly from splitting/merging the input stream across 64 parallel instances in its high-throughput build. A single instance doesn't need that.
  - Possible ablation: put pmem in LUTRAM/BRAM with a weight-row read port.

## 6. Decisions and working agreements
- **RTL, not HLS** (user decision, 2026-10-24), in the style of the user's U-Net project (`../../ps-1/U_net/zybo_z7_10`: a generic SystemVerilog engine + `convert_h5_to_mem.py` → weight blob + `WEIGHT_FORMAT.md`, per-channel requant `(acc+bias)*M + rnd >>> S`, `golden_model.py`, xsim TBs):
  - hand-written SystemVerilog;
  - a Python converter emitting a documented format;
  - a bit-exact golden model;
  - xsim testbenches.
- **Reasons for RTL:** finer control (bit widths, pipelining, DSP packing, guaranteed 1 sample/clk); KAN-LUT is RTL anyway; tiny models; the user's existing flow; resume value.
- **The one argument for HLS:** fair comparison with the paper (which used HLS). Handled by putting both the paper's CNN and ours through the *same* RTL engine. An optional HLS build of the paper's CNN would quantify the RTL-vs-HLS gain.
- **Weights:** on-chip, loaded over AXI-Lite at runtime (not baked-in constants and not DDR, because the models are tiny). Shape is fixed by package parameters. That enables swapping models without re-synthesis and output-layer-only adaptation (I4) on the board.
  - Possible ablation: a constant-weight build (LUT shift-add savings).
- **Never overwrite progress:** FP32 models are frozen in `checkpoints/fp32_v1` (read-only, hashed). Quantization and hardware export read from there and write elsewhere.
- **Progress tracking:** this file is updated at every milestone. Small updates go to a Haiku subagent; heavy work (design, code, analysis, comprehensive rewrites) is done by the main agent.
- **User preferences:**
  - wants non-trivial, genuinely novel and publishable-quality work;
  - avoids projects whose code is simply available;
  - enjoys multi-tool work (Cadence, Vivado, PYNQ);
  - don't assume missing tools;
  - asks for short answers when they say so;
  - expects honest reporting of what is and isn't verified.
- **Course caution:** check the course policy on AI assistance. The user must understand everything for the poster/viva, and the report must state member roles. A suggested split: (1) simulator + data + baselines, (2) ML methods + experiments, (3) RTL/FPGA + poster.
- **RTL change tracking:** no git repo; every RTL revision gets a full snapshot in `rtl/history/` and an itemised entry in `rtl/history/CHANGES.md`, so any revision can be restored exactly (user requirement).
- **Optimisation passes are done two changes at a time**, each verified bit-exact (unit TB + all models) and snapshotted before the next (user request 2026-10-25). Deployment target is the PYNQ-Z2 only (no Spartan-7 / XC7S25 build: user has no such board).
- **Version control (user request 2026-10-25):** private GitHub repo `JSpectre20/mlee-cnn-equalizer`. History starts 2026-10-25 with one commit per component (course material, eqsim, scripts+results, checkpoints, RTL, PYNQ-Z2 build, docs); earlier RTL evolution is documented in `rtl/history/` + `CHANGES.md`. Every later milestone gets its own commit (message ends with the Co-Authored-By line) and is pushed.

## 7. How to reproduce (commands)
1. Tests: `D:\venvs\mlee-eq\Scripts\python.exe -m pytest -q`
2. Python experiments:
   - `scripts/run_imdd_sanity.py`
   - `scripts/run_proakis.py --iters 10000 --seeds 3`
   - `scripts/run_proakis_seeds.py --seeds 10 --workers 6`
   - `scripts/run_imdd_dse.py --stage all --workers 6`, then `--stage confirm --seeds 3`
   - `scripts/plot_imdd_dse.py`
   - `scripts/freeze_checkpoints.py --tag fp32_v1` (already done; refuses to overwrite)
   - `scripts/run_quant.py --bits 8 6 5 4 3 --iters 4000 --workers 6`
   - `scripts/export_rtl.py --model results/quant/<m>/integer_model.pkl --name <m> [--frames 8 --frame-symbols 64]`
3. RTL:
   - sim: `powershell -NoProfile -ExecutionPolicy Bypass -File rtl\sim\run_sim.ps1 -Model <m> -Stall <0..90>`
   - unit TB: `powershell -NoProfile -ExecutionPolicy Bypass -File rtl\sim\run_unit.ps1`; DSP path: add `-UseDsp 1` to run_sim.ps1
   - impl (from `rtl/syn`): `D:\AMD\2025.2\Vivado\bin\vivado.bat -mode batch -nojournal -source impl_ooc.tcl -tclargs <m> 5.0 <use_dsp>`

## 8. Open questions for the user
- PYNQ board = **PYNQ-Z2 rev A.0** (board files in `C:\FPGA_boards\pynq-z2\A.0`). Still unknown: the PYNQ image version on the SD card (`pip show pynq` on the board).
- Whether the professor's Zynq UltraScale+ board is available, and which one.
- Lab fiber-optic trainer kit availability (the user is asking).
- Cadence specifics (PDK, tools, licence count), only if a Cadence stage is added.
- Team members and roles; the course's AI-assistance policy.

## 9. Research history (details in `../MLEE_paper_shortlist_and_ideas.md`)
- **2026-10-20 shortlist** (all papers read in full; PDFs and text in `../papers/`):
  - **A:** Liu et al., Sensors 2025, TI-pipelined ADC Volterra + NN calibration. The user's suggested paper. Weaknesses: Volterra adds ~0 dB on silicon, no NN-only ablation, sine-fit foreground only, an FPGA DSP-count inconsistency.
    - Proposal: blind cyclostationarity-loss calibration + physics-structured / LUT-native calibrator.
    - Recommended as the strongest research option.
  - **1:** OpenDPDv2 (LUT-compiled phase-normalized KAN DPD).
  - **2:** KANELÉ (decomposition-aware bipartite KAN edges for >8-bit precision).
  - **3:** Extended STE for analog CIM (bias-corrected STE).
  - **4:** PPAAS (critic-guided test-time search + conformal spec feasibility).
  - **5:** PINN-DAB (amortized SBI + power-neutral active excitation).
  - **New idea B:** KAN macromodels exported to Verilog-A `$table_model`.
  - Dropped: Conv-DLGN, CodeV-R1, NeuraLUT family.
- **Board and tool discussion:**
  - RFSoC would enable real TI-ADC / DPD silicon experiments (PG269 calibration freeze/override), but it needs Vivado Enterprise, which the user doesn't have. The PYNQ prebuilt overlays would allow data capture without Vivado.
  - Without an RFSoC, idea A would use a home-built 2-way TI-ADC from two ~65 MS/s pipelined ADC modules clocked 180° apart on the PYNQ.
- **Simpler projects suggested:**
  - with code: S1 (hls4ml jet-tagging on PYNQ-Z2 + KANELÉ), S2 (OpenDPD + ACPR loss);
  - **without code (chosen family):** P1 (analog-circuit fault diagnosis, Sci Rep 2025, Hou et al.) and **P2 (Ney et al. CNN equalizer). P2 was chosen.**
- **Prior art for P2 improvements:**
  - KAN equalizer for 112G PON: KIT, OFC 2025, arXiv 2411.19631 (complexity only, no hardware).
  - Ney & Wehn trainable FPGA equalizer: DSD 2024, arXiv 2407.02967 (full on-FPGA backprop, up to 20 GBd).
  - Ney et al. real-time demo: arXiv 2402.15288.
  - Freire et al. JLT 2023 (LUT only for activation approximation).
  - UCC 8-bit FPGA PON equalizer, ICMLCN 2025.
  - SNN IM/DD equalizer: arXiv 2205.04263.
  - Public IM/DD benchmark simulator: imdd-task, arXiv 2412.03129.
  - CE better than MSE for NN equalizers: Marvell/WSU magnetic recording, Southampton minimum-BER.
  - DFE fixes CD power-fading nulls (C-band studies); NN + MLSE used in 800G PAM4 (TUM JLT 2023).
  - I found **no** LUT-compiled DSP-free NN equalizer and no ADC-ENOB × equalizer power co-design study.
  - **2026-10-24 novelty check for I1** (two subagents + spot checks): Fischer, Matalla, Randel, Schmalen, "Non-linear Equalization in 112 Gb/s PONs Using KANs", OFC 2025, arXiv 2411.19631 (same KIT group as the base paper; linear B-spline KAN, complexity in real multiplications, no hardware). A Chen et al. Optics Express 2025 KAN equalizer for short-reach IM/DD is cited by others (not verified). LUT-based nonlinear equalizers (pattern/sample-indexed tables) on FPGA exist for PAM4 IM/DD. No FPGA implementation of a KAN equalizer was found.

## 10. Improvement roadmap (pick 2–3 for depth)
| ID | Idea | Status |
|---|---|---|
| I5 | **Decision feedback.** FFE+DFE as an honest baseline, plus a CNN+DFE hybrid (CE-trained CNN with 1-2 decision-feedback taps; teacher forcing + scheduled sampling). Find where FFE+DFE breaks (SNR 14-24 dB, fiber 20-40 km, ADC 4-8 bit, PAM4) and whether CNN(+DFE) wins there. Hardware: a DFE after the serializer is a few adders (1 symbol/clk is enough on PYNQ); report the parallel-DFE cost at 40 GBd | **Done (model + golden + RTL r8); hardware P&R running.** See §5.3 item 7, §5.4 |
| I3a | Cross-entropy training (decision-aligned) | **Done, the headline result** |
| I1 | LUT-native KAN (or LUT-NN) equalizer on raw low-res ADC codes, compiled to LUTs (KANELÉ flow, MIT licence); iso-BER comparison vs the CNN on LUT/FF/DSP/Fmax/power | Novelty partial (see §9): KAN equalizers for IM/DD/PON exist in simulation (Fischer et al., KIT, OFC 2025, arXiv 2411.19631: beats CNN at equal real-multiplication count; suggests LUT of slopes/offsets but no FPGA results). LUT-native KAN on FPGA exists in general (KANELÉ, arXiv 2512.12850), not for equalization. Open: an FPGA LUT-compiled KAN equalizer with an iso-BER hardware comparison. Lower priority than I5 |
| I2 | ADC ENOB (3–8 bits) × equalizer co-design; ADC power from the Walden FoM, P = FoM·2^ENOB·f_s (Murmann survey); total receiver power vs BER | Next |
| I3b | Soft outputs (LLRs) → GMI/AIR + post-FEC BER (Sionna/AFF3CT) | Optional |
| I4 | Drift (fiber length ±2 km, received power, bias) + output-layer-only decision-directed LMS adaptation vs full retraining | Optional |
| — | NN + short Viterbi / CRF (course 4.1); decision feedback / small RNN for fading nulls (course 4.2–4.3; limits parallelism) | Optional |
| — | Distillation into a tiny model; transfer learning across fiber lengths (course 7.1) | Optional |
| — | Training robustness: LR schedule, more seeds, ensembling (seed variance about 2–10×) | Optional, cheap |
| — | Hardware ablations: USE_DSP LUT vs DSP (running), constant-weight build, DSP packing (2 MACs/DSP), optional HLS build of the paper's CNN | Partly running |

## 11. Real-data plan (optional, for the poster)
- **PYNQ-Z2 audio loopback** (the user can do this; no breadboard available):
  - 3.5 mm male-to-male cable, headphone-out → line-in, through the ADAU1761 codec at a fixed 48 kHz.
  - Stock PYNQ `AudioADAU1761.play()`/`record()` are blocking and sequential, so write a full-duplex C helper (modified `bypass()` loop that plays from a buffer while recording). Fallback: laptop headphone → PYNQ line-in with `record()` (≤60 s, interleaved int32 L/R) plus preamble and timing recovery.
  - Signal design: PAM at 24 → 48 kBd near the ~21 kHz codec cutoff, drive near clipping, separate captures for train/val/test.
  - Hybrid option: apply the fiber CD + square-law model in software before playback.
  - Framing: a second *real* nonlinear ISI channel (like the paper's magnetic-recording channel), **not** an optical emulation.
  - Verify the board has both jacks.
- **Lab fiber-optic trainer kit** (LED/laser + fiber + PD, kHz–Mbps): a genuine IM/DD link with dispersion negligible at those rates; the user is asking the lab.
- If neither works: simulation-only is fine. The board results (LUT/DSP/Fmax/throughput/BER on the board) are real measurements regardless.

---

## Log
- **2026-10-20:** Research and shortlist (`../MLEE_paper_shortlist_and_ideas.md`). Later recalibrated for Cadence, multi-tool preference, retired Zybo, no RFSoC licence. Picked P2 (Ney et al. CNN equalizer). Title submitted.
- **2026-10-24:** Built `eqsim` (simulator, models, training) with 6→8 unit tests passing. IM/DD fading/eye/FIR-floor sanity checks pass.
- **2026-10-24:** Proakis-B reproduction done. Discovered the MSE-vs-CE effect and the MLSE gap.
- **2026-10-24:** IM/DD 135-config DSE (MSE + CE), refine with 3 seeds, fresh-test confirmation. The headline (16× vs the paper's CNN) holds on the fresh test set.
- **2026-10-24:** 10-seed Proakis-B study: BCE significantly better (p = 0.011); MSE expected best-of-3 = 8.5e-3 vs the paper's 8.4e-3.
- **2026-10-24:** Froze all FP32 models + datasets to `checkpoints/fp32_v1` (read-only, SHA-256 manifest). Reload check passed (2.702e-5).
- **2026-10-24:** Decided on RTL (SystemVerilog, U-Net style, runtime-loadable weights). Starting quantization.
- **2026-10-24:** Created PROGRESS.md. Implemented quantization (`eqsim/quant.py`) and the integer golden model; 11 tests pass. W8A8 QAT recovers FP32 BER for all four models. Full bit sweep launched. Starting RTL design.
- **2026-10-24:** Quantization sweep done (ours_bce W6 = 2.18e-5 vs paper_mse W8 = 4.96e-4). Wrote the RTL engine, converter and TB. All bit-exact tests pass after fixing a tag-reset bug. Vivado P&R launched.
- **2026-10-24:** First P&R: 139–146 MHz (200 MHz not met); ours W6 8,176 LUT vs the paper's 13,431. Fixed the requant critical path (split shift + registered clamp) and added `USE_DSP`; regression 11/11 PASS. P&R rerun (3 models × LUT/DSP) launched. PROGRESS.md fully rewritten to capture all chat context.
- **2026-10-24:** P&R round 2: 157-182 MHz. Fixed the FLUSH compare / job-FIFO WE path and the LUT multiplier (2-stage), registered the credit check; regression 10/10 PASS. Round 3 P&R launched.
- **2026-10-24:** P&R round 3 regressed (147-159 MHz; the round-3 rem computation became the critical path). Round 4: jobs-owed running counter. Added the conv1d_stream unit TB (16/16 PASS, catches an injected bug) and DSP-path simulation (`-UseDsp 1`, PASS). Found the DSP builds pack the first adder-tree level into DSPs (~136 vs ~93). Round 4 P&R launched.
- **2026-10-24:** Round 4 P&R: ours_bce_w6 199.2 / 198.7 MHz. Added `rtl/history/` (r2 + r4 snapshots, CHANGES.md), `run_sim.ps1 -ConvSrc`, and `impl_ooc_opt.tcl` (directive flow). Directive flow: ours_bce_w6 meets 200 MHz (200.3 LUT, 201.4 DSP); paper_mse_w8 DSP 198.7. Remaining 4 runs relaunched after an app restart orphaned the previous loop.
- **2026-10-24:** PYNQ-Z2 board files located at `C:\FPGA_boards\pynq-z2\A.0` (TUL, xc7z020clg400-1, DDR3 MT41J256M16 at 525 MHz, APU 650 MHz, FCLK0 default 100 MHz, HP0 disabled by default). I1 novelty check done (partial). DFE/Viterbi quick study: FFE25+DFE2 reaches 5e-7 at 27 MAC (vs the paper's CNN 4.4e-4 at 112.5); roadmap re-prioritised with I5 (decision feedback) first.
- **2026-10-25:** RTL optimisation passes r5/r6/r7/r7b (see §5.6): DSP build 136 -> 45 DSP at 207 MHz, LUT build -23% LUT. PYNQ-Z2 system built in context with two clocks, timing met at 200 MHz (core) / 100 MHz (DMA); overlay files produced. Vivado silent crashes traced to parallel per-IP synthesis on 8 GB RAM (fixed with global synthesis, one job).
- **2026-10-25:** Added `eqsim/dfe.py` and `scripts/run_dfe_stress.py` (smoke test: FFE25+DFE2 0 errors on 200k symbols; CNN+DFE trains/evaluates). DFE stress test launched. Froze `checkpoints/quant_v1` and `checkpoints/hw_v1`; source archive `../backups/equalizer_src_2026-10-25_1224.zip`.
- **2026-10-25:** Initialised git at `Project/` and pushed to the private GitHub repo JSpectre20/mlee-cnn-equalizer (9 commits, head e6463e4). The DFE stress test survived an app restart and kept running.
- **2026-10-25:** DFE stress test finished (9 conditions; CNN+DFE2 best on hard channels, FFE+DFE best at the paper's operating point). Tagged `v1.0-cnn-200mhz`. CNN+DFE2 QAT: W8 integer BER 5.0e-7 (~1000x below the paper's W8 CNN). RTL r8 adds `dfe_stream.sv`; bit-exact; commit 3223c82. Vivado queue (DFE + paper model on r8, PYNQ-Z2 rebuild) launched.
- **2026-10-25:** Final-engine P&R of the paper model (DSP 187.9 MHz / 7,056 LUT) and CNN+DFE2 timing closure (r8 153 MHz -> r8b input register -> r8c lane select in stage I: 202.4 MHz OOC, PYNQ-Z2 system 200 MHz WNS +0.160). Froze `checkpoints/hw_v2`; tagged `v2.0-cnn-dfe-200mhz` (commit 3e80dd8); untracked Vivado scratch files (040d894).
- **2026-10-25:** SAIF power flow (`rtl/power/`) and results for all six final builds (commits 0210238, f103361); all routed netlists bit-exact at gate level. ours_bce_w6 -14% (DSP) / -37% (LUT) dynamic power vs the paper's CNN; ours_bce_dfe_w8 ~1000x lower BER at +5% / +1%.
