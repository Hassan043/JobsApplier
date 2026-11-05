# Current architecture

See [LOCAL_FIRST_V2.md](LOCAL_FIRST_V2.md) for the implemented local-first workflow. The original scraper-to-Sheets architecture below describes preserved legacy scripts.

---

# Architecture

CLI that scrapes remote-job boards, ranks each posting against a local CV, writes a cover letter, and appends a row to Google Sheets.

```
main.py                      queries, caps, orchestration
pangian.py                   site scrapers
flexjobs.py
remote_co.py
bayt.py
browser_session.py           Playwright when a board needs a browser
        │
pdf_code.py                  CV text via pdfplumber
ranking_utils.py
chatgpt.py                   OpenAI rank + letter
        │
gsheet_api.py
setup_sheet.py               header schema
curriculums/                 source PDFs
```

Config templates are `config_example.py` and `config_template.py`. Secrets must live in the environment. A service-account JSON for Sheets is a local file, not a committed key. `SOP_GUIDE.md` and `QUICK_START.md` are the operator notes.

## Persistence

The spreadsheet is the database. CVs stay on disk. There is no local job store, so a rerun can rank the same URL twice unless the sheet is checked first.

## Boundaries

- `--max-jobs` is the spend cap. Do not remove it.
- Selectors will rot. Fixtures are the missing safety net.
- This tool prepares applications. It does not submit them.
