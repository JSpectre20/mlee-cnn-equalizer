"""Training and BER evaluation loops (fresh channel data every batch)."""
import numpy as np
import torch
import torch.nn as nn

from .metrics import ber, pam_levels


def make_batch(channel, batch: int, n_sym: int, rng: np.random.Generator):
    """Stack `batch` independent channel realizations of `n_sym` symbols each."""
    rx, idx = zip(*(channel(n_sym, rng) for _ in range(batch)))
    return np.stack(rx).astype(np.float32), np.stack(idx)


def train_sgd(model: nn.Module, channel, iters: int = 10_000, batch: int = 32, n_sym: int = 512,
              lr: float = 1e-3, crop: int = 32, seed: int = 0, log_every: int = 0, loss_type: str = "mse"):
    """Train with Adam on freshly generated data.

    loss_type="mse" is the Ney et al. recipe (Sec. 3.4): regress the PAM level,
    then hard-decide. loss_type="bce" (PAM2 only) treats the output as a logit
    for the bit, so training targets the decision rather than the amplitude; the
    sign decision used at test time is unchanged.
    """
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    levels = torch.tensor(pam_levels(channel.order), dtype=torch.float32)
    if loss_type == "bce" and channel.order != 2:
        raise ValueError("bce loss is implemented for PAM2 only")
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    history = []
    model.train()
    for it in range(1, iters + 1):
        rx, idx = make_batch(channel, batch, n_sym, rng)
        y = model(torch.from_numpy(rx))[:, crop:-crop]
        idx_t = torch.from_numpy(idx[:, crop:-crop])
        if loss_type == "bce":
            loss = nn.functional.binary_cross_entropy_with_logits(y, idx_t.float())
        else:
            loss = nn.functional.mse_loss(y, levels[idx_t])
        opt.zero_grad()
        loss.backward()
        opt.step()
        if log_every and it % log_every == 0:
            history.append((it, loss.item()))
    return history


@torch.no_grad()
def evaluate_ber(model: nn.Module, channel, n_symbols: int = 1_000_000, n_sym: int = 8192,
                 crop: int = 32, seed: int = 12345):
    """BER over `n_symbols` test symbols drawn with an independent seed."""
    rng = np.random.default_rng(seed)
    model.eval()
    errs, total = 0.0, 0
    chunks = max(1, n_symbols // (n_sym - 2 * crop))
    for _ in range(chunks):
        rx, idx = channel(n_sym, rng)
        y = model(torch.from_numpy(rx.astype(np.float32))[None])[0, crop:-crop].numpy()
        b = ber(y, idx[crop:-crop], channel.order)
        n = len(y) * int(np.log2(channel.order))
        errs += b * n
        total += n
    return errs / total, total
