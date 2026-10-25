import numpy as np
import torch

from eqsim.equalizers import NeyCNN
from eqsim.quant import QuantNeyCNN, export_integer

CFGS = (dict(layers=3, kernel=9, channels=5, vp=8), dict(layers=4, kernel=9, channels=3, vp=4))


def _model(cfg, seed=0):
    torch.manual_seed(seed)
    fp = NeyCNN(**cfg)
    # give BatchNorm non-trivial statistics so folding is exercised
    with torch.no_grad():
        for m in fp.net:
            if isinstance(m, torch.nn.BatchNorm1d):
                m.running_mean.uniform_(-0.3, 0.3)
                m.running_var.uniform_(0.5, 2.0)
                m.weight.uniform_(0.5, 1.5)
                m.bias.uniform_(-0.2, 0.2)
    return fp.eval()


def test_bn_folding_is_exact():
    for cfg in CFGS:
        fp = _model(cfg)
        q = QuantNeyCNN(fp)
        x = torch.randn(2, 512)
        with torch.no_grad():
            assert torch.allclose(q.forward_float(x), fp(x), atol=1e-5)


def test_integer_model_matches_fake_quant():
    for cfg in CFGS:
        fp = _model(cfg)
        q = QuantNeyCNN(fp, 8, 8, 8)
        x = torch.randn(1, 4096)
        q.calibrate(x)
        im = export_integer(q)
        with torch.no_grad():
            y = q(x)[0].double().numpy()
        bits, z = im.forward_int(im.quantize_input(x[0].double().numpy()))
        assert np.mean(bits == (y > 0)) > 0.999
        # Dequantized integer logits equal the fake-quant logits except where an intermediate
        # activation lands on a rounding tie (float32 fake-quant vs exact M/S integer requant),
        # which shifts that activation by one LSB. The integer model is the RTL reference.
        err = np.abs(im.dequantize_output(z) - y)
        assert np.median(err) < 1e-6 * np.abs(y).max() + 1e-12
        assert np.mean(err < 1e-3 * np.abs(y).max()) > 0.99


def test_integer_conv_semantics_match_torch():
    """With identity requant (M=1, S=1 after scaling) the integer path is a plain torch conv stack."""
    cfg = CFGS[1]
    q = QuantNeyCNN(_model(cfg), 8, 8, 8)
    x = torch.randn(1, 2048)
    q.calibrate(x)
    im = export_integer(q)
    xi = im.quantize_input(x[0].double().numpy())
    _, _, accs = im.forward_int(xi, return_acc=True)
    a = torch.tensor(xi, dtype=torch.float64)[None, None]
    w0 = torch.tensor(im.W[0], dtype=torch.float64)
    ref = torch.nn.functional.conv1d(a, w0, torch.tensor(im.bias[0], dtype=torch.float64), stride=im.strides[0], padding=im.K // 2)
    assert np.array_equal(accs[0], ref[0].numpy().astype(np.int64))
