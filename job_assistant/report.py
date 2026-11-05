"""Private local reports. All posting/model text is escaped, never executable."""
import csv
import html
import json
from pathlib import Path


def safe_cell(value):
    text=str(value if value is not None else "")
    return "'"+text if text.lstrip().startswith(("=","+","-","@","\t","\r")) else text


def write_reports(records, output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    (output/"jobs.json").write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding="utf-8")
    fields=["id","candidate","title","company","url","location","workplace","currency","salary","monthly_usd_minimum",
            "baseline_score","ai_score","ai_status","eligibility","status","warnings","notes"]
    with (output/"jobs.csv").open("w",newline="",encoding="utf-8-sig") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        for record in records:
            job=record["job"]; assessment=record["assessment"]
            row={k:job.get(k,"") for k in fields}
            row.update(id=record["id"],candidate=assessment["candidate"],monthly_usd_minimum=assessment["compensation"]["monthly_usd_minimum"],
                       baseline_score=assessment["score"],ai_score=assessment["ai_score"],ai_status=assessment["ai_status"],
                       eligibility=assessment["eligibility"],status=record.get("status","new"),
                       warnings="; ".join(assessment["warnings"]),notes=record.get("notes",""))
            writer.writerow({k:safe_cell(v) for k,v in row.items()})
    esc=lambda x:html.escape(str(x if x is not None else ""),quote=True)
    cards=[]
    for record in records:
        job=record["job"]; a=record["assessment"]
        matches=a.get("ai_matches") if a["ai_status"]=="completed" else a["matches"]
        items="".join(f'<li><strong>{esc(m["skill"])}</strong><br>CV [{esc(m["evidence_id"])}]: {esc(m["candidate_quote"])}<br>Posting: {esc(m["job_quote"])}</li>' for m in matches)
        warnings="".join(f'<li>{esc(x)}</li>' for x in a["warnings"])
        gaps="".join(f'<li>{esc(x)}</li>' for x in a.get("missing_requirements",[]))
        cards.append(f'''<article><h2><a href="{esc(job['url'])}" rel="noreferrer noopener">{esc(job['title'])}</a></h2>
<p>{esc(job['company'])} | {esc(job['location'])} | {esc(job['workplace'])} | {esc(job['salary'])}</p>
<p><b>Candidate:</b> {esc(a['candidate'])} | <b>Status:</b> {esc(record.get('status','new'))}<br>
<b>Keyword baseline:</b> {esc(a['score'])}/100 | <b>AI:</b> {esc(a['ai_score']) if a['ai_score'] is not None else 'Not scored'} ({esc(a['ai_status'])})<br>
<b>Eligibility:</b> {esc(a['eligibility'])} | <b>Compensation:</b> {esc(a['compensation']['note'])}</p>
<ul>{warnings}</ul><details><summary>Matched evidence ({len(matches)})</summary><ul>{items}</ul></details>
<details><summary>Missing/uncertain requirements</summary><ul>{gaps}</ul><p>Unverified profile skills: {esc(', '.join(a['unverified_profile_skills']))}</p></details>
<details><summary>Review-only letter draft</summary><pre>{esc(a.get('cover_letter','No evidence-backed draft available'))}</pre></details>
<details><summary>Job description</summary><p>{esc(job['description'])}</p></details>
<p class="muted">Candidate hash: {esc(a['profile_hash'])}<br>Job ID: {esc(record['id'])} | Source: {esc(job['source'])}<br>{esc(record.get('notes',''))}</p></article>''')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Job shortlist - review workspace</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1040px;margin:40px auto;padding:0 20px;background:#f5f7fb;color:#172237}article{background:white;padding:24px;margin:20px 0;border:1px solid #d9e0eb;border-radius:12px}h1,h2{line-height:1.25}a{color:#1754b3}pre{white-space:pre-wrap;font:inherit}details{margin:12px 0}summary{cursor:pointer;font-weight:600}.muted{color:#647084;font-size:13px}li{margin:8px 0}</style>
<h1>Your job review workspace</h1><p>Private local report. Scores are review aids, not hiring probabilities. Country eligibility and work authorization require confirmation. No applications are submitted.</p>
'''+f'<p>{len(records)} candidate/job assessments. Unknown and below-target salaries are retained; there is no upper salary cap.</p>'+"".join(cards)+"</html>"
    (output/"index.html").write_text(page,encoding="utf-8")
    return output/"index.html"
