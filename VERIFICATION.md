# Verification record — JHSS manuscript

This record documents an **end-to-end reproduction run** of the current
manuscript, *Bottlenecks and Committee Filtering: A Markov Chain Analysis of Bill
Progression in the Colorado General Assembly* (`BillProgressionMarkovModel.docx`),
executed on the three House Final Status Sheet PDFs placed in `data/`. It lists
the command that produces each result, the captured console output of the run,
the one table that rests on manual coding, and the two code/manuscript
corrections the run produced. It contains no history from the paper's earlier
draft.

## 1. Command -> result map

Run from the package root after `pip install -r requirements.txt` and
`python fetch_data.py` (which places the three status-sheet PDFs in `data/`).

| Command | Manuscript object(s) |
|---|---|
| `python run_all.py` | Tables 1–3; Table 5 (party, primary + robustness); Table 8; Figures 2–6; summary |
| `python run_all.py --bootstrap` | Table 4 / Appendix bootstrap 95% CIs |
| `python conditional_analysis.py` | Section 3.4 conditional OOC hazards by party |
| `python chamber_coding.py` | Tables 6–7 bicameral decomposition (reads `data/chamber_coding.csv`) |
| `python party_by_cohort.py`, `python mh_analysis.py` | Robustness: cohort-adjusted gap; Mantel–Haenszel ORs |
| `python test_het.py` | Table 8 / Section 3.6 homogeneity tests |
| `python generate_figures.py` | Figures 2–6 |

## 2. Captured output of the clean run

Parser sanity check (`python parse_status_sheets.py`):

```
  2022: 400 bills  (306 passed, 76.5% passage rate)
  2023: 311 bills  (218 passed, 70.1% passage rate)
  2024: 445 bills  (326 passed, 73.3% passage rate)
  Total: 1156 bills
  Most common trajectories:
     850  Introduced -> In_Committee -> Out_of_Committee -> On_Floor -> Passed
     167  Introduced -> In_Committee -> Failed
      77  Introduced -> In_Committee -> Out_of_Committee -> Failed
      62  Introduced -> In_Committee -> Out_of_Committee -> On_Floor -> Failed
```

(167 = 63+57+47 first-committee deaths; 77 = 17+17+43 OOC deaths; 62 = 14+19+29
floor deaths — the manuscript's stage counts, exactly.)

`run_all.py` summary:

```
2022:  Passage 0.7650  Floor sens -0.8000  OOC sens -0.8056
2023:  Passage 0.7010  Floor sens -0.7621  OOC sens -0.7512
2024:  Passage 0.7326  Floor sens -0.7978  OOC sens -0.8213
```

Table 8 (conditional OOC by introduction cohort, risk set):

```
Early tertile   7.9% (8/101)   4.9% (4/81)   13.7% (17/124)
Middle tertile  5.7% (6/105)  11.5% (9/78)   13.4% (17/127)
Late tertile    2.3% (3/131)   4.2% (4/95)    6.1% (9/147)
Aggregate       5.0%           6.7%           10.8%
chi2            3.92 (p=0.14)  4.27 (p=0.12)  5.31 (p=0.07)
```

`conditional_analysis.py` (Section 3.4):

```
2022   3.1% / 16.7%  +13.6pp  Fisher p=0.0009  [9/289 vs 8/48]
2023   2.8% / 29.7%  +27.0pp  Fisher p<1e-6    [6/217 vs 11/37]
2024   9.4% / 19.0%   +9.6pp  Fisher p=0.0391  [32/340 vs 11/58]
cross-session risk-set chi2 = 9.00, p = 0.011  (marginal 10.90/0.004 not used)
```

Bootstrap 95% CIs (`--bootstrap`, 2000 resamples) reproduce Table 4:
floor sensitivity [-0.838,-0.760] / [-0.807,-0.711] / [-0.836,-0.757];
OOC sensitivity [-0.842,-0.768] / [-0.797,-0.700] / [-0.858,-0.783].

All of the above match the manuscript. `B(0,0)` equals the empirical passage
rate exactly under maximum likelihood (2024: 0.7326 = 326/445).

## 3. Values confirmed against the manuscript

| | 2022 | 2023 | 2024 |
|---|---|---|---|
| Bills (N) | 400 | 311 | 445 |
| In Committee -> Failed | 63 | 57 | 47 |
| Out of Committee -> Failed | 17 | 17 | 43 |
| On Floor -> Failed | 14 | 19 | 29 |
| Passage B(0,0) | 0.7650 | 0.7010 | 0.7326 |

- First-committee gaps +46.7 / +39.4 / +29.3 pp (h 1.17 / 0.93 / 0.81),
  Fisher p < 10^-11; exclusion robustness +45.9 / +39.0 / +29.2 pp (D pool
  255 / 229 / 345) — both reproduced by `run_all.py`.
- Coding-rule check: the superseded FI/NFI rule inflates OOC -> Failed from the
  true 4.2 / 5.5 / 9.7% to ~20-24% per session.

## 4. Manually coded input (Tables 6–7)

The bicameral decomposition is not fully automatic. The parser identifies the 62
On-Floor failures (14 / 19 / 29) and the veto / House-side counts; attributing
each Senate-side loss versus a session-end death is a manual reading recorded in
`data/chamber_coding.csv` (every row `verified = YES`) and validated for per-year
totals by `chamber_coding.py`. **Table 7 uses this manual coding, and the
manuscript matches it exactly**, including 2024 (Senate-side 12, House-side 3,
veto 5, session-end 9). The 2023 Senate-side list (10 named bills, Table 6) and
the 2022 split also match. This is the only layer of the analysis that is
hand-coded rather than parsed from the PDFs.

## 5. Corrections produced by this run

Running the pipeline end-to-end surfaced and fixed two inconsistencies between an
earlier hand-tabulated draft and the actual computation:

- **`results_tables.table8_time_heterogeneity`** was computing the cohort test on
  *marginal* (all-introduced) denominators (chi2 = 2.37 / 3.07 / 3.37). It was
  corrected to the *risk-set* (reached-OOC) denominators the manuscript uses, and
  now reproduces Table 8 exactly (chi2 = 3.92 / 4.27 / 5.31, p = 0.14 / 0.12 /
  0.07).
- **Table 5, 2024 majority row.** The pipeline gives majority Floor -> Failed
  26/357 = 7.3% and passage 282/357 = 79.0%; the draft had 7.0% / 79.3% (off by
  one bill). The manuscript was corrected to the pipeline values (Floor gap -3.9,
  passage gap -29.0), which do not affect any first-committee, conditional-hazard,
  or sensitivity result.

## 6. Scope of the reproduction claim

The parser reproduces every aggregate count, transition probability, passage
rate, absorption / expected-time value, sensitivity coefficient, and homogeneity
test directly from the three public PDFs. The **party** results additionally
require `data/sponsor_parties.csv` (the sponsor-to-party map, buildable from the
73rd/74th General Assembly rosters via `build_party_map.py`); the **bicameral**
results additionally require `data/chamber_coding.csv` (the manual chamber coding
of §4). Both files are shipped and documented; the party CSV is internally
consistent (no sponsor coded both D and R; every R matches the roster).
