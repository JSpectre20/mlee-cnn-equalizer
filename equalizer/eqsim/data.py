"""Fixed, cached datasets for channels that are expensive to simulate (IM/DD).

A dataset is a list of independent chunks (each simulated with its own guard
symbols), so a training crop never straddles two unrelated realizations.
"""
from pathlib import Path

import numpy as np
import torch

from .metrics import ber


class DatasetChannel:
    """Serves random crops from pre-simulated chunks, with the channel-call interface."""

    def __init__(self, rx_chunks, idx_chunks, order: int, nos: int):
        self.rx, self.idx = list(rx_chunks), list(idx_chunks)
        self.order, self.nos = order, nos

    def __call__(self, n_sym: int, rng: np.random.Generator):
        c = int(rng.integers(len(self.rx)))
        start = int(rng.integers(len(self.idx[c]) - n_sym))
        return self.rx[c][self.nos * start: self.nos * (start + n_sym)], self.idx[c][start: start + n_sym]

    @property
    def n_symbols(self) -> int:
        return sum(len(i) for i in self.idx)


def simulate_chunks(channel, n_symbols: int, seed: int, chunk: int = 200_000):
    rng = np.random.default_rng(seed)
    rx, idx = [], []
    for _ in range(max(1, n_symbols // chunk)):
        r, i = channel(chunk, rng)
        rx.append(r.astype(np.float32))
        idx.append(i.astype(np.int8))
    return rx, idx


def save_dataset(path: Path, rx, idx):
    np.savez_compressed(path, **{f"rx{k}": r for k, r in enumerate(rx)}, **{f"idx{k}": i for k, i in enumerate(idx)})


def load_dataset(path: Path, order: int, nos: int) -> DatasetChannel:
    z = np.load(path)
    n = len([k for k in z.files if k.startswith("rx")])
    return DatasetChannel([z[f"rx{k}"] for k in range(n)], [z[f"idx{k}"].astype(np.int64) for k in range(n)], order, nos)


@torch.no_grad()
def evaluate_ber_dataset(model, ds: DatasetChannel, crop: int = 64):
    """BER over every chunk of a fixed test set (edges of each chunk cropped)."""
    model.eval()
    errs, total = 0.0, 0
    bits_per_sym = int(np.log2(ds.order))
    for r, i in zip(ds.rx, ds.idx):
        y = model(torch.from_numpy(r)[None])[0, crop:-crop].numpy()
        n = len(y) * bits_per_sym
        errs += ber(y, i[crop:-crop], ds.order) * n
        total += n
    return errs / total, total
