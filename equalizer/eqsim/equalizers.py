"""Equalizers: linear FIR, Volterra (orders 1-3) and the Ney et al. CNN template.

All equalizers map received samples of shape (B, N*nos) to symbol estimates of
shape (B, N). Windows are centred on the symbol's sampling instant nos*n.
"""
from itertools import combinations_with_replacement

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def _windows(x: torch.Tensor, taps: int, nos: int) -> torch.Tensor:
    """Centred windows of `taps` samples at every symbol: (B, N*nos) -> (B, taps, N)."""
    pad = taps // 2
    xp = F.pad(x, (pad, pad))
    return xp.unfold(-1, taps, nos)[:, : x.shape[-1] // nos].transpose(1, 2)


class FIREqualizer(nn.Module):
    """Linear feed-forward equalizer with `taps` (odd) taps at nos samples/symbol."""

    def __init__(self, taps: int, nos: int = 2):
        super().__init__()
        self.taps, self.nos = taps, nos
        self.w = nn.Parameter(torch.zeros(taps))
        self.b = nn.Parameter(torch.zeros(()))
        with torch.no_grad():
            self.w[taps // 2] = 1.0

    def forward(self, x):
        return torch.einsum("btn,t->bn", _windows(x, self.taps, self.nos), self.w) + self.b

    def macs_per_symbol(self) -> float:
        return float(self.taps)


class VolterraEqualizer(nn.Module):
    """Third-order Volterra equalizer with memories (m1, m2, m3).

    Only the unique (symmetric) kernel terms are kept, e.g. m2*(m2+1)/2
    second-order weights; m2 = 0 or m3 = 0 disables that order.
    """

    def __init__(self, m1: int, m2: int = 0, m3: int = 0, nos: int = 2):
        super().__init__()
        self.m, self.nos = (m1, m2, m3), nos
        self.idx2 = torch.tensor(list(combinations_with_replacement(range(m2), 2)), dtype=torch.long).reshape(-1, 2)
        self.idx3 = torch.tensor(list(combinations_with_replacement(range(m3), 3)), dtype=torch.long).reshape(-1, 3)
        self.w1 = nn.Parameter(torch.zeros(m1))
        self.w2 = nn.Parameter(torch.zeros(len(self.idx2)))
        self.w3 = nn.Parameter(torch.zeros(len(self.idx3)))
        self.b = nn.Parameter(torch.zeros(()))
        with torch.no_grad():
            self.w1[m1 // 2] = 1.0

    def features(self, x: torch.Tensor) -> torch.Tensor:
        """Volterra regressors (B, P, N) in the order [w1, w2, w3]."""
        m1, m2, m3 = self.m
        feats = [_windows(x, m1, self.nos)]
        if m2:
            x2 = _windows(x, m2, self.nos)
            feats.append(x2[:, self.idx2[:, 0]] * x2[:, self.idx2[:, 1]])
        if m3:
            x3 = _windows(x, m3, self.nos)
            feats.append(x3[:, self.idx3[:, 0]] * x3[:, self.idx3[:, 1]] * x3[:, self.idx3[:, 2]])
        return torch.cat(feats, dim=1)

    def forward(self, x):
        w = torch.cat([self.w1, self.w2, self.w3])
        return torch.einsum("bpn,p->bn", self.features(x), w) + self.b

    def macs_per_symbol(self) -> float:
        # Weight MACs plus the multiplications that form the product terms.
        return float(self.w1.numel() + self.w2.numel() * 2 + self.w3.numel() * 3)


class NeyCNN(nn.Module):
    """CNN topology template of Ney et al. (Fig. 1).

    L Conv1D layers with kernel K: first stride Vp, middle stride 1, last
    stride nos with Vp output channels; BatchNorm + ReLU after all but the
    last. Each output position yields Vp consecutive symbols.
    """

    def __init__(self, layers: int = 3, kernel: int = 9, channels: int = 5, vp: int = 8, nos: int = 2):
        super().__init__()
        assert layers >= 2
        self.L, self.K, self.C, self.vp, self.nos = layers, kernel, channels, vp, nos
        pad = kernel // 2
        mods = [nn.Conv1d(1, channels, kernel, stride=vp, padding=pad), nn.BatchNorm1d(channels), nn.ReLU()]
        for _ in range(layers - 2):
            mods += [nn.Conv1d(channels, channels, kernel, stride=1, padding=pad), nn.BatchNorm1d(channels), nn.ReLU()]
        mods += [nn.Conv1d(channels, vp, kernel, stride=nos, padding=pad)]
        self.net = nn.Sequential(*mods)

    def forward(self, x):
        n_sym = x.shape[-1] // self.nos
        y = self.net(x.unsqueeze(1))  # (B, vp, T)
        return y.transpose(1, 2).reshape(x.shape[0], -1)[:, :n_sym]

    def macs_per_symbol(self) -> float:
        """Exact multiply-accumulates per output symbol."""
        K, C, vp, nos = self.K, self.C, self.vp, self.nos
        return K * C * nos / vp + (self.L - 2) * K * C * C * nos / vp + K * C

    def macs_paper_formula(self) -> float:
        """MAC_sym exactly as printed in Ney et al. Sec. 3.5."""
        K, C, vp, nos = self.K, self.C, self.vp, self.nos
        return K * C / vp + (self.L - 2) * K * C * C / vp + K * C / nos


def fit_linear_in_params_logistic(model: nn.Module, rx, idx, crop: int, max_iter: int = 200,
                                  weight_decay: float = 1e-4) -> None:
    """Refit FIR/Volterra weights by logistic regression (binary cross-entropy, PAM2).

    Starts from the LS solution. The model output is used as a logit, so the
    sign decision is unchanged, but the objective targets errors rather than
    amplitude: an MSE fit spends capacity pulling correct outputs to exactly
    +-1, which for nonlinear (Volterra) equalizers can raise the BER.
    `rx`/`idx` may be single arrays or lists of independent chunks. A small
    L2 penalty keeps the fit from chasing the few remaining errors when the
    BER is already low.
    """
    rx_list, idx_list = _as_chunks(rx, idx)
    fit_linear_in_params_ls(model, rx_list, [2.0 * i - 1.0 for i in idx_list], crop)
    xs = [torch.as_tensor(r, dtype=torch.float32).reshape(1, -1) for r in rx_list]
    target = torch.cat([torch.as_tensor(i[crop:-crop], dtype=torch.float32) for i in idx_list])
    with torch.no_grad():
        scale = 1.0 / torch.cat([model(x)[0, crop:-crop] for x in xs]).std()
        for p in model.parameters():
            p.mul_(4.0 * scale)  # start from a sensible logit scale
    opt = torch.optim.LBFGS(model.parameters(), max_iter=max_iter, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        logits = torch.cat([model(x)[0, crop:-crop] for x in xs])
        loss = F.binary_cross_entropy_with_logits(logits, target)
        loss = loss + weight_decay * sum((p ** 2).sum() for n, p in model.named_parameters() if n != "b")
        loss.backward()
        return loss

    opt.step(closure)


def _as_chunks(rx, sym):
    if isinstance(rx, (list, tuple)):
        return list(rx), list(sym)
    return [rx], [sym]


def fit_linear_in_params_ls(model: nn.Module, rx, sym, crop: int, ridge: float = 1e-6) -> None:
    """Closed-form least-squares fit for FIR/Volterra (both are linear in their weights).

    This gives the MSE-optimal weights, i.e. the strongest possible baseline
    for a given memory, instead of relying on Adam convergence. `rx`/`sym` may
    be lists of chunks; the normal equations are accumulated chunk by chunk so
    large Volterra models fit in memory.
    """
    rx_list, sym_list = _as_chunks(rx, sym)
    AtA = Atb = None
    with torch.no_grad():
        for r, s in zip(rx_list, sym_list):
            x = torch.as_tensor(r, dtype=torch.float64).reshape(1, -1)
            if isinstance(model, FIREqualizer):
                phi = _windows(x, model.taps, model.nos)[0]
            else:
                phi = model.double().features(x)[0]
                model.float()
            phi = phi[:, crop:-crop].T.numpy()
            A = np.hstack([phi, np.ones((len(phi), 1))])
            AtA = A.T @ A if AtA is None else AtA + A.T @ A
            Atb = A.T @ s[crop:-crop] if Atb is None else Atb + A.T @ s[crop:-crop]
        w = np.linalg.solve(AtA + ridge * np.eye(AtA.shape[0]), Atb)
        if isinstance(model, FIREqualizer):
            model.w.copy_(torch.as_tensor(w[:-1]))
        else:
            n1, n2 = model.w1.numel(), model.w2.numel()
            model.w1.copy_(torch.as_tensor(w[:n1]))
            model.w2.copy_(torch.as_tensor(w[n1:n1 + n2]))
            model.w3.copy_(torch.as_tensor(w[n1 + n2:-1]))
        model.b.copy_(torch.as_tensor(w[-1]))
