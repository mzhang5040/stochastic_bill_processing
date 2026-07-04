"""
validate_clearance.py
=====================
Independent validation pass for the first-committee coding rule.

Draws a reproducible random sample (fixed seed) of bills the parser classifies
as clearing their first House committee (i.e. reaching Out_of_Committee), then
re-derives, from the raw status-sheet text for each sampled bill, whether the
FIRST committee actually reported/referred the bill (cleared) or postponed it
indefinitely (killed). A discrepancy is a sampled bill whose raw first-committee
disposition is a PI (kill) even though the parser labeled it cleared -- i.e. a
false-positive clearance.

The independent re-derivation here does NOT call the parser's
`_classify_first_committee`; it scans the first committee's full action region
in the raw text separately, so the check can catch an implementation error in
the primary rule.

Writes `validation_sample.csv` (the 100 bills with their raw evidence and both
labels) for human inspection, and prints the discrepancy count.

Usage:  python validate_clearance.py [--n 100] [--seed 20240101]
"""

import argparse
import csv
import random
import re

import parse_status_sheets as pss
from parse_status_sheets import SESSIONS, _COMMITTEE_RE


def raw_text_by_bill(pdf_path, bill_max):
    """Return {bill_num: raw_row_text} using the parser's own extraction/splitting
    (first occurrence per bill, matching parse_session's dedup)."""
    raw = pss._extract_text(pdf_path)
    blocks = pss._split_into_bill_blocks(raw)
    out = {}
    for block in blocks:
        nm = re.match(r'^(\d{4})', block[0].strip())
        if not nm:
            continue
        num = int(nm.group(1))
        if num < 1001 or num > bill_max:
            continue
        if num not in out:
            out[num] = ' '.join(block)
    return out


def independent_first_committee(text):
    """Re-derive the first committee's disposition from raw text, independently
    of _classify_first_committee.

    Returns ('cleared'|'killed'|'unclear', evidence_snippet).
    """
    m = re.search(rf'\b({_COMMITTEE_RE})\b', text)
    if not m:
        return 'unclear', ''
    after = text[m.end():]
    # Region belonging to the first committee = up to the next committee code.
    nxt = re.search(rf'\b{_COMMITTEE_RE}\b', after)
    region = (after[:nxt.start()] if nxt else after).strip()
    snippet = (m.group(1) + ' ' + region)[:70]

    pi = re.search(r'PI\s?\d{1,2}/\d{1,2}', region)             # postponed indefinitely
    referral = re.search(r'\bR\s?\d{1,2}/\d{1,2}', region)       # referred onward
    report = re.search(r'(?<![A-Za-z/])\d{1,2}/\d{1,2}\*?', region)  # bare report date

    # First committee killed the bill iff a PI is the leading disposition
    # (nothing that advances it appears before the PI).
    if pi and not (
        (referral and referral.start() < pi.start()) or
        (report and report.start() < pi.start())
    ):
        return 'killed', snippet
    if referral or report or nxt is not None:
        return 'cleared', snippet
    return 'unclear', snippet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--seed', type=int, default=20240101)
    ap.add_argument('--out', default='validation_sample.csv')
    args = ap.parse_args()

    # Population: bills the parser classifies as clearing first committee.
    cleared = []
    rawmaps = {}
    for yr, (path, bmax) in sorted(SESSIONS.items()):
        bills = pss.parse_session(path, yr, bmax)
        rawmaps[yr] = raw_text_by_bill(path, bmax)
        for b in bills:
            if '-> Out_of_Committee' in b['state_seq']:
                cleared.append((yr, b['bill_num']))

    print(f"Population of parser-classified first-committee clearances: {len(cleared)}")

    rng = random.Random(args.seed)
    sample = rng.sample(cleared, min(args.n, len(cleared)))
    sample.sort()

    rows, discrepancies = [], 0
    for yr, num in sample:
        text = rawmaps[yr].get(num, '')
        verdict, snip = independent_first_committee(text)
        agree = (verdict == 'cleared')
        if not agree:
            discrepancies += 1
        rows.append({'year': yr, 'bill_num': num,
                     'parser_label': 'cleared',
                     'independent_label': verdict,
                     'agree': 'YES' if agree else 'NO',
                     'first_committee_evidence': snip})

    with open(args.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['year', 'bill_num', 'parser_label',
                                          'independent_label', 'agree',
                                          'first_committee_evidence'])
        w.writeheader()
        w.writerows(rows)

    print(f"Sample size: {len(sample)} (seed={args.seed})")
    print(f"Discrepancies (independent review disagrees with 'cleared'): {discrepancies}")
    print(f"Audit written to: {args.out}")
    if discrepancies:
        print("\nDiscrepant bills:")
        for r in rows:
            if r['agree'] == 'NO':
                print(f"  {r['year']} HB{r['bill_num']}: {r['independent_label']} | {r['first_committee_evidence']}")


if __name__ == '__main__':
    main()
