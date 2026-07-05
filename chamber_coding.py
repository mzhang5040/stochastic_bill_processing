"""
chamber_coding.py
=================
Make the bicameral decomposition (Table 6, Table 7, Figure 5) reproducible
from an auditable data file instead of hardcoded counts.

Background
----------
The bicameral decomposition (Tables 6-7) attributes each On-Floor failure to a
mode of death. This module reads the completed manual coding in
`data/chamber_coding.csv`, validates the per-year totals against the corrected
parser's On_Floor -> Failed set, and exposes a `component_counts()` function
that `fig_bicameral` calls instead of a hardcoded dict.

CSV schema
----------
    bill_num    : int   HB number (e.g. 1115).
    year        : str   '2022' | '2023' | '2024'
    chamber     : str   one of: Senate-side | House-side | Veto | Session-end
                        (see Section 3.5 in the paper for the coding rule)
    policy_area : str   optional, used for the 2023 Table 6 breakdown
    note        : str   optional free text
    verified    : str   'YES' once the row is confirmed against the raw
                        status-sheet text

All 62 rows are coded and verified. The validator below fails loudly if any
per-year total drifts from the parser's actual On_Floor -> Failed set.

Usage
-----
    # 1. Audit / integrity check against the corrected parser:
    python chamber_coding.py

    # 2. In generate_figures.fig_bicameral, replace the hardcoded `data`
    #    dict with:
    #        from chamber_coding import component_counts
    #        counts = component_counts()
    #        data = {yr: [counts[yr][c] for c in COMPONENTS] for yr in sessions}
"""

import csv
import os
from collections import Counter, defaultdict

CSV_PATH = os.environ.get('CHAMBER_CSV', 'data/chamber_coding.csv')

COMPONENTS = ['Senate-side', 'House-side', 'Veto', 'Session-end']

# Paper Table 6 target counts (used only as a fallback sanity reference; the
# authoritative check is against the live parser -- see validate()).
PAPER_TABLE7 = {
    '2022': {'Senate-side': 6, 'House-side': 2, 'Veto': 4, 'Session-end': 2},
    '2023': {'Senate-side': 10, 'House-side': 1, 'Veto': 6, 'Session-end': 2},
    '2024': {'Senate-side': 12, 'House-side': 3, 'Veto': 5, 'Session-end': 9},
}


def load_rows(path=CSV_PATH):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def component_counts(path=CSV_PATH):
    """Return {year: {component: count}} computed from the CSV."""
    rows = load_rows(path)
    out = defaultdict(lambda: {c: 0 for c in COMPONENTS})
    for r in rows:
        yr, comp = r['year'], r['chamber'].strip()
        if comp not in COMPONENTS:
            raise ValueError(f"Unknown chamber label {comp!r} "
                             f"(bill {r.get('bill_num')}, {yr})")
        out[yr][comp] += 1
    return {y: dict(v) for y, v in out.items()}


def derived_shares(path=CSV_PATH):
    """Reproduce the paper's headline bicameral percentages from the CSV."""
    cc = component_counts(path)
    shares = {}
    for yr, c in cc.items():
        total = sum(c.values())
        senate_or_veto = c['Senate-side'] + c['Veto']
        senate_veto_end = senate_or_veto + c['Session-end']
        shares[yr] = {
            'total': total,
            'senate_side_strict_pct': 100 * c['Senate-side'] / total,
            'senate_or_veto_pct': 100 * senate_or_veto / total,   # paper: 71/84/72
            'senate_veto_end_pct': 100 * senate_veto_end / total,  # paper 2023: 95
            'house_strict_pct': 100 * c['House-side'] / total,     # paper 2024: 10
        }
    return shares


def validate(all_bills=None, path=CSV_PATH, strict=True):
    """
    Integrity check. Confirms:
      1. every row has a valid chamber label,
      2. per-year totals equal the number of On_Floor->Failed bills the
         corrected parser produces (if `all_bills` supplied) -- otherwise
         falls back to comparing against PAPER_TABLE7 totals,
      3. no duplicate (bill_num, year) among verified rows,
      4. reports how many rows are unverified (should be 0).
    Returns True on success; raises AssertionError on a hard mismatch.
    """
    rows = load_rows(path)
    cc = component_counts(path)

    # (3) duplicate verified bills
    seen = Counter((r['bill_num'], r['year'])
                   for r in rows if r['verified'].strip().upper() == 'YES'
                   and str(r['bill_num']).strip())
    dupes = [k for k, n in seen.items() if n > 1]
    assert not dupes, f"Duplicate verified (bill,year): {dupes}"

    # (2) totals
    if all_bills is not None:
        parser_floor_fail = {}
        for yr, bills in all_bills.items():
            parser_floor_fail[yr] = sum(
                1 for b in bills
                if 'On_Floor' in b['state_seq'] and b['markov'] == 'Failed')
    else:
        parser_floor_fail = {y: sum(PAPER_TABLE7[y].values())
                             for y in PAPER_TABLE7}

    ok = True
    print(f"{'Year':<6}{'CSV total':>10}{'target':>8}{'match':>7}   per-component")
    for yr in sorted(cc):
        csv_total = sum(cc[yr].values())
        target = parser_floor_fail.get(yr)
        match = (csv_total == target)
        ok &= match
        comp_str = ', '.join(f"{c}={cc[yr][c]}" for c in COMPONENTS)
        print(f"{yr:<6}{csv_total:>10}{str(target):>8}{'  OK' if match else ' FAIL':>7}   {comp_str}")

    n_unverified = sum(1 for r in rows
                       if r['verified'].strip().upper() != 'YES')
    n_missing_id = sum(1 for r in rows if not str(r['bill_num']).strip())
    print(f"\nRows: {len(rows)} total, {n_unverified} unverified, "
          f"{n_missing_id} with no bill_num yet (fill these from the PDFs).")

    if strict:
        assert ok, ("CSV per-year totals do not match the target floor-failure "
                    "counts. Do NOT edit counts to force a match -- if the "
                    "parser disagrees with the paper, that is a finding.")
    return ok


def print_shares(path=CSV_PATH):
    print("\nDerived shares (compare to paper Table 7 / Robustness):")
    print("  paper: senate-or-veto = 71% (2022), 84% (2023), 72% (2024);")
    print("         +session-end 2023 = 95%; house-strict 2024 = 10%")
    for yr, s in sorted(derived_shares(path).items()):
        print(f"  {yr}: n={s['total']:>2}  "
              f"Sen-strict={s['senate_side_strict_pct']:.0f}%  "
              f"Sen+veto={s['senate_or_veto_pct']:.0f}%  "
              f"Sen+veto+end={s['senate_veto_end_pct']:.0f}%  "
              f"House-strict={s['house_strict_pct']:.0f}%")


def table6(path=CSV_PATH):
    """Print Table 6: the 2023 Senate-side On-Floor failures by policy area."""
    import csv as _csv
    rows = [r for r in _csv.DictReader(open(path))
            if r['year'] == '2023' and r['chamber'] == 'Senate-side']
    missing = [r['bill_num'] for r in rows if not (r.get('policy_area') or '').strip()]
    if missing:
        raise SystemExit(
            "VALIDATION FAILED: 2023 Senate-side rows with empty policy_area: "
            + ", ".join(missing) + ". Populate policy_area in data/chamber_coding.csv "
            "(see Table 6) before running.")
    by_area = {}
    for r in rows:
        by_area.setdefault(r['policy_area'] or 'Unclassified', []).append(int(r['bill_num']))
    print("\nTABLE 6 -- 2023 Senate-side On-Floor failures by policy area")
    print("-" * 60)
    total = 0
    for area in sorted(by_area, key=lambda a: (-len(by_area[a]), a)):
        bills = sorted(by_area[area]); total += len(bills)
        print(f"  {area:<32} {', '.join('HB'+str(b) for b in bills):<28} n={len(bills)}")
    print("-" * 60)
    print(f"  {'Total':<32} {'':<28} n={total}")

if __name__ == '__main__':
    # Try to validate against the live parser if the PDFs are present;
    # otherwise validate against the paper's Table 6 totals.
    all_bills = None
    try:
        from parse_status_sheets import parse_session, SESSIONS
        if all(os.path.exists(p) for p, _ in SESSIONS.values()):
            all_bills = {y: parse_session(p, y, m)
                         for y, (p, m) in SESSIONS.items()}
            print("[validating against live parser output]\n")
        else:
            print("[PDFs not found -- validating against paper Table 7 totals]\n")
    except Exception as e:
        print(f"[parser unavailable ({e}) -- validating against Table 6]\n")

    validate(all_bills)
    print_shares()
    table6()



