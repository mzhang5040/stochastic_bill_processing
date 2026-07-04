import parse_status_sheets as p
import pdfplumber, re
from scipy.stats import chi2_contingency

def cohort_test(year, path, bmax, key_fn):
    bills = p.parse_session(path, year, bmax)
    with pdfplumber.open(path) as pdf:
        raw = ''.join(pg.extract_text() or '' for pg in pdf.pages)
    dated = []
    for b in bills:
        m = re.search(rf'(?m)^{b["bill_num"]}\*?\s', raw)
        if not m: continue
        rest = raw[m.start():]
        nxt = re.search(r'(?m)^\d{4}\*?\s', rest[10:])
        end = m.start() + 10 + nxt.start() if nxt else m.start() + 300
        block = raw[m.start():end]
        dm = re.search(r'\b(\d{1,2})/(\d{1,2})\b', block)
        if dm:
            dated.append((int(dm.group(1))*100+int(dm.group(2)), b))
    dated.sort(key=lambda x: x[0])
    n = len(dated)
    groups = [dated[:n//3], dated[n//3:2*n//3], dated[2*n//3:]]
    rows = []
    for grp in groups:
        yes = sum(1 for _, b in grp if key_fn(b))
        rows.append((yes, len(grp)))
    contingency = [[f, t-f] for f, t in rows]
    chi2, pval, _, _ = chi2_contingency(contingency)
    return chi2, pval, rows

tests = [
    ('InComm->F', lambda b: b['state_seq'] == 'Introduced -> In_Committee -> Failed'),
    ('OOC->F',     lambda b: b['state_seq'] == 'Introduced -> In_Committee -> Out_of_Committee -> Failed'),
    ('Floor->F',   lambda b: b['state_seq'] == 'Introduced -> In_Committee -> Out_of_Committee -> On_Floor -> Failed'),
    ('Passed',     lambda b: b['markov'] == 'Passed'),
]

for year in ['2022', '2023', '2024']:
    print(f'{year}:')
    for name, fn in tests:
        chi2, pval, rows = cohort_test(year, f'data/{year}-house-final-status-sheet-accessible.pdf',
                                        {'2022':1418,'2023':1311,'2024':1472}[year], fn)
        sig = '***' if pval < 0.001 else '**' if pval < 0.01 else '*' if pval < 0.05 else ''
        rates = ' '.join(f'{f}/{t}={f/t*100:.1f}%' for f, t in rows)
        print(f'  {name}: chi2={chi2:.2f}, p={pval:.4f}{sig}  [{rates}]')
    print()
