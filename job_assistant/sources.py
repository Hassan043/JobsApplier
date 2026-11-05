"""Offline imports and a bounded read-only Pangian collector."""
import csv
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .models import Job, clean


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    parser = TextParser()
    parser.feed(unescape(unescape(str(value or ""))))
    return clean(unescape(" ".join(parser.parts)))


class LinkedDataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.current = []
        self.documents = []
    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type", "").lower() == "application/ld+json":
            self.active = True
            self.current = []
    def handle_data(self, data):
        if self.active:
            self.current.append(data)
    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            self.documents.append("".join(self.current))
            self.active = False


def jsonld_jobs(text):
    parser = LinkedDataParser()
    parser.feed(text)
    found = []
    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            types = node.get("@type", [])
            if types == "JobPosting" or isinstance(types, list) and "JobPosting" in types:
                organization = node.get("hiringOrganization") or {}
                location = node.get("jobLocation") or {}
                if isinstance(location, list):
                    location = location[0] if location else {}
                address = location.get("address", {}) if isinstance(location, dict) else {}
                if not isinstance(address, dict):
                    address = {}
                found.append({"title": node.get("title"), "company": organization.get("name") if isinstance(organization, dict) else organization,
                              "url": node.get("url"), "description": plain_text(node.get("description")),
                              "location": ", ".join(str(address[k]) for k in ("addressLocality", "addressRegion", "addressCountry") if address.get(k)),
                              "workplace": "remote" if node.get("jobLocationType") == "TELECOMMUTE" else "unknown"})
            for key in ("@graph", "mainEntity", "itemListElement", "item"):
                if key in node:
                    walk(node[key])
    for document in parser.documents:
        walk(json.loads(document))
    return found


def parse_pangian(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Pangian response schema changed: expected data list")
    return [{"title": item.get("job_title"), "company": item.get("company"), "url": item.get("job_url"),
             "description": plain_text(item.get("description")), "location": item.get("job_location") or item.get("country_code"),
             "salary": item.get("salary", ""), "source": "pangian"} for item in payload["data"] if isinstance(item, dict)]


def validate_rows(rows, source):
    jobs, errors = [], []
    if not isinstance(rows, list):
        raise ValueError("Expected an array of job objects or an object containing jobs")
    if len(rows) > 10000:
        raise ValueError("Input exceeds 10,000 job records")
    for index, row in enumerate(rows, 1):
        try:
            jobs.append(Job.from_dict(row, source))
        except (ValueError, TypeError) as exc:
            errors.append(f"{source} row {index}: {exc}")
    return jobs, errors


def load_jobs(path):
    path = Path(path)
    if path.stat().st_size > 10_000_000:
        raise ValueError("Input exceeds 10 MB")
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8-sig")
    if suffix == ".csv":
        rows = list(csv.DictReader(__import__("io").StringIO(text)))
    elif suffix in {".html", ".htm"}:
        rows = jsonld_jobs(text)
        if not rows:
            raise ValueError("No JobPosting JSON-LD found; export JSON/CSV instead")
    elif suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        payload = json.loads(text)
        if isinstance(payload, dict) and "data" in payload:
            rows = parse_pangian(payload)
        else:
            rows = payload.get("jobs", []) if isinstance(payload, dict) else payload
    return validate_rows(rows, path.name)


def fetch_pangian(queries, limit, max_pages=3, opener=urlopen):
    jobs, errors = [], []
    seen = set()
    for query in queries:
        for page in range(1, max_pages + 1):
            if len(jobs) >= limit:
                return jobs, errors
            params = urlencode({"page": page, "limit": min(limit, 50), "q": query, "featured": "false", "pro": "false"})
            request = Request("https://pangian.com/remote/api/v1/job-listings/search/location?" + params,
                              headers={"Accept": "application/json", "User-Agent": "JobsApplier/2.0 (personal job research)"})
            try:
                with opener(request, timeout=15) as response:
                    raw = response.read(5_000_001)
                if len(raw) > 5_000_000:
                    raise ValueError("Source response too large")
                payload = json.loads(raw)
                parsed, invalid = validate_rows(parse_pangian(payload), "pangian")
                errors.extend(invalid)
                for job in parsed:
                    if job.url not in seen:
                        seen.add(job.url)
                        jobs.append(job)
                        if len(jobs) >= limit:
                            break
                if not payload["data"] or not parsed or page >= int(payload.get("totalPages") or 1):
                    break
                time.sleep(0.5)
            except Exception as exc:
                errors.append(f"Pangian collection failed ({type(exc).__name__}); source is unavailable, not an empty successful search")
                break
    return jobs, errors


def parse_greenhouse(payload, board):
    if not isinstance(payload,dict) or not isinstance(payload.get('jobs'),list):
        raise ValueError('Greenhouse schema changed: expected jobs list')
    rows=[]
    for item in payload['jobs']:
        location=(item.get('location') or {}).get('name','')
        rows.append({'title':item.get('title'),'company':board,'url':item.get('absolute_url'),
                     'description':plain_text(item.get('content')),'location':location,
                     'workplace':location_workplace(location),
                     'eligible_countries':['WORLDWIDE'] if __import__('re').search(r'\bworldwide\b',location,__import__('re').I) else [],
                     'source':'greenhouse:'+board})
    return rows


def parse_lever(payload, board):
    if not isinstance(payload,list):
        raise ValueError('Lever schema changed: expected posting list')
    rows=[]
    for item in payload:
        categories=item.get('categories') or {}
        sections=[item.get('descriptionPlain') or plain_text(item.get('description')),
                  item.get('openingPlain') or plain_text(item.get('opening'))]
        for section in item.get('lists') or []:
            sections.append(clean(section.get('text'))+' '+plain_text(section.get('content')))
        sections.append(item.get('additionalPlain') or plain_text(item.get('additional')))
        salary=item.get('salaryRange') or {}
        period={'year':'year','yearly':'year','month':'month','monthly':'month','hour':'hour','hourly':'hour'}.get(str(salary.get('interval','')).lower(),'')
        workplace=str(item.get('workplaceType') or 'unknown').lower().replace('on-site','onsite')
        if workplace not in {'remote','onsite','hybrid','unknown'}:workplace='unknown'
        rows.append({'title':item.get('text'),'company':board,'url':item.get('hostedUrl') or item.get('applyUrl'),
            'description':clean(' '.join(str(x or '') for x in sections)),'location':categories.get('location',''),
            'workplace':workplace,'source':'lever:'+board,'currency':salary.get('currency',''),
            'salary_min':salary.get('min'),'salary_max':salary.get('max'),'salary_period':period,
            'salary':item.get('salaryDescription') or (' '.join(str(x) for x in [salary.get('currency',''),salary.get('min',''),salary.get('max',''),period]) if salary else '')})
    return rows


def fetch_boards(provider,boards,queries,limit,opener=urlopen):
    import re
    from .models import contains
    if len(boards)>10:
        raise ValueError('At most 10 employer boards per provider per run')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',board) for board in boards):
        raise ValueError('Board identifiers must contain only letters, digits, underscore, or hyphen')
    jobs=[];errors=[]
    for board in boards:
        if len(jobs)>=limit:break
        if provider=='greenhouse':
            url=f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true'
        elif provider=='lever':
            url=f'https://api.lever.co/v0/postings/{board}?mode=json&limit=100'
        else:raise ValueError('Unknown provider')
        try:
            request=Request(url,headers={'Accept':'application/json','User-Agent':'JobsApplier/2.0 (personal job research)'})
            with opener(request,timeout=15) as response:raw=response.read(8_000_001)
            if len(raw)>8_000_000:raise ValueError('Board response exceeds 8 MB')
            payload=json.loads(raw)
            rows=parse_greenhouse(payload,board) if provider=='greenhouse' else parse_lever(payload,board)
            selected=[row for row in rows if not queries or any(contains(clean(row.get('title')),q) for q in queries)]
            parsed,invalid=validate_rows(selected,provider+':'+board)
            jobs.extend(parsed[:max(0,limit-len(jobs))]);errors.extend(invalid)
            if provider=='lever' and len(payload)>=100:
                errors.append(f'lever:{board}: first 100 postings only; pagination is not implemented yet')
        except Exception as exc:
            errors.append(f'{provider}:{board} unavailable ({type(exc).__name__}); no successful empty search assumed')
    return jobs,errors


def location_workplace(location):
    import re
    if re.search(r"\bremote\b|\bhome[ -]based\b",location,re.I):
        return "remote"
    if re.search(r"\boffice[ -]based\b|\bon[ -]site\b",location,re.I):
        return "onsite"
    return "unknown"
