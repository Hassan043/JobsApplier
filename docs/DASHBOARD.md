# Local review dashboard

Start from the repository folder with Python 3.10 or newer:

```powershell
python dashboard.py
```

Open http://127.0.0.1:8765. Stop with Ctrl+C. The dashboard uses only Python's standard library; PDF CV extraction additionally needs `pdfplumber`. It serves local HTML/CSS/JavaScript without third-party fonts, scripts, analytics, or a frontend build step.

## Complete workflow

1. Click **Explore synthetic demo** for three fictional opportunities and one fictional CV. The demo is explicitly labeled and is not a vacancy feed.
2. Expand **Add a CV profile**. Set your name, CV label, home country, target roles, skills, soft USD monthly target, remote-only preference, and relocation preference. Upload TXT/Markdown/PDF or paste verified CV text. Create separate labeled profiles for .NET, full-stack, AI, or mobile CV variants.
3. Expand **Import and match jobs**. Choose profiles and upload normalized JSON/JSONL/CSV or saved JobPosting JSON-LD HTML. `examples/jobs.json` is a synthetic sample. Native portal login and live collection are not available in the dashboard yet; existing CLI collectors remain separate.
4. Review the ranked CV–job matches. Filter by profile, eligibility, application stage, search, and monthly USD minimum. Unknown/nonconverted pay remains visible by default. There is no salary upper cap.
5. Inspect the original posting, pay interpretation, eligibility warnings, and exact CV/job evidence. **Country allowed** means supplied country metadata permits the candidate; it does not establish work authorization or employer acceptance. Unknown currency or arrangement can require review even if country metadata is present.
6. Edit the evidence-based application draft and download it as text. Edits stay in the current browser tab, with a discard warning on navigation. Drafts are not autosaved. Review all details before manually submitting.
7. Save the stage and tracking notes. State is separate for each job and CV profile and survives browser reloads. Saving **applied** records a manual action; it does not submit anything.

The dashboard currently runs the existing keyword baseline, explicitly labeled as such. Optional paid AI matching and live source collection remain CLI features. Screening-answer generation, saved draft revisions, automated refresh, profile editing/deletion, and production multi-user hosting are future work.

## Storage and boundaries

Default private workspace: `data/dashboard/`. This is a separate SQLite database from the CLI's `data/jobs.sqlite3`, avoiding demo writes to existing application history. Uploaded CVs are extracted into frozen evidence in private profile JSON files; the raw temporary upload is removed after processing. Import files are temporary; normalized job content, assessments, notes, and generated reports persist locally. All are excluded from Git by the existing `data/` ignore rule. Local storage is not encrypted by this application; use normal device/file protection.

```powershell
python dashboard.py --port 8766 --workspace data/my-review
```

Only one dashboard process should use a given workspace. The HTTP server is deliberately serial: imports finish before the next request. A run accepts up to 20 distinct profiles, retains at most 100 ranked jobs, and bounds the combined request to 12 MB; CV extraction is limited to 10 MB and 40,000 evidence characters. Only TXT/MD/PDF CVs and supported job import suffixes are accepted. Import warnings and truncation counts come from the maintained workflow. Different CV hashes keep separate status histories.

The server binds only to `127.0.0.1`, validates Host and mutation Origin, uses a per-process CSRF token, has a 20-second socket timeout, serves an explicit asset allowlist, and sends CSP/no-store/no-referrer headers. Job/CV strings enter the DOM as text, not HTML. Upload names cannot determine storage paths; profile `resume_path` references are refused. These controls are not a multi-user authentication system. Do not expose the server through a tunnel or reverse proxy; production hosting requires authentication, authorization, isolation, and additional hardening. Other users/processes with local access may read the workspace.

## Validation

```powershell
python -m pytest tests -q
node --check job_assistant/dashboard_assets/app.js
```

Dashboard HTTP integration tests cover a full demo, CV upload, multi-profile import, isolated/persistent status tracking, invalid inputs, traversal filenames, protected writes, upload bounds, asset allowlisting, and response headers. Manual browser verification additionally covers demo loading, eligibility filtering, status/notes saving, and persisted state after reload. No paid AI calls or job submissions are used for these checks.
