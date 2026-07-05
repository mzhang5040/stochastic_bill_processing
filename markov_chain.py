"""
markov_chain.py
===============
Estimate absorbing Markov chain parameters from bill trajectory records
and compute all quantities reported in the paper.

The model
---------
Six states: four transient (s0..s3) and two absorbing (a0, a1).

    s0  Introduced
    s1  In_Committee
    s2  Out_of_Committee
    s3  On_Floor
    a0  Passed
    a1  Failed

The canonical partition form is:

    P = | Q   R |
        | 0   I |

where Q (4x4) holds transient->transient probabilities and
      R (4x2) holds transient->absorbing probabilities.

Key quantities (all derived from the fundamental matrix N = (I-Q)^{-1}):
    B = N R               absorption probability matrix  (4x2)
    t = N 1               expected steps to absorption   (4x1)
    N[0,j]                expected visits to state j from Introduced

Sensitivity (Proposition 1 of the paper):
    Case (i)  (R-perturbation): dB[0,0]/dp[j,Failed] = -N[0,j]
    Case (ii) (Q-perturbation): dB[0,0]/dp[j,Failed] = -N[0,j] * B[ell,0]

Usage
-----
    from markov_chain import compute_chain, ChainResult

    # From bill records (output of parse_status_sheets.parse_session):
    result = compute_chain(bills)
    print(f"Passage rate: {result.B[0,0]:.4f}")
    print(f"Floor sensitivity: {result.floor_sensitivity:.4f}")

    # Access all quantities:
    result.Q          # transient submatrix (4x4)
    result.R          # absorption submatrix (4x2)
    result.N          # fundamental matrix (4x4)
    result.B          # absorption probabilities (4x2)
    result.t          # expected steps (4,)
    result.counts_Q   # observed transition counts for Q
    result.counts_R   # observed transition counts for R
"""

from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np


# ---------------------------------------------------------------------------
# State definitions
# ---------------------------------------------------------------------------

TRANSIENT_STATES = ['Introduced', 'In_Committee', 'Out_of_Committee', 'On_Floor']
ABSORBING_STATES = ['Passed', 'Failed']
ALL_STATES = TRANSIENT_STATES + ABSORBING_STATES
STATE_INDEX = {s: i for i, s in enumerate(TRANSIENT_STATES)}

N_TRANSIENT = len(TRANSIENT_STATES)
N_ABSORBING = len(ABSORBING_STATES)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ChainResult:
    """All estimated quantities for one session's absorbing Markov chain."""

    year: str
    n_bills: int

    # MLE transition matrices
    Q: np.ndarray          # (4,4)  transient -> transient probabilities
    R: np.ndarray          # (4,2)  transient -> absorbing probabilities

    # Raw counts (useful for verification)
    counts_Q: np.ndarray   # (4,4)  observed transient->transient counts
    counts_R: np.ndarray   # (4,2)  observed transient->absorbing counts

    # Derived quantities
    N: np.ndarray          # (4,4)  fundamental matrix (I-Q)^{-1}
    B: np.ndarray          # (4,2)  absorption probability matrix NR
    t: np.ndarray          # (4,)   expected steps to absorption N*1

    # Sensitivity coefficients (Proposition 1)
    floor_sensitivity: float   # dB[0,0]/dp[3,Failed] = -N[0,3]  (Case (i))
    ooc_sensitivity: float     # dB[0,0]/dp[2,Failed] = -N[0,2]*B[3,0]  (Case (ii))

    # Bottleneck rate (primary finding)
    bottleneck_rate: float     # p(Out_of_Committee -> Failed)

    def summary(self) -> str:
        """Return a formatted summary string."""
        lines = [
            f"Session {self.year}  ({self.n_bills} bills)",
            f"  Passage rate B[0,0]        : {self.B[0,0]:.4f}",
            f"  Bottleneck rate (OOC->Fail): {self.bottleneck_rate:.4f}",
            f"  Floor failure rate          : {self.R[3,1]:.4f}",
            f"  Expected steps from Intro  : {self.t[0]:.4f}",
            f"  Floor sensitivity -N[0,3]  : {self.floor_sensitivity:.4f}",
            f"  OOC sensitivity -N[0,2]*B[3,0]: {self.ooc_sensitivity:.4f}",
        ]
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Core estimation
# ---------------------------------------------------------------------------

def _build_count_matrices(bills: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """
    Count all observed state transitions in a list of bill records.

    Parameters
    ----------
    bills : list of dict
        Each dict must have a 'state_seq' key with arrow-separated states,
        e.g. 'Introduced -> In_Committee -> Out_of_Committee -> Failed'.

    Returns
    -------
    counts_Q : ndarray (4,4)
        counts_Q[i,j] = number of observed i->j transient transitions.
    counts_R : ndarray (4,2)
        counts_R[i,k] = number of observed i->absorbing[k] transitions.
    """
    counts_Q = np.zeros((N_TRANSIENT, N_TRANSIENT), dtype=float)
    counts_R = np.zeros((N_TRANSIENT, N_ABSORBING), dtype=float)

    for bill in bills:
        seq = bill['state_seq'].split(' -> ')
        for a, b in zip(seq[:-1], seq[1:]):
            if a not in STATE_INDEX:
                continue
            i = STATE_INDEX[a]
            if b in STATE_INDEX:
                counts_Q[i, STATE_INDEX[b]] += 1
            else:
                k = ABSORBING_STATES.index(b)
                counts_R[i, k] += 1

    return counts_Q, counts_R


def _mle_transition_matrices(counts_Q: np.ndarray,
                              counts_R: np.ndarray
                              ) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute MLE transition probabilities from raw counts.

    p_hat[i,j] = counts[i,j] / sum_k counts[i,k]

    Rows with zero total count keep probability 0 (these correspond to
    states never actually visited in the data).
    """
    Q = np.zeros_like(counts_Q)
    R = np.zeros_like(counts_R)
    row_totals = counts_Q.sum(axis=1) + counts_R.sum(axis=1)

    for i in range(N_TRANSIENT):
        if row_totals[i] > 0:
            Q[i] = counts_Q[i] / row_totals[i]
            R[i] = counts_R[i] / row_totals[i]

    return Q, R


def compute_chain(bills: list[dict], year: str = '') -> ChainResult:
    """
    Estimate the absorbing Markov chain from a list of bill records.

    Parameters
    ----------
    bills : list of dict
        Output from parse_status_sheets.parse_session().
    year : str, optional
        Session label for display purposes.

    Returns
    -------
    ChainResult
        All estimated parameters and derived quantities.

    Raises
    ------
    np.linalg.LinAlgError
        If (I - Q) is singular (should not occur with real data).
    """
    counts_Q, counts_R = _build_count_matrices(bills)
    Q, R = _mle_transition_matrices(counts_Q, counts_R)

    I = np.eye(N_TRANSIENT)
    N = np.linalg.inv(I - Q)   # fundamental matrix
    B = N @ R                   # absorption probability matrix
    t = N @ np.ones(N_TRANSIENT)  # expected steps to absorption

    # Sensitivity coefficients (Proposition 1)
    # Case (i): floor failure perturbation (R-perturbation)
    #   dB[0,0]/dp[3,Failed] = -N[0,3]
    floor_sens = -N[0, 3]

    # Case (ii): OOC bottleneck perturbation (Q-perturbation)
    #   dB[0,0]/dp[2,Failed] = -N[0,2] * B[3,0]
    #   (probability transfers from OOC->Floor to OOC->Failed)
    ooc_sens = -N[0, 2] * B[3, 0]

    return ChainResult(
        year=year,
        n_bills=len(bills),
        Q=Q,
        R=R,
        counts_Q=counts_Q,
        counts_R=counts_R,
        N=N,
        B=B,
        t=t,
        floor_sensitivity=floor_sens,
        ooc_sensitivity=ooc_sens,
        bottleneck_rate=R[2, 1],   # Out_of_Committee -> Failed
    )


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap_chain(bills: list[dict],
                    n_resamples: int = 5000,
                    seed: int = 42) -> dict:
    """
    Non-parametric bootstrap for all key statistics.

    Resamples bills with replacement n_resamples times.  For each
    resample, computes the chain and records the statistics of interest.

    Parameters
    ----------
    bills : list of dict
        Bill records for ONE session.
    n_resamples : int
        Number of bootstrap resamples (default 5000).
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict
        Keys: 'bottleneck_rate', 'floor_failure_rate', 'passage_rate',
              'floor_sensitivity', 'ooc_sensitivity'.
        Each value is a 1-D array of length n_resamples.
    """
    rng = np.random.default_rng(seed)
    n = len(bills)

    boot = {
        'bottleneck_rate': np.zeros(n_resamples),
        'floor_failure_rate': np.zeros(n_resamples),
        'passage_rate': np.zeros(n_resamples),
        'floor_sensitivity': np.zeros(n_resamples),
        'ooc_sensitivity': np.zeros(n_resamples),
    }

    for k in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        sample = [bills[i] for i in idx]
        try:
            r = compute_chain(sample)
            boot['bottleneck_rate'][k]   = r.bottleneck_rate
            boot['floor_failure_rate'][k] = r.R[3, 1]
            boot['passage_rate'][k]       = r.B[0, 0]
            boot['floor_sensitivity'][k]  = r.floor_sensitivity
            boot['ooc_sensitivity'][k]    = r.ooc_sensitivity
        except np.linalg.LinAlgError:
            # Singular resample (extremely rare); skip by repeating last value
            for key in boot:
                boot[key][k] = boot[key][max(0, k - 1)]

    return boot


def bootstrap_ci(boot_values: np.ndarray, alpha: float = 0.05) -> tuple:
    """
    Compute a percentile bootstrap confidence interval.

    Parameters
    ----------
    boot_values : ndarray
        Array of bootstrap statistics.
    alpha : float
        Significance level (default 0.05 -> 95% CI).

    Returns
    -------
    (lower, upper, sd) : tuple of float
    """
    lo = float(np.percentile(boot_values, 100 * alpha / 2))
    hi = float(np.percentile(boot_values, 100 * (1 - alpha / 2)))
    sd = float(np.std(boot_values))
    return lo, hi, sd


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from parse_status_sheets import parse_session, SESSIONS

    print("Computing chains for all sessions...\n")

    for year, (path, bill_max) in sorted(SESSIONS.items()):
        bills = parse_session(path, year, bill_max)
        result = compute_chain(bills, year=year)
        print(result.summary())
        print()

    print("Running bootstrap (5000 resamples per session)...")
    for year, (path, bill_max) in sorted(SESSIONS.items()):
        bills = parse_session(path, year, bill_max)
        boot = bootstrap_chain(bills, n_resamples=5000)

        lo_f, hi_f, sd_f = bootstrap_ci(boot['floor_sensitivity'])
        lo_o, hi_o, sd_o = bootstrap_ci(boot['ooc_sensitivity'])
        lo_b, hi_b, sd_b = bootstrap_ci(boot['bottleneck_rate'])

        print(f"\n{year} bootstrap 95% CIs:")
        print(f"  Bottleneck rate    : [{lo_b:.4f}, {hi_b:.4f}]  SD={sd_b:.4f}")
        print(f"  Floor sensitivity  : [{lo_f:.4f}, {hi_f:.4f}]  SD={sd_f:.4f}")
        print(f"  OOC sensitivity    : [{lo_o:.4f}, {hi_o:.4f}]  SD={sd_o:.4f}")
