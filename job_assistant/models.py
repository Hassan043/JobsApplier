"""Validated profile/job input and stable identity; no network or secrets on import."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import hashlib
import json
import re
import math


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def canonical_url(value):
    parts = urlsplit(str(value).strip())
    if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("Job links must be public HTTP(S) URLs without credentials")
    host = parts.hostname.lower()
    if parts.port and parts.port not in {80, 443}:
        host += f":{parts.port}"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "ref", "source"}]
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/") or "/", urlencode(sorted(query)), ""))


def contains(text, term):
    return bool(re.search(r"(?<!\w)" + re.escape(term.casefold()) + r"(?!\w)", text.casefold()))


@dataclass
class Job:
    title: str
    company: str
    url: str
    description: str
    source: str = "import"
    location: str = ""
    workplace: str = "unknown"
    eligible_countries: list = field(default_factory=list)
    salary: str = ""
    currency: str = ""
    employer_country: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_period: str = ""

    @classmethod
    def from_dict(cls, data, source="import"):
        if not isinstance(data, dict):
            raise ValueError("Each job must be an object")
        title = clean(data.get("title") or data.get("job_title"))
        description = clean(data.get("description") or data.get("job_description"))
        if not title or not description:
            raise ValueError("Job needs a nonempty title and description")
        if len(description) > 60000:
            raise ValueError("Job description exceeds 60,000 characters")
        countries = data.get("eligible_countries") or []
        if isinstance(countries, str):
            countries = [x.strip() for x in countries.split(";") if x.strip()]
        if not isinstance(countries, list) or any(not isinstance(x, str) for x in countries):
            raise ValueError("eligible_countries must be a list or semicolon-separated country codes")
        workplace = clean(data.get("workplace") or "unknown").lower()
        if workplace not in {"remote", "hybrid", "onsite", "unknown"}:
            raise ValueError("workplace must be remote, hybrid, onsite, or unknown")
        amounts = []
        for key in ("salary_min", "salary_max"):
            value = data.get(key)
            if value in (None, ""):
                amounts.append(None)
            else:
                if isinstance(value, bool):
                    raise ValueError("Salary amounts must be positive numbers")
                value = float(value)
                if not math.isfinite(value) or value < 0:
                    raise ValueError("Salary amounts must be finite nonnegative numbers")
                amounts.append(value)
        if all(x is not None for x in amounts) and amounts[0] > amounts[1]:
            raise ValueError("Salary minimum cannot exceed maximum")
        period = clean(data.get("salary_period")).lower()
        if period not in {"", "month", "year", "hour"}:
            raise ValueError("salary_period must be month, year, hour, or empty")
        return cls(title, clean(data.get("company") or data.get("company_name")) or "Not specified",
                   canonical_url(data.get("url") or data.get("job_url") or data.get("job_link") or ""),
                   description, clean(data.get("source") or source), clean(data.get("location")), workplace,
                   [c.upper() for c in countries], clean(data.get("salary")), clean(data.get("currency")).upper(),
                   clean(data.get("employer_country")).upper(), amounts[0], amounts[1], period)

    @property
    def id(self):
        return hashlib.sha256(self.url.encode()).hexdigest()[:24]

    @property
    def fingerprint(self):
        identity = self.to_dict()
        identity.pop("url")
        identity.pop("source")
        return hashlib.sha256(json.dumps(identity,sort_keys=True).casefold().encode()).hexdigest()

    def to_dict(self):
        return asdict(self)


@dataclass
class Profile:
    name: str
    target_roles: list
    skills: list
    evidence: dict
    base_country: str = ""
    remote_only: bool = False
    excluded_terms: list = field(default_factory=list)
    preferred_locations: list = field(default_factory=list)
    preferred_currencies: list = field(default_factory=lambda: ["USD", "EUR"])
    remote_preferred: bool = True
    open_to_relocation: bool = True
    target_monthly_usd: float = 2000.0
    label: str = ""

    @classmethod
    def load(cls, path, resume_override=None):
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("Profile must be an object")
        for key in ("target_roles", "skills", "excluded_terms", "preferred_locations", "preferred_currencies"):
            if not isinstance(data.get(key, []), list) or any(not isinstance(x, str) or not x.strip() for x in data.get(key, [])):
                raise ValueError(f"{key} must be a list of nonempty strings")
        for flag in ("remote_only", "remote_preferred", "open_to_relocation"):
            if flag in data and not isinstance(data[flag], bool):
                raise ValueError(f"{flag} must be boolean")
        target = data.get("target_monthly_usd", 2000)
        if isinstance(target, bool) or not isinstance(target, (int, float)) or not math.isfinite(target) or target <= 0:
            raise ValueError("target_monthly_usd must be positive and finite")
        if not isinstance(data.get("remote_only", False), bool):
            raise ValueError("remote_only must be a boolean")
        evidence = {}
        entries = data.get("evidence", [])
        if not isinstance(entries, list):
            raise ValueError("evidence must be a list of {id, text} objects")
        for item in entries:
            if not isinstance(item, dict):
                raise ValueError("Evidence entries must be objects")
            key, text = clean(item.get("id")), clean(item.get("text"))
            if not key or not text or key in evidence:
                raise ValueError("Evidence IDs must be unique and evidence text nonempty")
            evidence[key] = text
        resume_value = resume_override or data.get("resume_path")
        if resume_value:
            resume = Path(resume_override).resolve() if resume_override else (path.parent / resume_value).resolve()
            if resume.stat().st_size > 10_000_000:
                raise ValueError("CV exceeds 10 MB")
            if resume.suffix.lower() == ".pdf":
                try:
                    import pdfplumber
                except ImportError as exc:
                    raise ValueError("PDF import needs pdfplumber; text CVs work without extra dependencies") from exc
                with pdfplumber.open(resume) as pdf:
                    text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)
            else:
                text = resume.read_text(encoding="utf-8-sig")
            for index, paragraph in enumerate(re.split(r"\n\s*\n", text)):
                if clean(paragraph):
                    key = f"resume_{index + 1}"
                    if key in evidence:
                        raise ValueError(f"Reserved evidence ID collision: {key}")
                    evidence[key] = clean(paragraph)
        if not evidence:
            raise ValueError("Add your CV via resume_path or verified evidence entries before ranking")
        if sum(len(x) for x in evidence.values()) > 40000:
            raise ValueError("CV/evidence exceeds 40,000 characters; supply a concise profile")
        return cls(clean(data.get("name")) or "Candidate", data.get("target_roles", []), data.get("skills", []),
                   evidence, clean(data.get("base_country")).upper(), data.get("remote_only", False),
                   data.get("excluded_terms", []), data.get("preferred_locations", []),
                   data.get("preferred_currencies", ["USD", "EUR"]), data.get("remote_preferred", True),
                   data.get("open_to_relocation", True), float(target), clean(data.get("profile_label")))

    @property
    def hash(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()
