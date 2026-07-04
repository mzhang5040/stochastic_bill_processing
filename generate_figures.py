"""Generate publication-quality figures for the SIURO paper.

Outputs to ./figures/ as PNG files (or the FIGDIR environment variable).
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_status_sheets as pss
import markov_chain as mc

# Publication-quality defaults
mpl.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 10,
    'axes.titlesize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'axes.linewidth': 0.6,
    'xtick.major.width': 0.6,
    'ytick.major.width': 0.6,
    'axes.grid': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.edgecolor': 'black',
    'text.usetex': False,
})

import os as _os
FIGDIR = _os.environ.get('FIGDIR', 'figures')
_os.makedirs(FIGDIR, exist_ok=True)

CHAINS = {}
BILLS = {}
for year in ['2022', '2023', '2024']:
    path, bmax = pss.SESSIONS[year]
    bills = pss.parse_session(path, year, bmax)
    BILLS[year] = bills
    CHAINS[year] = mc.compute_chain(bills, year=year)


def fig_transition_probabilities():
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    sessions = ['2022', '2023', '2024']
    transitions = [
        (r'InComm$\to$OOC',    lambda r: r.Q[1, 2]),
        (r'InComm$\to$Failed', lambda r: r.R[1, 1]),
        (r'OOC$\to$Floor',     lambda r: r.Q[2, 3]),
        (r'OOC$\to$Failed',    lambda r: r.R[2, 1]),
        (r'Floor$\to$Passed',  lambda r: r.R[3, 0]),
        (r'Floor$\to$Failed',  lambda r: r.R[3, 1]),
    ]
    x = np.arange(len(transitions))
    width = 0.26
    colors = ['#4a7bb6', '#7aa4cc', '#d4856c']
    for i, yr in enumerate(sessions):
        r = CHAINS[yr]
        vals = [getter(r) for _, getter in transitions]
        offset = (i - 1) * width
        ax.bar(x + offset, vals, width, label=yr, color=colors[i],
               edgecolor='black', linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels([label for label, _ in transitions], rotation=20, ha='right')
    ax.set_ylabel(r'Estimated probability $\hat{p}_{ij}$')
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.grid(axis='y', alpha=0.3, linewidth=0.4)
    ax.set_axisbelow(True)
    ax.legend(title='Session', frameon=False, loc='upper right')
    fig.tight_layout()
    fig.savefig(f'{FIGDIR}/transition_probs.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  Saved: transition_probs.png')


def fig_party_gap():
    import csv
    party = {}
    with open('/home/claude/work/data/sponsor_parties.csv') as f:
        for r in csv.DictReader(f):
            party[(int(r['bill_num']), r['year'])] = r['party']

    fig, axes = plt.subplots(1, 3, figsize=(7.8, 3.2), sharey=True)
    sessions = ['2022', '2023', '2024']
    stages = [r'IC$\to$Failed', r'OOC$\to$Failed', r'Floor$\to$Failed']
    stage_keys = [
        'Introduced -> In_Committee -> Failed',
        'Introduced -> In_Committee -> Out_of_Committee -> Failed',
        'Introduced -> In_Committee -> Out_of_Committee -> On_Floor -> Failed',
    ]

    for ax_i, yr in enumerate(sessions):
        ax = axes[ax_i]
        bills = BILLS[yr]
        D = [b for b in bills if party.get((b['bill_num'], yr)) == 'D']
        R = [b for b in bills if party.get((b['bill_num'], yr)) == 'R']
        d_rates = [sum(1 for b in D if b['state_seq'] == k) / len(D) * 100 for k in stage_keys]
        r_rates = [sum(1 for b in R if b['state_seq'] == k) / len(R) * 100 for k in stage_keys]

        x = np.arange(len(stages))
        width = 0.38
        ax.bar(x - width/2, d_rates, width,
               label=f'Majority (D), n={len(D)}',
               color='#4a7bb6', edgecolor='black', linewidth=0.4)
        ax.bar(x + width/2, r_rates, width,
               label=f'Minority (R), n={len(R)}',
               color='#d4856c', edgecolor='black', linewidth=0.4)
        ax.set_xticks(x)
        ax.set_xticklabels(stages, rotation=20, ha='right', fontsize=8)
        ax.set_title(f'{yr}', fontsize=10)
        ax.grid(axis='y', alpha=0.3, linewidth=0.4)
        ax.set_axisbelow(True)
        ax.set_ylim(0, 60)
        if ax_i == 0:
            ax.set_ylabel(r'Failure rate (\% of introduced)')
        ax.legend(frameon=False, fontsize=7.5, loc='upper right')

    fig.tight_layout()
    fig.savefig(f'{FIGDIR}/party_gap.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  Saved: party_gap.png')


def fig_sensitivities():
    sessions = ['2022', '2023', '2024']
    sens_data = {}
    for yr in sessions:
        bills = BILLS[yr]
        boot = mc.bootstrap_chain(bills, n_resamples=2000, seed=42)
        rng = np.random.default_rng(42)
        inc = []
        for _ in range(2000):
            idx = rng.integers(0, len(bills), len(bills))
            try:
                r = mc.compute_chain([bills[i] for i in idx])
                inc.append(-r.N[0, 1] * r.B[2, 0])
            except Exception:
                pass
        inc = np.array(inc)
        sens_data[yr] = {
            'inc_mean': -CHAINS[yr].N[0, 1] * CHAINS[yr].B[2, 0],
            'inc_ci': (np.percentile(inc, 2.5), np.percentile(inc, 97.5)),
            'floor_mean': CHAINS[yr].floor_sensitivity,
            'floor_ci': (np.percentile(boot['floor_sensitivity'], 2.5),
                         np.percentile(boot['floor_sensitivity'], 97.5)),
            'ooc_mean': CHAINS[yr].ooc_sensitivity,
            'ooc_ci': (np.percentile(boot['ooc_sensitivity'], 2.5),
                       np.percentile(boot['ooc_sensitivity'], 97.5)),
        }

    fig, ax = plt.subplots(figsize=(6.4, 3.5))
    x = np.arange(len(sessions))
    width = 0.26

    def series(key):
        means = [abs(sens_data[yr][key + '_mean']) for yr in sessions]
        err = [
            [abs(sens_data[yr][key + '_mean']) - abs(sens_data[yr][key + '_ci'][1]) for yr in sessions],
            [abs(sens_data[yr][key + '_ci'][0]) - abs(sens_data[yr][key + '_mean']) for yr in sessions],
        ]
        return means, err

    inc_means, inc_err = series('inc')
    floor_means, floor_err = series('floor')
    ooc_means, ooc_err = series('ooc')

    ax.bar(x - width, inc_means, width, yerr=inc_err, capsize=3, ecolor='black',
           label=r'$|$First-cmte$|=N_{0,1}\cdot B_{2,0}$',
           color='#6aa06a', edgecolor='black', linewidth=0.4, error_kw={'elinewidth': 0.8})
    ax.bar(x, floor_means, width, yerr=floor_err, capsize=3, ecolor='black',
           label=r'$|$Floor$|=N_{0,3}$',
           color='#4a7bb6', edgecolor='black', linewidth=0.4, error_kw={'elinewidth': 0.8})
    ax.bar(x + width, ooc_means, width, yerr=ooc_err, capsize=3, ecolor='black',
           label=r'$|$OOC$|=N_{0,2}\cdot B_{3,0}$',
           color='#d4856c', edgecolor='black', linewidth=0.4, error_kw={'elinewidth': 0.8})

    ax.set_xticks(x)
    ax.set_xticklabels(sessions)
    ax.set_xlabel('Session')
    ax.set_ylabel(r'Sensitivity magnitude')
    ax.set_ylim(0.65, 0.96)
    ax.legend(frameon=False, loc='lower left', fontsize=8)
    ax.grid(axis='y', alpha=0.3, linewidth=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(f'{FIGDIR}/sensitivities.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  Saved: sensitivities.png')


def fig_cohorts():
    import re, pdfplumber
    fig, ax = plt.subplots(figsize=(5.5, 3.3))
    sessions = ['2022', '2023', '2024']
    colors = ['#4a7bb6', '#7aa4cc', '#d4856c']
    markers = ['o', 's', '^']
    tertile_labels = ['Early', 'Middle', 'Late']
    OOC_FAIL = 'Introduced -> In_Committee -> Out_of_Committee -> Failed'

    def intro_date(raw, bn):
        m = re.search(rf'(?m)^{bn}\*?\s', raw)
        if not m:
            return None
        rest = raw[m.start():]
        nxt = re.search(r'(?m)^\d{4}\*?\s', rest[10:])
        end = m.start() + 10 + nxt.start() if nxt else m.start() + 300
        dm = re.search(r'\b(\d{1,2})/(\d{1,2})\b', raw[m.start():end])
        return int(dm.group(1)) * 100 + int(dm.group(2)) if dm else None

    for yr, color, marker in zip(sessions, colors, markers):
        path, _ = pss.SESSIONS[yr]
        raw = ''.join(p.extract_text() or '' for p in pdfplumber.open(path).pages)
        dated = [(intro_date(raw, b['bill_num']), b) for b in BILLS[yr]
                 if intro_date(raw, b['bill_num']) is not None]
        dated.sort(key=lambda x: x[0])
        n = len(dated)
        cohorts = [dated[:n // 3], dated[n // 3:2 * n // 3], dated[2 * n // 3:]]
        ooc_rates, errs = [], []
        for c in cohorts:
            reach = sum(1 for _, b in c if 'Out_of_Committee' in b['state_seq'])
            ooc_f = sum(1 for _, b in c if b['state_seq'] == OOC_FAIL)
            p = ooc_f / reach
            ooc_rates.append(p * 100)
            errs.append(1.96 * np.sqrt(p * (1 - p) / reach) * 100)

        x = np.arange(3)
        ax.errorbar(x, ooc_rates, yerr=errs, fmt=marker + '-', capsize=3,
                    color=color, linewidth=1.2, markersize=6, label=yr,
                    elinewidth=0.8)

    ax.set_xticks(range(3))
    ax.set_xticklabels(tertile_labels)
    ax.set_xlabel('Introduction-date tertile')
    ax.set_ylabel(r'Conditional OOC failure rate (\% of bills reaching OOC)')
    ax.set_ylim(0, 22)
    ax.legend(title='Session', frameon=False, loc='upper right')
    ax.grid(axis='y', alpha=0.3, linewidth=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(f'{FIGDIR}/cohorts.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  Saved: cohorts.png')


def fig_bicameral():
    fig, ax = plt.subplots(figsize=(6.0, 3.3))
    sessions = ['2022', '2023', '2024']
    # Counts are computed from data/chamber_coding.csv (the manual chamber-level
    # coding of every On_Floor -> Failed bill), not hardcoded. The loader
    # validates that per-year totals equal the parser's floor-failure counts.
    from chamber_coding import component_counts
    cc = component_counts()
    csv_components = ['Senate-side', 'House-side', 'Veto', 'Session-end']
    data = {yr: [cc.get(yr, {}).get(c, 0) for c in csv_components]
            for yr in sessions}
    components = ['Senate-side', 'House-side', 'Gubernatorial veto', 'Session-end']
    colors = ['#4a7bb6', '#b8dfe8', '#d4856c', '#f0c674']

    x = np.arange(len(sessions))
    bottom = np.zeros(len(sessions))
    for i, comp in enumerate(components):
        vals = [data[yr][i] for yr in sessions]
        ax.bar(x, vals, bottom=bottom, label=comp, color=colors[i],
               edgecolor='black', linewidth=0.4)
        bottom += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels(sessions)
    ax.set_xlabel('Session')
    ax.set_ylabel('Floor failures (count)')
    totals = {yr: int(sum(data[yr])) for yr in sessions}
    for i, yr in enumerate(sessions):
        ax.text(i, totals[yr] + 0.7, f'n={totals[yr]}', ha='center', fontsize=9)

    ax.set_ylim(0, 34)
    ax.legend(frameon=False, loc='upper left', fontsize=8.5)
    ax.grid(axis='y', alpha=0.3, linewidth=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(f'{FIGDIR}/bicameral.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  Saved: bicameral.png')


if __name__ == '__main__':
    print('Generating figures...')
    fig_transition_probabilities()
    fig_party_gap()
    fig_sensitivities()
    fig_cohorts()
    fig_bicameral()
    print('Done.')
