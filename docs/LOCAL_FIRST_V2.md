# Jobs Applier v2: implementation and portfolio evidence

Status: implemented first local-first release, 5 November 2026. The legacy scripts remain preserved and are not covered by the new workflow's runtime guarantees.

## Actual system

```text
JSON / JSONL / CSV / saved JobPosting JSON-LD / explicit public job feeds
                         |
                typed normalized Job records
                         |
      canonical URL and normalized-content deduplication
                         |
    CV-specific profile + source-addressable evidence sections
                         |
   deterministic eligibility/pay signals and keyword baseline
                         |
 optional OpenAI structured fit assessment (explicit opt-in/cap)
                         |
       exact candidate/posting quotation validation
                         |
    SQLite cache + per-profile manual application status
                         |
        escaped private HTML / safe CSV / JSON reports
```

No automatic application submission, email, or Sheets writes are implemented in v2. No paid model requests were made during development. Optional AI request/validation behavior is tested using a fake client; live model quality remains unmeasured.

## Modules

- `models.py`: profile/CV loading, stable URL identity, content fingerprint, typed salary/workplace input. Text/Markdown CVs are supported without dependencies; PDFs use lazy pdfplumber import. Scanned PDFs need external text extraction.
- `sources.py`: bounded file imports, JobPosting JSON-LD, legacy-compatible Pangian payload parser, and read-only Greenhouse/Lever adapters. Board identifiers are allowlisted syntactically, destinations fixed, response sizes bounded, requests time out after 15 seconds.
- `scoring.py`: transparently labeled keyword baseline; only profile skills appearing in evidence can contribute. Country restrictions, remote preference, market preference, and pay-period signals remain separate. USD annual values normalize by 12; no guessed currency conversion or hourly workload assumptions. No salary upper cap.
- `ai.py`: optional Responses API request with strict JSON schema, explicit model/key, 30-second timeout, disabled SDK retries, 2500 response-token cap. Exact source quotations and requirement excerpts are independently checked. Refusal, incomplete response, malformed evidence, and exceptions have no AI score and stop further calls for the run.
- `store.py`: SQLite schema version 1, jobs, analyses, applications. Exact CV/profile hash owns analysis/application state. Cache key includes normalized job version, profile hash, model, prompt version, and scoring version. Failed/budget-exhausted assessments remain reviewable but are not reused as cache hits.
- `report.py`: private static HTML with escaped text and a restrictive content policy, CSV formula guarding, structured JSON. No third-party scripts/fonts or report server.
- `cli.py`: explicit collection/inference, global unique-job cap, global cross-profile AI-call cap, deterministic dry-run, application tracking, and report rebuilding.

## Persistence and consistency

The job URL is canonicalized without deleting semantic query parameters. Tracking parameters and fragments are removed. Content fingerprints include eligibility/workplace/pay/location fields so materially different postings are not silently merged. Same-content cross-source duplicates reuse the canonical stored record.

Job upserts preserve application state. Each profile/variant has independent application status, so one team member marking applied does not alter another's state. A changed profile creates a new hash; historical status does not automatically migrate to the changed CV. A future stable candidate identity would need an explicit migration.

Analyses store profile/model/scoring provenance. Changed job payload or profile invalidates cache identity. Report rebuild excludes assessments for old job versions. Application status changes are local labels reflecting manual actions, not proof an application was submitted.

## Operational boundaries

- Dry-run accepts only local files and makes no database, report, network, or model writes/calls.
- Ordinary local runs persist reports/state but need no credentials or installed AI SDK.
- The keyword baseline is not semantic search, a trained model, or a hiring probability.
- Eligibility rules are deliberately narrow and incomplete. A remote label or employer country does not establish applicant eligibility. Unknown country/work authorization/sponsorship remains a human review task.
- Salary targets are soft. Missing, below-target, and non-USD salaries remain present. Compensation figures are taken from input/source fields, not verified offers.
- Source retrieval is bounded and incomplete. Greenhouse fetches one bounded response; Lever is limited to its first 100 postings with a truncation warning. Source ordering/caps can affect coverage.
- Partial-source warnings are included in the run summary; an entirely failed/invalid collection exits without model/database/report work. No empty-success claim substitutes for an outage.
- Database and report files are private local data, not a multi-user secure service. No tenant-isolation or encrypted-at-rest guarantee is claimed.

## Portfolio presentation

Demonstrate a synthetic import with duplicate postings, one explicit country restriction, one unknown salary, and one high annual salary. Show evidence-backed keyword matches, optional fake-client AI contract tests, a rejected fabricated quote, and independent per-profile status.

Then show the offline evaluation runner with its labeled synthetic cases. The three-case fixture only verifies pipeline/metric reproducibility; a perfect fixture ranking says nothing about real ranking quality. A proper AI-quality claim needs a larger independently labeled held-out set and optional live-model evaluation with explicit consent and cost budget.

## Verified versus outstanding

Verified: 39 automated tests at initial implementation checkpoint; CLI help; synthetic full run; offline evaluation; private local CV loading; public Greenhouse smoke check. No claims of calibrated real-model matching or automatic application delivery.

Outstanding: semantic retrieval/reranking, a representative labeled benchmark, stable candidate IDs across CV revisions, source pagination/fairness, richer eligibility extraction, reviewed live-model experiments, refreshed paid-board adapters, optional Sheets sync, and UI beyond static reports.

## Official integration references

- [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board)
- [Lever Postings API](https://github.com/lever/postings-api)

## Benchmark infrastructure update - 5 November 2026

The new [JobFit protocol](../benchmarks/jobfit_v1/README.md) and [baseline report](BENCHMARK_RESULTS.md) provide 60 authored synthetic postings, 300 provisional judgments, family-separated dev/test evaluation, independent-review worksheets, and detailed failure reports. This expands the old three-case smoke evaluator rather than replacing it. The corpus is not an independently human-labeled real-world benchmark.

The local test suite now has 68 passing tests. Missing/duplicate labels, frozen-input tampering, path escape, external CV indirection, family leakage, malformed scorer outputs, error denominators, metrics, and annotation handling are checked offline. Actual model-quality evaluation and representative independent labels remain outstanding.

## Portal extension and repository cleanup

The current source inventory has 175 distinct entries with explicit implementation/access status. Remotive and Arbeitnow public-feed adapters are fixture-tested; they add source backlinks, request bounds, persistent refresh/cooldown, and local title filtering. See [coverage](PORTAL_COVERAGE.md). Most account/country portals remain unverified research/manual entries. The current local suite has 82 passing tests.

The clean GitHub main branch includes maintained v2 code and synthetic assets only; historical scripts are retained locally and ignored. See [provenance](PROVENANCE.md).
