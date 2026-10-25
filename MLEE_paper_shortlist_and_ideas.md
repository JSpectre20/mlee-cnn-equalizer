# MLEE (EEE G513) Project: Paper Shortlist and Novel Extension Ideas

Prepared 20 Oct 2026. Team/title form is due **today (20 Oct)**; final submission is due **20 Nov 2026**, so roughly 4 weeks of work. You must hand in a report, an A3 poster and running code/prototype, with at most 3 members, and no paper may be reused by another group.

PDFs and extracted text are in `papers/`. Every paper below was read in full. The novelty claims come from targeted prior-art searches done today (sources at the end). "No prior work found" means my searches found none. It does not prove none exists, so do a final Scholar/IEEE Xplore check before you write "first".

**Assets I assumed you have:**
- Vivado/Vitis 2025.2, which you've already used to ship an on-board CNN accelerator.
- Newer FPGA boards (exact models not confirmed yet; see the table below).
- Cadence (exact suite, PDK and licence count not confirmed; see Section 8).
- A separate GPU box for training. Your laptop should only write code and run small checks.

**What each board class unlocks** (I don't know your exact boards, so the plans below say "your board" and note where a class makes a real difference):

| Board class (examples) | What it unlocks for these projects |
|---|---|
| **Zynq UltraScale+ MPSoC** (ZCU102/104/106, Kria KV260/KR260) | Room for full-size calibrators, KAN-DPD with several parallel lanes, and larger LUT-NNs. ARM A53 + Linux (PYNQ) makes Python-driven on-board testing easy. **ZCU104 uses the XCZU7EV, the same part KANELÉ reports**, so you can compare against their numbers directly on hardware. |
| **Zynq UltraScale+ RFSoC** (ZCU111/208/216, RFSoC 4x2) | **A big upgrade for A and 1.** The on-chip RF-ADCs are multi-GS/s *time-interleaved* converters, so you have real TI-ADC silicon. The RF-DACs plus ADCs let you close a wideband DPD loop with a real PA at hundreds of MHz of bandwidth, with the KAN-DPD running in the PL in real time. |
| **Versal** (VCK190/VEK280) | AI Engines give a third implementation target (LUT fabric vs DSP vs AIE), which makes a good efficiency comparison for Ideas 1–2. |
| **Alveo / large Virtex UltraScale+** (e.g., VU9P) | Matches KANELÉ's other benchmark part. Fine for out-of-context comparisons, but no real-world I/O. |

---

## 0. Ranking at a glance

| # | Paper | Domain | Improvement in one line | Novelty | 1-month feasibility | Hardware deliverable |
|---|---|---|---|---|---|---|
| A | **Liu et al., Sensors 2025** (Volterra + NN TI-ADC calibration). This is the paper you asked about. | Mixed-signal | Reference-free (blind) background training through a cyclostationarity loss, plus a physics-structured / LUT-native calibrator and the ablations the paper skipped | High | High (needs only a behavioral ADC model) | Calibrator on your FPGA (LUT/DSP/Fmax), vs the paper's 328 DSP; on an RFSoC, calibrate real on-chip TI-ADCs |
| 1 | **OpenDPDv2** (TU Delft, GLOBECOM 2026) | RF / comms | Fully pipelined, LUT-compiled, phase-normalized KAN DPD, compared with the delta-GRU under real FPGA costs | High | High (dataset + PA surrogate + code are public) | Zero-DSP DPD core, 1 sample/clk/lane |
| 2 | **KANELÉ** (MIT, FPGA '26) | FPGA ML architecture | Decomposition-aware (bipartite/multipartite) KAN edges that break the 2^n table wall, so precise regression/DSP tasks become possible | Medium-high | Medium-high | First on-board KANELÉ with I/O |
| 3 | **Extended STE for analog CIM** (Beihang/HKU, arXiv 2025) | In-memory computing | Bias-corrected STE: an online-estimated Jacobian for the *systematic* non-idealities (IR-drop, ADC clipping) | Medium | High (IBM AIHWKit is open) | Simulated CIM only |
| 4 | **PPAAS** (UT Austin/Samsung, 2025) | Analog EDA + RL | Turns the policy into a planner: critic-guided test-time search plus conformal "spec infeasible" certification | Medium-high | Medium (PDK/ngspice setup and RL compute) | None (EDA) |
| 5 | **PINN-DAB** (Dey & Mallik, arXiv 2025) | Power electronics | Amortized Bayesian (simulation-based) inference with *power-neutral* active TPS excitation | High | Medium-low (no hardware, heavy modeling) | Optional C2000/ARM deployment |

> **Update:** you have Cadence and want multi-tool projects. Section 8 upgrades every idea with transistor-level, ASIC and real-hardware stages, and adds a new Cadence-native idea (**B: KAN macromodels → Verilog-A**).

**My recommendation:** do **A**. If another group already took that paper, do **1**. A and 1 share most of their machinery (a behavioral or surrogate model of an analog block, then a learned linearizer, then a LUT-native FPGA core). That lets a 3-person team split cleanly, e.g. *simulator & data*, *ML method*, *FPGA*. Idea 2 is the hardware engine both can use. Section 7 has suggested titles. **Final pick (20 Oct): A, with 2 as its hardware engine.** Your boards are a PYNQ board now and possibly a Zynq UltraScale+ through your professor, with no RFSoC. Section 9 has the hardware plan for those: a home-built real TI-ADC with a live on-FPGA calibration demo.

---

## A. Liu et al., "Ensembling a Learned Volterra Polynomial with a Neural Network for Joint Nonlinear Distortions and Mismatch Errors Calibration of TI-Pipelined ADCs", *Sensors* 25(13):4059, 2025 ([MDPI](https://www.mdpi.com/1424-8220/25/13/4059), [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12251562/))

### What it does (verified from the full text)
- **Stage 1:** a per-channel truncated Volterra model (3rd order, memory 2, 40 coefficients in total for 4 channels) trained with Adam. It is meant to remove each sub-ADC's static ("baseline") nonlinearity. Ground truth comes from sine fitting with a time-shift phase-spectrum method, done per channel.
- **Stage 2:** an FCNN 8→256→8→4 with LeakyReLU. Inputs are 4 interleaved pre-calibrated samples plus 4 derivatives from a 32-tap FIR differentiator. It outputs residual corrections for dynamic nonlinearity and mismatch (offset, gain, timing skew). About 4.4 k parameters and 8.57 MFLOPs per 4096 samples.
- **Data:** 2800 random input frequencies, the first 500 samples of each, split 70/30 by frequency. 2000 epochs, cosine LR.
- **Results:**
  - Simulink model (12 b, 4 GS/s): SFDR 38.2→80.0 dB.
  - 12 b, 3 GS/s silicon: SFDR 35.47→79.70 dB, SNDR 35.35→55.63 dB.
  - 16 b, 1 GS/s silicon: SFDR 38.62→80.90 dB, SNDR 40.21→62.43 dB.
- **FPGA (XCZU15EG):** 3480 LUT, 28.8 k FF, 328 DSP, 1.5 W.

### Weaknesses I found while reading
1. **The "ensemble" claim is untested.** In their own ablation (Table 3), the Volterra stage alone moves silicon SFDR from 35.47 to 35.50 dB and from 38.62 to 38.63 dB, with about 2 dB of SNDR. There is **no NN-only ablation**, so the Volterra front-end's contribution is not shown.
2. **Foreground only.** Ground truth requires known sinusoidal inputs (sine fit). The method cannot follow temperature, supply or aging drift, which is exactly what makes TI mismatch hard in the field.
3. **Narrow test signals.** Only single and two-tone inputs are tested. There are no wideband modulated signals (OFDM, dense multitone, chirps) and no amplitude sweeps. An NN trained on sines plus their derivatives may learn sinusoid-specific structure.
4. **The hardware numbers don't add up for the reported model.** The 256-wide FCNN needs 8·256 + 256·8 + 8·4 = 4128 MACs per 4 samples, which is about 1.03 TMAC/s at 1 GS/s. 328 DSPs at 250 MHz give about 82 GMAC/s, roughly 12× short. Their FLOP count does match the 256-wide model. So the FPGA build is probably a reduced/quantized variant: their Fig. 14 shows 32 neurons costs 5–6 dB and 8-bit LSQ gives about 62 dB SFDR. Which accuracy goes with which hardware is never stated.
5. **Nothing to replicate from.** No code or data is released.

### Proposed project: "Reference-free background calibration of TI-ADCs with a physics-structured, LUT-native neural calibrator"

**(i) Honest replication.** Build a Python/PyTorch behavioral 4-channel 12-bit TI-pipelined ADC with:
- 1.5-bit/stage MDAC capacitor mismatch, inter-stage gain error, and residue-amp cubic nonlinearity with a memory term (their Eq. 4–7);
- input-switch dynamic nonlinearity, (A4 + A5·x + A6·x²)·dx/dt (their Eq. 8/11);
- per-channel offset, gain, timing-skew and bandwidth mismatch, plus thermal noise and jitter.

Generate the input analytically in continuous time so you get *exact* ground truth for any signal. Reproduce their 38→80 dB-class result, then run the missing ablations: Volterra-only, NN-only, ensemble, and a **physics-structured model**. That last model is per-channel Volterra plus (Δt_m + a_m + b_m·x + c_m·x²)·D(x) with a short FIR differentiator D, about 10 parameters per channel and solvable by least squares. My hypothesis is that it recovers most of the FCNN's gain at a tiny fraction of the DSPs. Either outcome is publishable.

**(ii) The novel core: blind/self-supervised training.** Train the calibrator *without* a reference by enforcing properties a correct TI-ADC output must have.
- **Cyclostationarity loss.** Mismatch makes a stationary input appear M-periodically non-stationary. Penalize differences across channel phases m in:
  - per-phase moments (mean, variance, kurtosis);
  - lag-1 and lag-2 cross-channel correlations E[y[n]·y[n+1]] (these are sensitive to timing skew);
  - equivalently, spectral correlation at the cyclic frequencies k·fs/M.
- **Spectral-hole loss** for the common-mode nonlinearity, which leaves stationarity intact. With a band-limited input or known empty bands (true for most receivers), harmonics and intermodulation land in the empty bins, so minimize the energy there, like ACPR in DPD.
- **Anchors to prevent trivial solutions** (a calibrator that outputs zero is perfectly "stationary"): channel 0 serves as the gain/timing reference, in-band power is preserved, the correction is residual, and small corrections are regularized. Doing the identifiability analysis (what is and isn't recoverable blind) is part of the contribution.
- **Experiments:**
  - (a) static case: blind vs sine-fit supervised;
  - (b) **drift**: mismatch parameters follow a temperature profile, and the blind calibrator adapts online with streaming SGD while the paper's frozen model degrades;
  - (c) generalization to OFDM, multitone and amplitude sweeps.

**(iii) Hardware.** Map the calibrator to your FPGA in Vivado: the structured model on DSPs, and/or a KAN whose inputs are *already ADC integer codes*, so every edge is literally a truth table (see Idea 2).
- **Throughput target:** the paper's 1 GS/s rate (4+ samples per clock at 250 MHz). That's realistic on any UltraScale+ part.
- **What to report:** LUT/FF/DSP/Fmax/throughput, in particular the DSP count at the *full* 80 dB-class accuracy against the paper's 328 DSP.
- **Minimum demo:** stream test vectors from PS DDR through AXI-Stream.
- **On an RFSoC:** calibrate the board's own RF-ADC directly (see Section 8).

**Novelty check:**
- Supervised ML TI-ADC calibration is crowded: FCNN, CNN and ANN papers, including ASU's VTS 2025 supervised method that uses a reference ADC, and CICC 2025 circuits-informed ML that also uses a reference ADC.
- Blind *non-ML* mismatch calibration (correlation/statistics/cyclostationarity based) is classical.
- I found **no NN calibrator trained with a reference-free cyclostationarity or spectral loss** for joint nonlinearity plus mismatch. Two extended searches found none.
- The physics basis x·dx/dt itself is not new (Nikaeen & Murmann 2009). Use it as the strong baseline, not the claim.

**4-week plan:**
- W1: simulator, sine-fit ground truth, replicate the paper.
- W2: ablations, structured model, blind losses.
- W3: drift and wideband experiments.
- W4: FPGA implementation on your board, poster, report. On an RFSoC, the real-ADC experiment should already start in W3.

**Risks:** blind nonlinearity calibration may be only partially identifiable. Mitigations are the spectral-hole assumption and a hybrid "supervised once at test time, blind tracking afterwards" mode. That hybrid is still novel and practical.

**Venues:** IEEE TCAS-II, ISCAS, IEEE Sensors Journal.

---

## 1. Wu, Li, Gao, "OpenDPDv2: A Unified Learning and Optimization Framework for Neural Network Digital Predistortion", GLOBECOM 2026 ([arXiv 2507.06849](https://arxiv.org/abs/2507.06849), [code+data](https://github.com/lab-emi/OpenDPD), Apache-2.0)

### What it does (verified)
- **Model:** TRes-DeltaGRU. A DeltaGRU skips MACs whose input/hidden deltas fall below thresholds Θφ/Θh, and a TCN residual path (dilated Conv1D K=3, D=16, a channel mixer and Hardswish) keeps fast output dynamics alive under sparsity.
- **Training:** end-to-end through a frozen DGRU PA surrogate (2751 params, −39.96 dB NMSE), plus QAT.
- **Data:** APA_200MHz, TM3.1a 5×40 MHz 256-QAM, PAPR about 10 dB, 983.04 MS/s, 98,304 samples, 3.5 GHz GaN Doherty at 41.2 dBm.
- **Results:**
  - 999 params FP32: ACPR −59.9 dBc, EVM −42.1 dB.
  - 56% sparsity, W12A12, 450 active params: −51.8 dBc / −35.2 dB.
  - Energy, Gem5 ARMv7: 2.8× from quantization alone, 4.5–5.2× with sparsity. They note that L1 D-cache energy is more than 10× arithmetic energy.

### Weaknesses
1. **Wrong platform for the energy claim.** Energy is evaluated on a simulated embedded CPU, but a 983 MS/s DPD runs in FPGA/ASIC pipelines. There, *data-dependent* temporal sparsity does not reduce provisioned hardware (you size for the worst case) and saves only dynamic power. The paper admits control overhead grows with sparsity.
2. **The recurrence limits pipelining.** At about 1 GS/s you need 3–4 samples per FPGA clock, and the GRU's h_{t−1} loop is a serial dependency. Their TCN branch is feedforward and parallelizes trivially, which hints at the alternative.
3. **Narrow evaluation.** One PA, one signal, one power level.
4. **Quantization cost.** W12A12 costs about 5 dB ACPR even in the dense model.

### Proposed project: "Zero-DSP, fully pipelined DPD with LUT-compiled phase-normalized Kolmogorov–Arnold networks"
- **Model.** A feedforward KAN DPD whose inputs are |x_t|, |x_{t−k}| and phase-normalized memory terms Re/Im(x_{t−k}·x_t*) for k = 1…M. Using the conjugate product avoids a divider. It outputs a complex gain g with u_t = g·x_t. Phase normalization turns the target into mostly an AM/AM–AM/PM function of amplitudes, which suits KAN's univariate edges. KAN is effectively a deep, learned generalization of the classic LUT-memory-polynomial DPD.
- **Training.** End-to-end through OpenDPD's PA surrogate with QAT, with a **learned compander** on |x| (the signal is high-PAPR, so most samples are small). This lets 7–8-bit edge inputs reach about 11-bit-equivalent resolution where it matters.
- **Compilation.** Each edge becomes an L-LUT with the KANELÉ flow (MIT licence). Only the final complex multiply uses DSPs, 3–4 per lane. P lanes give P samples per clock.
- **Evaluation at iso-ACPR/EVM** against:
  - TRes-DeltaGRU (999/450);
  - GMP;
  - classic LUT-MP DPD;
  - an MLP/RVTDNN via hls4ml;
  - a non-LUT KAN (DPD-KAN style).

  Metrics: params, BOPs, *post-route* LUT/FF/DSP/Fmax/latency on your board's part at full rate (983 MS/s means ≥4 lanes at about 250 MHz), and Vivado power at real signal activity. On an RFSoC, also run it **in the real DAC→PA→ADC loop** (Section 8). Also give a frank analysis of when temporal sparsity does or doesn't pay in a pipelined design.

**Novelty check:**
- KAN-based DPD exists: DPD-KAN for 5G analog radio-over-fiber, [arXiv 2606.21178](https://arxiv.org/abs/2606.21178), and ETDKAN, [arXiv 2606.27042](https://arxiv.org/abs/2606.27042), both June 2026, plus BO-KAN (IEEE TVT 2025). These count complexity in BOPs or use symbolic KANs. **None maps KAN edges to FPGA LUTs or reports post-route hardware.**
- LUT-NN work (LogicNets/PolyLUT/NeuraLUT/KANELÉ) has never targeted DPD. SparseDPD (FPL 2025) is sparse MACs, not LUT-native.
- So "LUT-compiled KAN DPD with real FPGA cost against temporal-sparsity RNN DPD" looks open.

**4-week plan:**
- W1: run the OpenDPD baselines and reproduce Table I numbers through the PA surrogate.
- W2: KAN-DPD with QAT and the compander.
- W3: KANELÉ compile, Vivado post-route, power.
- W4: sweeps, poster, report.

**Risks:**
- ACPR needs precision, and KAN tables grow as 2^bits. Mitigate with the compander and Idea 2's bipartite edges.
- All linearization results go through the PA *surrogate* (no PA lab). This is standard OpenDPD practice, but say it explicitly.

**Venues:** IEEE MWTL, IMS, FPL, ISCAS.

---

## 2. Hoang, Gupta, Harris, "KANELÉ: Kolmogorov–Arnold Networks for Efficient LUT-based Evaluation", FPGA '26 ([arXiv 2512.12850](https://arxiv.org/abs/2512.12850), [code](https://github.com/Duchstf/KANELE), MIT; the repo lists it as a Best Paper)

### What it does (verified)
- B-spline KAN edges on fixed domains, Brevitas QAT with per-layer uniform quantizers, and L2-norm edge pruning with exponential warm-up.
- Every surviving edge is enumerated into a truth table, followed by pipelined balanced adder trees and VHDL generation, synthesized out-of-context on VU9P/ZU7EV.
- **Results:**
  - JSC CERNBox: 75.1% with 5,034 LUT at 870 MHz.
  - JSC OpenML: 76.0% with 1,232 LUT.
  - MNIST: 96.3% with 3,809 LUT.
  - More than 4000× fewer LUTs than the prior KAN-FPGA work.
  - ToyADMOS autoencoder with 0 DSP/BRAM, and a HalfCheetah policy.

### Weaknesses / open edges
1. **The exponential precision wall.** LUT cost grows as 2^n in the edge input bitwidth (their Fig. 6d), so every benchmark uses 6–8-bit activations. Regression and signal-processing tasks (ADC calibration, DPD, control, scientific formulas, where KANs are strongest) need 10–14 bits.
2. **Uniform quantizers only** on fixed domains.
3. **No real I/O.** Results are out-of-context synthesis only, never deployed on a board.
4. **Temporal/streaming KANs** are listed as future work.

### Proposed project: "Precision-scalable LUT-KANs via decomposition-aware training"
- **Bipartite edge form.** Split each edge input x (n bits) into (x_h, x_l) and parameterize the edge *during training* as φ(x) = A[x_h] + B[x_h′, x_l], where x_h′ holds the top few bits of x_h. This is the bipartite form, with multipartite as the generalization. Table cost drops from 2^n to about 2^h + 2^(h′+l), roughly 2^(2n/3) for smooth functions per the classic Das Sarma–Matula / Schulte–Stine results. B-splines are smooth by construction, so they fit this regime.
- **Train in the cheap family directly** (structural QAT) instead of post-hoc decomposition. That avoids decomposition error.
- **Choose splits per edge** (h, h′, l) with a simple LUT-cost model (lightweight NAS).
- **Evaluate:**
  - Feynman symbolic-regression benchmarks (KAN's home turf);
  - ADC calibration and DPD (Ideas A and 1);
  - JSC for parity.

  Report the accuracy-vs-LUT Pareto front at 8/10/12/14-bit edges, plus the **first on-board KANELÉ demo** with AXI-Stream I/O from the ARM. On a ZCU104 (XCZU7EV), the same part as the paper's Table 4/7, you can reproduce their numbers *on hardware* before beating them.

**Novelty check:**
- ReducedLUT ([arXiv 2412.18579](https://arxiv.org/abs/2412.18579)) and CompressedLUT do *post-training* table compression for LUT-NNs. ReducedLUT notes that multipartite methods work poorly on *multivariate* neuron tables. KAN edges are univariate, which is exactly where multipartite methods shine.
- The A*STAR work ([arXiv 2508.17069](https://arxiv.org/abs/2508.17069)) uses "adaptive lookup tables" for KANs on edge FPGAs, targeting classification. **Read its architecture section before claiming novelty.** I only saw its abstract.
- I found no work that *trains* KAN edges natively in bipartite/multipartite form.

**Feasibility:** medium-high. The code is open, and Vivado 2025.2 vs their 2024.1 should be fine. With an UltraScale+-class board, model size isn't the constraint. Table *precision* is, and that's exactly what this idea attacks.

**Risk:** gains may be small at ≤8 bits, so pick tasks that genuinely need precision.

**Venues:** FPT, FPL, FCCM, ACM TRETS.

---

## 3. Feng, Zhou et al., "Extending Straight-Through Estimation for Robust Neural Networks on Analog CIM Hardware" ([arXiv 2508.11940](https://arxiv.org/abs/2508.11940), 4 pages)

### What it does (verified)
- The forward pass runs a full, non-differentiable CIM simulator: int8 I/O, ADC/DAC quantization, device nonlinearity, programming and read noise, thermal drift, retention and IR-drop.
- It returns y_clean + (y_noisy − y_clean).detach(), so the backward pass uses the clean gradient (∂N/∂W ≈ I).
- The "theory" is a cosine-similarity argument that assumes the noise-induced gradient bias is uncorrelated with the clean gradient.
- **Results:**
  - CIFAR-10 (VGG/ResNet): +1.4 to 5.3%.
  - Shakespeare BERT/GPT: perplexity −0.24 to −0.72.
  - 2.2× faster and 37.9% less peak memory than backpropagating through the noisy simulation.

### Weaknesses
1. **Thin, and the anchor paper is the weakest of the six.** The method is essentially noisy-forward / clean-backward, which closely resembles standard hardware-aware training ([IBM, arXiv 2302.08469](https://arxiv.org/abs/2302.08469)). The baseline in Table II is under-specified.
2. **The key assumption fails for the dominant non-idealities.** IR-drop, ADC clipping and conductance nonlinearity are **systematic and input-dependent** (non-zero-mean). For them, ∂N/∂W departs strongly from I, so STE optimizes the wrong objective, e.g. growing activations that later saturate the ADC.
3. **Not reproducible.** The simulator is proprietary and no code is released.

### Proposed project: "Bias-corrected STE: online Jacobian estimation for systematic analog-CIM non-idealities"
- **Method.** Decompose N(W, x) = D(W, x) + ε, with D the deterministic distortion and ε zero-mean noise. Keep the *exact* simulator in the forward pass. In the backward pass, apply a cheap, online-estimated Jacobian of D: per-column effective gain/compression fitted by least squares between y_noisy and y_clean on each batch (detached), times an ADC-saturation mask. Use plain STE only for ε.
- **Theory.** Show the STE bias equals E[∂D/∂W − I]·x-terms, and bound how much the correction removes.
- **Experiments in IBM AIHWKit** (open, with IR-drop, ADC/DAC resolution and bounds, PCM drift):
  - ResNet-20/CIFAR-10 and a small KWS or Transformer;
  - an ablation **by non-ideality type**. The prediction is that corrected STE ≈ STE under pure stochastic noise and wins clearly under IR-drop and ADC clipping on large (512×512) tiles.
  - Upper bound: training through a differentiable IR-drop model (IR-QNN-style) on small networks.
- **Byproduct:** an independent open-source replication, since the original has no code.

**Novelty check:** IR-QNN (IEEE Access 2020) and NN-based IR-drop predictors embed differentiable IR-drop models in training. AIHWKit models IR-drop in the forward pass. I found no STE variant that corrects the *systematic* bias with an online-estimated Jacobian while keeping the exact forward simulator.

**Feasibility:** high (pip install aihwkit; train on the GPU box). **Risk:** gains could be modest unless tiles are large or ADC bounds tight, so design the sweeps around those regimes. **Venues:** DATE, ICCAD workshop, IEEE TCAD letter, AICAS.

---

## 4. Kim et al., "PPAAS: PVT and Pareto Aware Analog Sizing via Goal-conditioned Reinforcement Learning", 2025 ([arXiv 2507.17003](https://arxiv.org/abs/2507.17003); reportedly ICCAD 2025; the paper says code and benchmarks are public)

### What it does (verified)
- Goal-conditioned SAC with continuous delta actions. The goal is the target specs plus [nominal-ok, all-corners-ok] flags.
- **Skip-on-Fail:** simulate the nominal corner first, and all 16 corners only if nominal passes.
- **PDGS:** candidate goals not Pareto-dominated by already-achieved goals, sampled by softmax(−Q/T).
- **Conservative HER:** relabeled transitions get a pessimistic reward, R′ ≤ R.
- **Benchmarks:** two-stage amp, cascode Miller amp and comparator on GF180 (17 training / 45 test corners), and an LDO on SKY130, all in ngspice.
- **Results:** success rates of 92.6/89.3/88.4/69.6%, about 1.6× sample efficiency and 4.1× simulation efficiency vs prior methods.

### Weaknesses
1. **No fallback at deployment.** Deployment is one deterministic rollout (mean action, horizon 30). For the 7–30% of goals it misses, the designer gets nothing, and an *infeasible* spec is indistinguishable from a hard one.
2. **SoF is a fixed heuristic.** Once nominal passes, all 16 corners are simulated even if the first corner fails.
3. **Global corners only.** There is no local-mismatch Monte Carlo, and GLOVA (DAC 2025, [arXiv 2505.11208](https://arxiv.org/abs/2505.11208)) already covers MC + simulation reordering, so I don't recommend "yield-aware PPAAS" as the main idea.
4. **PDGS hurts low-dimensional goal spaces.** The comparator result shows it, and the paper admits it.

### Proposed project: "From policy to planner: critic-guided test-time search and calibrated spec-feasibility for goal-conditioned analog sizing"
- **(a) Test-time search.** At each deployment step, sample N actions from the stochastic actor, score them with the twin critics (no SPICE), and simulate only the top-k. Add best-so-far restarts. Report success rate vs simulation budget. The claim is that it dominates the single rollout without retraining (AlphaZero-style policy improvement at inference).
- **(b) Feasibility certification.** Get "true" achievable fronts for a cheap circuit (two-stage amp, about 130 ms per simulation) by brute force (CMA-ES/BO with a large budget). Turn the critic value at s0, or the distance to the achieved-goal Pareto front, into a **conformal-calibrated "infeasible at 95%" detector**. When a spec is infeasible, project it onto the nearest achievable spec on the learned front, which is designer-facing value.
- **(c) Secondary: learned fail-fast corner ordering.** A tiny classifier predicts per-corner failure from the state and nominal metrics, and corner simulation stops at the first failure. This is incremental vs GLOVA's reordering, so present it as an ablation.

**Novelty check:** I found no test-time search or calibrated feasibility certification for goal-conditioned RL sizing. ACOF uses a critic to redirect search, but it is not goal-conditioned and does not certify feasibility.

**Feasibility:** medium. Install ngspice + GF180/SKY130 PDKs (use WSL), reproduce PPAAS first (hours on a multi-core box per circuit), then add (a)/(b). **Risk:** reproduction effort eats week 1–2. **Venues:** DAC/ICCAD workshops (MLCAD), ISCAS.

---

## 5. Dey & Mallik, "Physics Informed Neural Network – Estimated Circuit Parameter Adaptive Modulation of DAB" ([arXiv 2502.17452](https://arxiv.org/abs/2502.17452))

### What it does (verified)
- **NIFDM:** a multi-harmonic frequency-domain DAB model with winding/ESR/R_ds,on, transformer capacitances, resonant dead-time transitions and nonlinear-Coss switching loss, within about 5% of hardware power flow.
- Loss-optimal TPS modulation (δp, δs, φ) is fitted as 4th-order polynomials in (Vout, P, Lt, Rt).
- **"PINN":** an MLP with 2×64 ReLU layers maps (Vin, Vout, Iin, Iout, Ploss, δp, δs, φ) to (Lt, Rt). The loss is MSE on the labels plus λ·MSE on NIFDM-predicted Pin/Pout.
- **Data:** 1000 hardware + 4000 simulated samples.
- **Results:**
  - MAE 2.7% for Lt and 3.1% for Rt, vs 5.9% / 11% for a pure NN.
  - NN runs on a PC and talks SPI to a C2000.
  - 2 kW / 100 kHz GaN DAB: +1.4% average efficiency with a 30% inductance drop.

### Weaknesses
1. **Not a PINN in the usual sense.** It is supervised regression with a physics-consistency term, and it still needs *labeled* Lt/Rt, which on hardware means physically swapping components.
2. **No model-based baseline.** With a ≤5%-accurate differentiable model, nonlinear least squares, an EKF or RLS on the same measurements is the obvious baseline, and DAB RLS/LS inductance identification already exists in IEEE TPEL letters.
3. **Identifiability and uncertainty are ignored.** Rt is inferred through Ploss, which also contains ZVS-dependent switching and Coss loss, so it is weakly observable at light load. No uncertainty is reported, yet the modulation trusts point estimates.
4. **Minor:** the input count is inconsistent (7 vs 8), and there is no code or data.

### Proposed project: "Uncertainty-aware, power-neutral active identification of DAB parameters via amortized simulation-based inference"
- **Model and estimator.** Build a differentiable DAB steady-state model in PyTorch (an NIFDM-lite harmonic model). Train an **amortized neural posterior** q(Lt, Rt | measurements, modulation): a conditional normalizing flow or mixture density network trained on simulations with domain-randomized nuisances (Coss scale, dead-time, Lm, sensor gain/offset). Check calibration with simulation-based calibration (SBC).
- **Key idea: power-neutral excitation.** TPS has 3 degrees of freedom, but the power setpoint pins only one. The remaining 2-D manifold of *equal-power* modulations can be used to **probe the parameters without disturbing power delivery**. Choose the perturbation that maximizes expected information gain (or Fisher information via autodiff) under an efficiency/ZVS budget, and iterate a few steps.
- **Then:** uncertainty-aware (expected-loss-minimizing) modulation vs point-estimate modulation.
- **Baselines:** the replicated PINN, NLS, EKF/RLS.
- **"Hardware" proxy:** ngspice/LTspice switching-level DAB with vendor GaN models, which gives a real sim-to-real gap. Use a lab converter if your department has one.

**Novelty check:** I found no SBI or normalizing-flow posterior estimation for power converters. KIT used it for grid-frequency dynamics, and a 2026 paper ([arXiv 2608.30915](https://arxiv.org/abs/2608.30915)) does differentiable-physics parameter estimation for buck converters without UQ. I found no power-neutral active excitation in TPS.

**Feasibility:** medium-low in one month. The modeling is heavy and there is no hardware. **Best suited if a teammate is strong in power electronics.** **Venues:** IEEE OJPEL, ECCE, APEC, COMPEL.

---

## 6. Papers considered and dropped
- **Convolutional Differentiable Logic Gate Networks** (Petersen et al., NeurIPS 2024, [arXiv 2411.04732](https://arxiv.org/abs/2411.04732)). Excellent paper, but the follow-up space is already crowded in 2025–26: WARP-LUTs, unit tying (ICML 2026), connection optimization, EEG/ECG/time-series LGNs, FPGA LGNs for the CMS trigger. Bigger boards make CIFAR-scale models (16–61 M gates) partly feasible, but the training cost (custom CUDA kernels, days of GPU time) and the crowded novelty space still make it a poor 4-week bet.
- **CodeV-R1 / RL for Verilog LLMs:** 7B-scale RL is out of a student GPU budget for one month.
- **NN optical equalizers on FPGA (KIT/RPTU):** solid, but the LUT-KAN angle overlaps Idea 1. Keep it as a fallback application.
- **NeuraLUT-Assemble / PolyLUT / TreeLUT:** a crowded LUT-NN family. KANELÉ is the strongest entry point into it.

## 7. Suggested project titles (for today's form)
- **A:** "Reference-Free Background Calibration of Time-Interleaved ADCs with a Physics-Structured, LUT-Native Neural Calibrator"
- **1:** "Zero-DSP Digital Predistortion: LUT-Compiled Phase-Normalized Kolmogorov–Arnold Networks on FPGA"
- **2:** "Precision-Scalable LUT-Based Kolmogorov–Arnold Networks via Decomposition-Aware Training"
- **3:** "Bias-Corrected Straight-Through Estimation for Systematic Non-Idealities in Analog Compute-in-Memory"
- **4:** "From Policy to Planner: Test-Time Search and Calibrated Feasibility for Goal-Conditioned Analog Circuit Sizing"
- **5:** "Power-Neutral Active Identification of Dual-Active-Bridge Parameters via Amortized Bayesian Inference"

**Suggested role split (3 people, for A or 1):** (1) behavioral model/simulator + data + baselines; (2) learning method (blind loss or KAN-DPD + QAT) + experiments; (3) FPGA/RTL + Vivado results + poster.

## 8. Multi-tool upgrades (Cadence, ASIC flow, real hardware)

The common pattern: **transistor-level truth (Spectre) → ML (PyTorch) → two hardware targets (FPGA in Vivado and ASIC in Genus/Innovus) → real-world measurement where possible.** Comparing FPGA against ASIC cost for the same learned block is a strong poster story, and it fits the course's hardware unit (6.1–6.3) closely.

Things to confirm first (each one changes the scope):
- **PDK:** gpdk045/gpdk090 (Cadence generic) or a foundry PDK through BITS (TSMC/UMC/SCL 180)? Does it include MC/mismatch models and corners?
- **Cadence tools:** Virtuoso + ADE (Explorer/Assembler) + Spectre/APS, Spectre RF, Xcelium, Genus/Innovus/Joules, PSpice, AWR?
- **Licences:** how many Spectre seats run in parallel? This matters for the RL idea, which needs 10⁴–10⁵ simulations.
- **FPGA boards:** which ones exactly? **An RFSoC changes A and 1 the most** (real TI-ADC silicon and a real DPD loop).
- **Lab hardware:** signal generator, spectrum analyzer, PA evaluation boards, SDR (ADALM-Pluto/USRP), ADC evaluation boards, C2000 LaunchPad.

### A (TI-ADC), multi-tool version: "silicon-grounded" calibration
1. **Virtuoso/Spectre:** design the error-dominant front-end at transistor level: a bootstrapped sampling switch plus the first MDAC stage (opamp, cap DAC), as in the paper's Fig. 1–2. Write the rest of the pipeline (comparators, later stages, digital correction) in Verilog-A. Run **Monte Carlo** per channel to get *real* channel-to-channel mismatch, and run PVT corners to get the drift scenario. Script it with OCEAN/SKILL, or drive Spectre netlists from Python, export PSF to CSV, and feed PyTorch.
2. **Speed problem and its fix:** transistor-level transient runs of 10⁵-sample captures are slow. Use **Idea B** to learn a fast macromodel of the front-end from a few Spectre runs, then generate training data at Python speed. This chains two contributions together.
3. **PyTorch:** the blind cyclostationarity calibrator from Section A.
4. **Two hardware targets:**
   - **Vivado:** calibrator on your FPGA at full rate.
   - **Genus (+ Innovus for real P&R):** the same RTL synthesized in the *same node as the ADC* (gpdk045). Report area in µm², power in mW (from VCD activity in Xcelium simulation through Joules or Genus power) and energy per conversion step, i.e. the calibrator's overhead on the ADC's figure of merit. This is how ADC papers judge digital calibration, and the Sensors paper gives only FPGA numbers.
5. **Real silicon on an RFSoC (best option if you have one).** The RF-ADCs are multi-GS/s time-interleaved converters with on-chip background calibration for offset, gain and time skew. The RF Data Converter API reportedly lets you freeze or override those calibration blocks; **confirm in AMD PG269 for your RFSoC generation.** Freeze them to expose the raw interleaving spurs, then compare:
   - (i) no calibration;
   - (ii) AMD's built-in calibration;
   - (iii) your blind NN calibrator running in the PL next to the ADC.

   Beating or matching a commercial on-chip calibration on real GS/s silicon is a very strong result. It turns the project from simulation-only into a measured-hardware paper. Drive it with a signal generator, or loop back the board's own RF-DAC with a band-pass filter.
6. **Optional real data, if the lab has one:** a GS/s ADC evaluation board with an interleaving mode (e.g., TI ADC12DJ-series dual-edge sampling). Check the datasheet and availability.

### 1 (DPD), multi-tool version: measured over-the-air DPD
- **Real loop, best option, on an RFSoC:** RF-DAC → PA evaluation board (or a gain block driven into compression) → coupler/attenuator → RF-ADC, with the KAN-DPD running **in the PL at full sample rate**. This gives measured ACPR/EVM at 100–200 MHz bandwidths comparable to the OpenDPD dataset, *and* a real-time hardware DPD. The OpenDPD paper itself has neither: it trains offline and evaluates energy on a Gem5 CPU.
- **Low-cost alternative:** ADALM-Pluto (AD936x) TX → cheap PA → attenuator → RX via pyadi-iio/MATLAB. Measured, but limited to about 20 MHz and with the DPD running on the host.
- **Waveforms:** MATLAB Communications/5G Toolbox. The OpenDPD 200 MHz dataset stays as the public benchmark.
- **Spectre RF:** a transistor-level class-AB PA in your PDK, swept over PVT/temperature, gives a dataset for **DPD robustness under PA drift**. Neither OpenDPD nor the KAN-DPD papers test that. AWR Microwave Office/VSS works too, if you have it.
- **Genus:** ASIC synthesis of KAN-DPD vs TRes-DeltaGRU (as an MAC datapath) at the same throughput. Base-station DPD is ASIC, so this is the fair energy comparison the paper lacks (it uses a Gem5 CPU).

### 2 (KANELÉ), multi-tool version: LUT-KANs beyond FPGAs
- **ASIC mapping of KAN truth tables:** synthesize the edge tables as random logic with Genus, or with ABC (open-source) using don't-care exploitation, vs ROM macros. Compare FPGA LUT cost to ASIC gate area/power. I found no ASIC study of LUT-KANs, so this pairs naturally with the bipartite-edge idea (bipartite tables also shrink logic).
- **Xcelium:** run the generated VHDL against PyTorch golden vectors, i.e. bit-exact regression like your U-Net project.

### 3 (STE-CIM), multi-tool version: circuit-grounded non-idealities
- **Virtuoso/Spectre:** design a small charge-domain SRAM-CIM column (e.g., 64 rows of 8T cells, capacitive accumulation) plus a column SAR ADC. Use Spectre MC + PVT to extract the *systematic* transfer: MAC-value INL, dependence on activation density (IR-drop-like), ADC clipping. Fit a data-driven non-ideality model and plug it into the AIHWKit/PyTorch forward pass.
- **Then the main experiment:** STE vs bias-corrected STE under *your circuit's* non-idealities.
- **Novelty note:** characterizing CIM from circuits/silicon for training has been done: D-NAT (JETCAS 2022) used a measured macro, and ICare used a CIM-aware framework. The novelty stays the bias-corrected gradient. The Spectre macro makes it credible and adds solid analog-design content.

### 4 (PPAAS), multi-tool version: an industrial simulator and baseline
- **Spectre/APS + PDK** with real corners and MC instead of ngspice, plus **Virtuoso ADE Assembler's built-in optimizer** as an industrial baseline. Beating, or honestly losing to, a commercial optimizer is a valuable result.
- **Watch the licence count:** RL needs many simulations, so check parallel Spectre seats.

### 5 (PINN-DAB), multi-tool version: sim-to-real, then embedded
- **PSpice/OrCAD** (Cadence) with vendor GaN models (EPC/GaN Systems publish PSpice models) as the "hardware" proxy. Use MATLAB/Simulink or PLECS for the controller.
- **TI C2000 LaunchPad (F28379D):** run the posterior network *on the MCU*. The paper ran its NN on a PC over SPI.

### NEW idea B (Cadence-native): "KAN macromodels: learned, interpretable behavioral models auto-exported to Verilog-A"
- **Problem:** mixed-signal verification is bottlenecked by slow transistor-level sims. Behavioral models (Verilog-A, SystemVerilog real-number models) are hand-written and drift from the circuit.
- **Idea:** learn a KAN (or KAN plus a small linear state-space part for memory) from Spectre transient/AC data of a block: OTA, sampler, LDO, comparator, VCO. Then **auto-generate Verilog-A**. Each KAN edge is a 1-D function, so it maps directly to `$table_model` lookups or closed-form splines, and sums are trivial. The output is compact, interpretable and differentiable (smooth splines help simulator convergence).
- **Validation:** run Spectre with the macromodel in place of the transistor block inside a larger system (e.g., the TI-ADC from Idea A). Report the speed-up and the accuracy (SNDR/SFDR error, settling error) across PVT, with PVT as extra KAN inputs.
- **Novelty check:** I found Hammerstein-to-Verilog-A macromodels and table-model behavioral modeling flows, but **no KAN-to-Verilog-A/table_model flow**. One search; re-check "neural network Verilog-A" prior art. Neural compact/behavioral models in Verilog-A do exist, so position KAN as the interpretable, table-native alternative.
- **Tools:** Virtuoso/Spectre + Python + Verilog-A (+ Xcelium/AMS for SV-RNM export). With A it forms one pipeline; on its own it is a solid project.

### Scope warning
A multi-tool chain multiplies integration risk with four weeks left. Define tiers up front:
- **MVP (must run by 10 Nov):** Python/PyTorch + one hardware target.
- **Stretch:** the Spectre stage and the second hardware target.
- **Bonus:** real measured data.

Keep the poster story intact at every tier.

## 9. Hardware plan for your actual boards (PYNQ now, Zynq UltraScale+ possibly)

There is no RFSoC and no Vivado Enterprise licence, so build a real TI-ADC yourself instead of using an RFSoC's.

**Boards and licences.**
- **PYNQ-Z1/Z2 (XC7Z020):** about 53k LUT, 220 DSP, 140 BRAM36, Pmod + Arduino + (Z2) Raspberry-Pi headers. **Covered by the free Vivado ML Standard edition.**
- **PYNQ-ZU (XCZU5EG):** check which PYNQ board you have; this one is UltraScale+.
- **Zynq UltraScale+ from your professor:** Kria and smaller ZU+ parts are generally in the free edition. Larger ones (e.g., ZCU102's ZU9EG) may need the kit's voucher or a university licence, so check AMD's UG973 device list before relying on it.
- PYNQ itself is open source, and Cadence covers the ASIC side.

**The build: a real 2-way time-interleaved *pipelined* ADC.**
- **Parts:** two low-cost 12-bit, ~65 MS/s pipelined-ADC modules (AD9226-class boards are common FPGA add-ons; check the datasheet and module pinout first).
- **Wiring:** 2 × (12 data + clock) ≈ 26 GPIO, which fits on the PYNQ-Z2's Raspberry-Pi header plus a Pmod.
- **Clocking:** clock the two modules from FPGA MMCM outputs **180° apart**, which gives a 2-channel TI-ADC at ~130 MS/s. That's the same architecture class as the Sensors paper, at lower speed.
- **What you get:**
  - **Real mismatch for free:** offset, gain and bandwidth mismatch between two physical chips, plus real pipeline nonlinearity, and front-end-buffer nonlinearity on the cheap modules, which is fine since that's what you're calibrating.
  - **Controlled timing skew:** the MMCM's dynamic phase shift (step size depends on the VCO setting, typically tens of ps) lets you *sweep* skew deliberately, which is ground truth for the skew experiment.
  - **Drift on demand:** a hair dryer or freeze spray on one module changes its mismatch live, which tests blind background tracking.
- **Inputs:** a lab signal generator for tones, plus your own arbitrary waveforms through a DAC if available. A band-pass filter on the tone generator improves the reference purity.
- **Signal-integrity caution:** 65 MHz LVCMOS on header jumpers is marginal. Keep wires short, use a small adapter PCB or ribbon, and register the data on the module's output clock.

**The live demo (poster centrepiece).**
- **Layout:** the PL runs capture + the calibrator in real time. The ARM side (PYNQ/Jupyter) computes the blind loss on streaming captures, updates the calibrator coefficients/tables over AXI, and plots the spectrum before and after live.
- **Timing is trivial:** at 2 samples/clock and 65 MHz, Fmax won't be a problem on a 7020.
- **The comparison:**
  - (i) raw;
  - (ii) the paper's method: supervised sine-fit, Volterra + FCNN;
  - (iii) classical blind mismatch correction;
  - (iv) yours.

  Run all four on the same captured and live data.

**Scaling with the professor's Zynq UltraScale+.**
- **More channels:** a 4-way interleave with four modules, using FMC/Pmod I/O or an FMC breakout.
- **More throughput:** higher clock rates.
- **A KANELÉ cross-check:** if it's a ZCU104 (XCZU7EV, KANELÉ's own part), reproduce their numbers on hardware.
- PYNQ also supports ZCU104 and Kria, so the software stack carries over.

**Hardware-cost results, no paid licence needed.**
- **FPGA:** Vivado (free edition) LUT/FF/DSP/BRAM/Fmax/power for the calibrator on your board.
- **ASIC:** Cadence Genus (+ Innovus) for gpdk045 area/power, and the calibrator's overhead on the ADC's energy per conversion step.
- **Compare against the paper's 328 DSP / 1.5 W** at matched SFDR.

**Simulation layers stay.** The behavioral model and Spectre front-end (Sections A and 8) give exact ground truth and GS/s-rate experiments. The home-built TI-ADC gives *real-world* validation. Together: simulation for the scale experiments, hardware for the honesty check.

## 10. Two simpler projects with no public code (you implement them, modest improvement)

These have **no official code**. You build the data pipeline, the model and the hardware yourself from the paper's description, so the work isn't trivial. But each method is small and clearly specified, and the improvement is modest and low-risk.

### P1. Analog-circuit fault diagnosis, then a tiny on-board self-test
- **Paper:** Hou, Liu & Yu, "Enhanced analog circuit fault diagnosis via continuous wavelet transform and dual-stream convolutional fusion", *Scientific Reports* 15:19828 (2025), [PMC12141528](https://pmc.ncbi.nlm.nih.gov/articles/PMC12141528/). Code/data are only "on request".
- **What they do:**
  - **Circuits:** Sallen–Key band-pass (9 classes), four-op-amp biquad high-pass (13), Tow-Thomas (18).
  - **Faults:** components shifted ±30%, with 5%/10% R/C tolerance, 200 Monte Carlo runs per class, simulated in Multisim.
  - **Stimulus:** a 5 V, 10 µs pulse, with 300–750 response samples.
  - **Model:** Morlet CWT images (224×224×3) feed a 2D-CNN, which is fused with a 1D-CNN on the raw signal, then CBAM attention and FC 120/84.
  - **Results:** 100% / 99.66% / 97.71%. Hardware check on a PCB biquad: 99.12%. **Accuracy drops to 76.6% at 0 dB SNR** on Tow-Thomas.
- **Reproduce (no code given):**
  - **Data:** build the three circuits in **Cadence (Spectre/PSpice)** or ngspice, run the fault plus Monte Carlo sweeps by script, and export the transient responses.
  - **Model:** implement CWT-DSCNN-CBAM in PyTorch and match their accuracy table.
- **Improvement (pick one or two):**
  - **(a) Right-size it.** A 224×224×3 image CNN with attention is massive overkill for 300-sample responses. Show a tiny 1D-CNN or an FFT-feature MLP reaching the same accuracy at 100–1000× fewer MACs. Then deploy it as a **built-in self-test on your PYNQ**:
    - a GPIO pin drives the pulse into a breadboard biquad (potentiometers make the faults);
    - the on-chip XADC samples the response (the biquad's 1 µs sampling equals the XADC's 1 MS/s);
    - the tiny network classifies the fault live.
  - **(b) Noise robustness.** Fix their low-SNR collapse with noise-augmented training, or SNR-conditioned models. Plot accuracy vs SNR against their curve.
  - **(c) Sim-to-real.** Train only on Spectre Monte Carlo data, test on your breadboard, and close the gap with simple domain adaptation (input normalization or fine-tuning on a few real samples).
- **Course fit:** supervised classification, CNNs, feature transformation, complexity analysis, embedded deployment. It's cheap hardware too: op-amps, resistors, capacitors and a signal source; the PYNQ can be the source.

### P2. CNN equalizer for optical (IM/DD) links, with your own channel and an FPGA build
- **Paper:** Ney et al., "CNN-Based Equalization for Communications: Achieving Gigabit Throughput with a Flexible FPGA Hardware Architecture" ([arXiv 2405.02323](https://arxiv.org/abs/2405.02323); later in Int. J. Parallel Programming). No public code.
- **What they do:** a CNN equalizer that removes inter-symbol interference in optical IM/DD, with a quantization analysis and an FPGA architecture with variable parallelism. They report about 4× lower BER than a conventional equalizer and >40 GBd; a low-cost configuration is shown on a magnetic-recording channel.
- **Reproduce (no code given):**
  - **Channel:** write your own IM/DD channel in Python: PAM2/PAM4 → pulse shaping → fiber chromatic dispersion (a frequency-domain phase) → square-law photodiode → noise → ADC quantization.
  - **Equalizers:** train the CNN and compare it against a linear FFE and a Volterra equalizer (BER vs fiber length/SNR).
  - **Quantization:** do QAT (Brevitas or hand-rolled) and repeat their bit-width analysis.
- **Improvement (pick one):**
  - **(a) FPGA build on your PYNQ.** A low-parallelism instance in HLS or RTL, streaming symbols from DDR. Report BER-vs-LUT/DSP and throughput, and compare against the FFE on the same board. Your own simple Pareto of BER vs hardware cost is the contribution.
  - **(b) Structure.** A tiny KAN or a decision-feedback hybrid (CNN plus 1-tap DFE) at equal complexity. It's a simple ablation, and it either wins or gives an honest negative result.
- **Course fit:** CNNs, communication systems, quantization, FPGA.

**Which one?** P1 is the safer and more electronics-flavoured choice, and it makes a great live poster demo with a breadboard plus PYNQ. P2 is more communications and DSP heavy. **A cheaper fallback with the same flavour:** a "lite" version of A, i.e. reproduce the Sensors ADC paper in simulation, run its missing NN-only ablation, and put an 8-bit version of their FCNN on the PYNQ.

### (Previous version, kept for reference: projects *with* public code. You may consider these too easy.)

### S1. Jet-tagging MLP on an FPGA with hls4ml, then a KAN on the same board
- **Paper:** Duarte et al., "Fast inference of deep neural networks in FPGAs for particle physics", JINST 2018 ([arXiv 1804.06913](https://arxiv.org/abs/1804.06913)).
- **Code:** the [hls4ml tutorial](https://github.com/fastmachinelearning/hls4ml-tutorial). Part 7a builds a bitstream **for the PYNQ-Z2 specifically** ([docs](https://fastmachinelearning.org/hls4ml-tutorial/part7a_bitstream.html)).
- **Reproduce:**
  - train the 16→64→32→32→5 jet-tagging MLP (the dataset auto-downloads from OpenML);
  - do the tutorial's quantization (QKeras) and pruning steps;
  - generate the PYNQ-Z2 overlay;
  - run inference on the board from Jupyter;
  - report accuracy, LUT/FF/DSP/BRAM, latency and throughput.
- **Improvement:** train a KAN on the *same dataset* with KANELÉ (its repo includes this JSC benchmark). Wrap its VHDL in AXI-Stream + DMA in a Vivado block design and run both networks **on the same PYNQ board**. KANELÉ only reported synthesis numbers, never measured on a board, so a measured MLP-vs-KAN comparison (accuracy, resources, latency, measured throughput) is a small but real addition.
- **Tool caveat:** the tutorial's part 7 expects old Vivado HLS 2019.2/2020.1, which is free for the 7020. Either install that, or use hls4ml's newer Vitis HLS backend and write the AXI wrapper yourself.
- **Course fit:** units 6.1–6.3 (FPGA, quantization, pruning, complexity analysis). The effort is mostly software, plus one block design.

### S2. Neural-network DPD with OpenDPD, plus a spectrum-aware loss
- **Paper:** Wu et al., OpenDPD (ISCAS 2024, [arXiv 2401.08318](https://arxiv.org/abs/2401.08318)), and the OpenDPDv2 / TRes-DeltaGRU results in Section 1.
- **Code + data:** [lab-emi/OpenDPD](https://github.com/lab-emi/OpenDPD) (Apache-2.0, `pip install opendpd`, APA_200MHz dataset included).
- **Reproduce:** train the PA model, then the GRU / DeltaGRU / TRes-DeltaGRU DPDs. Report NMSE/ACPR/EVM against their tables (through their PA surrogate).
- **Improvement (pick one):**
  - **(a) ACPR-aware loss:** MSE + λ × out-of-band power of the cascaded DPD→PA output, computed with an FFT on each training batch. Sweep λ and plot the ACPR-vs-EVM trade-off. This idea is known in industry (an Analog Devices blog mentions ACPR/EVM loss terms), so frame it as "a systematic study", not "first".
  - **(b) Feature engineering:** add phase-normalized memory features (Re/Im of x_{t−k}·conj(x_t)) and |x|² / |x|⁴. Show the same ACPR with fewer parameters. This maps to course unit 1.5 (feature transformation).
- **Effort:** software only, runs in hours on the GPU box, no board needed. Optional extra: use their quantization code to show W8/W12/W16 trade-offs.

**Which one?** S1 if you want an on-board demo for the poster; S2 if you want the least risk.

## 11. Expanded plan for P2: LUT-native neural equalization for low-resolution IM/DD receivers

**Suggested title:** *"Multiplier-Free, LUT-Native Neural Equalization for Low-Resolution IM/DD Optical Receivers: ADC–Equalizer Co-Design on FPGA"*

### What the paper actually does (read in full: Ney et al., [arXiv 2405.02323](https://arxiv.org/abs/2405.02323), 27 pp.)
- **Channel:** a lab IM/DD link with **40 GBd PAM2**, RRC pulses, MZM at quadrature, 31.5 km SSMF (D ≈ 16 ps/nm/km, 1550 nm), 40 GHz photodiode, real-time scope, oversampling N_os = 2. **That data isn't public.** The second channel is a simulated, fully specified Proakis-B magnetic-recording channel h = [0.407, 0.815, 0.407] at 20 dB SNR.
- **Model:** 1-D CNN template (L layers, kernel K, C channels, V_p symbols out in parallel; BN + ReLU; first stride V_p, last stride N_os). They explore 135 configs and pick **L=3, K=9, C=5, V_p=8**. Training is MSE, then **hard decision to the nearest symbol**.
- **Baselines:** FIR (3–1017 taps) and 3rd-order Volterra. The CNN gets about 4× lower BER than FIR and more than 10× lower than Volterra at equal MACs per symbol. FIR floors near 1e-4. On Proakis-B: CNN 8.4e-3 vs FIR 9.6e-3.
- **Quantization:** learned per-layer bit widths (BitPruning-style, with separate integer and fraction widths and a QLF penalty). Ends at **~13-bit weights and ~10-bit activations**.
- **Hardware:** Vitis HLS + Vivado 2022.2.
  - **High-throughput build:** XCVU13P, 64 CNN instances, 200 MHz, ≥40 GBd net. It uses **9,648 DSPs (78.5%)**, 68% LUT and 79% BRAM, with stream split/merge plus an overlap/latency model.
  - **Low-power build:** XC7S25, degree of parallelism (DOP) 1–225, 4–110 Mbit/s at 0.1–0.2 W.
  - Power is a *Vivado estimate*, not measured.

### Gaps the improvements target
1. **The design is DSP-bound and clock-limited.** They note designs above 200 MHz fail timing, and throughput is N_i·V_p·f_clk. Every gain in f_clk or in MACs per DSP directly cuts the instance count.
2. **High precision (13b/10b) despite low-resolution inputs.** Real optical receivers digitize with **low-resolution ADCs (roughly 4–8 effective bits)**, so the equalizer's inputs are already a few-bit integers. That's exactly where LUT-native networks are exact and cheap: KANELÉ's precision wall (Section 2) doesn't apply.
3. **Hard decisions only.** MSE regression plus nearest-symbol decisions produce no soft information for the FEC, and there's no GMI/post-FEC metric.
4. **Static channel.** There is no drift study here. Their DSD 2024 follow-up ([arXiv 2407.02967](https://arxiv.org/abs/2407.02967)) retrains the full network with backprop on the FPGA, which is expensive.
5. **No public data and no code.** Power figures are estimates only.

### Reproduction (what you build yourself)
- **R1. Channel simulator (Python).**
  - **Transmit and fiber:** PAM2 (and later PAM4) → RRC → MZM sin transfer at quadrature → chromatic dispersion as the all-pass H(ω) = exp(jβ₂Lω²/2) → square-law photodiode with bandwidth limit.
  - **Receiver impairments:** thermal, shot and RIN noise → **ADC with a configurable ENOB** → N_os = 2.
  - **Sanity check:** the first CD power-fading null falls at f ≈ √(c / (2λ²DL)) ≈ **11 GHz**, inside the 20 GHz band. That's why linear FIR floors, so the simulator should show the same qualitative behaviour.
  - **Anchors:** calibrate noise to match the paper's FIR/CNN gap. Reproduce **Proakis-B exactly**, since it's fully specified, as a numerical anchor.
  - **Library:** OptiCommPy (open source) can speed this up.
- **R2. DSE:** the CNN template sweep (V_p, L, K, C), FIR and Volterra baselines, MACs per symbol from their formula, and a Pareto plot like their Fig. 2.
- **R3. Learned-bit-width QAT** with a QLF sweep, as in their Figs. 5–6.
- **R4. Hardware:** their low-power DOP architecture in Vitis HLS 2025.2 on your PYNQ (XC7Z020). Reproduce the resource/throughput-vs-DOP trend (their Fig. 8), measure on-board throughput (DDR → DMA → equalizer → DDR) and check that board BER matches the Python golden model.

### Improvements (pick I1 + I2 as the core; I3/I4 add depth)
- **I1. LUT-native, multiplier-free equalizer.**
  - **Model:** a KAN, or LUT-neuron network, whose **first-layer inputs are the raw ADC codes**. With a 4–8-bit ADC, each first-layer edge is an *exact* table of 16–256 entries. Later layers use QAT.
  - **Compile and compare:** use the KANELÉ flow (VHDL). Compare against the reproduced CNN at **iso-BER** on:
    - DSP/LUT/FF/BRAM;
    - **Fmax** (LUT designs typically close timing far above 200 MHz);
    - throughput per LUT and per watt;
    - instances needed for 40 GBd, extrapolated to the VU13P via out-of-context synthesis.
  - **Prior art:**
    - A KAN equalizer for 112 Gb/s PAM4 PON exists (KIT, OFC 2025, [arXiv 2411.19631](https://arxiv.org/abs/2411.19631)), but only as a complexity study with no hardware.
    - Freire et al. (JLT 2023) used LUTs only to approximate activation functions.
    - **I found no LUT-compiled, DSP-free NN equalizer.**
- **I2. ADC-resolution × equalizer co-design.**
  - **Sweep:** ADC ENOB from 3 to 8 bits. For each, find the best equalizer under a hardware budget.
  - **Power model:** add ADC power from the Walden FoM, P ≈ FoM·2^ENOB·f_s, using values from Murmann's ADC survey. Plot **total receiver power (ADC + equalizer) vs BER**.
  - **Hypothesis:** a nonlinear LUT equalizer lets you drop 1–2 ADC bits and save more ADC power than the equalizer costs. That's a system-level electronics result, not just an ML one.
  - **Novelty:** I didn't find this joint analysis for NN equalizers, but re-check before claiming it.
- **I3. Soft outputs for FEC.**
  - **Training:** replace MSE plus hard decision with bitwise BCE that outputs LLRs.
  - **Metrics:** report **GMI/AIR** and post-FEC BER with a free LDPC decoder (Sionna or AFF3CT, in software).
  - **Hardware cost:** only a few output bits.
  - **Novelty:** CE training is common, so this is depth, not the headline.
- **I4. Drift plus cheap adaptation.**
  - **Method:** freeze the feature layers and adapt **only the output layer** with decision-directed LMS (a handful of MACs in hardware).
  - **Drift scenarios:** fiber length ±2 km (CD change), received-power change, modulator-bias drift.
  - **Compare:** BER recovery and hardware cost against full on-FPGA retraining (Ney & Wehn, DSD 2024).

### Optional stretch, if you enjoy multi-tool work: "IM/DD on a breadboard"
- **The circuit (designed in Cadence):** an electrical analog of the optical channel at audio/sub-MHz rates.
  - **Dispersion:** a cascade of op-amp all-pass stages, which have frequency-dependent group delay.
  - **Square-law detection:** an analog multiplier such as an AD633 squaring the "field".
  - **Drive and capture:** PYNQ Pmod DAC/ADC or the audio codec.
- **What it gives you:** *real* analog impairments and a live poster demo with an on-board equalizer.
- **Risk:** extra; skip it if time is short.
- **No-breadboard fallback, about free:** loop the PYNQ-Z2's own audio jacks back with a 3.5 mm cable (headphone-out → line-in, through the ADAU1761 codec, controlled from PYNQ's audio API). Send PAM symbols near the codec's ~20 kHz band edge, and drive it close to clipping. You get *real* captured data with band-limiting ISI, AC-coupling baseline wander and amplifier nonlinearity. Check that your board revision has both jacks.
  - **Driver catch:** in PYNQ's stock driver, `play()` and `record()` are *blocking and sequential*, so you can't play and record at once out of the box. But `bypass()` already reads the input and writes the output in a single loop on the same I2S clock. That means a small custom C helper (a modified bypass that plays samples from a buffer while storing the input) gives **true full-duplex loopback with zero clock offset**.
  - **No-code fallback:** laptop headphone-out → PYNQ line-in (`record()` only, up to 60 s per call, 48 kHz, interleaved int32 L/R). This needs a preamble plus timing recovery, because the two clocks differ by tens of ppm. That's a real-receiver impairment, and the paper did timing recovery too.
  - **Signal design:** the sample rate is fixed at 48 kHz (changing it through the API doesn't reconfigure the codec).
    - Raise the PAM symbol rate (24 → 32 → 48 kBd) until the signal spills past the codec's ~21 kHz digital cutoff and a linear FIR starts to floor.
    - Sweep the volume from linear to clipping.
    - Use separate captures (not just segments) for train/val/test.
  - **Hybrid option:** digitally apply the fiber CD + square-law model *before* playback. You get simulated optics with real analog front-end impairments (band-limit, noise, clipping), which is a hardware-in-the-loop version of the optical channel.
  - **Framing:** treat it as a second *real* nonlinear ISI channel, like the paper's magnetic-recording channel, not as an optical emulation.

  Without either option the project is still sound: the hardware results (LUT/DSP/Fmax/throughput/BER on the board) are real measurements either way, and the channel is anchored to Proakis-B plus the public imdd-task simulator.

### Tools
Python/PyTorch (+ OptiCommPy); Brevitas or custom QAT; Vitis HLS + Vivado 2025.2 (already on D:); KANELÉ (MIT licence); PYNQ for on-board runs; Sionna/AFF3CT (free) for FEC; Cadence only for the optional breadboard channel. **No paid Vivado licence needed** for XC7Z020; Kria and small ZU+ parts are generally covered too.

### Rough timeline (if you do it yourself in about 4 weeks)
- **W1:** simulator, Proakis-B anchor, CNN/FIR/Volterra reproduction.
- **W2:** QAT and HLS CNN on PYNQ.
- **W3:** KAN-LUT (I1) and the ADC sweep (I2).
- **W4:** I3/I4 if time allows, poster and report.

## Sources (prior-art checks)
- Sensors 2025 ADC paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC12251562/
- ASU supervised ML TI-ADC (VTS 2025): https://asu.elsevierpure.com/en/publications/machine-learning-based-blind-digital-calibration-of-time-interlea/
- CICC 2025 circuits-informed ML ADC: https://arxiv.org/abs/2412.14051
- OpenDPDv2: https://arxiv.org/abs/2507.06849 · OpenDPD repo: https://github.com/lab-emi/OpenDPD
- DPD-KAN (A-RoF): https://arxiv.org/abs/2606.21178 · ETDKAN: https://arxiv.org/abs/2606.27042
- KANELÉ: https://arxiv.org/abs/2512.12850 · repo: https://github.com/Duchstf/KANELE
- KAN lookup FPGA (A*STAR): https://arxiv.org/abs/2508.17069 · ReducedLUT: https://arxiv.org/abs/2412.18579
- LUT-NN survey: https://arxiv.org/abs/2506.07367 · NeuraLUT-Assemble: https://arxiv.org/abs/2504.00592
- PPAAS: https://arxiv.org/abs/2507.17003 · GLOVA: https://arxiv.org/abs/2505.11208 · ZO-MC-SGD yield: https://arxiv.org/abs/2609.30678
- Extended STE for CIM: https://arxiv.org/abs/2508.11940 · IBM HWA training: https://arxiv.org/abs/2302.08469 · AIHWKit: https://arxiv.org/abs/2307.09357
- PINN-DAB: https://arxiv.org/abs/2502.17452 · Differentiable-physics buck estimation: https://arxiv.org/abs/2608.30915
- Conv. DLGN: https://arxiv.org/abs/2411.04732
- Section 11 checks: Ney et al. CNN equalizer: https://arxiv.org/abs/2405.02323 · Ney real-time demo: https://arxiv.org/abs/2402.15288 · trainable FPGA equalizer (DSD 2024): https://arxiv.org/abs/2407.02967 · KAN equalizer for PON: https://arxiv.org/abs/2411.19631 · Freire et al. JLT 2023 FPGA equalizers: https://research.aston.ac.uk/en/publications/implementing-neural-network-based-equalizers-in-a-coherent-optica · UCC 8-bit FPGA PON equalizer: https://research.ucc.ie/en/publications/low-complexity-fpga-accelerated-nn-based-adaptive-equalizer-for-1-2/ · SNN IM/DD equalizer: https://arxiv.org/abs/2205.04263
- Section 8 checks: NN DPD on FPGA (Tarver et al.): https://arxiv.org/abs/1907.00766 · PICO-RAM SRAM CIM: https://arxiv.org/abs/2407.12829 · peripheral-aware CIM training: https://arxiv.org/abs/2408.06390 · Verilog-A behavioral abstraction (Frankfurt): https://www.em.cs.uni-frankfurt.de/fileadmin/em_files/Paper/2019/paper.pdf
