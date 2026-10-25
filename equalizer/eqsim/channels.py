"""Channel simulators.

Both channels return the received samples at `nos` samples per symbol together
with the transmitted symbol indices, aligned so that sample ``rx[nos * n]`` is
the sampling instant of symbol ``n``.

* ProakisBChannel: the simulated magnetic-recording channel of Ney et al.
  (Sec. 2.2): RC pulse shaping, symbol-spaced Proakis-B impulse response
  [0.407, 0.815, 0.407], additive white Gaussian noise.
* IMDDChannel: a physics-based stand-in for their 40 GBd PAM2 optical IM/DD
  link (Sec. 2.1): RRC pulse, zero-chirp MZM at quadrature, chromatic
  dispersion of standard single-mode fiber, square-law photodiode with finite
  bandwidth, thermal noise, AC coupling and an optional low-resolution ADC.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy import signal

from .metrics import pam_levels
from .pulses import rc_taps, rrc_taps

C_LIGHT = 299_792_458.0


def _awgn(x: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    """Add white Gaussian noise for a per-sample SNR of `snr_db`."""
    p_sig = np.mean(x ** 2)
    sigma = np.sqrt(p_sig / 10 ** (snr_db / 10))
    return x + sigma * rng.standard_normal(x.shape)


@dataclass
class ProakisBChannel:
    snr_db: float = 20.0
    nos: int = 2
    order: int = 2
    beta: float = 0.25
    span: int = 16
    h: tuple = (0.407, 0.815, 0.407)

    def __call__(self, n_symbols: int, rng: np.random.Generator):
        idx = rng.integers(self.order, size=n_symbols)
        s = pam_levels(self.order)[idx]
        up = np.zeros(n_symbols * self.nos)
        up[:: self.nos] = s
        p = rc_taps(self.beta, self.nos, self.span)
        x = np.convolve(up, p)
        h_up = np.zeros((len(self.h) - 1) * self.nos + 1)
        h_up[:: self.nos] = self.h
        y = np.convolve(x, h_up)
        delay = len(p) // 2 + (len(self.h) // 2) * self.nos
        y = y[delay: delay + n_symbols * self.nos]
        return _awgn(y, self.snr_db, rng), idx


@dataclass
class IMDDChannel:
    baud: float = 40e9
    order: int = 2
    nos: int = 2
    sps_sim: int = 8
    rrc_beta: float = 0.2
    rrc_span: int = 32
    length_km: float = 31.5
    dispersion_ps_nm_km: float = 16.0
    wavelength_m: float = 1550e-9
    mod_index: float = 0.8
    pd_bandwidth_hz: float = 40e9
    pd_order: int = 4
    snr_db: float = 20.0
    adc_bits: int | None = None
    adc_clip_sigma: float = 3.0
    guard_symbols: int = 64
    extra: dict = field(default_factory=dict)

    @property
    def beta2(self) -> float:
        """Group-velocity dispersion beta2 in s^2/m."""
        d = self.dispersion_ps_nm_km * 1e-12 / (1e-9 * 1e3)
        return -d * self.wavelength_m ** 2 / (2 * np.pi * C_LIGHT)

    def fading_null_hz(self, k: int = 0) -> float:
        """k-th small-signal power-fading null of chirp-free IM/DD.

        The small-signal response is cos(beta2 * L * w^2 / 2), which vanishes
        when beta2 * L * w^2 / 2 = pi/2 + k*pi.
        """
        L = self.length_km * 1e3
        w = np.sqrt((np.pi / 2 + k * np.pi) * 2 / (abs(self.beta2) * L))
        return w / (2 * np.pi)

    def _drive(self, idx: np.ndarray) -> np.ndarray:
        s = pam_levels(self.order)[idx]
        up = np.zeros(len(idx) * self.sps_sim)
        up[:: self.sps_sim] = s
        p = rrc_taps(self.rrc_beta, self.sps_sim, self.rrc_span)
        x = np.convolve(up, p)[len(p) // 2: len(p) // 2 + len(up)]
        return x / np.max(np.abs(x))

    def _fiber(self, field_in: np.ndarray) -> np.ndarray:
        fs = self.baud * self.sps_sim
        w = 2 * np.pi * np.fft.fftfreq(len(field_in), d=1 / fs)
        L = self.length_km * 1e3
        return np.fft.ifft(np.fft.fft(field_in) * np.exp(1j * self.beta2 / 2 * w ** 2 * L))

    def simulate(self, n_symbols: int, rng: np.random.Generator, noise: bool = True):
        """Return (rx at nos samples/symbol, symbol indices, internals dict)."""
        g = self.guard_symbols
        idx_full = rng.integers(self.order, size=n_symbols + 2 * g)
        drive = self._drive(idx_full)
        # Push-pull MZM biased at quadrature: field = cos(pi/4 - pi/4 * m * v).
        e_tx = np.cos(np.pi / 4 - np.pi / 4 * self.mod_index * drive)
        e_rx = self._fiber(e_tx.astype(complex))
        current = np.abs(e_rx) ** 2
        fs = self.baud * self.sps_sim
        sos = signal.bessel(self.pd_order, self.pd_bandwidth_hz, fs=fs, output="sos", norm="mag")
        sig = signal.sosfilt(sos, current - current.mean())
        if noise:
            n = signal.sosfilt(sos, rng.standard_normal(len(sig)))
            n *= np.sqrt(np.var(sig) / (np.var(n) * 10 ** (self.snr_db / 10)))
            sig = sig + n
        rx = signal.resample_poly(sig, 1, self.sps_sim // self.nos)
        rx = (rx - rx.mean()) / rx.std()
        rx = self._align(rx, idx_full)
        if self.adc_bits is not None:
            rx = self.adc(rx)
        sl = slice(g * self.nos, (g + n_symbols) * self.nos)
        internals = {"drive": drive, "current": current, "fs_sim": fs}
        return rx[sl], idx_full[g: g + n_symbols], internals

    def __call__(self, n_symbols: int, rng: np.random.Generator):
        rx, idx, _ = self.simulate(n_symbols, rng)
        return rx, idx

    def _align(self, rx: np.ndarray, idx: np.ndarray, max_lag: int = 64) -> np.ndarray:
        """Shift rx so that rx[nos*n] is the sampling instant of symbol n."""
        ref = np.zeros(len(idx) * self.nos)
        ref[:: self.nos] = pam_levels(self.order)[idx]
        lags = np.arange(-max_lag, max_lag + 1)
        scores = [np.dot(np.roll(rx, -lag), ref) for lag in lags]
        return np.roll(rx, -lags[int(np.argmax(scores))])

    def adc(self, x: np.ndarray) -> np.ndarray:
        """Uniform mid-rise quantizer over +-adc_clip_sigma (input has unit std)."""
        full = self.adc_clip_sigma
        n_levels = 2 ** self.adc_bits
        step = 2 * full / n_levels
        q = np.floor(np.clip(x, -full, full - 1e-12) / step) + 0.5
        return q * step
