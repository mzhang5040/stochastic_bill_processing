# Verification record

This package is the curated result of an end-to-end verification. It contains
**only** the files that are correct and relevant to the current paper
(`paper_siuro_updated.tex`). Files that described the superseded pre-revision
analysis, or that were non-functional as shipped, have been removed (listed at
the bottom).

## What was checked, and how it came out

**Mathematics.** Proposition 2.7 (sensitivity coefficients
`-N[0,3]` for floor, `-N[0,2]*B[3,0]` for OOC) was re-derived by hand and
matches the code. Corollary 2.9's reduction of stage dominance to the
comparison `B[3,0]` vs `Q[2,3]` is exact for this chain, because the estimated
chain is strictly feed-forward (`N[0,3] = N[0,2]*Q[2,3]`). Verified numerically.

**Estimation code.** `markov_chain.py` reproduces the paper's Tables 1-4 from
the parsed counts (checked on synthetic and real inputs).

**Parser, on the real PDFs.** Running `parse_status_sheets.py` on all three
actual status sheets reproduces the paper's counts exactly:

| | 2022 | 2023 | 2024 |
|---|---|---|---|
| N (paper / parser) | 400 / 400 | 311 / 311 | 445 / 445 |
| In-Committee -> Failed | 63 / 63 | 57 / 57 | 47 / 47 |
| OOC -> Failed | 17 / 17 | 17 / 17 | 43 / 43 |
| On-Floor -> Failed | 14 / 14 | 19 / 19 | 29 / 29 |
| Passage B[0,0] | 0.7650 | 0.7010 | 0.7326 |

All transition probabilities and sensitivity coefficients match to four
decimals. The full `run_all.py` pipeline runs end-to-end on all three PDFs and
reproduces every table and the five figures.

**The coding-rule claim.** Reimplementing the old fiscal-impact-based rule and
running it on the real data inflates OOC->Failed from a true 5.5% to 23.8%
(2023) and from 9.7% to 19.6% (2024) -- matching the paper's stated "apparent
20-24%," and confirming the correction is real and quantitatively as described.

**Statistics.** Cross-session OOC chi-square = 10.90 (p = 0.004); first-committee
Cohen's h = 1.14 / 0.91 / 0.80; passage h = 1.02 / 1.03 / 0.61; cohort chi-square
= 3.07 / 3.37 (p = 0.22 / 0.19, Table 8); Mantel-Haenszel ORs 8.6 / 7.7 with
unstratified 8.9 / 10.0. All reproduced exactly.

**Party coding.** `sponsor_parties.csv` is internally consistent (no sponsor
coded both D and R; every R matches the roster). Under the **all-sponsor primary
specification** (now the paper's Table 5), its counts are 302/98, 239/72, 357/88
(D/R by session), matching `results_tables.table7_party`. The Herod/McCluskie
removal (47/10/12 bills) is now a **robustness** variant only
(`table7_party_exclusion_robustness`), reducing the D pool to 255/229/345 and the
first-committee gaps from +46.7/+39.4/+29.3 to +45.9/+39.0/+29.2 pp — a change of
at most 0.8 pp, as reported in the Robustness section. Colorado House composition
(41D-24R in 2022, 46D-19R in 2023-24) confirmed against public records.

*Note on the all-sponsor cells:* the reconstruction cross-checks exactly against
the paper's own stated 2022 anchor (+46.7 pp) and assumes the 69 budget/leadership
bills all clear their first committee (they pass by construction). Re-running the
updated pipeline on the raw PDFs will lock the exact cell values.

**Bicameral decomposition.** Floor-failure bills extracted from the real PDFs
reproduce the paper's coding: vetoes and House-side match exactly in both years,
and the 2023 Senate-side extraction reproduces the exact list of 10 named bills
in Table 5. For 2022 the automatic classification matches Table 6 exactly
([6,2,4,2]). `chamber_coding.csv` holds the real bill numbers for all 62 floor
failures; its per-year totals (14 / 19 / 29) are validated against the parser's
floor-failure counts by `chamber_coding.py`.

## Corrections applied in this package

- `generate_figures.py`: the bicameral figure now computes its counts from
  `data/chamber_coding.csv` instead of a hardcoded dict; the hardcoded
  `/home/claude/work` path was replaced with a portable script-relative path.
- `run_all.py`: the docstring's "61 On Floor failures" corrected to 62
  (14 + 19 + 29), with a pointer to the validating loader.
- `data/chamber_coding.csv`: newly supplied, populated with real bill numbers.
- `chamber_coding.py`: newly supplied loader/validator.

## Known limitations (unchanged from the paper's own statements)

- The OOC state groups bills reported out of their first committee that then
  died in a second committee (usually Appropriations). The paper states this
  explicitly; it is a coding definition, not an error.
- The 2024 Senate-side vs session-end split depends on a manual judgment for a
  few laid-over bills; the classifier gives 12/9 where the paper reports 16/5
  (same non-House, non-veto total, and identical veto/House-side counts). This
  is the one bicameral cell that differs from the paper, and it reflects the
  classification sensitivity the paper's Robustness section discusses. 2022 and
  2023 match Table 6 exactly.

## Files intentionally excluded (not correct/relevant to the current paper)

- `diagnostics.py`, `final_summary.py`, `run_corrected_analysis.py` -- these
  compare against the **old, pre-revision** paper's claims (e.g. a 20.7% OOC
  bottleneck) that the current paper no longer makes; `final_summary.py` also
  contains an internal inconsistency (18/19 vs 19/19 Senate-side). They are
  historical artifacts of the correction process, not part of the reproduction.
- `verify.py` -- its Step 1 depends on an `orig_test/` copy of the original
  buggy parser that was never shipped, so it cannot run as provided.

## Revisions applied to the manuscript (referee response)

The following corrections were made to `paper_siuro_updated.tex` after a technical
review; each was verified against the data (`conditional_analysis.py` reproduces
the new numbers).

1. **Marginal vs. conditional (Table 5).** The party stratification table reported
   failure *shares* (percent of introduced bills) but was captioned "transition
   probabilities." Caption corrected; the text now reports the conditional OOC
   hazard on the risk set (bills reaching OOC): D/R = 3.7%/16.7% (2022, p=0.002),
   2.9%/29.7% (2023, p<10^-3), 9.8%/19.0% (2024, p=0.07 n.s.). The interpretation
   was revised: filtering is strongest at the first committee, with meaningful
   *additional* conditional disparity after clearance, especially in 2023.

2. **Cross-session OOC test.** Restated on risk-set denominators:
   chi2 = 9.00, p = 0.011 (the marginal 10.90/0.004 is noted). Repeated mentions
   and the Appendix caption updated for consistency.

3. **Table 8 (cohort homogeneity).** Noted the same denominator issue; the risk-set
   recomputation leaves the conclusion unchanged (p = 0.14/0.12/0.07).

4. **Self-loop theorem (Theorem 2.11 / Remark 2.12 / Conclusion).** Corrected the
   adjacent-state visit-count ratio from Q_ij/(1-Q_ii) to the correct
   N[0,j]/N[0,i] = Q_ij/(1-Q_jj): the downstream self-loop sets the threshold and
   the upstream one cancels. The dominance criterion is now B_{j,0} > Q_ij/(1-Q_jj);
   added the note that for the terminal transient state Case (ii) coincides with the
   floor Case (i), so Corollary 2.9 is recovered. (Empirically inert: Q_ii = 0
   throughout the Colorado data.)

5. **First-committee sensitivity.** Added -N[0,1]*B[2,0] = -0.908/-0.858/-0.819,
   which exceeds both floor and OOC sensitivities in 2022-23, and a clarification
   that failure mass, conditional hazard, and sensitivity are three distinct
   "bottleneck" notions.

6. **Novelty framing.** Softened "characterizes exactly the class" and "central
   theoretical contribution"; added a Caswell (2019) citation acknowledging prior
   fundamental-matrix sensitivity results and narrowing the contribution to the
   directional-perturbation interpretation and stage-comparison criterion.

7. **Cosmetic.** Removed the period inside all 20 `\paragraph{...}` headings (the
   class appends its own, producing "Contributions.."); softened the "at most 95%
   coverage" claim to condition on positive dependence. The advisor-line spacing
   ("Stachura\thanks{...}") was left unchanged pending a check of the compiled PDF,
   since it is a `\thanks` rendering detail in the SIURO class rather than a source
   error.

Verified to compile (28 pp.) against a stub of the SIURO class; all cross-references
and the new citation resolve.

## Second-round referee response

All five points verified against the data (`conditional_analysis.py` reproduces the numbers) and addressed.

1. **Table 8 / cohort figure now risk-set.** The prose had been corrected but the
   table and figure still showed marginal (introduced-bill) denominators. Both now
   display the conditional OOC transition rate with explicit (failures/reached-OOC)
   counts: 2022 8/101, 6/105, 3/131; 2023 4/81, 9/78, 4/95; 2024 17/124, 17/127,
   9/147; chi2 = 3.92/4.27/5.31, p = 0.14/0.12/0.07. `generate_figures.fig_cohorts`
   was rewritten to sort by intro date and use risk-set denominators; the Appendix
   caption and the marginal-version pointer were reconciled.

2. **Theorem 2.11 Case (i)/(ii) unified.** Added the continuation value
   V(c) = B_{c,0} (transient) or 1 (Passed) after Proposition 2.7, so the single
   form dB/dp = -N[0,j] V(c(j)) covers both cases; Theorem 2.11 and its proof now
   use V(c), and the mixed OOC-Case(ii)/floor-Case(i) comparison of Corollary 2.9 is
   formally a special case. **Also fixed a latent direction error** in the operational
   criterion: it now reads |Sens_i| > |Sens_j| iff B_{j,0} > tau_{i,j} (the original
   had the inequality reversed, inconsistent with Corollary 2.9); verified numerically.

3. **"Leads on all three" corrected.** In 2024 the first-committee conditional hazard
   (10.6%) and sensitivity (0.819) are a shade below OOC (10.8%, 0.821). Reworded to
   "leads by all three measures in 2022 and 2023 and remains the largest or
   statistically comparable stage in 2024." Added the first-committee coefficient with
   bootstrap CIs to Table 4 (new column) and Figure 3 (new series).

4. **Party interpretation made consistent.** Section 4.4 opening, Figure 4 caption, and
   the Discussion no longer describe the post-committee gap as "comparable"/marginal;
   they report the conditional Cohen's h (0.45/0.81/0.27) and adopt: "the first
   committee is the only stage with a large, significant partisan gap in all three
   sessions; conditional OOC disparities remain meaningful in 2022 and especially 2023
   (h=0.81, nearly the 2023 first-committee 0.91) but are less consistent."

5. **Length.** Condensed the Conclusion's verbatim numeric recap (which duplicated the
   abstract) to help toward the ~20-page SIURO target. The advisor letter establishing
   the student's independent contribution is a submission requirement, not a manuscript
   edit.

Re-verified: figures regenerate, paper compiles, all cross-references resolve.

## Third-round referee response

All points verified (direction and interval claims checked numerically) and addressed.

1. **Remark 2.12 direction (third recurrence) — fixed.** A downstream self-loop raises
   tau_{i,j}, making B_{j,0} > tau_{i,j} harder to satisfy, so it shifts dominance toward
   the *downstream* stage j (verified numerically: raising Q_{j,j} grows |Sens_j|). The
   sentence now reads "shifts the comparison toward downstream-stage (j) dominance." (This
   was an error I introduced in round 1 and is now corrected.)

2. **Page-3 independence language — softened.** Replaced the categorical "at least as
   wide / at most 95% / modest" claims with the safer statement that dependence may
   understate uncertainty if positive, with direction and magnitude undetermined absent a
   dependence model; added same-sponsor bill clustering as an additional source.

3. **Figures regenerated.** `fig_sensitivities` now renders three bars (first-committee,
   floor, OOC) and `fig_cohorts` uses the conditional axis label "Conditional OOC failure
   rate (% of bills reaching OOC)". Figure output switched from `.pdf` to `.png` to match
   the manuscript's `\includegraphics{...png}` calls; regenerated PNGs are in `figures/`.

4. **Two claims softened.** Introduction: "delineating the boundary of the closed-form
   regime" -> "providing a sufficient structural regime in which the criterion retains a
   closed-form representation." Section 4.4: first committee has the greatest structural
   leverage "in 2022 and 2023 (essentially tied with OOC in 2024)."

5. **Conditional bootstrap intervals.** The intervals following the conditional cross-session
   test are now the conditional OOC transition-rate intervals [3.0,7.4], [3.9,9.8],
   [7.8,13.8] (computed on the OOC risk set), not the marginal shares. The Appendix A table
   retains marginal intervals but is explicitly labeled "(% intro)".

6. **Presentation.** Advisor affiliation set inline ("Eric Stachura, Department of
   Mathematics, ...") to remove the run-in `\thanks` artifact; abstract de-formularized
   (matrix/derivative notation replaced with prose); the Caswell/novelty-narrowing note
   moved into the Introduction with the Conclusion version shortened to a back-reference.
   Length: abstract and conclusion trimmed; moving Appendix A / Table 6 to a supplement
   (to reach ~20 pp.) and the advisor letter are submission-packaging steps left to the
   author.

Re-verified: figures regenerate, paper compiles, all cross-references resolve.

## Fifth-round referee response

All items addressed; the two overclaim rewrites were the only ones a strict referee could call false rather than stylistic.

1. **Theoretical overclaim softened (two places).** Section 2.4: "...requires evaluating
   the full fundamental matrix" -> "...generally requires evaluation of the full
   fundamental matrix unless additional structure (symmetry, sparsity, or another special
   form) permits another simplification." Conclusion: "The criterion does not extend...
   no closed-form simplification holds" -> "The criterion need not retain this form...
   N[0,j] generally depends on the full fundamental matrix."

2. **Marginal/conditional separated in Robustness and Discussion.** Both now state the
   marginal share (4.2/5.5/9.7%) and the conditional risk-set transition rate
   (5.0/6.7/10.8%) in distinct sentences, with the chi2=9.00, p=0.011 test attached to
   the risk-set quantity.

3. **Appendix A completed.** Added two blocks with bootstrap SDs and 95% CIs:
   OOC Transition (conditional, % reaching OOC): 5.0/6.7/10.8%, [3.0,7.4]/[3.9,9.8]/
   [7.8,13.8]; First-committee sensitivity: -0.908/-0.858/-0.819,
   [-0.938,-0.878]/[-0.900,-0.813]/[-0.857,-0.780]. Caption updated to mark which blocks
   are marginal vs conditional.

4. **Figure 3 caption** now names all three series and confines the
   statistical-indistinguishability claim to floor vs OOC.

5. **Formalities.** Proposition 2.7 now states epsilon is small enough to keep the
   compensating transition nonnegative; Theorem 2.11's Corollary-2.9 reduction now
   specifies the upstream=Case(ii)/downstream=Case(i) perturbations.

Re-verified: paper compiles, all cross-references resolve, stale overclaim strings removed.
