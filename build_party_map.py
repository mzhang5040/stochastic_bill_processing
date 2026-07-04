"""
build_party_map.py
==================
Build a sponsor_parties.csv from the parsed bill list, using publicly-known
party affiliations for the Colorado House across the 73rd and 74th General
Assemblies.

Output: data/sponsor_parties.csv with columns bill_num, year, party
        where party is 'D' (majority Democrat) or 'R' (minority Republican).

Sources for party roster:
  - 73rd GA (2022 session): Colorado House 41D-24R
  - 74th GA (2023-2024):     Colorado House 46D-19R
  - Cross-checked with Colorado Newsline, Colorado Politics, Hall Evans LLC
    reporting on leadership elections and committee assignments (accessed
    through public web searches).

Usage
-----
    python build_party_map.py

This writes data/sponsor_parties.csv.
"""

import csv
import os
import re
import pdfplumber

from parse_status_sheets import parse_session, SESSIONS

# Override the 2024 path to match the uploaded file name.
SESSIONS = dict(SESSIONS)
SESSIONS['2024'] = ('data/2024-house-final-status-sheet-accessible.pdf', 1472)


# -----------------------------------------------------------------
# Party roster for Colorado House Republicans
# -----------------------------------------------------------------
# Anyone NOT on this list is coded as 'D' (majority Democrat).
# Names are matched against the UPPERCASE sponsor name extracted from
# the PDF, so they must be in the canonical form used there.

# 73rd General Assembly (2022 session) - 24 House Republicans
REPUBLICANS_73RD = {
    'BAISLEY', 'BOCKENFELD', 'BRADFIELD', 'CARVER', 'CATLIN',
    'GEITNER', 'HANKS', 'HOLTORF', 'LARSON', 'LUCK',
    'LYNCH', 'MCKEAN', 'NEVILLE', 'PELTON', 'PICO',
    'RANSOM', 'RICH', 'SANDRIDGE', 'SOPER', 'VAN BEBER',
    'VAN WINKLE', 'WILL', 'WILLIAMS', 'WOOG',
}

# 74th General Assembly (2023-2024 sessions) - 19 House Republicans
# Source: leadership election reports plus 2023 session coverage
REPUBLICANS_74TH = {
    'ARMAGOST', 'BOCKENFELD', 'BOTTOMS', 'BRADFIELD', 'BRADLEY',
    'CATLIN', 'DEGRAAF', 'EVANS', 'FRIZELL', 'HARTSOOK',
    'HOLTORF', 'LUCK', 'LYNCH', 'PUGLIESE', 'SOPER',
    'TAGGART', 'WEINBERG', 'WILSON', 'WINTER',  # WINTER = Ty Winter (R)
}

# Budget/leadership sponsors (JBC chair Herod; Speaker McCluskie). These are
# MAJORITY (Democratic) members, so under the all-sponsor PRIMARY specification
# their bills stay in the D pool like everyone else. They are removed only in the
# Table 5 *robustness* variant (results_tables.table7_party_exclusion_robustness),
# which locates them via the 'sponsor' column written below -- NOT here. The map
# is retained for that downstream robustness filter, not to drop rows at build time.
ROBUSTNESS_EXCLUDE_SPONSORS = {
    'MCCLUSKIE', 'HEROD',
}

# Year -> roster map
ROSTERS = {
    '2022': REPUBLICANS_73RD,
    '2023': REPUBLICANS_74TH,
    '2024': REPUBLICANS_74TH,
}


def _extract_primary_sponsor(pdf_path, year, bill_max):
    """
    Re-extract the primary House sponsor name from the PDF for each bill.

    Returns dict: bill_num -> sponsor_name (uppercase, first listed).

    Approach: tokenize each bill line after the bill number, keep the
    leading ALL-CAPS tokens (which form the sponsor block), stop at
    the first token containing a lowercase letter (which marks the
    start of the bill title). Then take everything before the first
    ``&`` as the primary sponsor.
    """
    with pdfplumber.open(pdf_path) as pdf:
        text = ''.join(p.extract_text() or '' for p in pdf.pages)

    sponsors = {}
    for line in text.split('\n'):
        line = line.strip()
        m = re.match(r'^(\d{4})\*?\s+(.*)$', line)
        if not m:
            continue
        bn = int(m.group(1))
        if bn < 1001 or bn > bill_max:
            continue

        # Collect leading all-caps tokens
        tokens = m.group(2).split()
        sponsor_tokens = []
        for t in tokens:
            test = t.rstrip('.,-')
            letters = [c for c in test if c.isalpha()]
            if not letters:
                if t == '&':
                    sponsor_tokens.append(t)
                    continue
                break
            if all(c.isupper() for c in letters):
                sponsor_tokens.append(t)
            else:
                break

        full = ' '.join(sponsor_tokens).strip()
        # First sponsor is everything before "&"
        first = full.split('&')[0].strip().rstrip('-').strip()
        # Strip any short acronym tokens that sometimes appear in bill text
        tokens2 = first.split()
        clean_tokens = []
        for t in tokens2:
            if t in {'CO', 'HOA', 'PERA', 'CASA', 'ABLE', 'FPPA', 'DOC',
                     'ARPA', 'OEDIT', 'S', 'SFC', 'U.S.S.',
                     'CDOT', 'AG', 'DORA', 'DOLA', 'DHS'}:
                break
            clean_tokens.append(t)
        name = ' '.join(clean_tokens).strip()
        if name and bn not in sponsors:
            sponsors[bn] = name
    return sponsors


def _classify(sponsor_name, year):
    """Return 'D' or 'R' for the primary (all-sponsor) specification.

    No sponsor is dropped here: Herod/McCluskie classify as 'D' (they are majority
    members) and are removed only in the downstream robustness variant.
    """
    roster = ROSTERS.get(year, set())
    # Try exact match first
    if sponsor_name in roster:
        return 'R'
    # Try first word (surname) match against roster
    first_word = sponsor_name.split()[0] if sponsor_name else ''
    if first_word in roster:
        return 'R'
    # Check any roster name starts with sponsor first word (e.g. "VAN BEBER")
    for r in roster:
        if r.startswith(first_word + ' ') or r == first_word:
            return 'R'
    # Default to Democrat (majority)
    return 'D'


def main():
    os.makedirs('data', exist_ok=True)
    out_path = 'data/sponsor_parties.csv'

    rows = []
    for year, (path, bill_max) in sorted(SESSIONS.items()):
        if not os.path.exists(path):
            print(f'[{year}: PDF not found, skipping]')
            continue
        sponsors = _extract_primary_sponsor(path, year, bill_max)
        bills = parse_session(path, year, bill_max)
        valid_bns = {b['bill_num'] for b in bills}

        n_r = n_d = n_skip = 0
        for bn in sorted(valid_bns):
            sp = sponsors.get(bn, '')
            party = _classify(sp, year)
            if party is None:
                n_skip += 1
                continue
            rows.append({'bill_num': bn, 'year': year, 'party': party,
                         'sponsor': sp})
            if party == 'R':
                n_r += 1
            else:
                n_d += 1

        print(f'{year}: {n_d} Dem, {n_r} Rep, {n_skip} excluded '
              f'(of {len(valid_bns)} total)')

    with open(out_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['bill_num', 'year', 'party', 'sponsor'])
        w.writeheader()
        w.writerows(rows)

    print(f'\nWrote {len(rows)} rows to {out_path}')


if __name__ == '__main__':
    main()
