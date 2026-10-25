"""Quantization-aware training and the integer golden model for the NeyCNN equalizer.

Integer arithmetic (this is the contract the RTL implements, see rtl/WEIGHT_FORMAT.md):

  input       x_q  = clamp(round_half_up(rx / s_in), -2^(Bin-1)+1, 2^(Bin-1)-1)       signed Bin bits
  layer l     acc  = sum_{ic,k} W_q[oc,ic,k] * a_pad[ic, p*stride + k]                 exact integer
              (a_pad = input zero-padded by K//2 on both ends, as torch Conv1d)
  hidden      a'   = clamp(((acc + bias_q[oc]) * M[oc] + 2^(S[oc]-1)) >>> S[oc], 0, 2^Ba - 1)
              (ReLU and requantization in one step; >>> is an arithmetic right shift)
  last layer  z    = acc + bias_q[oc]; decision bit = (z > 0); soft output = z

Weights are symmetric per output channel, W_q in [-(2^(Bw-1)-1), 2^(Bw-1)-1].
BatchNorm is folded into the preceding convolution before quantization.
"""
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .equalizers import NeyCNN

M_BITS = 16  # unsigned requant multiplier width (same as the U-Net engine)
S_MAX = 40


def round_half_up(x: torch.Tensor) -> torch.Tensor:
    return torch.floor(x + 0.5)


def _round_ste(x):
    return (round_half_up(x) - x).detach() + x


def _grad_scale(s, g):
    return (s - s * g).detach() + s * g


class LSQ(nn.Module):
    """Learned-step-size fake quantizer (Esser et al., ICLR 2020) with round-half-up."""

    def __init__(self, bits: int, signed: bool, channels: int | None = None):
        super().__init__()
        self.bits, self.signed = bits, signed
        self.qn = -(2 ** (bits - 1) - 1) if signed else 0
        self.qp = 2 ** (bits - 1) - 1 if signed else 2 ** bits - 1
        shape = (channels, 1, 1) if channels else ()
        self.log_s = nn.Parameter(torch.zeros(shape))

    @property
    def s(self):
        return self.log_s.exp()

    def init_from(self, x: torch.Tensor, percentile: float | None = None):
        with torch.no_grad():
            if self.log_s.dim():  # per-channel weights: max-abs
                m = x.abs().amax(dim=tuple(range(1, x.dim()))).clamp_min(1e-8)
                self.log_s.copy_(torch.log(m / self.qp).reshape(self.log_s.shape))
            else:
                v = x.abs().flatten() if self.signed else x.clamp_min(0).flatten()
                m = torch.quantile(v[:: max(1, len(v) // 200_000)], percentile).clamp_min(1e-8)
                self.log_s.copy_(torch.log(m / self.qp))

    def forward(self, x):
        g = 1.0 / np.sqrt(max(1, x.numel() // max(1, self.log_s.numel())) * self.qp)
        s = _grad_scale(self.s, g)
        return _round_ste(torch.clamp(x / s, self.qn, self.qp)) * s

    def to_int(self, x):
        return torch.clamp(round_half_up(x / self.s), self.qn, self.qp)


def fold_bn(conv: nn.Conv1d, bn: nn.BatchNorm1d):
    inv = bn.weight / torch.sqrt(bn.running_var + bn.eps)
    w = conv.weight * inv[:, None, None]
    b = (conv.bias - bn.running_mean) * inv + bn.bias
    return w.detach().clone(), b.detach().clone()


class QuantNeyCNN(nn.Module):
    """BN-folded NeyCNN with fake-quantized input, weights, biases and activations."""

    def __init__(self, fp: NeyCNN, w_bits: int = 8, a_bits: int = 8, in_bits: int = 8):
        super().__init__()
        self.L, self.K, self.C, self.vp, self.nos = fp.L, fp.K, fp.C, fp.vp, fp.nos
        self.w_bits, self.a_bits, self.in_bits = w_bits, a_bits, in_bits
        convs = [m for m in fp.net if isinstance(m, nn.Conv1d)]
        bns = [m for m in fp.net if isinstance(m, nn.BatchNorm1d)]
        self.strides = [c.stride[0] for c in convs]
        self.pad = self.K // 2
        ws, bs = [], []
        for i, c in enumerate(convs):
            w, b = fold_bn(c, bns[i]) if i < len(bns) else (c.weight.detach().clone(), c.bias.detach().clone())
            ws.append(nn.Parameter(w))
            bs.append(nn.Parameter(b))
        self.weights, self.biases = nn.ParameterList(ws), nn.ParameterList(bs)
        self.in_q = LSQ(in_bits, signed=True)
        self.w_q = nn.ModuleList([LSQ(w_bits, signed=True, channels=w.shape[0]) for w in ws])
        self.a_q = nn.ModuleList([LSQ(a_bits, signed=False) for _ in ws[:-1]])

    def calibrate(self, x: torch.Tensor):
        """Initialise all step sizes from a float forward pass on `x` (B, N*nos)."""
        with torch.no_grad():
            self.in_q.init_from(x, percentile=0.9999)
            for wq, w in zip(self.w_q, self.weights):
                wq.init_from(w)
            a = x.unsqueeze(1)
            for i, (w, b) in enumerate(zip(self.weights, self.biases)):
                a = F.conv1d(a, w, b, stride=self.strides[i], padding=self.pad)
                if i < len(self.a_q):
                    a = F.relu(a)
                    self.a_q[i].init_from(a, percentile=0.999)

    def _bias_hat(self, i, s_in_act):
        step = (s_in_act * self.w_q[i].s.reshape(-1))
        return _round_ste(self.biases[i] / step) * step

    def forward(self, x):
        n_sym = x.shape[-1] // self.nos
        a = self.in_q(x).unsqueeze(1)
        s_act = self.in_q.s
        for i, w in enumerate(self.weights):
            a = F.conv1d(a, self.w_q[i](w), self._bias_hat(i, s_act), stride=self.strides[i], padding=self.pad)
            if i < len(self.a_q):
                a = self.a_q[i](F.relu(a))
                s_act = self.a_q[i].s
        return a.transpose(1, 2).reshape(x.shape[0], -1)[:, :n_sym]

    def forward_float(self, x):
        """BN-folded model without any quantization (for checking the fold)."""
        n_sym = x.shape[-1] // self.nos
        a = x.unsqueeze(1)
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            a = F.conv1d(a, w, b, stride=self.strides[i], padding=self.pad)
            if i < len(self.weights) - 1:
                a = F.relu(a)
        return a.transpose(1, 2).reshape(x.shape[0], -1)[:, :n_sym]

    def macs_per_symbol(self) -> float:
        K, C, vp, nos = self.K, self.C, self.vp, self.nos
        return K * C * nos / vp + (self.L - 2) * K * C * C * nos / vp + K * C


def _requant_params(r: np.ndarray):
    """Per-channel (M, S) with M < 2^M_BITS and M / 2^S ~= r (maximal S for precision)."""
    S = np.clip(np.floor(np.log2((2 ** M_BITS - 1) / r)), 1, S_MAX).astype(np.int64)
    M = np.round(r * 2.0 ** S).astype(np.int64)
    assert np.all(M < 2 ** M_BITS) and np.all(M > 0), (M, S, r)
    return M, S


@dataclass
class IntegerModel:
    """Everything the RTL needs; produced by export_integer()."""
    vp: int
    nos: int
    K: int
    strides: list
    in_bits: int
    w_bits: int
    a_bits: int
    s_in: float
    W: list          # per layer int64 (oc, ic, K)
    bias: list       # per layer int64 (oc,)
    M: list          # per hidden layer int64 (oc,)
    S: list          # per hidden layer int64 (oc,)
    out_scale: np.ndarray  # (vp,) real value of one LSB of z for output channel v (symbol n uses v = n % vp)

    def dequantize_output(self, z: np.ndarray) -> np.ndarray:
        return z * self.out_scale[np.arange(len(z)) % self.vp]

    def quantize_input(self, rx: np.ndarray) -> np.ndarray:
        q = np.floor(rx / self.s_in + 0.5)
        lim = 2 ** (self.in_bits - 1) - 1
        return np.clip(q, -lim, lim).astype(np.int64)

    def forward_int(self, x_int: np.ndarray, return_acc: bool = False):
        """Integer inference on one frame of input codes (N*nos,). Returns (bits, z[, accs])."""
        n_sym = len(x_int) // self.nos
        a = x_int[None, :].astype(np.int64)
        pad = self.K // 2
        qa = 2 ** self.a_bits - 1
        accs = []
        for i, (W, b) in enumerate(zip(self.W, self.bias)):
            ap = np.pad(a, ((0, 0), (pad, pad)))
            n_out = (ap.shape[1] - self.K) // self.strides[i] + 1
            idx = np.arange(n_out)[:, None] * self.strides[i] + np.arange(self.K)[None, :]
            win = ap[:, idx]  # (ic, n_out, K)
            acc = np.einsum("oik,ipk->op", W, win) + b[:, None]
            accs.append(acc)
            if i < len(self.M):
                M, S = self.M[i][:, None], self.S[i][:, None]
                a = np.clip((acc * M + (1 << (S - 1))) >> S, 0, qa)
            else:
                z = acc.T.reshape(-1)[:n_sym]
        bits = (z > 0).astype(np.int64)
        return (bits, z, accs) if return_acc else (bits, z)

    def acc_bits_needed(self, x_int_frames) -> list:
        """Signed accumulator width (incl. bias) needed per layer, measured on data."""
        m = [0] * len(self.W)
        for x in x_int_frames:
            _, _, accs = self.forward_int(x, return_acc=True)
            m = [max(mi, int(np.abs(a).max())) for mi, a in zip(m, accs)]
        return [int(np.ceil(np.log2(v + 1))) + 1 for v in m]


def export_integer(q: QuantNeyCNN) -> IntegerModel:
    with torch.no_grad():
        Ws, bs, Ms, Ss = [], [], [], []
        s_act = q.in_q.s.item()
        for i, w in enumerate(q.weights):
            s_w = q.w_q[i].s.reshape(-1).double().numpy()
            Ws.append(q.w_q[i].to_int(w).long().numpy().astype(np.int64))
            bs.append(np.floor(q.biases[i].double().numpy() / (s_act * s_w) + 0.5).astype(np.int64))
            if i < len(q.a_q):
                s_out = q.a_q[i].s.item()
                M, S = _requant_params(s_act * s_w / s_out)
                Ms.append(M)
                Ss.append(S)
                s_act = s_out
            else:
                out_scale = s_act * s_w
    return IntegerModel(q.vp, q.nos, q.K, q.strides, q.in_bits, q.w_bits, q.a_bits, q.in_q.s.item(), Ws, bs, Ms, Ss, out_scale)


def integer_ber(im: IntegerModel, ds, crop: int = 64):
    """BER of the integer model over a DatasetChannel (each chunk processed as one frame)."""
    errs = total = 0
    for rx, idx in zip(ds.rx, ds.idx):
        bits, _ = im.forward_int(im.quantize_input(rx.astype(np.float64)))
        errs += int(np.sum(bits[crop:-crop] != idx[crop:-crop]))
        total += len(idx) - 2 * crop
    return errs / total, total
