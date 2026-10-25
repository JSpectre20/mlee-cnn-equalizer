"""Pulse-shaping filters (raised cosine and root-raised cosine)."""
import numpy as np


def rc_taps(beta: float, sps: int, span: int) -> np.ndarray:
    """Raised-cosine impulse response, `span` symbols long, peak normalized to 1.

    Zero crossings fall at every non-zero multiple of the symbol period, so
    sampling at the symbol instants gives no ISI.
    """
    t = np.arange(-span * sps // 2, span * sps // 2 + 1) / sps
    h = np.sinc(t)
    if beta > 0:
        denom = 1.0 - (2.0 * beta * t) ** 2
        sing = np.isclose(denom, 0.0)
        h = np.where(sing, np.pi / 4 * np.sinc(1 / (2 * beta)), h * np.cos(np.pi * beta * t) / np.where(sing, 1.0, denom))
    return h / h[len(h) // 2]


def rrc_taps(beta: float, sps: int, span: int) -> np.ndarray:
    """Root-raised-cosine impulse response, normalized to unit energy."""
    t = np.arange(-span * sps // 2, span * sps // 2 + 1) / sps
    h = np.empty_like(t)
    for i, ti in enumerate(t):
        if np.isclose(ti, 0.0):
            h[i] = 1.0 - beta + 4 * beta / np.pi
        elif beta > 0 and np.isclose(abs(ti), 1 / (4 * beta)):
            h[i] = beta / np.sqrt(2) * ((1 + 2 / np.pi) * np.sin(np.pi / (4 * beta)) + (1 - 2 / np.pi) * np.cos(np.pi / (4 * beta)))
        else:
            num = np.sin(np.pi * ti * (1 - beta)) + 4 * beta * ti * np.cos(np.pi * ti * (1 + beta))
            den = np.pi * ti * (1 - (4 * beta * ti) ** 2)
            h[i] = num / den
    return h / np.sqrt(np.sum(h ** 2))
