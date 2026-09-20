# ITT 2026 joint outcome analysis

This package supports the English manuscript **Ranking Prompt Injection Defense 
Configurations for AI Agents Using Joint Outcome Bounds**. It is a completed secondary
analysis of published tables and archived execution logs. No new model executions,
GPU access, model subscription, or API key are required to reproduce its numerical
results. The final document uses the user-supplied IEEE A4 conference template
and includes the five authors supplied by the user. This version supersedes the
earlier pilot-plus-protocol plan. The identified manuscript needs author review;
the conference's double-blind submission requires a separate anonymized copy.

## Evidence and scope

Two evidence sources remain separate:

- AgentDyn v3 Tables 9–17 provide three metrics for 122 model–configuration
  combinations in three suites (366 suite-level configuration records). The main
  rectangular panel has 12 models and 10 configurations: 120 conditions and 540
  within-model pairs. Two Meta-SecAlign rows are retained but excluded from that
  panel because their model labels differ.
- The pilot contains 288 original logs: 192 attacked and 96 clean records, from
  12 distinct user tasks, two models, and four configurations. There are four
  sampled tasks per suite, two attack objectives per task, and one historical
  realization per condition. These are not 288 independent tasks.

The full raw repository was not reanalyzed. The published-table comparisons
assume that task and attack marginals refer to the same evaluated cases and
weights in each suite. They condition on source metric and error conventions
that cannot be reconstructed from aggregate tables. Pilot and table results are
not combined into one sample size or interpreted as current production behavior.

## Reproduce offline

The verified runtime is Python 3.12.14. Install the pinned dependencies in
`requirements.txt` if needed; installation itself requires package access.
Then, from the extracted package directory:

```bash
python analysis/analyze_pilot.py
python extended/analysis/analyze_extended.py
```

Both analyses use local inputs and make no model or external API calls. The
pilot script checks Git blob hashes, source identifiers, pairing, and the sample
structure, then calculates counts and 10,000 task bootstrap replicates. The
extended script extracts the numerical tables, audits Overall arithmetic,
computes rounding-aware bounds, examines pairwise orderings and score sensitivity,
and checks exact pilot joint rates against their bounds.

The five numerical JSON files reproduce exactly with the verified dependencies:
`analysis/results/pilot_outcomes.json`, `pilot_summary.json`,
`published_table3.json`, and `extended/results/published_marginals.json` and
`extended_results.json`. Figure metadata can vary without changing the results.
`REPRODUCTION.json` records the offline rerun and hashes; `CHECKSUMS.sha256`
covers all packaged files except itself.

Generate the final English manuscript with:

```bash
python extended/analysis/apply_itt2026_template.py
```

This writes `itt2026_output/ITT2026_Final_Manuscript_EN.docx` alongside the
extracted package folder. The document contains ten numbered, editable native
Word equations, four numbered scientific tables, one figure, and twelve
references. It includes Goran Lazarov, Thaeer Kobbaey, Vishwesh Akre,
Waleed Al-Sit, and Nedaa Al Barghuthi with the affiliations and email addresses
supplied by the user. Clean-record counts in Table III come from the unchanged
pilot analysis; the source arithmetic audit is Table IV.

`extended/template/conference-template-a4.docx` preserves the supplied template.
The builder converts its Strict OOXML namespaces and point measurements to
equivalent Transitional syntax for editing, then uses its page geometry,
paragraph styles, numbering, and theme. It removes all sample content.
`extended/template_alignment.json` records the template and output hashes;
`extended/document_validation.json` records the final document checks.
The intermediate `finalize_itt2026.py` prepares the text and figure and is called
by the A4 builder. The earlier `build_empirical_manuscript.py` and
`analysis/build_documents.py` remain as dependencies and draft-generation helpers.
No model executions are performed during document generation.

## Mathematical definitions

For a valid attacked execution, U denotes user-task completion and A denotes
attacker-goal success. The joint outcome is J = U(1 − A). Its mean satisfies
j = u(1 − a) − Cov(U,A); multiplying marginal rates assumes zero covariance.
Classical Fréchet–Hoeffding bounds give

    max(0, u − a) <= j <= min(u, 1 − a).

We apply these bounds separately within suites, then average with equal weights.
Printed percentages receive ±0.005 percentage-point rounding tolerance, clipped
to valid probabilities. Identification intervals represent missing dependence,
not sampling error. Pooled intervals are computed from the mean of the printed
suite cells with conservative rounding tolerance. The separately printed Overall
column is retained for audit rather than silently corrected.

Two configurations receive a strict joint ordering only when their intervals
are disjoint. A certified reversal means this ordering opposes the strictly
lower-ASR ordering after accounting for rounding. Overlap means unresolved, not
equivalent. The pairs share models and source cases and are not independent tests.

The illustrative score S(lambda) = j − lambda*a is examined at lambda values
0, 0.1, 0.25, 0.5, 1, 2, and 5. Its interval uses endpoint optimization per suite.
It is a preference sensitivity analysis on attacked benchmark cases, not a
calibrated economic loss or estimate of production attack prevalence.

## Main derived findings

| Quantity | Result |
| --- | ---: |
| Within-model pairs | 540 |
| Strictly ordered using pooled marginals | 337 |
| Strictly ordered using suite marginals | 394 |
| Additional ordered pairs | 57 |
| Joint ordering opposed to lower ASR | 298 |
| Mean pooled interval width | 5.535638889 percentage points |
| Mean suite interval width | 4.775027778 percentage points |
| Conditions with narrower intervals | 51 |
| Source Overall arithmetic discrepancies | 3 |
| Fresh model executions | 0 |

Three attacked-utility rows have Overall values inconsistent with equal suite
averages beyond ordinary two-decimal rounding: Spotlighting / Claude-Sonnet-3.5,
Spotlighting / Claude-Sonnet-4.5, and DRIFT / Kimi-K2.5. The source cells are
preserved exactly. We do not infer which field is wrong. Excluding these conditions
leaves 513 pairs, with 312 pooled and 369 suite-separated pairs and 281 reversals.

The pilot has no logged technical errors. On attacked records, `security=True`
means the injection objective **succeeded**, not that the run was secure. Clean
records follow a different convention and do not enter attack-rate calculations.
The 12-task bootstrap retains both attacks and all compared conditions when
resampling tasks within suites. Its intervals are exploratory; degenerate
all-zero/all-one intervals are suppressed. They do not describe variability
across new model calls. Joint completion does not certify every tool action.

## Provenance and attribution

Primary table source: [AgentDyn v3](https://arxiv.org/abs/2602.03117v3), dated
May 7, 2026. `extended/sources/published_numeric_tables.html` preserves numerical
Tables 9–17; `sources/agentdyn_table3.html` retains the separate Table 3 used in
the earlier pilot context. The full article is not redistributed.

Upstream logs: [SaFo-Lab/AgentDyn](https://github.com/SaFo-Lab/AgentDyn), pinned to
`5353cf7615b135cace8d07c8f12dac53a16b6db3`. Logged evaluation dates are January 22
and January 24, 2026. The selection manifest was recorded on September 15, 2026
using seed 20260915 before the selected outcomes were downloaded. This is an
exploratory secondary study, not an externally preregistered experiment.

`data/pilot_manifest.json` gives all 288 paths, hashes, and selection identifiers.
`data/download_report.json` records transfers and SHA-256 hashes. The packaged
`sources/agentdyn_tree.json` is a selected subset of a truncated repository
inventory, not a complete tree. `analysis/download_pilot.py` is optional and
verifies existing files; absent files require public network access. The analysis
never executes agent instructions contained in source logs.

The copied upstream license appears in `sources/AgentDyn_LICENSE.txt`; its
attributed authors are not the authors of the new manuscript. Numerical tables
are attributed to AgentDyn. No additional public license is asserted for the
new manuscript or analysis scripts.

OpenAI ChatGPT assisted with study design, mathematical exposition, drafting and
editing all manuscript sections, and code generation. The code computed the
reported values from cited data. Submitting authors remain responsible for the
analysis, citations, AI-assistance disclosure, and final conference formatting.
No public archive upload, conference submission, acceptance, or citation impact
is claimed. Package checkpoint: September 16, 2026.
