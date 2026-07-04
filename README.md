# Reproduction package — *Bottlenecks and Committee Filtering: A Markov Chain Analysis of Bill Progression in the Colorado General Assembly*

This package reproduces every quantitative result, table, and figure in the JHSS
manuscript from the primary public source data (the Colorado House status
sheets). Given the three status-sheet PDFs (downloaded by `fetch_data.py`) and a
Python environment, running `python run_all.py` regenerates the full analysis.

---

## 1. Contents

```
├── README.md                  This file
├── requirements.txt           Python dependencies
├── fetch_data.py              Downloads the 3 public status-sheet PDFs into data/
├── run_all.py                 Master script: parse → estimate → tables → figures
│
├── parse_status_sheets.py     PDF → per-bill Markov state sequences (corrected coding rule)
├── markov_chain.py            Absorbing-chain estimation, fundamental matrix, sensitivity, bootstrap
├── results_tables.py          Paper Tables 1–3, 5 (party, primary + robustness), 8
├── generate_figures.py        Paper Figures 2–6 (PNG)
├── conditional_analysis.py    Risk-set conditional OOC hazards by party (Section 3.4)
├── party_by_cohort.py         Cohort-adjusted party gap (Robustness)
├── chamber_coding.py          Bicameral decomposition of the 62 floor failures (Tables 6–7)
├── build_party_map.py         (Re)builds data/sponsor_parties.csv from the PDFs + rosters
├── mh_analysis.py             Mantel–Haenszel pooled odds ratios (Robustness)
├── test_het.py                Within-session time-homogeneity χ² tests (Table 8 / Section 3.6)
│
└── data/
    ├── sponsor_parties.csv     Primary-sponsor party (D/R) for all 1,156 bills  [included]
    ├── chamber_coding.csv      Manual chamber attribution of the 62 floor failures [included]
    └── <status-sheet PDFs>     Primary source data — fetched by fetch_data.py     [not included]
```

The **raw status-sheet PDFs are not redistributed** in this package. They are
public records of the Colorado General Assembly; `fetch_data.py` retrieves them
directly from the Assembly's servers. The two CSVs **are** included: one is the
derived primary-sponsor party map, the other is the hand-coded chamber
attribution of the floor failures.

---

## 2. Requirements

- Python 3.10 or newer
- Packages in `requirements.txt` (`pdfplumber`, `numpy`, `scipy`, `matplotlib`)

```bash
pip install -r requirements.txt
```

---

## 3. Reproduce (three commands)

```bash
pip install -r requirements.txt
python fetch_data.py      # downloads the 3 House status-sheet PDFs into data/
python run_all.py         # prints all tables to stdout, writes figures to figures/
```

To include the bootstrap 95% confidence intervals used in Table 4 and the
supplementary bootstrap table (adds a few minutes):

```bash
python run_all.py --bootstrap
```

If `fetch_data.py` cannot reach the files (offline, or the Assembly moves them),
download the three "House Final Status Sheet" PDFs manually from
<https://leg.colorado.gov/bill-search> and place them in `data/` under the exact
filenames printed by `fetch_data.py`. Then run `python run_all.py`.

Individual components can also be run on their own, e.g.:

```bash
python parse_status_sheets.py      # prints per-session passage rates (a quick sanity check)
python conditional_analysis.py     # conditional OOC hazards by party
python chamber_coding.py           # bicameral decomposition (Tables 6–7)
python test_het.py                 # time-homogeneity tests
python generate_figures.py         # figures only
```

---

## 4. What maps to what in the paper

| Paper object | Produced by |
|---|---|
| Table 1 — transition probabilities | `results_tables.table1_transitions` |
| Table 2 — failures by stage | `results_tables.table2_failures` |
| Table 3 — absorption (B, t) | `results_tables.table3_absorption` |
| Table 4 — sensitivity coefficients + bootstrap CIs | `markov_chain` (compute + `bootstrap_*`); run with `--bootstrap` |
| Table 5 — party stratification (primary) | `results_tables.table7_party` |
| Table 5 — exclusion robustness | `results_tables.table7_party_exclusion_robustness` |
| Tables 6–7 — bicameral decomposition | `chamber_coding.py` (uses `data/chamber_coding.csv`) |
| Table 8 — cohort time-heterogeneity | `results_tables.table8_time_heterogeneity`, `test_het.py` |
| Section 3.4 — conditional OOC hazards by party | `conditional_analysis.py` |
| Robustness — cohort-adjusted gap / MH odds ratios | `party_by_cohort.py`, `mh_analysis.py` |
| Figure 1 — chain diagram | schematic (drawn in the manuscript; not data-derived) |
| Figure 2 — transition probabilities | `generate_figures.fig_transition_probabilities` |
| Figure 3 — sensitivity coefficients | `generate_figures.fig_sensitivities` |
| Figure 4 — party comparison | `generate_figures.fig_party_gap` |
| Figure 5 — floor-failure decomposition | `generate_figures.fig_bicameral` |
| Figure 6 — cohort comparison | `generate_figures.fig_cohorts` |

Figure 1 (the state-space diagram) is a schematic and is included with the
manuscript's figure files; it is not generated from the data.

---

## 5. Expected output (correctness check)

A correct run reports these per-session passage rates (after excluding
supplemental appropriations, which pass by construction):

```
2022: 76.5%   2023: 70.1%   2024: 73.3%
```

and these bill counts and first-committee failure counts:

```
Bills analyzed:            2022 = 400    2023 = 311    2024 = 445   (total 1,156)
In Committee → Failed:     2022 =  63    2023 =  57    2024 =  47   (total   167)
```

The passage probability B(0,0) equals the empirical passage rate exactly under
maximum likelihood (e.g., 2024 → 0.7326 = 326/445), which is a built-in
internal-consistency check.

---

## 6. Key data files

- **`data/sponsor_parties.csv`** — one row per bill: `bill_num`, `year`,
  `party` (`D`/`R`), and `sponsor`. Covers all 1,156 bills with an identifiable
  primary House sponsor. This is the **all-sponsor** map used by the paper's
  primary Table 5; the Herod/McCluskie exclusion is applied downstream only as a
  robustness variant (`results_tables.table7_party_exclusion_robustness`). It can
  be regenerated from the PDFs plus the 73rd/74th GA rosters with
  `build_party_map.py`.
- **`data/chamber_coding.csv`** — one row per floor failure: `bill_num`,
  `year`, `chamber` (`Senate`/`House`/`Session-end`). Encodes the manual coding
  of all 62 On-Floor failures (14 in 2022, 19 in 2023, 29 in 2024) used for the
  bicameral decomposition; `chamber_coding.py` validates these totals against the
  parser's floor-failure counts.

---

## 7. Notes on the coding rule

The parser implements the **corrected** first-committee rule: a bill is coded as
having cleared committee (`Out_of_Committee`) only if its first House committee
reported it out on a specific date or referred it onward — **not** on the basis
of the fiscal-impact (FI/NFI) notation, which is recorded for essentially every
heard bill, including those postponed indefinitely in the same hearing. The
earlier FI/NFI-based rule misclassified ~10–17% of bills per session; see the
docstring in `parse_status_sheets.py` (`_classify_first_committee`).

---

## 8. Provenance and licensing

The source data are public records of the Colorado General Assembly (House Daily
/ Final Status Sheets; member and sponsorship records; chamber and joint rules;
OLLS action-code definitions). Please cite the Assembly as the data source. The
code in this package may be used and modified for academic reproduction and
extension.
