# ITT 2026 Joint Outcome Analysis

This repository contains the reproducibility package for the manuscript:

**Ranking Prompt Injection Defense Configurations for AI Agents Using Joint Outcome Bounds**

Authors:

- Goran Lazarov
- Vishwesh Akre
- Thaeer Kobbaey
- Munther Al Hassan
- Waleed Al-Sit
- Nedaa Al Barghuthi

## Scope

This package contains a completed secondary analysis of published AgentDyn tables and archived execution records.

The study:

- does not perform new model executions;
- does not require GPU access, model subscriptions, or API keys;
- computes joint-outcome bounds from published marginal rates;
- audits source-table arithmetic;
- analyzes a small paired archival pilot;
- provides derived results, figures, provenance records, and reproduction scripts.

The original AgentDyn source code and archived execution logs were created by SaFo-Lab. They are cited and identified in this repository but are not redistributed in this package.

## Evidence sources

The analysis uses two separate evidence sources.

### AgentDyn published tables

AgentDyn version 3 provides published utility and attack-success rates for 122 model-configuration combinations across the Shopping, GitHub, and DailyLife suites.

The main comparison contains:

- 12 model labels;
- 10 configurations;
- 120 model-configuration conditions;
- 540 unordered within-model pairs.

The numerical tables used in the analysis are preserved in:

```text
extended/sources/published_numeric_tables.html
```

A separate source table used for the archival pilot is preserved in:

```text
sources/agentdyn_table3.html
```

The complete AgentDyn article is not redistributed.

### Archival pilot

The pilot analysis uses 288 archived records:

- 192 attacked records;
- 96 clean records;
- 12 user tasks;
- four tasks per suite;
- two attack objectives per task;
- two models;
- four configurations.

The original upstream log files are not included in this repository.

The manifest records their original paths, hashes, and selection identifiers:

```text
data/pilot_manifest.json
```

The download report records the previously obtained files and their SHA-256 hashes:

```text
data/download_report.json
```

The original logs can be obtained, subject to the upstream repository's applicable terms, from the pinned AgentDyn repository:

```text
https://github.com/SaFo-Lab/AgentDyn/tree/5353cf7615b135cace8d07c8f12dac53a16b6db3
```

## Reproduce the numerical results

Use Python 3.12 or a compatible Python environment.

Install the pinned dependencies if required:

```powershell
python -m pip install -r requirements.txt
```

Run the pilot analysis:

```powershell
python analysis/analyze_pilot.py
```

Run the extended published-table analysis:

```powershell
python extended/analysis/analyze_extended.py
```

Both analyses use local inputs and do not call language models or external APIs.

The pilot analysis verifies:

- source identifiers;
- file hashes;
- pairing structure;
- task and suite composition;
- joint-outcome counts;
- task-bootstrap intervals.

The extended analysis:

- extracts the published numerical tables;
- audits the printed Overall values;
- computes rounding-aware joint-outcome bounds;
- evaluates within-model orderings;
- examines reversals relative to attack-success ranking;
- evaluates penalty sensitivity.

## Numerical outputs

The principal numerical outputs are:

```text
analysis/results/pilot_outcomes.json
pilot_summary.json
published_table3.json
extended/results/published_marginals.json
extended_results.json
```

The reported numerical outputs reproduce exactly with the recorded software versions.

Figure metadata may vary without changing the numerical results.

The file below records the reproduction configuration and hashes:

```text
REPRODUCTION.json
```

The complete package checksum list is stored in:

```text
CHECKSUMS.sha256
```

## Generate the manuscript

The final English manuscript can be generated with:

```powershell
python extended/analysis/apply_itt2026_template.py
```

The generated document is written to:

```text
itt2026_output/ITT2026_Final_Manuscript_EN.docx
```

The manuscript contains:

- ten numbered native Word equations;
- four numbered scientific tables;
- one figure;
- twelve references;
- the six listed authors and their affiliations.

The supplied conference template is preserved in:

```text
extended/template/conference-template-a4.docx
```

Template alignment information is recorded in:

```text
extended/template_alignment.json
```

Document validation information is recorded in:

```text
extended/document_validation.json
```

## Mathematical definitions

For a valid attacked execution, U denotes user-task completion and A denotes attacker-goal success.

The joint outcome is:

```text
J = U(1 - A)
```

Its mean satisfies:

```text
j = u(1 - a) - Cov(U,A)
```

Multiplying marginal rates assumes zero covariance.

Classical Frechet-Hoeffding bounds give:

```text
max(0, u - a) <= j <= min(u, 1 - a)
```

The bounds are applied separately within suites and then averaged with equal suite weights.

Printed percentages are treated with a +/-0.005 percentage-point rounding tolerance.

Identification intervals represent uncertainty caused by missing dependence information. They are not confidence intervals and do not measure sampling variation.

## Main findings

The analysis reports:

- 540 within-model configuration pairs;
- 337 pairs strictly ordered using pooled marginals;
- 394 pairs strictly ordered using suite-level marginals;
- 57 additional ordered pairs after using suite-level information;
- 298 pairs whose joint ordering opposes ordering by lower attack success;
- three detected arithmetic inconsistencies in printed Overall values;
- zero new model executions.

The archival pilot demonstrates that multiplying marginal task-success and attack-failure rates need not recover the observed joint-completion rate.

## Provenance and attribution

The primary published source is:

```text
H. Li, R. Wen, S. Shi, N. Zhang, Y. Vorobeychik, and C. Xiao,
"AgentDyn: Are Your Agent Security Defenses Deployable in Real-World Dynamic Environments?"
arXiv:2602.03117v3, 2026.
```

The source repository is:

```text
https://github.com/SaFo-Lab/AgentDyn
```

The analysis uses the following pinned snapshot:

```text
5353cf7615b135cace8d07c8f12dac53a16b6db3
```

The upstream license notice is retained in:

```text
sources/AgentDyn_LICENSE.txt
```

The upstream authors and source materials are not claimed as original work of the authors of this analysis.

The file below contains a selected repository inventory:

```text
sources/agentdyn_tree.json
```

It is not a complete copy of the upstream repository.

## Licensing

The root LICENSE file applies to the original analysis code and associated documentation created for this package.

It does not relicense or claim ownership of:

- AgentDyn source code;
- AgentDyn archived execution logs;
- third-party benchmark materials;
- third-party documentation;
- other upstream materials.

Applicable upstream attribution and license notices are retained.

Users should consult the upstream AgentDyn repository and its license terms before reusing original upstream materials.

## AI assistance

OpenAI ChatGPT assisted with study design, mathematical exposition, drafting, editing, and code generation.

The reported numerical results were computed by the supplied analysis scripts from the cited source material.

The submitting authors remain responsible for the analysis, citations, licensing statements, AI-assistance disclosure, and final conference formatting.

## Repository contents

```text
analysis/                       Pilot analysis scripts and results
data/pilot_manifest.json        Manifest of upstream log paths and hashes
data/download_report.json       Download and hash report
extended/                       Published-table analysis and manuscript builder
sources/                        Source notices, metadata, and preserved tables
CHECKSUMS.sha256                Package checksums
LICENSE                         License for original package materials
PROVENANCE.json                 Provenance information
README.md                      This file
REPRODUCTION.json               Reproduction record
requirements.txt                Pinned Python dependencies
```

The original upstream execution logs are intentionally not included in this repository.