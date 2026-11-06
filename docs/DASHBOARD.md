# Dashboard workflow

Run `python dashboard.py`, then open http://127.0.0.1:8765. Stop with Ctrl+C. Python 3.10+ is required. The core dashboard needs no extra packages or frontend build; PDF CV extraction optionally uses `pdfplumber`.

## Workspace

On desktop, the control sidebar, job list, and detail pane scroll separately. Filters remain beside the results. **Match overview** shows eligibility, compensation, and grouped source evidence; **Application & tracking** contains draft editing and application state. Sort by match, USD salary, or company. Known-ineligible postings remain behind other postings even when sorting by salary.

The layout was visually checked at 1600×1000, 1920×1080, and a narrow mobile viewport. At narrower sizes, controls reflow above the results; mobile filters start collapsed. CV/import/source controls open focused, keyboard-accessible native dialogs rather than pushing the jobs down the page.

## Profiles and matching

1. Choose **Explore demo** for fictional data, or open **CV profiles** and upload a TXT, Markdown, or selectable-text PDF CV (or paste CV text). Set name, label, country, roles, skills, salary target, and relocation/remote preferences.
2. To edit, select and load a saved profile. Saving a changed profile creates a new file/revision. Prior CVs, assessments, drafts, and application history remain accessible. A replacement CV upload replaces the prior evidence; unchanged pasted evidence retains its original IDs.
3. Open **Import postings** to choose active profiles and upload normalized JSON/JSONL/CSV or saved JobPosting JSON-LD HTML. Profile selection is shared with source collection and reassessment. `examples/jobs.json` is a synthetic sample.
4. Alternatively open **Sources & AI**, select Remotive/Arbeitnow feeds or enter Greenhouse/Lever board identifiers, optionally specify role queries, and choose **Collect & match**. These are public read-only sources; account portals are not automated. Collection sends no CVs to job sources.
5. **Reassess saved jobs** compares the current profiles with stored postings, using the chosen job cap and optional AI settings. Earlier profile histories are retained; current profiles show by default, while previous revisions can be selected explicitly in the profile filter.

Country allowed means supplied metadata permits the candidate's country; it does not establish work authorization, employer acceptance, or sponsorship. Unknown pay/eligibility stays reviewable. USD annual pay is divided by 12; other currencies and hourly pay are not guessed. There is no salary upper cap. The displayed top-CV suggestion compares keyword evidence across active CVs for that posting, with ties explicit; it is not an AI or hiring recommendation.

## Optional AI

Local keyword matching is the default. In **Sources & AI**, select a provider, model, maximum AI calls, and explicitly enable AI for the next import/collection/reassessment. Successful runs clear the AI checkbox, requiring opt-in again.

- **Ollama:** fixed local endpoint `127.0.0.1:11434`; no API key or per-call provider fee. Requires a separately installed runtime and downloaded local model. See [local setup](FREE_LOCAL_AI.md). The app does not install software or download models.
- **OpenAI:** install `requirements-ai.txt`, set `OPENAI_API_KEY` in the server environment, and choose a model. Selected CV evidence and job text are sent to the provider. Keys are never entered or returned through the dashboard. Call caps are not dollar budgets.

Both providers use the same structured schema and exact CV/job quotation validator. Missing-requirement excerpts must occur in the posting. Failures, refusals, invalid quotes, incomplete output, and exhausted budgets remain explicitly labeled; they do not become invented AI scores. Keyword and AI scores are labeled separately. Mixed rankings can contain both; they are not calibrated to a common hiring probability. Real-model semantic quality has not been measured.

## Drafts and tracking

In **Application & tracking**, edit and **Save draft** to retain a private revision. Reopening the job/CV pair or reloading restores the latest saved text. Each save appends a revision in SQLite; revision browsing/restoration is not yet exposed in the UI. **Download draft** saves plain text for manual use. Drafts must be checked before submission.

Save the stage and notes for each job/CV pair. **Applied** records an action you performed elsewhere; it submits nothing. Changing CV content/preferences changes its identity, so prior tracking is preserved under the old revision and is not silently copied to the new one.

## Limits and storage

Default private storage is `data/dashboard/`, separate from the CLI's `data/jobs.sqlite3`. Extracted CV evidence persists as profile JSON; raw uploads are temporary. Jobs, analyses, per-CV tracking, and draft revisions persist in SQLite; generated reports stay in the same ignored workspace. Local files are not encrypted by the app.

```powershell
python dashboard.py --port 8766 --workspace data/portfolio-demo
```

Use one process per workspace. Current request handling is serial; a long run occupies the server until its bounded work completes. The interface prevents duplicate concurrent actions. Each public source request uses the existing 15-second timeout/8 MB response cap. Dashboard collection accepts at most 3 boards per employer provider, 2 feeds, 5 queries, and 20 profiles. The job cap is 1–100 (default 30), or at most 30 when AI is enabled; AI budget is 1–5 calls across all profiles/jobs. OpenAI timeout is 30 seconds/call and Ollama 60 seconds/call, without retries. Several providers/calls can therefore take minutes in the worst case; this is a request limit, not a whole-run deadline. Remotive refresh/cooldown is 6 hours, Arbeitnow 1 hour, including failed attempts.

Uploads are limited to 12 MB combined, CVs to 10 MB and 40,000 extracted characters. Local Ollama rejects combined prompt content above 12,000 characters rather than silently truncating it, with a 16,384-token configured context and 2,000 output-token cap. Hardware memory and tokenization still vary.

The server is loopback-only with Host/Origin checks, per-process CSRF tokens, allowlisted assets, CSP, no-store responses, a 20-second client socket timeout, and text-only DOM insertion of untrusted fields. Upload names cannot determine storage locations, and external `resume_path` references are refused. Ollama bypasses proxies and rejects redirects/cloud-named models; disable cloud in the runtime as documented. This is a private single-machine app, not an authenticated multi-user service. Do not expose it through tunnels or reverse proxies without a separate production security design.

See [release validation](RELEASE_VALIDATION.md) and [portfolio tour](PORTFOLIO_DEMO.md).
