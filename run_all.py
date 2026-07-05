"""
run_all.py
==========
Master script: parse data, compute all results, and generate all figures
for the paper "Bottlenecks and Committee Filtering: A Markov Chain
Analysis of Bill Progression in the Colorado General Assembly."

This script is a convenience wrapper.  You can also run each module
independently (see each module's Usage section).

Usage
-----
    # Full pipeline (tables + figures, no bootstrap):
    python run_all.py

    # Include bootstrap CIs (adds ~3 min):
    python run_all.py --bootstrap

    # Custom output directories:
    python run_all.py --figures-out my_figures/ --tables-out my_tables.txt

Steps performed
---------------
    1. Parse the three Colorado House status sheet PDFs
    2. Estimate the absorbing Markov chain for each session
    3. Print all paper tables to stdout (or --tables-out file)
    4. Generate Figures 2-6 as PNG files (Figure 1 is a separately maintained schematic)
    5. Optionally compute bootstrap confidence intervals

Data requirements
-----------------
    Place the following PDF files in a data/ subdirectory:
        data/2022-house-final-status-sheet-accessible.pdf
        data/2023-house-final-status-sheet-accessible.pdf
        data/2024-house-final-status-sheet-accessible.pdf

    The PDF files are publicly available from the Colorado General
    Assembly at: https://leg.colorado.gov/bill-search

    Optional (for party stratification table):
        data/sponsor_parties.csv
        Columns: bill_num (int), year (str), party ('D' or 'R')

    Optional (for bicameral decomposition verification):
        data/chamber_coding.csv
        Columns: bill_num (int), year (str),
                 chamber ('Senate', 'House', or 'Session-end')
        This CSV records the manual coding of the 62 On_Floor failures
        (14 in 2022, 19 in 2023, 29 in 2024). See chamber_coding.py, which
        validates these totals against the parser's floor-failure counts.

Requirements
------------
    Python 3.10+
    pdfplumber >= 0.9
    numpy >= 1.24
    scipy >= 1.10
    matplotlib >= 3.7

    Install with:
        pip install pdfplumber numpy scipy matplotlib

File structure
--------------
    run_all.py                  <- this file (master script)
    parse_status_sheets.py      <- PDF parsing
    markov_chain.py             <- chain estimation + bootstrap
    results_tables.py           <- all paper tables
    generate_figures.py         <- all paper figures
    data/                       <- put PDFs here
    figures/                    <- figures written here
"""

import argparse
import sys
import os

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

def _check_deps():
    missing = []
    for pkg in ['pdfplumber', 'numpy', 'scipy', 'matplotlib']:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("Missing required packages:", ', '.join(missing))
        print("Install with:  pip install " + ' '.join(missing))
        sys.exit(1)

_check_deps()

from parse_status_sheets import parse_session, SESSIONS
from markov_chain import compute_chain, bootstrap_chain, bootstrap_ci
from results_tables import (table1_transitions, table2_failures,
                             table3_absorption, table7_party,
                             table7_party_exclusion_robustness,
                             table8_time_heterogeneity, tableA1_bootstrap)
from generate_figures import (fig_transition_probabilities, fig_party_gap,
                               fig_sensitivities, fig_cohorts, fig_bicameral)


def main():
    parser = argparse.ArgumentParser(
        description='Run the full Markov chain legislative analysis pipeline.')
    parser.add_argument('--bootstrap', action='store_true',
                        help='Run Table 4 bootstrap 95% CIs (~3 min)')
    parser.add_argument('--n-resamples', type=int, default=2000,
                        help='Bootstrap resamples (default: 2000, matching the manuscript)')
    parser.add_argument('--figures-out', default='figures',
                        help='Directory for figure PNGs (default: figures/)')
    parser.add_argument('--tables-out', default=None,
                        help='File for table output; default is stdout')
    parser.add_argument('--party-file', default='data/sponsor_parties.csv')
    args = parser.parse_args()

    # Redirect stdout to file if requested
    if args.tables_out:
        sys.stdout = open(args.tables_out, 'w')

    # ------------------------------------------------------------------
    # Step 1: Parse data
    # ------------------------------------------------------------------
    print("=" * 65)
    print("COLORADO MARKOV CHAIN ANALYSIS — FULL PIPELINE")
    print("=" * 65)
    print("\nStep 1: Parsing status sheets...")

    all_bills = {}
    results = {}
    for year, (path, bill_max) in sorted(SESSIONS.items()):
        if not os.path.exists(path):
            print(f"\n  ERROR: {path} not found.")
            print("  Please place the PDF in the data/ directory.")
            print("  Download from: https://leg.colorado.gov/bill-search")
            sys.exit(1)
        bills = parse_session(path, year, bill_max)
        all_bills[year] = bills
        results[year] = compute_chain(bills, year=year)
        print(f"  {year}: {len(bills)} bills  "
              f"(passage rate {results[year].B[0,0]:.1%})")

    total = sum(len(b) for b in all_bills.values())
    print(f"\n  Total: {total} bills across {len(all_bills)} sessions")

    # ------------------------------------------------------------------
    # Step 2: Print tables
    # ------------------------------------------------------------------
    print("\nStep 2: Computing tables...")
    table1_transitions(results)
    table2_failures(all_bills)
    table3_absorption(results)
    table7_party(all_bills, args.party_file)                      # primary: all sponsors
    table7_party_exclusion_robustness(all_bills, args.party_file)  # robustness: drop Herod/McCluskie
    table8_time_heterogeneity(all_bills)

    if args.bootstrap:
        print("\nStep 2b: Bootstrap CIs (this may take a few minutes)...")
        tableA1_bootstrap(all_bills, n_resamples=args.n_resamples)
    else:
        print("\n[Table 4 bootstrap CIs omitted. Use --bootstrap to include.]")

    # Restore stdout if redirected
    if args.tables_out:
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        print(f"Tables written to: {args.tables_out}")

    # ------------------------------------------------------------------
    # Step 3: Generate figures
    # ------------------------------------------------------------------
    print(f"\nStep 3: Generating figures -> {args.figures_out}/")
    os.makedirs(args.figures_out, exist_ok=True)

    # generate_figures.py writes to its own hardcoded FIGDIR; call directly
    # and copy if user specified an alternate output directory
    import generate_figures as gf
    gf.FIGDIR = args.figures_out
    gf.fig_chain()                      # Figure 1 (separately maintained schematic)
    gf.fig_transition_probabilities()   # Figures 2-6 computed from data
    gf.fig_party_gap()
    gf.fig_sensitivities()
    gf.fig_cohorts()
    gf.fig_bicameral()
    print("  Figure 1 is a separately maintained schematic; Figures 2-6 are computed from data.")

    # ------------------------------------------------------------------
    # Step 4: Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("SUMMARY OF KEY RESULTS")
    print("=" * 65)
    for yr in sorted(results):
        r = results[yr]
        print(f"\n{yr}:")
        print(f"  Passage rate:         {r.B[0,0]:.4f}")
        print(f"  OOC failure rate:     {r.bottleneck_rate:.4f}")
        print(f"  Floor failure rate:   {r.R[3,1]:.4f}")
        print(f"  Floor sensitivity:    {r.floor_sensitivity:.4f}")
        print(f"  OOC sensitivity:      {r.ooc_sensitivity:.4f}")

    print("\nDone.")


if __name__ == '__main__':
    main()
