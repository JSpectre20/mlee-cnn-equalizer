# Low-Complexity Neural Network Equalization for Optical Fibre Communication on FPGA

MLEE (EEE G513) course project. It reproduces and extends Ney et al., *"CNN-Based Equalization for Communications: Achieving Gigabit Throughput with a Flexible FPGA Hardware Architecture"* ([arXiv:2405.02323](https://arxiv.org/abs/2405.02323)). The paper releases no code and no data, so everything here is built from the paper's description.

## Layout

```
eqsim/            simulator + models (importable package)
  pulses.py       raised-cosine / root-raised-cosine filters
  channels.py     ProakisBChannel (paper Sec. 2.2), IMDDChannel (physics model of Sec. 2.1)
  equalizers.py   FIR, Volterra (orders 1-3), NeyCNN template (Fig. 1), closed-form LS fitting
  metrics.py      PAM decisions, Gray-coded BER, confidence interval
  train.py        Adam/MSE training on fresh data, BER evaluation
scripts/
  run_proakis.py      reproduce Fig. 4 (Proakis-B, 20 dB)
  run_imdd_sanity.py  power-fading check, eye diagrams, FIR error floor
tests/            unit tests (pytest)
results/          generated figures and JSON (not hand-edited)
```

## Setup

```bash
python -m venv D:/venvs/mlee-eq
D:/venvs/mlee-eq/Scripts/python -m pip install numpy scipy matplotlib pytest
D:/venvs/mlee-eq/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Run everything from this folder with `PYTHONPATH` set to it:

```bash
D:/venvs/mlee-eq/Scripts/python -m pytest -q
D:/venvs/mlee-eq/Scripts/python scripts/run_imdd_sanity.py
D:/venvs/mlee-eq/Scripts/python scripts/run_proakis.py --iters 10000 --seeds 3
```

## Modeling choices (things the paper does not specify)

| Item | Paper | Here |
|---|---|---|
| Proakis-B pulse | "raised-cosine", roll-off not given | RC, β = 0.25 |
| Proakis-B SNR definition | "20 dB" | per-sample signal power / noise variance at N_os = 2 |
| Proakis-B channel spacing | h = [0.407, 0.815, 0.407] | symbol-spaced taps |
| IM/DD data | lab measurements (not public) | physics simulator: RRC β = 0.2, zero-chirp MZM at quadrature (m = 0.8), 31.5 km SSMF with D = 16 ps/nm/km at 1550 nm, square-law PD with a 4th-order Bessel 40 GHz response, in-band thermal noise, AC coupling, optional ADC |
| FIR / Volterra training | Adam + MSE | closed-form least squares (MSE-optimal, i.e. the strongest baseline for a given memory) |

## Results so far

### IM/DD simulator sanity (`results/imdd_sanity/`)
- **Power fading:** the simulated small-signal response matches theory, |cos(β₂Lω²/2)|, with the first null at **11.1 GHz** and the second at 19.3 GHz, both inside the 20 GHz signal band (`power_fading.png`). This is enforced by a unit test.
- **Eye:** open back-to-back, fully closed after 31.5 km (`eyes.png`).
- **Linear FIR error floor:** with LS-optimal taps, BER saturates as SNR increases. At 40 dB, FIR-17 gives 2.1e-2, FIR-57 gives 6.7e-4 and FIR-121 gives 4.1e-4. That's the nonlinear CD × square-law impairment, which a linear equalizer can't remove. It matches the paper's qualitative picture (FIR floor near 1e-4 with up to 1017 taps).

### Proakis-B reproduction (`results/proakis/`, `ber_vs_macs.png`)
SNR 20 dB, 10⁶ test symbols per point, independent test seed. FIR/Volterra are fitted in closed form; the CNN is the paper's selected model (L=3, K=9, C=5, V_p=8), trained with Adam for 10k iterations.

| Equalizer | MAC/sym | BER | Paper |
|---|---|---|---|
| FIR 57 taps, MSE fit | 57 | 8.96e-3 | 9.6e-3 (FIR at similar complexity) |
| CNN, MSE (paper recipe), 6 runs over 2 sessions | 112.5 | 6.4e-3 – 1.26e-2 (best of 3: 6.4e-3 and 8.4e-3) | **8.4e-3** |
| CNN, BCE, 3 runs | 112.5 | 5.8e-3 – 9.3e-3 | – |
| Volterra (9,3,3), MSE / cross-entropy fit | 51 | 2.54e-2 / **8.7e-3** | – |
| Volterra (13,5,3), MSE / CE | 73 | 2.16e-2 / **5.7e-3** | – |
| Volterra (15,5,5), MSE / CE | 150 | 2.16e-2 / **3.2e-3** | – |
| Volterra (25,9,9), MSE / CE | 610 | 1.02e-2 / **8.3e-4** | – |
| MLSE (4-state Viterbi, reference) | – | **0 errors in 9.9×10⁵ symbols** | – |

**Takeaways**
1. **The reproduction holds.** The paper's CNN and FIR numbers fall inside our run-to-run spread.
2. **The training objective matters more than the architecture.** Fitted by MSE (the paper's recipe), Volterra is *worse* than FIR at the same linear memory: the cubic terms lower the MSE but raise the BER, because MSE rewards pushing correct outputs to exactly ±1. Fitted by cross-entropy, Volterra improves by 3–12×. It matches the CNN at 73 MAC/sym (vs 112.5) and beats it at 150. The paper's "CNN > Volterra" conclusion therefore appears to depend on MSE training.
3. **For the CNN, cross-entropy also helps, but it takes more than 3 seeds to show it.** A 10-seed study (`seeds.json`, `seeds.png`) gives:
   - MSE: median 1.13e-2, range 6.7e-3 – 1.42e-2. The **expected best-of-3 is 8.5e-3, matching the paper's 8.4e-3.**
   - BCE: median **6.7e-3**, range 4.6e-3 – 9.4e-3 plus one diverged run at 3.8e-2; expected best-of-3 5.2e-3.
   - BCE < MSE with one-sided Mann-Whitney p = 0.011, i.e. about 1.7× lower BER at the median.

   With 3 seeds (the earlier run) the ranges overlapped, which is why this was first reported as "within noise".
4. **The 20 dB operating point is far from optimal.** MLSE is error-free there, and already reaches 1.6e-3 at 12 dB, i.e. better than the CNN at about 8 dB less SNR. Proakis-B (a known, linear ISI channel) is a weak showcase for a CNN.

_Note: in the table's CNN runs the weight initialisation wasn't seeded (only the data was). The 10-seed study above seeds both and is the reference result._

### IM/DD design-space exploration (`results/imdd_dse/`, `dse.png`)
Simulated 40 GBd PAM2, 31.5 km SSMF, electrical SNR 24 dB. Fixed 2M-symbol train and test sets. All 135 CNN configs of the paper's grid were trained with **both MSE (paper) and binary cross-entropy**, 10k Adam iterations each. Pareto-front configs got 3 seeds. FIR/Volterra were fitted in closed form (LS) and by logistic regression. The paper's 40 GBd budget on the XCVU13P (its formula: 73.7 "MAC_sym") equals **147 MACs per symbol** in exact units.

**Confirmation on a fresh 4M-symbol test set** (`confirm.jsonl`), so configs weren't selected on the reported data. Each cell is best / median of 3 seeds:

| Model | MAC/sym | MSE (paper recipe) | Cross-entropy |
|---|---|---|---|
| FIR 57 | 57 | 8.3e-4 | 7.8e-4 |
| FIR 121 | 121 | 4.5e-4 | 3.8e-4 |
| Paper's CNN (V_p=8, L=3, K=9, C=5) | 112.5 | 4.4e-4 / 5.7e-4 | 4.5e-4 / 5.1e-4 |
| Best in-budget CNN for MSE (V_p=4, L=3, K=15, C=3) | 135 | 1.3e-4 / 1.9e-4 | 1.2e-4 / 1.7e-4 |
| Best in-budget CNN for CE (V_p=4, L=4, K=9, C=3) | 121.5 | 9.4e-4 / 1.3e-3 | **2.7e-5 / 4.2e-5** |
| Best Volterra within budget (13,5,3) | 73 | 4.2e-2 | 3.9e-2 |

**Takeaways**
1. **The paper's central claim reproduces, though with a different config.** Within its hardware budget, a CNN beats FIR by about 3.5× (MSE), close to the paper's "about 4×". The paper's *selected* topology only ties FIR on our simulated link. This is plausibly a channel difference (simulated vs. their lab capture), so the config choice shouldn't be read as an error in the paper.
2. **Cross-entropy is a free, real improvement at equal hardware cost.** The best in-budget CE CNN reaches **2.7e-5**: about 14× below FIR-121, about 16× below the paper's CNN, and about 5× below the best MSE CNN in budget. It costs nothing at inference: the same network and the same sign decision.
3. **Why:** deeper nets are hard to train with MSE. The 4-layer config is the worst of the three under MSE and the best under CE (about 30× gap at the median). For the paper's own 3-layer config the loss barely matters.
4. **Volterra can't compete within the budget.** It needs 1000+ MACs (CE fit: 5.5e-5 at 1200 MACs). That's consistent with the paper's finding, and CE again helps Volterra by about 3×.
5. **The nonlinearity is learnable.** Several larger CNNs (400–2400 MACs) make zero errors in 2M bits (BER < about 1.5e-6), so the remaining gap is a *cost* problem, which is what the hardware-side improvements target.
6. **Seed variance is still large** (e.g. 2.7e-5 vs 2.6e-4 across seeds for the best CE config). A learning-rate schedule and ensembling are a sensible next ML fix.

Saved weights for these configs are in `results/imdd_dse/models/`. A **frozen, read-only copy** of all FP32 models plus the exact datasets is in `checkpoints/fp32_v1/`, with `MANIFEST.json` listing config, loss, seed, fresh-test BER and SHA-256 for every file (created by `scripts/freeze_checkpoints.py`, which refuses to overwrite an existing tag). Quantization and hardware export load from there and write new files elsewhere. A check that the best model reloads from the frozen copy and gives 2.702e-5 again passed.

## Observations about the paper
- **MAC formula:** the printed MAC_sym formula (Sec. 3.5) gives 56.25 for the selected CNN (L=3, K=9, C=5, V_p=8). Counting the convolutions exactly gives **112.5 MACs per output symbol**, which is N_os = 2 times more. The printed formula seems to count per *input sample*. If FIR taps are counted per symbol, that makes the CNN look 2× cheaper in Fig. 2/4. Both counts are reported here.

- **Training objective:** with MSE training, nonlinear equalizers are handicapped (finding 2 above); the paper's MSE + hard-decision recipe is applied to every model.
- **No optimal reference:** there is no MLSE / optimal-detector baseline for the Proakis-B channel.

## Next steps
1. ~~IM/DD design-space exploration with MSE vs cross-entropy~~ (done, above).
2. ~~Quantization (QAT) of the paper's CNN and the best CE CNN~~ (done; `PROGRESS.md` §5.4).
3. Hand-written SystemVerilog engine (decided over HLS; see `rtl/README.md` and `PROGRESS.md` §5.5-5.6), then the PYNQ-Z2 block design and on-board BER/throughput.
4. Improvements: LUT-native KAN equalizer on raw ADC codes (I1), ADC-ENOB × equalizer power co-design (I2).
5. Real-channel capture: PYNQ-Z2 audio loopback and/or a lab fiber-optic trainer kit.
