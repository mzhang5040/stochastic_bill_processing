"""Mantel-Haenszel pooled party effect controlling for cohort."""
import csv, re, pdfplumber
import parse_status_sheets as p
import math

party = {}
with open('data/sponsor_parties.csv') as f:
    for row in csv.DictReader(f):
        party[(int(row['bill_num']), row['year'])] = row['party']


def get_intro_date(raw, bn):
    m = re.search(rf'(?m)^{bn}\*?\s', raw)
    if not m: return None
    rest = raw[m.start():]
    nxt = re.search(r'(?m)^\d{4}\*?\s', rest[10:])
    end = m.start() + 10 + nxt.start() if nxt else m.start() + 300
    block = raw[m.start():end]
    dm = re.search(r'\b(\d{1,2})/(\d{1,2})\b', block)
    if not dm: return None
    return int(dm.group(1)) * 100 + int(dm.group(2))


print('Cohort-adjusted party gap at first committee (MH pooled by tertile)')
print('=' * 70)

for year in ['2022', '2023', '2024']:
    path, bmax = p.SESSIONS[year]
    bills = p.parse_session(path, year, bmax)
    with pdfplumber.open(path) as pdf:
        raw = ''.join(pg.extract_text() or '' for pg in pdf.pages)
    enriched = []
    for b in bills:
        pt = party.get((b['bill_num'], year))
        dt = get_intro_date(raw, b['bill_num'])
        if pt and dt is not None:
            enriched.append({**b, 'party': pt, 'intro_sort': dt})

    enriched.sort(key=lambda x: x['intro_sort'])
    n = len(enriched)
    cohorts = [enriched[:n // 3], enriched[n // 3:2 * n // 3], enriched[2 * n // 3:]]

    # Mantel-Haenszel estimate for InComm-F odds ratio
    # Strata k: compute a_k, b_k, c_k, d_k, n_k
    # a_k = Republican-InComm-F, b_k = Republican-not
    # c_k = Democratic-InComm-F, d_k = Democratic-not
    num = 0
    den = 0
    total_mh_num = 0
    total_mh_den = 0

    for k, cohort in enumerate(cohorts):
        D = [b for b in cohort if b['party'] == 'D']
        R = [b for b in cohort if b['party'] == 'R']
        a = sum(1 for b in R if b['state_seq'] == 'Introduced -> In_Committee -> Failed')
        b_ = len(R) - a
        c = sum(1 for b in D if b['state_seq'] == 'Introduced -> In_Committee -> Failed')
        d = len(D) - c
        n_k = a + b_ + c + d
        if n_k == 0: continue

        num += a * d / n_k
        den += b_ * c / n_k

        print(f'  {year} tertile {k+1}: R InComm-F = {a}/{a+b_}, D InComm-F = {c}/{c+d}')

    or_mh = num / den if den > 0 else float('inf')
    print(f'{year} Mantel-Haenszel OR = {or_mh:.2f}')
    print()

    # Also compute cohort-weighted average gap
    sum_gap = 0
    sum_w = 0
    for cohort in cohorts:
        D = [b for b in cohort if b['party'] == 'D']
        R = [b for b in cohort if b['party'] == 'R']
        if not D or not R: continue
        p_d = sum(1 for b in D if b['state_seq'] == 'Introduced -> In_Committee -> Failed') / len(D)
        p_r = sum(1 for b in R if b['state_seq'] == 'Introduced -> In_Committee -> Failed') / len(R)
        # weight by min(nD, nR)
        w = min(len(D), len(R))
        sum_gap += (p_r - p_d) * w
        sum_w += w
    if sum_w > 0:
        avg_gap = sum_gap / sum_w
        print(f'{year} cohort-weighted average InComm gap: +{avg_gap*100:.1f}pp')
    print()
