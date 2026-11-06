# Release validation — 6 November 2026

## Verified

- 97 automated tests pass, including HTTP workflow, multiple CVs, preserved profile revisions, saved draft revisions, AI consent and global budgets, exact evidence validation, source routing, and local Ollama transport failure cases.
- JavaScript syntax check passes. Frozen synthetic benchmark generator check and manifest/schema validation pass (60 postings, 5 fictional CVs, 300 authored provisional judgments).
- Browser checks: draft save/restoration after reload; load/edit/save profile revision; reassess stored jobs against the new CV; grouped evidence; overview/application tabs; focused source/AI dialogs.
- Desktop layouts checked at 1600×1000 and 1920×1080, with document scroll width equal to viewport width on the 1920 check. Narrow mobile layout also showed no horizontal overflow. Desktop controls, results, and details have independent scroll regions.
- Remotive public feed: 3 valid matching postings in one bounded smoke check. Arbeitnow public feed: 3 valid matching postings. Only role queries/public provider requests were used; no CV data went to job sources. Private smoke-cache data is ignored by Git.
- Existing Greenhouse smoke evidence remains from 5 November. Lever remains fixture-tested; no new live verification claim.

## Explicit limitations

The AI provider tests use synthetic data and injected transports. No paid hosted calls or actual Ollama inference ran. Ollama was absent from PATH and checked standard Windows installation folders. A separately installed runtime/model or user-supplied hosted key is needed for real-model validation. Existing benchmark results compare title/keyword baselines, not real LLM performance; these results must not be marketed as proof of AI improvement.

The demo video is a silent screenshot tour of the implemented interface using fictional data, not a recording of model inference or application submissions. Job sources can change independently of a successful smoke check. Remote eligibility, sponsorship, salary currency, and application facts still require manual verification.

This release is a private local portfolio product. It does not provide production multi-user hosting, automatic applications, account scraping, model installation, independent human-rated model-quality claims, a dollar-denominated spending budget, or full coverage of the 175 catalog sources.

## Reproduce

```powershell
python -m pytest tests -q
node --check job_assistant/dashboard_assets/app.js
python tools/build_jobfit_benchmark.py --check
python benchmark.py validate
python benchmark.py evaluate --split dev --output output/release-baseline-dev
python dashboard.py --port 8766 --workspace data/portfolio-demo
```

Use **Explore demo**. No external provider is required for the default workflow. See [dashboard guide](DASHBOARD.md) for live source/AI opt-ins and [local setup](FREE_LOCAL_AI.md) for prerequisites.
