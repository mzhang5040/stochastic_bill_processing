# Verification record (JHSS version)

This record documents reproduction of the current manuscript,
*Bottlenecks and Committee Filtering: A Markov Chain Analysis of Bill
Progression in the Colorado General Assembly*. It lists only current numbers and
section/table numbering, the exact commands used, and the captured output of a
clean end-to-end run on the three House status-sheet PDFs.

## 1. Commands

From the package root, after `pip install -r requirements.txt` and
`python fetch_data.py` (which places the three PDFs in `data/`):

| Command | Produces |
|---|---|
| `python run_all.py` | Tables 1–3; Table 5 (party, primary + robustness); Table 8; Figures 2–6; summary |
| `python run_all.py --bootstrap` | Table 4 / Appendix bootstrap 95% CIs |
| `python conditional_analysis.py` | Section 3.4 conditional Out-of-Committee hazards by party |
| `python chamber_coding.py` | Tables 6–7 bicameral decomposition (reads `data/chamber_coding.csv`) |
| `python test_het.py` | Table 8 / Section 3.6 homogeneity tests |
| `python validate_clearance.py` | first-committee coding validation (writes `validation_sample.csv`) |
| `python generate_figures.py` | Figures 2–6 |

## 2. Captured output of a clean run

`python parse_status_sheets.py`:

```
  2022: 400 bills  (306 passed, 76.5% passage rate)
  2023: 311 bills  (218 passed, 70.1% passage rate)
  2024: 445 bills  (326 passed, 73.3% passage rate)
  Total: 1156 bills
  850  Introduced -> In_Committee -> Out_of_Committee -> On_Floor -> Passed
  167  Introduced -> In_Committee -> Failed
   77  Introduced -> In_Committee -> Out_of_Committee -> Failed
   62  Introduced -> In_Committee -> Out_of_Committee -> On_Floor -> Failed
```

`python run_all.py` (summary and Table 8):

```
2022:  Passage 0.7650  Floor sens -0.8000  OOC sens -0.8056
2023:  Passage 0.7010  Floor sens -0.7621  OOC sens -0.7512
2024:  Passage 0.7326  Floor sens -0.7978  OOC sens -0.8213

TABLE 8 (conditional OOC by introduction cohort, risk set)
  Early    7.9% (8/101)   4.9% (4/81)   13.7% (17/124)
  Middle   5.7% (6/105)  11.5% (9/78)   13.4% (17/127)
  Late     2.3% (3/131)   4.2% (4/95)    6.1% (9/147)
  Aggregate 5.0% / 6.7% / 10.8%
  chi2      3.92 (p=0.14)  4.27 (p=0.12)  5.31 (p=0.07)
```

`python conditional_analysis.py` (Section 3.4):

```
2022   D/R 3.1% / 16.7%   +13.6pp   Fisher p=0.0009   [9/289 vs 8/48]
2023   D/R 2.8% / 29.7%   +27.0pp   Fisher p<1e-6     [6/217 vs 11/37]
2024   D/R 9.4% / 19.0%    +9.6pp   Fisher p=0.039    [32/340 vs 11/58]
cross-session OOC homogeneity (risk set): chi2 = 9.00, p = 0.011
```

`python validate_clearance.py`:

```
Population of parser-classified first-committee clearances: 989
Sample size: 100 (seed=20240101)
Discrepancies: 0
```

(0 of 100 gives a one-sided 95% upper confidence bound of approximately 3.0% for the first-committee false-clearance rate.)

`run_all.py --bootstrap` reproduces the Table 4 95% CIs (floor sensitivity
[-0.838,-0.760] / [-0.807,-0.711] / [-0.836,-0.757]; OOC sensitivity
[-0.842,-0.768] / [-0.797,-0.700] / [-0.858,-0.783]).

## 3. Values confirmed against the manuscript

| | 2022 | 2023 | 2024 |
|---|---|---|---|
| Bills (N) | 400 | 311 | 445 |
| In Committee -> Failed | 63 | 57 | 47 |
| Out of Committee -> Failed | 17 | 17 | 43 |
| On Floor -> Failed | 14 | 19 | 29 |
| Passage B(0,0) | 0.7650 | 0.7010 | 0.7326 |

- Sensitivity coefficients (Table 4): first-committee -0.908 / -0.858 / -0.819;
  floor -0.800 / -0.762 / -0.798; OOC -0.806 / -0.751 / -0.821.
- First-committee party gaps (Table 5): +46.7 / +39.4 / +29.3 pp
  (Cohen's h 1.17 / 0.93 / 0.81; Fisher p < 10^-11 each); exclusion-robustness
  variant +45.9 / +39.0 / +29.2 pp.
- B(0,0) equals the empirical passage rate exactly under maximum likelihood
  (2024: 0.7326 = 326/445).

## 4. Manually coded input (Tables 6–7)

The parser identifies the 62 On-Floor failures and the veto and House-side
counts automatically. The Senate-side versus session-end attribution is a manual
reading recorded in `data/chamber_coding.csv` (every row `verified = YES`) and
validated for per-year totals by `chamber_coding.py`. Table 7 uses this coding,
and the manuscript matches it, including 2024: **Senate-side 12, House-side 3,
veto 5, session-end 9**.

## 5. Scope of the reproduction claim

The parser reproduces every aggregate count, transition probability, passage
rate, absorption / expected-time value, sensitivity coefficient, and homogeneity
test directly from the three public PDFs. The party results additionally use
`data/sponsor_parties.csv` (buildable from the 73rd/74th General Assembly rosters
via `build_party_map.py`); the bicameral results additionally use
`data/chamber_coding.csv` (Section 4). Both files are shipped and documented.
