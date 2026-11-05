# JobFit v1: test baseline report

Generated: 2026-11-05T17:08:07.574989+00:00
Labels: scenario_authored_provisional

24 authored postings / 12 families / 5 fictional CVs / 120 judgments.

**Synthetic evaluation only. These are not real vacancies, independent human ratings, or measured hiring outcomes.**

| Scorer | NDCG@k | Precision@k | Recall@k | MRR@k | Ineligible@k | Unknown@k |
|---|---|---|---|---|---|---|
| title_only | 0.4979 | 0.4000 | 0.3833 | 0.5333 | 0.0000 | 0.4000 |
| keyword | 0.8267 | 0.6800 | 0.6333 | 1.0000 | 0.0000 | 0.3200 |

k = 5. Macro averages give equal weight to each candidate. Relevance threshold is 2. Known-ineligible jobs have zero actionable relevance; unknown eligibility stays reviewable and is reported separately.

## title_only

Completed: 120/120; eligibility accuracy: 1.0000; missed-ineligible rate: 0.0000.
Pay-normalization accuracy: 1.0000; exact-quote support: n/a over 0 excerpts.
Local scoring latency (ms): p50 0.0274, p95 0.0435. This excludes network/model latency.

| Candidate | NDCG@k | Precision@k | Recall@k | MRR@k |
|---|---|---|---|---|
| aiml | 0.5531 | 0.4000 | 0.3333 | 1.0000 |
| android | 0.5143 | 0.6000 | 0.7500 | 0.3333 |
| dotnet | 0.7428 | 0.4000 | 0.3333 | 1.0000 |
| fullstack | 0.1918 | 0.0000 | 0.0000 | 0.0000 |
| python | 0.4874 | 0.6000 | 0.5000 | 0.3333 |

### Eligibility confusion

| Expected | Predicted eligible | Predicted ineligible | Predicted unknown | Error |
|---|---|---|---|---|
| eligible | 60 | 0 | 0 | 0 |
| ineligible | 0 | 20 | 0 | 0 |
| unknown | 0 | 0 | 40 | 0 |

### Error and risk slices

| Slice | Cases | Eligibility accuracy | Pay accuracy |
|---|---|---|---|
| country_restriction | 20 | 1.0000 | 1.0000 |
| hard_negative | 20 | 1.0000 | 1.0000 |
| high_salary | 20 | 1.0000 | 1.0000 |
| missing_salary | 10 | 1.0000 | 1.0000 |
| non_usd | 30 | 1.0000 | 1.0000 |
| paraphrase_pair | 100 | 1.0000 | 1.0000 |
| relocation | 20 | 1.0000 | 1.0000 |
| seniority_gap | 20 | 1.0000 | 1.0000 |
| soft_salary_target | 40 | 1.0000 | 1.0000 |
| synthetic | 120 | 1.0000 | 1.0000 |
| unknown_eligibility | 20 | 1.0000 | 1.0000 |
| untrusted_instruction | 10 | 1.0000 | 1.0000 |
| worldwide | 40 | 1.0000 | 1.0000 |

### Failure analysis

Counts: {"nonrelevant_top_k": 15, "relevant_below_k": 18}

First 20 flagged candidate/job cases are included below; the JSONL export contains every attempted case. Multiple reasons can apply to one case.

- aiml / android_3_a: rank 3, grade 0, reasons: nonrelevant_top_k.
- aiml / android_3_b: rank 4, grade 0, reasons: nonrelevant_top_k.
- aiml / android_4_a: rank 5, grade 0, reasons: nonrelevant_top_k.
- aiml / python_1_a: rank 17, grade 2, reasons: relevant_below_k.
- aiml / python_1_b: rank 18, grade 2, reasons: relevant_below_k.
- aiml / python_4_a: rank 19, grade 2, reasons: relevant_below_k.
- aiml / python_4_b: rank 20, grade 2, reasons: relevant_below_k.
- android / aiml_5_a: rank 1, grade 0, reasons: nonrelevant_top_k.
- android / aiml_5_b: rank 2, grade 0, reasons: nonrelevant_top_k.
- android / android_4_b: rank 6, grade 3, reasons: relevant_below_k.
- dotnet / aiml_5_a: rank 3, grade 0, reasons: nonrelevant_top_k.
- dotnet / aiml_5_b: rank 4, grade 0, reasons: nonrelevant_top_k.
- dotnet / android_3_a: rank 5, grade 0, reasons: nonrelevant_top_k.
- dotnet / fullstack_3_a: rank 9, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_3_b: rank 10, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_5_a: rank 11, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_5_b: rank 12, grade 2, reasons: relevant_below_k.
- fullstack / aiml_5_a: rank 1, grade 1, reasons: nonrelevant_top_k.
- fullstack / aiml_5_b: rank 2, grade 1, reasons: nonrelevant_top_k.
- fullstack / android_3_a: rank 3, grade 1, reasons: nonrelevant_top_k.
## keyword

Completed: 120/120; eligibility accuracy: 1.0000; missed-ineligible rate: 0.0000.
Pay-normalization accuracy: 1.0000; exact-quote support: 1.0000 over 140 excerpts.
Local scoring latency (ms): p50 0.0824, p95 0.2881. This excludes network/model latency.

| Candidate | NDCG@k | Precision@k | Recall@k | MRR@k |
|---|---|---|---|---|
| aiml | 0.6992 | 0.6000 | 0.5000 | 1.0000 |
| android | 1.0000 | 0.8000 | 1.0000 | 1.0000 |
| dotnet | 0.7680 | 0.4000 | 0.3333 | 1.0000 |
| fullstack | 0.7422 | 0.8000 | 0.6667 | 1.0000 |
| python | 0.9239 | 0.8000 | 0.6667 | 1.0000 |

### Eligibility confusion

| Expected | Predicted eligible | Predicted ineligible | Predicted unknown | Error |
|---|---|---|---|---|
| eligible | 60 | 0 | 0 | 0 |
| ineligible | 0 | 20 | 0 | 0 |
| unknown | 0 | 0 | 40 | 0 |

### Error and risk slices

| Slice | Cases | Eligibility accuracy | Pay accuracy |
|---|---|---|---|
| country_restriction | 20 | 1.0000 | 1.0000 |
| hard_negative | 20 | 1.0000 | 1.0000 |
| high_salary | 20 | 1.0000 | 1.0000 |
| missing_salary | 10 | 1.0000 | 1.0000 |
| non_usd | 30 | 1.0000 | 1.0000 |
| paraphrase_pair | 100 | 1.0000 | 1.0000 |
| relocation | 20 | 1.0000 | 1.0000 |
| seniority_gap | 20 | 1.0000 | 1.0000 |
| soft_salary_target | 40 | 1.0000 | 1.0000 |
| synthetic | 120 | 1.0000 | 1.0000 |
| unknown_eligibility | 20 | 1.0000 | 1.0000 |
| untrusted_instruction | 10 | 1.0000 | 1.0000 |
| worldwide | 40 | 1.0000 | 1.0000 |

### Failure analysis

Counts: {"nonrelevant_top_k": 8, "relevant_below_k": 11}

First 20 flagged candidate/job cases are included below; the JSONL export contains every attempted case. Multiple reasons can apply to one case.

- aiml / negative_writer_a: rank 3, grade 0, reasons: nonrelevant_top_k.
- aiml / negative_writer_b: rank 5, grade 0, reasons: nonrelevant_top_k.
- aiml / python_1_b: rank 6, grade 2, reasons: relevant_below_k.
- aiml / python_4_a: rank 17, grade 2, reasons: relevant_below_k.
- aiml / python_4_b: rank 18, grade 2, reasons: relevant_below_k.
- android / negative_writer_a: rank 5, grade 0, reasons: nonrelevant_top_k.
- dotnet / negative_writer_a: rank 3, grade 0, reasons: nonrelevant_top_k.
- dotnet / negative_writer_b: rank 4, grade 0, reasons: nonrelevant_top_k.
- dotnet / python_1_a: rank 5, grade 1, reasons: nonrelevant_top_k.
- dotnet / fullstack_5_a: rank 9, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_5_b: rank 10, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_3_a: rank 13, grade 2, reasons: relevant_below_k.
- dotnet / fullstack_3_b: rank 16, grade 2, reasons: relevant_below_k.
- fullstack / negative_writer_a: rank 5, grade 0, reasons: nonrelevant_top_k.
- fullstack / dotnet_1_a: rank 11, grade 2, reasons: relevant_below_k.
- fullstack / dotnet_1_b: rank 14, grade 2, reasons: relevant_below_k.
- python / dotnet_1_a: rank 3, grade 1, reasons: nonrelevant_top_k.
- python / aiml_5_a: rank 9, grade 2, reasons: relevant_below_k.
- python / aiml_5_b: rank 10, grade 2, reasons: relevant_below_k.

## Reproducibility

Manifest SHA-256: `40b7cb7e30765831a5630d48f7425be45ea035799cbb6000f6920e9013d67413`
Judgments SHA-256: `874bdf7a9615622b4552cef3d95c3a21e1d164e5b6d4decd8006248ed93be3cf`

Code hashes:
```json
{
  "benchmark.py": "fa98f625c19d3575933757e3e21cba6f20fb34c1386b258b5c8beb718fe1cb9b",
  "models.py": "9d7f0559aa7eb453d66f7dde7fdf04c4d879a034ef91f405f4f99ae4a8aeb53b",
  "scoring.py": "51d22b1425bcdbe1ae623ca64c7a71629b02ef33d867a95bc48389bda51f3a6e"
}
```

Both scorers use the same eligibility and pay rules. Title-only uses role-title matching, while keyword uses the existing evidence-backed baseline. This is not an AI-model comparison.

Missing/failed cases remain in denominators. NDCG is n/a when all reference gains are zero; recall is n/a when no actionable grade-2/3 items exist. Exact quote support only validates provenance, not semantic entailment or truth.

## Limitations

- Authored synthetic scenarios and provisional labels; not independent real-world quality evidence.
- Candidate CVs are fictional. No private CVs, network access, model calls, or learned semantic matcher are used.
- Unknown eligibility remains reviewable; it is not permission to apply. Exact-quote checks do not establish semantic truth.
- Once test results are inspected, this split is observed. Future tuning needs a fresh final evaluation set.
