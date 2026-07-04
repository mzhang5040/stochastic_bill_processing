"""
results_tables.py
=================
Compute all numerical results reported in the paper and print
the data underlying each table.

Tables produced
---------------
    Table 1  Transition probabilities (Q and R matrices)
    Table 2  Failures by stage
    Table 3  Absorption probabilities B and expected steps t
    Table 5  Bicameral decomposition (requires manual coding CSV)
    Table 7  Party stratification (requires sponsor party CSV)
    Table 8  Within-session time heterogeneity chi-square tests
    Table A1 Bootstrap confidence intervals (Appendix)

Usage
-----
    python results_tables.py

This prints all table data to stdout.  Redirect to a file to save:
    python results_tables.py > tables_output.txt

Dependencies
------------
    parse_status_sheets.py  -- bill parsing
    markov_chain.py         -- chain estimation and bootstrap

Notes on additional data requirements
--------------------------------------
    Party stratification (Table 7) requires a CSV with columns:
        bill_num, year, party   (party in {'D', 'R', 'Other'})
    Example:  sponsor_parties.csv
    If this file is absent, the party stratification table is skipped.

    Bicameral decomposition (Table 5) requires a CSV with columns:
        bill_num, year, chamber   (chamber in {'Senate', 'House', 'Session-end'})
    Example:  chamber_coding.csv
    If absent, Table 5 is skipped.
"""

import csv
import sys
import os
import numpy as np
from scipy.stats import chi2_contingency
from collections import defaultdict

from parse_status_sheets import parse_session, SESSIONS, TRANSIENT_STATES, ABSORBING_STATES
from markov_chain import compute_chain, bootstrap_chain, bootstrap_ci, ChainResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(x: float) -> str:
    return f"{x:.1%}"

def _fmt4(x: float) -> str:
    return f"{x:.4f}"

def _fmt3(x: float) -> str:
    return f"{x:.3f}"

def header(title: str):
    print('\n' + '=' * 65)
    print(title)
    print('=' * 65)


# ---------------------------------------------------------------------------
# Table 1: Transition probabilities
# ---------------------------------------------------------------------------

def table1_transitions(results: dict[str, ChainResult]):
    """Print Table 1: estimated transition probabilities for all sessions."""
    header("TABLE 1 — Estimated transition probabilities p_hat[i,j]")

    row_labels = [
        'Introduced -> InComm',
        'InComm -> OOC',
        'OOC -> Floor',
        'OOC -> Failed',
        'Floor -> Passed',
        'Floor -> Failed',
    ]

    years = sorted(results.keys())
    print(f"{'Transition':<26}", end='')
    for yr in years:
        print(f"  {yr:>8}", end='')
    # Deltas
    for i in range(len(years) - 1):
        print(f"  Δ{years[i][-2:]}→{years[i+1][-2:]}", end='')
    print()
    print('-' * (26 + len(years)*10 + (len(years)-1)*9))

    def get_prob(r: ChainResult, row: str) -> float:
        if row == 'Introduced -> InComm':   return r.Q[0, 1]
        if row == 'InComm -> OOC':          return r.Q[1, 2]
        if row == 'OOC -> Floor':           return r.Q[2, 3]
        if row == 'OOC -> Failed':          return r.R[2, 1]
        if row == 'Floor -> Passed':        return r.R[3, 0]
        if row == 'Floor -> Failed':        return r.R[3, 1]
        return 0.0

    for row in row_labels:
        probs = [get_prob(results[yr], row) for yr in years]
        print(f"{row:<26}", end='')
        for p in probs:
            print(f"  {p:8.4f}", end='')
        for i in range(len(probs) - 1):
            d = probs[i+1] - probs[i]
            sign = '+' if d >= 0 else ''
            print(f"  {sign}{d:.4f}", end='')
        print()


# ---------------------------------------------------------------------------
# Table 2: Failures by stage
# ---------------------------------------------------------------------------

def table2_failures(all_bills: dict[str, list]):
    """Print Table 2: bill failures by stage."""
    header("TABLE 2 — Failures by stage and session")

    stages = [
        ('In_Committee -> Failed',   'In_Committee',   'Failed'),
        ('Out_of_Committee -> Failed', 'Out_of_Committee', 'Failed'),
        ('On_Floor -> Failed',        'On_Floor',        'Failed'),
    ]

    years = sorted(all_bills.keys())
    print(f"{'Failure stage':<30}", end='')
    for yr in years:
        print(f"  {yr:>12}", end='')
    print()
    print('-' * (30 + len(years)*14))

    for label, from_state, to_state in stages:
        counts = []
        pcts = []
        for yr in years:
            bills = all_bills[yr]
            n_total = len(bills)
            n = sum(1 for b in bills
                    if f'{from_state} -> {to_state}' in b['state_seq']
                    or b['state_seq'].endswith(f'{from_state} -> {to_state}'))
            # More precise: last transition in seq
            n = sum(1 for b in bills
                    if _last_two(b['state_seq']) == (from_state, to_state))
            counts.append(n)
            pcts.append(n / n_total if n_total > 0 else 0)

        print(f"{label:<30}", end='')
        for p in pcts:
            print(f"  {p:11.1%}", end='')
        print()

    # Total failed
    print('-' * (30 + len(years)*14))
    print(f"{'Total failed':<30}", end='')
    for yr in years:
        bills = all_bills[yr]
        n_total = len(bills)
        n_failed = sum(1 for b in bills if b['markov'] == 'Failed')
        print(f"  {n_failed:3d} ({n_failed/n_total:.1%})", end='')
    print()


def _last_two(state_seq: str) -> tuple:
    """Return the last two states in a sequence string."""
    parts = state_seq.split(' -> ')
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return ('', parts[-1])


# ---------------------------------------------------------------------------
# Table 3: Absorption probabilities
# ---------------------------------------------------------------------------

def table3_absorption(results: dict[str, ChainResult]):
    """Print Table 3: absorption probabilities and expected steps."""
    header("TABLE 3 — Absorption probabilities B[i,0] and expected steps t[i]")

    state_labels = ['Introduced', 'In Committee', 'Out of Committee', 'On Floor']
    years = sorted(results.keys())

    print(f"{'Starting state':<22}", end='')
    for yr in years:
        print(f"   t({yr})  B({yr})", end='')
    print()
    print('-' * (22 + len(years)*16))

    for i, label in enumerate(state_labels):
        print(f"{label:<22}", end='')
        for yr in years:
            r = results[yr]
            print(f"   {r.t[i]:5.3f}  {r.B[i,0]:6.4f}", end='')
        print()


# ---------------------------------------------------------------------------
# Table 5: Party stratification
# ---------------------------------------------------------------------------

def table7_party(all_bills: dict[str, list], party_file: str = 'data/sponsor_parties.csv'):
    """
    Print Table 5: stratified transition probabilities by party.

    Uses trajectory-level rates (% of introduced bills per party) to match
    the paper's Table 5.

    Requires party_file: CSV with columns bill_num, year, party.
    """
    if not os.path.exists(party_file):
        print(f"\n[Table 5 skipped: {party_file} not found]")
        print("  To generate, create a CSV with columns: bill_num, year, party")
        print("  where party is 'D' (majority) or 'R' (minority) for each bill.")
        return

    header("TABLE 5 — Party-stratified failure rates (% of introduced bills)")
    print("  [PRIMARY specification: ALL primary sponsors, none excluded]")

    # Load party data
    party_map = {}
    with open(party_file) as f:
        for row in csv.DictReader(f):
            party_map[(int(row['bill_num']), row['year'])] = row['party']

    # The primary specification excludes NO sponsor. The Herod/McCluskie removal
    # is a robustness check only (see table7_party_exclusion_robustness below and
    # paper Section "Robustness"). We therefore build no exclusion set here.
    _run_party_table(all_bills, party_map, exclude_sponsor=None, party_file=party_file)


# Sponsors removed only in the robustness specification (paper Section 3.3 / Robustness).
ROBUSTNESS_EXCLUDE_SPONSORS = {'HEROD', 'MCCLUSKIE'}


def table7_party_exclusion_robustness(all_bills: dict[str, list],
                                      party_file: str = 'data/sponsor_parties.csv'):
    """Robustness variant of Table 5: drop Herod/McCluskie budget-leadership bills.

    Reported in the paper's Robustness section, NOT as the primary table. Requires
    a 'sponsor' column in the party CSV to identify the excluded sponsorships.
    """
    if not os.path.exists(party_file):
        print(f"\n[Table 5 robustness skipped: {party_file} not found]")
        return
    party_map, sponsor_map = {}, {}
    with open(party_file) as f:
        rdr = csv.DictReader(f)
        has_sponsor = 'sponsor' in (rdr.fieldnames or [])
        for row in rdr:
            key = (int(row['bill_num']), row['year'])
            party_map[key] = row['party']
            if has_sponsor:
                sponsor_map[key] = (row.get('sponsor') or '').strip().upper()
    if not sponsor_map:
        print("\n[Table 5 robustness skipped: party CSV has no 'sponsor' column]")
        return
    excl = {k for k, sp in sponsor_map.items()
            if any(sp == e or sp.startswith(e + ' ') for e in ROBUSTNESS_EXCLUDE_SPONSORS)}
    header("TABLE 5 (ROBUSTNESS) — Party rates excluding Herod/McCluskie")
    print(f"  [ROBUSTNESS specification: {len(excl)} budget/leadership bills removed]")
    _run_party_table(all_bills, party_map, exclude_sponsor=excl, party_file=party_file)


def _run_party_table(all_bills, party_map, exclude_sponsor, party_file):
    """Shared body: print party-stratified failure shares.

    exclude_sponsor : set of (bill_num, year) keys to drop, or None for all-sponsor.
    """
    excl = exclude_sponsor or set()
    years = sorted(all_bills.keys())
    # All numerators use trajectory-level failure classes
    metrics = [
        ('InComm -> Failed',
         lambda b: b['state_seq'] == 'Introduced -> In_Committee -> Failed'),
        ('OOC -> Failed',
         lambda b: b['state_seq'] == 'Introduced -> In_Committee -> Out_of_Committee -> Failed'),
        ('Floor -> Failed',
         lambda b: b['state_seq'] == 'Introduced -> In_Committee -> Out_of_Committee -> On_Floor -> Failed'),
        ('P(Pass|Intro)',
         lambda b: b['markov'] == 'Passed'),
    ]

    print(f"{'Metric':<20}", end='')
    for yr in years:
        print(f"   Maj({yr})  Min({yr})", end='')
    print()
    print('-' * (20 + len(years)*18))

    def _keep(b, yr):
        return (b['bill_num'], yr) not in excl

    for label, numer_fn in metrics:
        print(f"{label:<20}", end='')
        for yr in years:
            bills = [b for b in all_bills[yr] if _keep(b, yr)]
            maj_d = [b for b in bills if party_map.get((b['bill_num'], yr), '') == 'D']
            min_d = [b for b in bills if party_map.get((b['bill_num'], yr), '') == 'R']
            maj_rate = sum(1 for b in maj_d if numer_fn(b)) / len(maj_d) if maj_d else 0
            min_rate = sum(1 for b in min_d if numer_fn(b)) / len(min_d) if min_d else 0
            print(f"   {maj_rate:7.1%}  {min_rate:7.1%}", end='')
        print()

    # Print N
    print(f"{'N':<20}", end='')
    for yr in years:
        bills = [b for b in all_bills[yr] if _keep(b, yr)]
        maj_n = sum(1 for b in bills if party_map.get((b['bill_num'], yr), '') == 'D')
        min_n = sum(1 for b in bills if party_map.get((b['bill_num'], yr), '') == 'R')
        print(f"   {maj_n:>7d}  {min_n:>7d}", end='')
    print()


# ---------------------------------------------------------------------------
# Table 8: Time heterogeneity
# ---------------------------------------------------------------------------

def table8_time_heterogeneity(all_bills: dict[str, list]):
    """Print Table 8: OOC -> Failed rate by introduction cohort (chi-sq tests).

    Uses trajectory-level OOC->Failed rate (OOC_F / all introduced in cohort),
    matching the paper's Table 8.
    """
    header("TABLE 8 — OOC -> Failed rate by introduction cohort")

    years = sorted(all_bills.keys())
    cohort_labels = ['Early tertile', 'Middle tertile', 'Late tertile']

    # Tertile split: use all bills (bill-number order = intro-date order for CO)
    print(f"{'Cohort':<20}", end='')
    for yr in years:
        print(f"  {yr:>14}", end='')
    print()
    print('-' * (20 + len(years)*16))

    chi2_stats = []
    for yr in years:
        bills = all_bills[yr]
        n = len(bills)
        t1 = n // 3
        t2 = 2 * n // 3
        cohorts = [bills[:t1], bills[t1:t2], bills[t2:]]
        chi2_stats.append((yr, cohorts))

    # Print per-tertile OOC->Failed counts as % of cohort total
    for cohort_idx, cohort_name in enumerate(cohort_labels):
        print(f"{cohort_name:<20}", end='')
        for yr, cohorts in chi2_stats:
            c = cohorts[cohort_idx]
            n_total = len(c)
            n_ooc_f = sum(1 for b in c if b['state_seq'] ==
                          'Introduced -> In_Committee -> Out_of_Committee -> Failed')
            rate = n_ooc_f / n_total if n_total > 0 else 0
            print(f"  {rate:5.1%} ({n_ooc_f}/{n_total})", end='')
        print()

    # Aggregate
    print('-' * (20 + len(years)*16))
    print(f"{'Aggregate rate':<20}", end='')
    for yr in years:
        bills = all_bills[yr]
        n_total = len(bills)
        n_ooc_f = sum(1 for b in bills if b['state_seq'] ==
                      'Introduced -> In_Committee -> Out_of_Committee -> Failed')
        rate = n_ooc_f / n_total if n_total > 0 else 0
        print(f"  {rate:14.1%}", end='')
    print()

    print(f"{'chi2 statistic':<20}", end='')
    for yr, cohorts in chi2_stats:
        table = []
        for c in cohorts:
            n_total = len(c)
            n_ooc_f = sum(1 for b in c if b['state_seq'] ==
                          'Introduced -> In_Committee -> Out_of_Committee -> Failed')
            table.append([n_ooc_f, n_total - n_ooc_f])
        try:
            chi2, p, dof, _ = chi2_contingency(table)
            stars = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else ''))
            print(f"  {chi2:5.2f}{stars:3s} (p={p:.2f})", end='')
        except Exception:
            print(f"  {'N/A':>14}", end='')
    print()


# ---------------------------------------------------------------------------
# Table A1: Bootstrap confidence intervals
# ---------------------------------------------------------------------------

def tableA1_bootstrap(all_bills: dict[str, list], n_resamples: int = 5000):
    """Print Appendix Table A1: bootstrap 95% confidence intervals."""
    header("TABLE A1 — Bootstrap 95% confidence intervals")
    print(f"  ({n_resamples} resamples per session)\n")

    years = sorted(all_bills.keys())

    stat_labels = [
        ('Bottleneck rate',         'bottleneck_rate',    True),
        ('Floor failure rate',      'floor_failure_rate', True),
        ('Passage rate B[0,0]',     'passage_rate',       True),
        ('Floor sensitivity -N[0,3]', 'floor_sensitivity', False),
        ('OOC sensitivity -N[0,2]*B[3,0]', 'ooc_sensitivity', False),
    ]

    fmt = f"  {'Statistic':<35} {'Session':>7} {'Point':>8} {'SD':>7} {'95% CI lower':>13} {'95% CI upper':>13}"
    print(fmt)
    print('  ' + '-' * 83)

    for label, key, is_pct in stat_labels:
        for yr in years:
            bills = all_bills[yr]
            boot = bootstrap_chain(bills, n_resamples=n_resamples)
            point = compute_chain(bills)

            if key == 'bottleneck_rate':
                pt = point.bottleneck_rate
            elif key == 'floor_failure_rate':
                pt = point.R[3, 1]
            elif key == 'passage_rate':
                pt = point.B[0, 0]
            elif key == 'floor_sensitivity':
                pt = point.floor_sensitivity
            elif key == 'ooc_sensitivity':
                pt = point.ooc_sensitivity

            lo, hi, sd = bootstrap_ci(boot[key])
            lbl_col = label if yr == years[0] else ''
            if is_pct:
                print(f"  {lbl_col:<35} {yr:>7} {pt:8.1%} {sd:7.4f}  [{lo:.4f}, {hi:.4f}]")
            else:
                print(f"  {lbl_col:<35} {yr:>7} {pt:8.4f} {sd:7.4f}  [{lo:.4f}, {hi:.4f}]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Compute all paper tables.')
    parser.add_argument('--bootstrap', action='store_true',
                        help='Run bootstrap CI table (slow: ~1 min per session)')
    parser.add_argument('--n-resamples', type=int, default=5000)
    parser.add_argument('--party-file', default='data/sponsor_parties.csv')
    args = parser.parse_args()

    print("Loading data...")
    all_bills = {}
    results = {}
    for year, (path, bill_max) in sorted(SESSIONS.items()):
        bills = parse_session(path, year, bill_max)
        all_bills[year] = bills
        results[year] = compute_chain(bills, year=year)
        print(f"  {year}: {len(bills)} bills")

    table1_transitions(results)
    table2_failures(all_bills)
    table3_absorption(results)
    table7_party(all_bills, args.party_file)
    table8_time_heterogeneity(all_bills)

    if args.bootstrap:
        print("\n[Running bootstrap — this takes a few minutes...]")
        tableA1_bootstrap(all_bills, n_resamples=args.n_resamples)
    else:
        print("\n[Appendix bootstrap table skipped; use --bootstrap to run]")
