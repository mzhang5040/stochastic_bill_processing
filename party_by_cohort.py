"""Party gap by introduction-date tertile (robustness check)."""
import csv, re, pdfplumber
import parse_status_sheets as p
from scipy.stats import fisher_exact
import math

# Load party map
party = {}
with open('data/sponsor_parties.csv') as f:
    for row in csv.DictReader(f):
        party[(int(row['bill_num']), row['year'])] = row['party']


def cohen_h(p1, p2):
    """Cohen's h for two proportions."""
    if p1 < 0 or p1 > 1 or p2 < 0 or p2 > 1:
        return float('nan')
    return abs(2 * (math.asin(math.sqrt(p1)) - math.asin(math.sqrt(p2))))


def get_intro_date(raw, bn):
    """Find first date in bill block."""
    m = re.search(rf'(?m)^{bn}\*?\s', raw)
    if not m: return None
    rest = raw[m.start():]
    nxt = re.search(r'(?m)^\d{4}\*?\s', rest[10:])
    end = m.start() + 10 + nxt.start() if nxt else m.start() + 300
    block = raw[m.start():end]
    dm = re.search(r'\b(\d{1,2})/(\d{1,2})\b', block)
    if not dm: return None
    return int(dm.group(1)) * 100 + int(dm.group(2))


for year in ['2022', '2023', '2024']:
    path, bmax = p.SESSIONS[year]
    bills = p.parse_session(path, year, bmax)
    with pdfplumber.open(path) as pdf:
        raw = ''.join(pg.extract_text() or '' for pg in pdf.pages)

    # Attach party and intro date
    enriched = []
    for b in bills:
        pt = party.get((b['bill_num'], year))
        dt = get_intro_date(raw, b['bill_num'])
        if pt and dt is not None:
            enriched.append({
                **b,
                'party': pt,
                'intro_sort': dt,
            })

    enriched.sort(key=lambda x: x['intro_sort'])
    n = len(enriched)
    t1 = enriched[:n // 3]
    t2 = enriched[n // 3:2 * n // 3]
    t3 = enriched[2 * n // 3:]

    print(f'\n{"=" * 70}')
    print(f'{year} — N={n}  Early={len(t1)}  Middle={len(t2)}  Late={len(t3)}')
    print(f'{"=" * 70}')

    for label, cohort in [('Early', t1), ('Middle', t2), ('Late', t3)]:
        dems = [b for b in cohort if b['party'] == 'D']
        reps = [b for b in cohort if b['party'] == 'R']
        nD, nR = len(dems), len(reps)

        # InComm -> Failed
        d_ic = sum(1 for b in dems if b['state_seq'] == 'Introduced -> In_Committee -> Failed')
        r_ic = sum(1 for b in reps if b['state_seq'] == 'Introduced -> In_Committee -> Failed')

        # Overall Pass
        d_pass = sum(1 for b in dems if b['markov'] == 'Passed')
        r_pass = sum(1 for b in reps if b['markov'] == 'Passed')

        p_d_ic = d_ic / nD if nD else 0
        p_r_ic = r_ic / nR if nR else 0
        p_d_pass = d_pass / nD if nD else 0
        p_r_pass = r_pass / nR if nR else 0

        gap_ic = p_r_ic - p_d_ic
        h_ic = cohen_h(p_d_ic, p_r_ic)

        gap_pass = p_r_pass - p_d_pass
        h_pass = cohen_h(p_d_pass, p_r_pass)

        # Fisher test for InComm gap
        odds, pval_ic = fisher_exact([[d_ic, nD - d_ic], [r_ic, nR - r_ic]])

        print(f'\n{label} (nD={nD}, nR={nR}):')
        print(f'  InComm-F: D={p_d_ic*100:.1f}%  R={p_r_ic*100:.1f}%  '
              f'gap=+{gap_ic*100:.1f}pp  h={h_ic:.2f}  p={pval_ic:.4f}')
        print(f'  Pass:     D={p_d_pass*100:.1f}%  R={p_r_pass*100:.1f}%  '
              f'gap={gap_pass*100:+.1f}pp  h={h_pass:.2f}')
