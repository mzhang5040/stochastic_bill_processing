"""
conditional_analysis.py
=======================
Reproduce the risk-set (conditional) quantities added to the paper in revision,
in response to the observation that Table 5 and Table 8 report failure *shares*
(percent of introduced bills), not conditional transition probabilities.

Produces:
  1. Conditional OOC hazard  P(OOC failure | reached OOC)  by party, per session,
     with Fisher exact tests   (Section 4.4 text).
  2. Cross-session test of the OOC transition on the risk set (Section 4.2 text).
  3. First-committee sensitivity  -N[0,1]*B[2,0]           (Section 4.3 text).
  4. Cohort homogeneity of the OOC transition on the risk set (Section 4.6 text).

Run:
    python conditional_analysis.py
"""
import csv, re
import pdfplumber
from scipy.stats import fisher_exact, chi2_contingency

from parse_status_sheets import parse_session, SESSIONS
from markov_chain import compute_chain

OOC_FAIL = 'Introduced -> In_Committee -> Out_of_Committee -> Failed'


def load_party(path='data/sponsor_parties.csv'):
    m = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            m[(int(r['bill_num']), r['year'])] = r['party']
    return m


def intro_date(raw, bn):
    m = re.search(rf'(?m)^{bn}\*?\s', raw)
    if not m:
        return None
    rest = raw[m.start():]
    nxt = re.search(r'(?m)^\d{4}\*?\s', rest[10:])
    end = m.start() + 10 + nxt.start() if nxt else m.start() + 300
    dm = re.search(r'\b(\d{1,2})/(\d{1,2})\b', raw[m.start():end])
    return int(dm.group(1)) * 100 + int(dm.group(2)) if dm else None


def main():
    party = load_party()
    years = sorted(SESSIONS)

    print('1. CONDITIONAL OOC HAZARD BY PARTY  P(OOC fail | reached OOC)')
    print('   (paper Section 4.4; contrast with the marginal shares in Table 5)')
    print(f'   {"":6}{"Maj (D)":>10}{"Min (R)":>10}{"gap":>9}{"Fisher p":>11}')
    for yr in years:
        path, bmax = SESSIONS[yr]
        bills = parse_session(path, yr, bmax)
        st = {p: {'reach': 0, 'fail': 0} for p in 'DR'}
        for b in bills:
            p = party.get((b['bill_num'], yr))
            if p in st and 'Out_of_Committee' in b['state_seq']:
                st[p]['reach'] += 1
                if b['state_seq'] == OOC_FAIL:
                    st[p]['fail'] += 1
        d, r = st['D'], st['R']
        dr, rr = d['fail'] / d['reach'], r['fail'] / r['reach']
        _, pf = fisher_exact([[d['fail'], d['reach'] - d['fail']],
                              [r['fail'], r['reach'] - r['fail']]])
        print(f'   {yr:6}{dr*100:9.1f}%{rr*100:9.1f}%{(rr-dr)*100:+8.1f}pp{pf:11.4f}'
              f'   [{d["fail"]}/{d["reach"]} vs {r["fail"]}/{r["reach"]}]')

    print('\n2. CROSS-SESSION OOC TRANSITION TEST (risk set vs marginal)')
    marg, cond = [], []
    for yr in years:
        path, bmax = SESSIONS[yr]
        r = compute_chain(parse_session(path, yr, bmax), yr)
        oocF = int(r.counts_R[2, 1]); reach = int(r.counts_Q[1, 2]); n = r.n_bills
        marg.append([oocF, n - oocF]); cond.append([oocF, reach - oocF])
    c1, p1, _, _ = chi2_contingency(marg)
    c2, p2, _, _ = chi2_contingency(cond)
    print(f'   marginal   (/introduced) : chi2={c1:.2f}, p={p1:.3f}')
    print(f'   risk-set   (/reached OOC): chi2={c2:.2f}, p={p2:.3f}   <- reported in revision')

    print('\n3. FIRST-COMMITTEE SENSITIVITY  -N[0,1]*B[2,0]  (paper Section 4.3)')
    for yr in years:
        path, bmax = SESSIONS[yr]
        r = compute_chain(parse_session(path, yr, bmax), yr)
        print(f'   {yr}: -N[0,1]*B[2,0] = {-r.N[0,1]*r.B[2,0]:.4f}   '
              f'(floor {r.floor_sensitivity:.4f}, OOC {r.ooc_sensitivity:.4f})')

    print('\n4. COHORT HOMOGENEITY OF OOC TRANSITION, RISK SET (paper Section 4.6)')
    for yr in years:
        path, bmax = SESSIONS[yr]
        bills = parse_session(path, yr, bmax)
        raw = ''.join(pg.extract_text() or '' for pg in pdfplumber.open(path).pages)
        dated = [(intro_date(raw, b['bill_num']), b) for b in bills
                 if intro_date(raw, b['bill_num']) is not None]
        dated.sort(key=lambda x: x[0])
        n = len(dated)
        groups = [dated[:n // 3], dated[n // 3:2 * n // 3], dated[2 * n // 3:]]
        rows = []
        for g in groups:
            f = sum(1 for _, b in g if b['state_seq'] == OOC_FAIL)
            reach = sum(1 for _, b in g if 'Out_of_Committee' in b['state_seq'])
            rows.append([f, reach - f])
        c, p, _, _ = chi2_contingency(rows)
        print(f'   {yr}: chi2={c:.2f}, p={p:.2f}  -> homogeneity '
              f'{"not rejected" if p > 0.05 else "REJECTED"}')


if __name__ == '__main__':
    main()
