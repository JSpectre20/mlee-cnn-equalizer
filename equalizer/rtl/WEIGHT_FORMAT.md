# CNN equalizer: parameter memory and stream format

The single source of truth for the contract between `scripts/export_rtl.py` (writer), `eqsim/quant.py` (integer golden model) and the RTL (`rtl/src/`). If any side changes, this file changes first.

## Network shape (synthesis-time parameters, package `cnn_eq_pkg` in `rtl/gen/<model>/cnn_eq_pkg.sv`)
Ney et al. topology: `L` Conv1D layers, kernel `K` (odd), zero padding `PAD = K/2` on both ends of each frame.

| layer l | IC | OC | stride | input | output |
|---|---|---|---|---|---|
| 0 | 1 | C | VP | signed `B_IN`-bit sample codes | unsigned `B_A`-bit activations |
| 1 … L-2 | C | C | 1 | activations | activations |
| L-1 | C | VP | NOS | activations | signed accumulator `z` (ACC_W bits) |

Output position `p` of the last layer yields `VP` consecutive symbols `p*VP + v`, with v = output channel.

## Arithmetic (exactly `IntegerModel.forward_int`)
```
acc[oc] = sum_{ic,k} W[oc][ic][k] * a_pad[ic][p*stride + k]      (a_pad: frame zero-padded by PAD)
hidden: a'[oc] = clamp( ((acc[oc] + bias[oc]) * M[oc] + 2^(S[oc]-1)) >>> S[oc], 0, 2^B_A - 1 )
last:   z[oc]  = acc[oc] + bias[oc]        decision bit = (z > 0)
```
- Weights are signed `B_W`-bit, symmetric: |W| ≤ 2^(B_W-1) - 1.
- `bias` is signed and fits in `ACC_W` bits.
- `M` is unsigned 16-bit, 1 ≤ M < 2^16.
- `S` is in 1..40.
- `>>>` is an arithmetic shift, so the floor of a negative value stays negative and clamps to 0.
- The converter checks the worst-case |acc + bias| < 2^(ACC_W-1) for every layer, so no overflow is possible.

## Parameter memory (AXI-Lite, write-only words)
Word `i` lives at byte address `0x4000 + 4*i`. Each word holds one value in its low bits (two's complement for signed fields). Layers are stored in order l = 0 … L-1. Within each layer:

| block | count | order | width used |
|---|---|---|---|
| weights | OC·IC·K | `((oc*IC + ic)*K + k)` | B_W |
| bias | OC | oc | ACC_W |
| M (hidden layers only) | OC | oc | 16 |
| S (hidden layers only) | OC | oc | 6 |

The per-layer offsets `W_OFF[l]`, `B_OFF[l]`, `M_OFF[l]` and `S_OFF[l]` and the total `N_PARAM` are emitted into `cnn_eq_pkg.sv`. `params.mem` holds the full image (one 32-bit hex word per line).

## Control / status registers (AXI-Lite)
| addr | name | access | meaning |
|---|---|---|---|
| 0x0000 | ID | R | 0x4E455131 ("NEQ1") |
| 0x0004 | SHAPE | R | {L[7:0], K[7:0], C[7:0], VP[7:0]} |
| 0x0008 | NPARAM | R | N_PARAM |
| 0x000C | CTRL | R/W | bit0 = datapath soft reset (params kept) |
| 0x0010 | FRAMES | R | frames completed (output TLAST count) |
| 0x0014 | BUSY_CYC | R | cycles with any frame in flight |
| 0x0018 | IN_BEATS | R | input samples accepted |
| 0x001C | OUT_BEATS | R | output symbols produced |

## Streams
- **Input (AXI-Stream slave):** one received sample per beat in `tdata[B_IN-1:0]` (two's complement, i.e. the quantized ADC code `x_q`). `tlast` is set on the last sample of a frame. Frame length must be `n_sym * NOS` samples with `n_sym` a multiple of `VP`. Every frame is processed independently with zero padding (identical to running the golden model on that frame).
- **Output (AXI-Stream master):** one symbol per beat, `tdata[15:0]` = `z` saturated to signed 16 bits (decision bit = `tdata > 0`). `tlast` is set on the last symbol of the frame. A frame of `n_sym` symbols in gives exactly `n_sym` symbols out.
