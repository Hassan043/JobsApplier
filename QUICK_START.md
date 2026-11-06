# Jobs Applier v2 quick start

## 1. Run an offline demo

From the Jobs_Applier folder:

```powershell
python main.py run --profile examples/demo_profile.json --input examples/jobs.json
```

Open `output/index.html`. Reports also include `jobs.csv` and `jobs.json`. These are synthetic fixtures, not real vacancies. SQLite is stored at `data/jobs.sqlite3`; reruns reuse matching analysis and preserve application status.

The baseline workflow needs Python 3.10+ and no extra packages. Run tests with `python -m pip install -r requirements-dev.txt`, then `python -m pytest tests -q`. Legacy scrapers need their original requirements; they are not imported by v2.

## 2. Add your real CV

```powershell
python main.py init-profile profiles/hassan.remote.json
python main.py run --profile profiles/hassan.remote.json --cv "C:/CVs/backend.txt" --input jobs.json
```

Edit roles, skills, excluded title terms, preferred markets/currencies, remote preference, and soft salary target. Skills are counted only when present in supplied evidence. The template deliberately contains no invented work history. Set `resume_path` relative to each profile file for repeatable/team runs, or supply verified `{id,text}` evidence entries. PDFs require `pdfplumber`; image-only PDFs are not silently accepted as a valid CV.

Several profiles can review the same jobs without changing each other's application status:

```powershell
python main.py run --profile profiles/backend.json --profile profiles/mobile.json --input jobs.json --max-jobs 30
```

Use a separate profile per team member or CV variant. `--cv` is a convenience override for exactly one profile. Changing profile/CV content invalidates its cached analysis; application tracking currently belongs to that exact profile hash, so historical status for an older profile remains separate.

## 3. Collect public employer postings

```powershell
python main.py run --profile profiles/hassan.remote.json --cv "C:/CVs/backend.txt" --greenhouse canonical --queries engineer developer --max-jobs 30
python main.py run --profile profiles/hassan.remote.json --cv "C:/CVs/backend.txt" --lever EMPLOYER_SITE --queries engineer developer --max-jobs 30
```

Replace board/site tokens with the employer's actual public identifier. Maximum ten boards/provider/run, 15-second request timeout. Greenhouse currently fetches one bounded board response; Lever fetches the first 100 postings and warns when pagination may be needed. Source order and collection limits can limit coverage: this is not a worldwide exhaustive job search. Query filtering is title-based and baseline-based, not semantic search.

The Canonical Greenhouse smoke test succeeded; board availability changes. The collector never posts applications. Company board token is used as the company label; verify actual employer details. Location/workplace fields are not proof of applicant-country eligibility.

The preserved Pangian endpoint is optional (`--sites pangian --queries "software engineer"`) but currently returned non-JSON in a live test. Treat its warning as a failed source, not zero jobs. FlexJobs/Remote.co/Bayt live paths remain legacy; use saved imports until independently verified.

## 4. Import jobs without scraping

```powershell
python main.py run --profile profiles/hassan.remote.json --cv "C:/CVs/backend.txt" --input jobs.json jobs.csv saved-job.html --max-jobs 30
python main.py run --profile examples/demo_profile.json --input examples/jobs.json --dry-run
```

JSON may be an array or `{ "jobs": [...] }`; JSONL is one object per line. CSV headers match input keys. Saved HTML must contain JobPosting JSON-LD; it is not a universal scraper for arbitrary page markup. Required fields: `title`, `url`, `description`. Optional: `company`, `location`, `workplace` (`remote`, `hybrid`, `onsite`, `unknown`), `eligible_countries` (ISO codes or WORLDWIDE), `employer_country`, `salary`, `currency`, `salary_min`, `salary_max`, `salary_period` (`year`, `month`, `hour`). Do not infer worldwide eligibility from a remote label.

`--dry-run` is strictly offline and forbids live sources and AI. It prints the preview and writes no database/report files. Ordinary offline runs create local state/reports but make no network/model calls.

## 5. Optional AI matching

```powershell
python -m pip install -r requirements-ai.txt
$env:OPENAI_API_KEY = "YOUR_KEY"
$env:OPENAI_MODEL = "YOUR_STRUCTURED_OUTPUT_COMPATIBLE_MODEL"
python main.py run --profile profiles/hassan.remote.json --cv "C:/CVs/backend.txt" --input jobs.json --ai --max-jobs 10 --max-ai-calls 5
```

Explicitly sends supplied CV evidence and job descriptions to OpenAI. `.env.example` is documentation; no automatic dotenv loading occurs. The model is intentionally selected by you. Maximum calls covers all profiles/jobs combined; SDK retries are disabled, request timeout is 30 seconds, response token cap is 2500. This is a call/token limit, not a guaranteed monetary cap.

Errors/refusals/incomplete output have no AI score; they never become fake medium matches. After an AI error, further calls stop for that run. Exact source quotations are checked independently. Remaining semantic interpretation requires human review. Missing requirements must be posting excerpts. Drafts use supported candidate quotes rather than invented prose/metrics. All drafts need editing before use.

## 6. Track manual application progress

Copy the full job ID from the report:

```powershell
python main.py status JOB_ID shortlisted --notes "Check worldwide contractor eligibility"
python main.py status JOB_ID applied --notes "Applied manually on employer site"
python main.py report
```

States: new, shortlisted, applied, interview, rejected, withdrawn. If several profiles have assessed a job, add `--candidate PROFILE_HASH` from the report. Status changes never submit an application. JSON/CSV/HTML exports can be used for your existing tracking process; Google Sheets synchronization is not enabled in v2.

## Privacy and limits

`profiles/`, `curriculums/`, `data/`, and `output/` are ignored for new files. Git ignores do not remove anything already tracked. Never commit real CVs, credentials, sessions, or reports. The report escapes HTML, blocks script execution, and guards CSV formula cells; local files still contain personal information. No currency exchange-rate lookup, CV auto-rewriting, semantic embeddings, calibrated fit probability, exhaustive board discovery, or automatic submissions are claimed.

## 7. Portfolio benchmark (offline)

```powershell
python tools/build_jobfit_benchmark.py --check
python benchmark.py validate
python benchmark.py evaluate --split dev
python benchmark.py evaluate --split test
python benchmark.py annotations --output output/reviewer.csv
```

Outputs default to separate output/benchmark-dev and output/benchmark-test directories. See [the full protocol](benchmarks/jobfit_v1/README.md). The 60-posting/300-judgment fixture is authored and synthetic; obtain independent labels before real quality claims. No live jobs, private CVs, network, or model calls are used.

## 8. Inspect portal coverage and optional public feeds

```powershell
python main.py portals --group remote_boards
python main.py portals --country AU --json
python main.py run --profile examples/demo_profile.json --feeds remotive arbeitnow --queries engineer developer --max-jobs 30
```

The final command explicitly fetches a bounded live feed snapshot; it is not a synthetic benchmark. Remotive refresh is limited to every six hours and Arbeitnow to every hour locally, including failed-attempt cooldown. Fresh cached snapshots are filtered locally. Public-feed source links are retained in reports. Read [coverage and provider rules](docs/PORTAL_COVERAGE.md) before use. Account-based sites remain manual/research entries, not automatic login collectors.


## Interactive review workspace

Run `python dashboard.py` and open http://127.0.0.1:8765. Start with the synthetic demo or add CV profiles and import job files. See [dashboard guide](docs/DASHBOARD.md) for the full workflow, separate local storage, and operating limits.
