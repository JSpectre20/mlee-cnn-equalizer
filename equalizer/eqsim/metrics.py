"""Decision and error-rate metrics for PAM signals."""
import numpy as np


def pam_levels(order: int) -> np.ndarray:
    """Equally spaced PAM levels in [-1, 1], e.g. PAM2 -> [-1, 1]."""
    return np.linspace(-1.0, 1.0, order)


def hard_decision(y: np.ndarray, levels: np.ndarray) -> np.ndarray:
    """Map each equalizer output to the index of the nearest PAM level."""
    return np.argmin(np.abs(np.asarray(y)[..., None] - levels), axis=-1)


def gray_bits(idx: np.ndarray, order: int) -> np.ndarray:
    """Gray-coded bits for PAM level indices, shape (..., log2(order))."""
    nbits = int(np.log2(order))
    g = idx ^ (idx >> 1)
    return ((g[..., None] >> np.arange(nbits - 1, -1, -1)) & 1).astype(np.uint8)


def ber(y: np.ndarray, sym_idx: np.ndarray, order: int) -> float:
    """Bit error ratio after hard decision with Gray mapping."""
    levels = pam_levels(order)
    dec = hard_decision(y, levels)
    if order == 2:
        return float(np.mean(dec != sym_idx))
    return float(np.mean(gray_bits(dec, order) != gray_bits(sym_idx, order)))


def ber_confidence(ber_value: float, n_bits: int) -> tuple:
    """Approximate 95% Wilson interval for a measured BER."""
    z = 1.96
    p = ber_value
    denom = 1 + z ** 2 / n_bits
    centre = (p + z ** 2 / (2 * n_bits)) / denom
    half = z * np.sqrt(p * (1 - p) / n_bits + z ** 2 / (4 * n_bits ** 2)) / denom
    return max(centre - half, 0.0), centre + half
