# JobFit v1 benchmark

Status: authored synthetic evaluation fixture, 5 November 2026. **Not real vacancies, independent human ratings, or a representative real-world matching benchmark.** No private CVs, live job collection, network requests, paid models, or secrets are needed.

## Dataset and split

- 60 fictional postings, grouped into 30 families with two related variants each.
- Five fictional candidate profiles: .NET backend, full-stack web, Python backend/automation, applied AI/ML, Android.
- 300 provisional candidate/job judgments covering the complete cross-product.
- Development: 36 postings / 18 families / 180 judgments.
- Test: 24 postings / 12 families / 120 judgments.
- A family and its wording variant stay in one split. URLs and normalized posting content must also be unique.

Cases include equivalent wording, cross-stack partial fit, keyword-heavy nonengineering jobs, seniority gaps, explicit country restrictions, unknown eligibility, relocation uncertainty, missing/non-USD salaries, below-target pay, high annual salaries, and untrusted instructions embedded in a posting. These are designed scenarios, not sampled labor-market frequencies. Titles/descriptions are deliberately short, so long-document and real-source generalization remain unmeasured.

`tools/build_jobfit_benchmark.py` contains explicit scenario definitions and overlap grades. It never calls the scorer to generate labels. That separation does not make the labels independent: both are authored project assets and require external review.

## Files

- `manifest.json`: schema, candidate paths, provenance, split unit, grading threshold, SHA-256 hashes.
- `jobs.jsonl`: posting records plus benchmark ID, family ID, split, and slice tags.
- `judgments.jsonl`: all candidate/job grades, eligibility, expected normalized pay, and rationale.
- `candidates/*.json`: fictional CV evidence and matching preferences.
- `results/`: archived synthetic baseline outputs, added after evaluation. Results are not frozen input data.

The initial candidate location/preferences mirror the workflow requirements (Pakistan-based, remote preferred, relocation possible, USD 2000/month soft target, no upper salary cap). Candidate identities and work history are fictional. Results do not assess Hassan or any team member.

## Label rubric

Technical relevance is independent of compensation and geographic eligibility:

| Grade | Meaning |
|---|---|
| 0 | Different occupation or no meaningful engineering evidence for the task. |
| 1 | Adjacent skills, substantial task/domain gaps. |
| 2 | Useful technical match with identifiable missing requirements. |
| 3 | Strong match to the authored task from supplied CV evidence. |

For the synthetic family matrix, senior leadership requirements reduce a technical grade 3 to 2 because the CVs contain only three years and no leadership evidence. Reviewers may reasonably disagree; rationale and adjudication matter more than preserving these provisional numbers.

Eligibility labels:

- `eligible`: source explicitly permits the candidate country/worldwide and no blocking constraint is given. This is not a legal work-authorization guarantee.
- `ineligible`: an explicit restriction excludes this candidate or a strict candidate constraint is violated.
- `unknown`: country scope, remote arrangement, sponsorship, or relocation still requires confirmation.

Expected pay is the USD/month lower bound when currency and monthly/annual period are explicit. Non-USD, hourly-without-hours, and missing pay use blank/null. A low salary never makes a job geographically ineligible, and a high salary is never excluded.

## Reproduce

Run from the repository root:

```powershell
python tools/build_jobfit_benchmark.py --check
python benchmark.py validate
python benchmark.py evaluate --split dev --output output/benchmark-dev
python benchmark.py evaluate --split test --output output/benchmark-test
```

The builder refuses to overwrite an existing fixture. `--check` compares all frozen inputs byte-for-byte with deterministic scenario generation. The loader validates hashes, schemas, unique identities, family isolation, and complete judgments before running either split.

The evaluator produces `report.md`, `report.json`, and `cases.jsonl`. Every attempted pair remains in the denominator, including scorer errors. No database is written, and no application is submitted. Report directories may be regenerated; immutable input changes require a new benchmark version.

## Metrics

- NDCG@k uses graded gain `2^grade - 1`; known-ineligible items receive zero actionable gain.
- Precision@k and recall@k treat actionable grades 2/3 as relevant. Unknown eligibility remains reviewable and is reported separately.
- MRR@k is reciprocal rank of the first actionable grade-2/3 item, or zero if absent within k.
- Ineligible@k and unknown@k use reference eligibility, exposing safety/uncertainty even when a scorer misclassifies it.
- Macro ranking averages give equal weight to each candidate, not each job. Precision divides by the available retrieved count when fewer than k exist.
- NDCG is n/a if all reference gains are zero; recall is n/a if no actionable grade-2/3 item exists. Such values are excluded from that macro mean; per-candidate rows show support.
- Eligibility confusion and missed-ineligible rate include all attempts; scorer errors are not credited as correct unknown predictions.
- Pay-normalization accuracy compares expected numeric/null values without invented FX rates.
- Exact quote support verifies source ID/substrings only. It does not establish semantic entailment, truthful CV claims, or overall fit.
- Local p50/p95 scoring latency excludes provider/network latency. No cost or model-quality metric is fabricated when no model runs.

Both baselines use the same country/pay rules. Title-only matches configured role names; keyword uses the existing evidence-backed scorer. This is a baseline comparison, not an AI-model comparison.

## Independent annotation workflow

```powershell
python benchmark.py annotations --output output/annotation-reviewer-a.csv
python benchmark.py annotations --output output/annotation-reviewer-b.csv
```

Each worksheet has 300 rows with candidate evidence and posting context, but no scores, grades, or suggested eligibility decisions. Reviewers should not inspect provisional labels or result reports before labeling. The fixture is public, so this is procedural blinding rather than an access-control guarantee.

1. Give each reviewer the rubric and blank worksheet.
2. Fill relevance, eligibility, expected_monthly_usd (blank when unknown), reviewer identifier, and rationale for every row.
3. Compare disagreements and create an adjudicated complete worksheet; retain both originals. Inter-rater agreement/consensus automation is not implemented.
4. Evaluate the completed file:

```powershell
python benchmark.py evaluate --split dev --annotations output/adjudicated.csv --output output/reviewed-dev
```

CSV imports require complete pair coverage, valid labels/pay, and reviewer/rationale fields. Provenance is reported as reviewer-declared, not independently authenticated human review. Do not overwrite the provisional inputs to make reviewed results look identical to the original fixture.

## Test-set discipline

Use development cases for implementation. The test split holds out posting families, not candidate identities or every scenario type. Once its results have been inspected, call it an observed evaluation split. Do not tune to its failures and then keep describing it as a pristine final test; create a new version/final set before a later quality claim.

No confidence interval or significance claim is supplied: the corpus is intentionally small and authored, and paired variants are correlated. A larger independently sampled/reviewed corpus is the next evidence milestone.
