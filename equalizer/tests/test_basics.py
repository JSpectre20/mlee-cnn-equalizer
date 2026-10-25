import numpy as np
import torch
from scipy import signal

from eqsim.channels import IMDDChannel, ProakisBChannel
from eqsim.equalizers import FIREqualizer, NeyCNN, VolterraEqualizer
from eqsim.pulses import rc_taps, rrc_taps


def test_rc_has_zero_isi_at_symbol_instants():
    h = rc_taps(0.25, sps=4, span=16)
    centre = len(h) // 2
    at_symbols = h[centre % 4::4]
    assert np.isclose(h[centre], 1.0)
    assert np.allclose(np.delete(at_symbols, centre // 4), 0.0, atol=1e-12)


def test_rrc_unit_energy():
    assert np.isclose(np.sum(rrc_taps(0.2, 8, 32) ** 2), 1.0)


def test_proakis_alignment_noise_free():
    ch = ProakisBChannel(snr_db=200)
    rx, idx = ch(2000, np.random.default_rng(1))
    s = 2.0 * idx - 1.0
    expected = 0.407 * np.roll(s, 1) + 0.815 * s + 0.407 * np.roll(s, -1)
    assert np.allclose(rx[::2][20:-20], expected[20:-20], atol=1e-3)


def test_imdd_power_fading_null_matches_theory():
    ch = IMDDChannel(mod_index=0.05)
    _, _, internals = ch.simulate(20_000, np.random.default_rng(2), noise=False)
    fs = internals["fs_sim"]
    f, pxy = signal.csd(internals["drive"], internals["current"], fs=fs, nperseg=4096)
    _, pxx = signal.welch(internals["drive"], fs=fs, nperseg=4096)
    mag = np.abs(pxy / pxx)
    band = (f > 3e9) & (f < 19e9)
    f_min = f[band][np.argmin(mag[band])]
    assert abs(f_min - ch.fading_null_hz()) / ch.fading_null_hz() < 0.05


def test_mlse_is_exact_without_noise_and_sane_with_noise():
    from eqsim.detectors import mlse_viterbi
    from eqsim.metrics import pam_levels

    for snr, max_ber in ((200, 0.0), (12, 5e-3)):
        ch = ProakisBChannel(snr_db=snr)
        rx, idx = ch(20_000, np.random.default_rng(3))
        dec = mlse_viterbi(rx[::2], np.array(ch.h), pam_levels(2))
        assert np.mean(dec[10:-10] != idx[10:-10]) <= max_ber


def test_logistic_refit_does_not_hurt_fir():
    from eqsim.equalizers import fit_linear_in_params_logistic, fit_linear_in_params_ls
    from eqsim.train import evaluate_ber

    ch = ProakisBChannel()
    rx, idx = ch(50_000, np.random.default_rng(4))
    ls, ce = FIREqualizer(9), FIREqualizer(9)
    fit_linear_in_params_ls(ls, rx, 2.0 * idx - 1.0, crop=32)
    fit_linear_in_params_logistic(ce, rx, idx, crop=32)
    assert evaluate_ber(ce, ch, 100_000)[0] <= 1.1 * evaluate_ber(ls, ch, 100_000)[0]


def test_fir_identity_initialisation_picks_symbol_instants():
    x = torch.randn(2, 64)
    y = FIREqualizer(taps=9, nos=2)(x)
    assert torch.allclose(y, x[:, ::2])


def test_equalizer_output_shapes_and_macs():
    x = torch.randn(3, 2 * 256)
    cnn = NeyCNN(layers=3, kernel=9, channels=5, vp=8, nos=2)
    assert cnn(x).shape == (3, 256)
    assert np.isclose(cnn.macs_per_symbol(), 112.5)
    assert np.isclose(cnn.macs_paper_formula(), 56.25)
    assert VolterraEqualizer(9, 3, 3)(x).shape == (3, 256)
