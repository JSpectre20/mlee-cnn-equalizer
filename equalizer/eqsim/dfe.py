"""Decision-feedback equalisation for PAM2 (symbols s = 2*idx - 1).

  FFE+DFE  linear FIR at nos samples/symbol plus B feedback taps on past decisions, fitted in
           closed form (LS with the true past symbols, the usual way a DFE is trained).
  CNN+DFE  the Ney et al. CNN followed by B feedback taps: z[n] = cnn(x)[n] + sum_k fb[k] * d[n-1-k].
           Trained with teacher forcing (true past symbols) and cross-entropy; the feedback is
           linear in +-1 decisions, so in hardware it is +-fb[k] (adders only, no multipliers).

Evaluation always feeds back the equalizer's own decisions (error propagation included); each
chunk starts from known symbols for its first `crop` symbols (a training preamble).
"""
import numpy as np
import torch
import torch.nn as nn
from numpy.lib.stride_tricks import as_strided

from .equalizers import NeyCNN


def windows(rx: np.ndarray, taps: int, nos: int = 2) -> np.ndarray:
    """(N, taps) centred windows at every symbol, as a strided view (no copy)."""
    pad = taps // 2
    xp = np.pad(rx.astype(np.float64), (pad, pad + nos))
    n_sym = len(rx) // nos
    return as_strided(xp, shape=(n_sym, taps), strides=(xp.strides[0] * nos, xp.strides[0]))


def fit_ffe_dfe(ds, taps: int, n_fb: int, crop: int = 64, step: int = 50_000) -> np.ndarray:
    """LS weights for [window, 1, s[n-1] .. s[n-n_fb]] -> s[n] over all chunks of `ds`."""
    d = taps + 1 + n_fb
    A, b = np.zeros((d, d)), np.zeros(d)
    for rx, idx in zip(ds.rx, ds.idx):
        s = 2.0 * idx - 1.0
        W = windows(rx, taps, ds.nos)
        for a in range(crop, len(s) - crop, step):
            e = min(a + step, len(s) - crop)
            n = np.arange(a, e)
            X = np.empty((e - a, d))
            X[:, :taps] = W[a:e]
            X[:, taps] = 1.0
            for k in range(1, n_fb + 1):
                X[:, taps + k] = s[n - k]
            A += X.T @ X
            b += X.T @ s[n]
    return np.linalg.solve(A + 1e-6 * np.eye(d), b)


def dfe_decide(y: np.ndarray, fb: np.ndarray, s_known: np.ndarray, crop: int) -> np.ndarray:
    """Sequential decisions d[n] = sign(y[n] + sum_k fb[k] d[n-1-k]); d[:crop] = s_known[:crop]."""
    d = np.zeros(len(y))
    d[:crop] = s_known[:crop]
    fb = [float(v) for v in fb]
    for n in range(crop, len(y)):
        v = y[n]
        for k, c in enumerate(fb):
            v += c * d[n - 1 - k]
        d[n] = 1.0 if v > 0 else -1.0
    return d


def ber_ffe_dfe(ds, w: np.ndarray, taps: int, n_fb: int, crop: int = 64):
    errs = tot = 0
    for rx, idx in zip(ds.rx, ds.idx):
        y = windows(rx, taps, ds.nos) @ w[:taps] + w[taps]
        s = 2.0 * idx - 1.0
        d = dfe_decide(y, w[taps + 1:], s, crop) if n_fb else np.where(y > 0, 1.0, -1.0)
        errs += int(np.sum(d[crop:-crop] != s[crop:-crop]))
        tot += len(s) - 2 * crop
    return errs / tot, tot


class CNNDFE(nn.Module):
    """NeyCNN + n_fb linear decision-feedback taps on its output (logit scale)."""

    def __init__(self, n_fb: int = 2, **cnn_cfg):
        super().__init__()
        self.cnn = NeyCNN(**cnn_cfg)
        self.n_fb = n_fb
        self.fb = nn.Parameter(torch.zeros(n_fb))

    def forward(self, x, s_true=None):
        """x: (B, N*nos). With s_true (B, N, +-1) adds the feedback with true past symbols."""
        y = self.cnn(x)
        if s_true is not None:
            for k in range(self.n_fb):
                y = y + self.fb[k] * torch.nn.functional.pad(s_true, (k + 1, 0))[:, : y.shape[1]]
        return y

    def macs_per_symbol(self) -> float:
        return self.cnn.macs_per_symbol()   # feedback = n_fb additions of +-fb


def train_cnn_dfe(model: CNNDFE, ds, iters: int = 10_000, batch: int = 32, n_sym: int = 512,
                  lr: float = 1e-3, crop: int = 32, seed: int = 0):
    """Adam + BCE with teacher forcing (true past symbols in the feedback)."""
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()
    for _ in range(iters):
        rx, idx = zip(*(ds(n_sym, rng) for _ in range(batch)))
        rx = torch.from_numpy(np.stack(rx).astype(np.float32))
        idx = torch.from_numpy(np.stack(idx).astype(np.int64))
        y = model(rx, 2.0 * idx.float() - 1.0)[:, crop:-crop]
        loss = nn.functional.binary_cross_entropy_with_logits(y, idx[:, crop:-crop].float())
        opt.zero_grad()
        loss.backward()
        opt.step()


@torch.no_grad()
def ber_cnn_dfe(model: CNNDFE, ds, crop: int = 64):
    """BER with the model's own decisions fed back."""
    model.eval()
    fb = model.fb.detach().numpy()
    errs = tot = 0
    for rx, idx in zip(ds.rx, ds.idx):
        y = model.cnn(torch.from_numpy(rx.astype(np.float32))[None])[0].numpy().astype(np.float64)
        s = 2.0 * idx - 1.0
        d = dfe_decide(y, fb, s, crop)
        errs += int(np.sum(d[crop:-crop] != s[crop:-crop]))
        tot += len(s) - 2 * crop
    return errs / tot, tot
