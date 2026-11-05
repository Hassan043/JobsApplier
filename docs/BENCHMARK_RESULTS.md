# Ranking benchmark results - 5 November 2026

Status: synthetic baseline comparison. No private CVs, live role search, model calls, or independent human ratings.

The versioned [JobFit v1 corpus](../benchmarks/jobfit_v1/README.md) contains 60 authored postings, 30 families, five fictional candidate profiles, and 300 provisional judgments. Development uses 36 postings; test uses 24, with no family overlap.

| Split | Scorer | NDCG@5 | Precision@5 | Recall@5 | MRR@5 | Ineligible@5 | Unknown@5 |
|---|---|---|---|---|---|---|---|
| Development | title_only | 0.605 | 0.560 | 0.311 | 0.800 | 0.000 | 0.440 |
| Development | keyword | 0.894 | 0.920 | 0.551 | 1.000 | 0.000 | 0.400 |
| Test (observed) | title_only | 0.498 | 0.400 | 0.383 | 0.533 | 0.000 | 0.400 |
| Test (observed) | keyword | 0.827 | 0.680 | 0.633 | 1.000 | 0.000 | 0.320 |

## Interpretation

- Keyword matching outperforms title-only matching on these authored labels. This is not proof of real-world AI ranking quality, calibrated job fit, or hiring impact.
- Technical-content-writing examples are incorrectly retrieved for AI/ML candidates because shared technology words outweigh occupation differences. A future matcher should evaluate the task being performed and negative evidence, not only vocabulary.
- Relevant alternate-title jobs can fall below the top-five cutoff; synonym/task understanding is a justified next hypothesis. Some relevant-below-k flags are unavoidable in a limited shortlist and are diagnostics, not automatically defects.
- Both baselines share country/pay rules, so their identical eligibility/pay accuracy on this small fixture is not evidence one ranker is safer. Country rules remain narrow and require a broader reviewed challenge set.
- Exact-quote support only checks provenance; a quote can be real but irrelevant or misleading. Semantic entailment still needs independent review.
- Unknown eligibility remains visible. None of these results authorizes an application or establishes work authorization.
- Test results are now observed. Do not optimize against them and then claim the same split is a fresh final evaluation.

## Reproduce and review

```powershell
python tools/build_jobfit_benchmark.py --check
python benchmark.py validate
python benchmark.py evaluate --split dev
python benchmark.py evaluate --split test
python benchmark.py annotations --output output/reviewer.csv
```

Two reviewers should independently label blank worksheets, then adjudicate disagreements. Use the completed CSV with `--annotations`; provenance remains reviewer-declared. The shipped provisional labels are not silently replaced.

## Artifacts

- [Development report](../benchmarks/jobfit_v1/results/dev_report.md)
- [Observed test report](../benchmarks/jobfit_v1/results/test_report.md)
- Each report has a JSON counterpart and complete per-case JSONL with hashes, scorer versions, failure categories, and measured local latency.
- [Full protocol and grading rubric](../benchmarks/jobfit_v1/README.md)

CI runs hash validation, family/label checks, offline tests, and development evaluation. It does not tune to a test score or enforce an arbitrary ranking-quality threshold. No remote CI execution is claimed.
