# JobFit v1: dev baseline report

Generated: 2026-11-05T17:09:30.027344+00:00
Labels: scenario_authored_provisional

36 authored postings / 18 families / 5 fictional CVs / 180 judgments.

**Synthetic evaluation only. These are not real vacancies, independent human ratings, or measured hiring outcomes.**

| Scorer | NDCG@k | Precision@k | Recall@k | MRR@k | Ineligible@k | Unknown@k |
|---|---|---|---|---|---|---|
| title_only | 0.6049 | 0.5600 | 0.3114 | 0.8000 | 0.0000 | 0.4400 |
| keyword | 0.8940 | 0.9200 | 0.5514 | 1.0000 | 0.0000 | 0.4000 |

k = 5. Macro averages give equal weight to each candidate. Relevance threshold is 2. Known-ineligible jobs have zero actionable relevance; unknown eligibility stays reviewable and is reported separately.

## title_only

Completed: 180/180; eligibility accuracy: 1.0000; missed-ineligible rate: 0.0000.
Pay-normalization accuracy: 1.0000; exact-quote support: n/a over 0 excerpts.
Local scoring latency (ms): p50 0.0583, p95 0.1874. This excludes network/model latency.

| Candidate | NDCG@k | Precision@k | Recall@k | MRR@k |
|---|---|---|---|---|
| aiml | 1.0000 | 1.0000 | 0.5000 | 1.0000 |
| android | 0.7822 | 0.4000 | 0.5000 | 1.0000 |
| dotnet | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| fullstack | 0.6670 | 0.4000 | 0.2000 | 1.0000 |
| python | 0.5755 | 1.0000 | 0.3571 | 1.0000 |

### Eligibility confusion

| Expected | Predicted eligible | Predicted ineligible | Predicted unknown | Error |
|---|---|---|---|---|
| eligible | 90 | 0 | 0 | 0 |
| ineligible | 0 | 30 | 0 | 0 |
| unknown | 0 | 0 | 60 | 0 |

### Error and risk slices

| Slice | Cases | Eligibility accuracy | Pay accuracy |
|---|---|---|---|
| country_restriction | 30 | 1.0000 | 1.0000 |
| hard_negative | 30 | 1.0000 | 1.0000 |
| high_salary | 30 | 1.0000 | 1.0000 |
| missing_salary | 15 | 1.0000 | 1.0000 |
| non_usd | 45 | 1.0000 | 1.0000 |
| paraphrase_pair | 150 | 1.0000 | 1.0000 |
| relocation | 30 | 1.0000 | 1.0000 |
| seniority_gap | 30 | 1.0000 | 1.0000 |
| soft_salary_target | 60 | 1.0000 | 1.0000 |
| synthetic | 180 | 1.0000 | 1.0000 |
| unknown_eligibility | 30 | 1.0000 | 1.0000 |
| untrusted_instruction | 15 | 1.0000 | 1.0000 |
| worldwide | 60 | 1.0000 | 1.0000 |

### Failure analysis

Counts: {"nonrelevant_top_k": 11, "relevant_below_k": 34}

First 20 flagged candidate/job cases are included below; the JSONL export contains every attempted case. Multiple reasons can apply to one case.

- aiml / aiml_4_b: rank 6, grade 3, reasons: relevant_below_k.
- aiml / python_3_a: rank 27, grade 2, reasons: relevant_below_k.
- aiml / python_3_b: rank 28, grade 2, reasons: relevant_below_k.
- aiml / python_5_a: rank 29, grade 2, reasons: relevant_below_k.
- aiml / python_5_b: rank 30, grade 2, reasons: relevant_below_k.
- android / aiml_1_a: rank 3, grade 0, reasons: nonrelevant_top_k.
- android / aiml_1_b: rank 4, grade 0, reasons: nonrelevant_top_k.
- android / aiml_3_a: rank 5, grade 0, reasons: nonrelevant_top_k.
- android / android_5_a: rank 9, grade 2, reasons: relevant_below_k.
- android / android_5_b: rank 10, grade 2, reasons: relevant_below_k.
- dotnet / aiml_1_a: rank 1, grade 0, reasons: nonrelevant_top_k.
- dotnet / aiml_1_b: rank 2, grade 0, reasons: nonrelevant_top_k.
- dotnet / aiml_3_a: rank 3, grade 0, reasons: nonrelevant_top_k.
- dotnet / aiml_3_b: rank 4, grade 0, reasons: nonrelevant_top_k.
- dotnet / aiml_4_a: rank 5, grade 0, reasons: nonrelevant_top_k.
- dotnet / dotnet_3_a: rank 11, grade 3, reasons: relevant_below_k.
- dotnet / dotnet_3_b: rank 12, grade 3, reasons: relevant_below_k.
- dotnet / dotnet_4_a: rank 13, grade 3, reasons: relevant_below_k.
- dotnet / dotnet_4_b: rank 14, grade 3, reasons: relevant_below_k.
- dotnet / dotnet_5_a: rank 15, grade 2, reasons: relevant_below_k.
## keyword

Completed: 180/180; eligibility accuracy: 1.0000; missed-ineligible rate: 0.0000.
Pay-normalization accuracy: 1.0000; exact-quote support: 1.0000 over 210 excerpts.
Local scoring latency (ms): p50 0.2584, p95 0.4563. This excludes network/model latency.

| Candidate | NDCG@k | Precision@k | Recall@k | MRR@k |
|---|---|---|---|---|
| aiml | 1.0000 | 1.0000 | 0.5000 | 1.0000 |
| android | 0.9735 | 0.8000 | 1.0000 | 1.0000 |
| dotnet | 0.7393 | 1.0000 | 0.5000 | 1.0000 |
| fullstack | 0.9392 | 0.8000 | 0.4000 | 1.0000 |
| python | 0.8178 | 1.0000 | 0.3571 | 1.0000 |

### Eligibility confusion

| Expected | Predicted eligible | Predicted ineligible | Predicted unknown | Error |
|---|---|---|---|---|
| eligible | 90 | 0 | 0 | 0 |
| ineligible | 0 | 30 | 0 | 0 |
| unknown | 0 | 0 | 60 | 0 |

### Error and risk slices

| Slice | Cases | Eligibility accuracy | Pay accuracy |
|---|---|---|---|
| country_restriction | 30 | 1.0000 | 1.0000 |
| hard_negative | 30 | 1.0000 | 1.0000 |
| high_salary | 30 | 1.0000 | 1.0000 |
| missing_salary | 15 | 1.0000 | 1.0000 |
| non_usd | 45 | 1.0000 | 1.0000 |
| paraphrase_pair | 150 | 1.0000 | 1.0000 |
| relocation | 30 | 1.0000 | 1.0000 |
| seniority_gap | 30 | 1.0000 | 1.0000 |
| soft_salary_target | 60 | 1.0000 | 1.0000 |
| synthetic | 180 | 1.0000 | 1.0000 |
| unknown_eligibility | 30 | 1.0000 | 1.0000 |
| untrusted_instruction | 15 | 1.0000 | 1.0000 |
| worldwide | 60 | 1.0000 | 1.0000 |

### Failure analysis

Counts: {"nonrelevant_top_k": 2, "relevant_below_k": 25}

First 20 flagged candidate/job cases are included below; the JSONL export contains every attempted case. Multiple reasons can apply to one case.

- aiml / aiml_4_b: rank 6, grade 3, reasons: relevant_below_k.
- aiml / python_5_a: rank 10, grade 2, reasons: relevant_below_k.
- aiml / python_5_b: rank 11, grade 2, reasons: relevant_below_k.
- aiml / python_3_a: rank 15, grade 2, reasons: relevant_below_k.
- aiml / python_3_b: rank 22, grade 2, reasons: relevant_below_k.
- android / negative_sales_a: rank 5, grade 0, reasons: nonrelevant_top_k.
- dotnet / dotnet_4_b: rank 6, grade 3, reasons: relevant_below_k.
- dotnet / fullstack_1_a: rank 18, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_1_b: rank 24, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_4_a: rank 29, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_4_b: rank 30, grade 2, reasons: relevant_below_k.
- fullstack / negative_sales_a: rank 5, grade 0, reasons: nonrelevant_top_k.
- fullstack / dotnet_5_a: rank 14, grade 2, reasons: relevant_below_k.
- fullstack / dotnet_5_b: rank 15, grade 2, reasons: relevant_below_k.
- fullstack / dotnet_3_a: rank 22, grade 2, reasons: relevant_below_k.
- fullstack / dotnet_3_b: rank 26, grade 2, reasons: relevant_below_k.
- fullstack / dotnet_4_a: rank 29, grade 2, reasons: relevant_below_k.
- fullstack / dotnet_4_b: rank 30, grade 2, reasons: relevant_below_k.
- python / negative_qa_a: rank 6, grade 2, reasons: relevant_below_k.
- python / negative_analyst_b: rank 7, grade 2, reasons: relevant_below_k.

## Reproducibility

Manifest SHA-256: `40b7cb7e30765831a5630d48f7425be45ea035799cbb6000f6920e9013d67413`
Judgments SHA-256: `874bdf7a9615622b4552cef3d95c3a21e1d164e5b6d4decd8006248ed93be3cf`

Code hashes:
```json
{
  "benchmark.py": "cb1e4f8fbecaa61cb2464eb3164bb25f06b99c36397eda7f05cd4686765ce0f8",
  "models.py": "69d584911faedc99bde25d7adb36a7c8017063909eab2ce3950575960cc0b00c",
  "scoring.py": "4c24fc3dbdc8fc51e5e456bff41e6960faed6ab1a8bd3e3f9cedb35b305fe936"
}
```

Both scorers use the same eligibility and pay rules. Title-only uses role-title matching, while keyword uses the existing evidence-backed baseline. This is not an AI-model comparison.

Missing/failed cases remain in denominators. NDCG is n/a when all reference gains are zero; recall is n/a when no actionable grade-2/3 items exist. Exact quote support only validates provenance, not semantic entailment or truth.

## Limitations

- Authored synthetic scenarios and provisional labels; not independent real-world quality evidence.
- Candidate CVs are fictional. No private CVs, network access, model calls, or learned semantic matcher are used.
- Unknown eligibility remains reviewable; it is not permission to apply. Exact-quote checks do not establish semantic truth.
- Once test results are inspected, this split is observed. Future tuning needs a fresh final evaluation set.
