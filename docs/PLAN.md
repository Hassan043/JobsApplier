# Current implementation plan - 5 November 2026

The local-first v2 workflow is implemented. See [LOCAL_FIRST_V2.md](LOCAL_FIRST_V2.md) and [QUICK_START.md](../QUICK_START.md) for current behavior. The older plan below is preserved as historical context and is not an authoritative status check.

## Completed in this iteration

- Configurable software/.NET/AI/mobile profiles and CV evidence; no hard-coded EA/CS requirement in v2.
- Local imports, bounded public employer feeds, canonical deduplication, versioned cache, local tracking/export.
- Explicit salary period/currency, worldwide targeting, soft USD 2000/month target, no salary ceiling.
- Evidence-linked keyword baseline and optional strict-schema AI adapter with honest error states and global call cap.
- Reproducible synthetic demo, automated tests, and offline evaluation runner.

## Next portfolio milestones

1. Curate a consented/labeled benchmark with held-out job/candidate groups; measure keyword baseline before adding embeddings/reranking.
2. Evaluate the optional AI path with an explicit provider budget and distinguish exact citation validation from semantic factuality.
3. Add stable candidate identity across CV revisions and versioned state migration.
4. Extend source pagination and coverage with deterministic fixture tests and transparent health reporting.
5. Improve review UX and optional export integrations only after the core quality report exists.

---

## Historical plan

# Plan

## Current state

Four site scrapers, OpenAI ranking, cover letters, and Sheets append work as a personal CLI. Docs still describe editing secrets in source. There is no dry-run and no HTML fixtures.

## Now

1. Read OpenAI and Sheets settings from the environment. Point `QUICK_START.md` at that, not at editing Python files.
2. Add `--dry-run` that prints rows and skips `gsheet_api.py`.
3. Deduplicate URLs across sites before a ranking call.
4. Save one HTML fixture per scraper and test the parser against it.
5. Keep `--max-jobs` required for any run that calls the model.

## Later

- Reuse `browser_session.py` for boards that sit behind a login wall.
- A local sqlite of seen URLs if the sheet lookup gets slow.

## Non-goals

- Auto-submitting applications.
- More job boards before the four current parsers have fixtures.

## Done when

A dry-run spends no model calls beyond the cap you set, writes no sheet row, and secrets are absent from git diffs.

## Benchmark milestone - 5 November 2026

Implemented a versioned 60-posting/5-fictional-CV fixture with 300 provisional judgments, family-level dev/test isolation, frozen hashes, dual baseline evaluation, error analysis, and blind annotation worksheets. See [protocol](../benchmarks/jobfit_v1/README.md). This completes evaluation infrastructure and authored scenarios, not independent human labeling or representative real-world validation.

Next: independently label/adjudicate the corpus, extend with permitted representative examples, and only then compare semantic matching against the frozen baseline. Do not tune on observed test results.
