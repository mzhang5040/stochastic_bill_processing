# Verification record

This file records what has been checked in the reproduction package and states,
precisely, which numbers come directly from the raw House status-sheet PDFs and
which additionally depend on the two supplementary data files shipped alongside
them. All figures below match the current manuscript.

## 1. What reproduces directly from the PDFs

Running `parse_status_sheets.py` on the three House Final Status Sheets, then
`markov_chain.py` / `results_tables.py`, reproduces the following:

| | 2022 | 2023 | 2024 |
|---|---|---|---|
| Bills analyzed (N) | 400 | 311 | 445 |
| In Committee -> Failed | 63 | 57 | 47 |
| Out of Committee -> Failed | 17 | 17 | 43 |
| On Floor -> Failed | 14 | 19 | 29 |
| Passage probability B(0,0) | 0.7650 | 0.7010 | 0.7326 |

`B(0,0)` equals the empirical passage rate exactly under maximum likelihood
(e.g. 2024: 0.7326 = 326/445). All transition probabilities, the absorption and
expected-time vectors, and the stage sensitivity coefficients -- first-committee
-0.908 / -0.858 / -0.819, floor -0.800 / -0.762 / -0.798, OOC -0.806 / -0.751 /
-0.821 -- follow from these parsed counts and match the manuscript to four
decimals.

**Statistics (risk-set, matching the manuscript).**

- Cross-session Out-of-Committee homogeneity on the risk set (bills reaching
  OOC): **chi-square = 9.00, p = 0.011** (conditional rates 5.0% / 6.7% /
  10.8%). This is the statistic the manuscript uses; the older *marginal*
  cross-session value (chi-square = 10.90, p = 0.004, computed on introduced-bill
  denominators) is not used.
- Cohort (introduction-tertile) homogeneity on the risk set:
  **chi-square = 3.92 / 4.27 / 5.31, p = 0.14 / 0.12 / 0.07** -- no session
  rejects (Table 8).
- First-committee Fisher exact p < 10^-11 each session; Cohen's h = 1.17 / 0.93 /
  0.81.

**The coding-rule correction.** Reimplementing the superseded fiscal-impact
(FI/NFI) rule on the real data inflates the OOC -> Failed share from the true
4.2 / 5.5 / 9.7% to roughly 20-24% per session (e.g. ~23.8% in 2023, ~19.6% in
2024), matching the manuscript's stated "apparent 20-24%" and confirming the
correction is real and quantitatively as described. See
`_classify_first_committee` in `parse_status_sheets.py`.

## 2. What additionally depends on the two supplementary files

Two labels the status sheets do not carry in directly analyzable form are
supplied by shipped files; the party and bicameral results follow from the PDFs
**plus** these files.

### `data/sponsor_parties.csv` -- party stratification (Table 5)

Primary-sponsor party for all 1,156 bills, built from the 73rd/74th General
Assembly membership rosters (`build_party_map.py`). Under the **all-sponsor
primary specification** the pipeline (`results_tables.table7_party`) computes
directly from the parsed states plus this file -- there is **no** "budget bills
assumed to pass" step; the parser classifies those bills from the PDF like any
other:

- First-committee gaps **+46.7 / +39.4 / +29.3 pp** (h 1.17 / 0.93 / 0.81),
  Fisher p < 10^-11 each.
- Conditional OOC hazards (risk set) D/R = **3.1% / 16.7%** (2022; +13.6 pp,
  h 0.49, p = 0.0009), **2.8% / 29.7%** (2023; +27.0 pp, h 0.82, p < 10^-6),
  **9.4% / 19.0%** (2024; +9.6 pp, h 0.28, p = 0.039).
- Exclusion robustness (`table7_party_exclusion_robustness`, dropping the 69
  Herod/McCluskie budget bills; D pool 255 / 229 / 345): +45.9 / +39.0 / +29.2 pp
  (h 1.14 / 0.91 / 0.80).

Colorado House composition (41D-24R in 2022; 46D-19R in 2023-24) confirmed
against public records. The CSV is internally consistent (no sponsor coded both
D and R; every R matches the roster).

### `data/chamber_coding.csv` -- bicameral decomposition (Tables 6-7)

The parser identifies the 62 On-Floor failures (14 / 19 / 29) and reproduces the
gubernatorial-veto and House-side counts automatically. Attributing each
Senate-side loss versus a session-end death is a manual reading of the status
sheet, recorded in `chamber_coding.csv` and validated for per-year totals by
`chamber_coding.py`. The manuscript's Table 7 uses this manual coding.

For 2024 the manual coding records **16 Senate-side and 5 session-end** deaths;
a naive automated heuristic splits the same non-veto, non-House-side bills
**12/9**. This is a coding judgment on a handful of laid-over bills, not a
quantity derivable from the PDF text alone, and is exactly the classification
sensitivity the manuscript's Robustness section flags (the 2024 House-chamber
share is quoted there as a 10-45% range). The 2023 Senate-side list (10 named
bills, Table 6) and the 2022 split match the automated extraction exactly.

## 3. Scope of the reproduction claim

To be precise: the parser reproduces every **aggregate count, transition
probability, passage rate, absorption / expected-time value, sensitivity
coefficient, and homogeneity test** in the manuscript directly from the three
public PDFs. The **party** results additionally require `sponsor_parties.csv`,
and the **bicameral** results additionally require `chamber_coding.csv`; both
files are shipped, documented, and (for the party map) regenerable from the
rosters, or (for the chamber coding) validatable in per-year totals against the
parser. The one number that reflects a manual judgment rather than the automated
pipeline is the 2024 Senate-side / session-end division (16/5), documented above.

## 4. Package corrections relative to the original scripts

- `generate_figures.py`: the bicameral figure computes its counts from
  `data/chamber_coding.csv` rather than a hardcoded dict; a hardcoded absolute
  path was replaced with a script-relative one; figure output is `.png` to match
  the manuscript's `\includegraphics{...png}` calls.
- `results_tables.py` / `run_all.py` / `build_party_map.py`: the all-sponsor
  party table is the primary specification, with the Herod/McCluskie exclusion
  moved to a clearly labeled robustness function
  (`table7_party_exclusion_robustness`).
- `data/chamber_coding.csv`, `chamber_coding.py`: supplied loader and validator
  for the 62 floor failures.

## 5. Known limitations (as stated in the manuscript)

- The Out-of-Committee state groups bills reported out of their first committee
  that then died in a later committee (usually Appropriations). This is a coding
  definition stated in the manuscript, not an error.
- The 2024 Senate-side vs session-end split rests on a manual judgment for a few
  laid-over bills (Section 2 above); 2022 and 2023 match the automated
  extraction.
- The independence assumption behind the bootstrap may understate uncertainty if
  within-session dependence is positive; reported intervals and p-values are
  descriptive measures of variation rather than exact coverage guarantees.
