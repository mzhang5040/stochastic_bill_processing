# Code for the SIURO paper

**"Bottlenecks and Committee Filtering: A Markov Chain Analysis of Bill
Progression in the Colorado General Assembly"**

This is the curated, verified reproduction package. Every number, table, and
figure in `paper_siuro_updated.tex` is reproduced by the code below. The
pipeline has been checked end-to-end against the raw Colorado House status
sheets (see `VERIFICATION.md`).

## Quick start

```bash
pip install pdfplumber numpy scipy matplotlib

# Place the three source PDFs in data/ (see "Required input data" below), then:
python run_all.py                 # tables + figures
python run_all.py --bootstrap     # also compute Appendix A bootstrap CIs (~3 min)
```

## Required input data

Three Colorado House final status sheets (public), placed in `data/`:

```
data/2022-house-final-status-sheet-accessible.pdf   (HB22-1001..1418)
data/2023-house-final-status-sheet-accessible.pdf   (HB23-1001..1311)
data/2024-house-final-status-sheet-accessible.pdf   (HB24-1001..1472)
```

Source: https://content.leg.colorado.gov/sites/default/files/&lt;year&gt;-house-final-status-sheet-accessible.pdf
(also searchable at https://leg.colorado.gov/bill-search).

Two derived CSVs are included:

```
data/sponsor_parties.csv    primary-sponsor party (D/R) per bill  [included]
data/chamber_coding.csv     chamber-level coding of every On_Floor->Failed bill [included]
```

## Module index

### Core pipeline (reproduces every table and figure)

| File | Purpose |
|------|---------|
| `parse_status_sheets.py` | Parse the raw PDFs into per-bill trajectory records. Implements the corrected first-committee coding rule (Section 6, "A methodological contribution"). |
| `markov_chain.py` | Absorbing-chain estimation: Q, R, fundamental matrix N, absorption B, expected steps t, sensitivity coefficients (Proposition 2.7 / Corollary 2.9), and the non-parametric bootstrap. |
| `results_tables.py` | Print Tables 1, 2, 3, 7 (party), 8 (cohort), and A1 (bootstrap). Uses `sponsor_parties.csv` and `chamber_coding.csv` when present. |
| `generate_figures.py` | Figures 2-6. The bicameral figure reads counts from `chamber_coding.csv` (not hardcoded). |
| `run_all.py` | Master pipeline: parse -> estimate -> print tables -> generate figures. |

### Data preparation

| File | Purpose |
|------|---------|
| `build_party_map.py` | (Re)generate `sponsor_parties.csv` from the raw PDFs plus the 73rd/74th GA Republican rosters (Colorado House 41D-24R in 2022, 46D-19R in 2023-24). |
| `chamber_coding.py` | Load and validate `chamber_coding.csv` for the bicameral decomposition (Tables 5-6, Figure 6). `validate()` fails loudly if any per-year total drifts from the parser's On_Floor->Failed count. |

### Robustness checks (all cited in the paper)

| File | Purpose |
|------|---------|
| `test_het.py` | Within-session time-heterogeneity chi-square tests by stage (Table 8 / Section "Within-Session Heterogeneity"). |
| `party_by_cohort.py` | First-committee party gap by introduction-date tertile (Robustness, "Cohort-adjusted party gap"). |
| `mh_analysis.py` | Mantel-Haenszel first-committee odds ratios, cohort-adjusted (Robustness). |
| `conditional_analysis.py` | Risk-set (conditional) OOC hazards by party, cross-session OOC transition test, and first-committee sensitivity (Sections 4.2--4.4, 4.6). Reproduces the conditional quantities added in revision. |

## Verification

`VERIFICATION.md` documents an end-to-end check of the pipeline against the
raw status sheets. In brief, running the full pipeline on all three real PDFs
reproduces the paper's Table 1-4 numbers exactly:

```
2022: N=400  InComm->F 63  OOC->F 17  Floor->F 14  Passed 306  B00=0.7650
2023: N=311  InComm->F 57  OOC->F 17  Floor->F 19  Passed 218  B00=0.7010
2024: N=445  InComm->F 47  OOC->F 43  Floor->F 29  Passed 326  B00=0.7326
```

and the corresponding sensitivity coefficients:

```
2022: Floor -0.8000  OOC -0.8056        2023: Floor -0.7621  OOC -0.7512
2024: Floor -0.7978  OOC -0.8213
```

## Dependencies

Python 3.10+, `pdfplumber`, `numpy`, `scipy`, `matplotlib`. No others.
