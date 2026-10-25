"""Reference detectors (not hardware candidates): Viterbi MLSE for known linear ISI."""
import itertools

import numpy as np


def mlse_viterbi(r: np.ndarray, h: np.ndarray, levels: np.ndarray) -> np.ndarray:
    """Maximum-likelihood sequence detection for r[n] = sum_k h[k] s[n+c-k] + AWGN.

    `h` is symbol-spaced with its centre tap aligned to r[n] (c = len(h)//2),
    i.e. the convention of ProakisBChannel sampled at rx[::nos]. Returns the
    detected level indices. States hold the last len(h)-1 symbols.
    """
    h = np.asarray(h, dtype=float)
    mem = len(h) - 1
    c = len(h) // 2
    q = len(levels)
    states = list(itertools.product(range(q), repeat=mem))  # (s[n-c], ..., s[n+c-1]) oldest first
    s_index = {s: i for i, s in enumerate(states)}
    n_states = len(states)
    # For each (state, new symbol) the noiseless output and next state.
    out = np.empty((n_states, q))
    nxt = np.empty((n_states, q), dtype=np.int64)
    for i, st in enumerate(states):
        for a in range(q):
            window = st + (a,)  # s[n-c] ... s[n+c]
            out[i, a] = sum(h[k] * levels[window[len(h) - 1 - k]] for k in range(len(h)))
            nxt[i, a] = s_index[window[1:]]
    N = len(r)
    cost = np.zeros(n_states)
    back_state = np.zeros((N, n_states), dtype=np.int64)
    back_sym = np.zeros((N, n_states), dtype=np.int64)
    for n in range(c, N - c):
        cand = cost[:, None] + (r[n] - out) ** 2  # (n_states, q)
        new = np.full(n_states, np.inf)
        bs = np.zeros(n_states, dtype=np.int64)
        ba = np.zeros(n_states, dtype=np.int64)
        flat_next = nxt.ravel()
        flat_cand = cand.ravel()
        np.minimum.at(new, flat_next, flat_cand)  # survivor = minimum per next state
        hit = flat_cand == new[flat_next]
        for j in np.nonzero(hit)[0]:
            bs[flat_next[j]], ba[flat_next[j]] = divmod(j, q)
        cost = new - new.min()
        back_state[n], back_sym[n] = bs, ba
    dec = np.zeros(N, dtype=np.int64)
    st = int(np.argmin(cost))
    for n in range(N - c - 1, c - 1, -1):
        dec[n + c] = back_sym[n, st]
        st = back_state[n, st]
    for k in range(mem):  # oldest symbols of the starting state
        dec[k] = states[st][k]
    return dec
