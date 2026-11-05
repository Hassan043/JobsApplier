"""Transparent baseline and conservative country/workplace signals."""
import re
from .models import contains

SCORING_VERSION = "keyword-v2.0.0"


def eligibility(job, profile):
    warnings = []
    if profile.remote_only and job.workplace in {"onsite", "hybrid"}:
        return "ineligible", ["Profile requires fully remote work"]
    countries = set(job.eligible_countries)
    if countries and profile.base_country and profile.base_country not in countries and not countries.intersection({"WORLDWIDE", "ANY", "GLOBAL"}):
        if job.workplace in {"onsite", "hybrid"} and profile.open_to_relocation:
            warnings.append("Relocation/work authorization must be confirmed; currently listed country differs")
        else:
            return "ineligible", ["Explicit applicant-country restriction excludes your current country"]
    text = job.description
    restricted = bool(re.search(r"\b(?:US|USA|U\.S\.)[ -]only\b",text)) or bool(re.search(
        r"\b(?:united states[ -]only|must (?:be based|reside|live) in (?:the )?(?:us|usa|united states))\b",text,re.I))
    if profile.base_country and profile.base_country != "US" and restricted:
        return "ineligible", ["Posting explicitly limits applicants to the United States"]
    if not countries:
        warnings.append("Applicant-country eligibility is unverified; remote does not mean worldwide")
    if job.workplace == "unknown":
        warnings.append("Remote/onsite arrangement is unverified")
    if job.workplace in {"onsite", "hybrid"}:
        warnings.append("Secondary relocation option; confirm sponsorship and work authorization")
    if not job.currency:
        warnings.append("Compensation currency is not explicitly provided")
    return ("review_needed" if warnings else "eligible_by_declared_country"), warnings


def compensation(job, profile):
    currency, period, low, high = job.currency, job.salary_period, job.salary_min, job.salary_max
    if low is None and job.salary:
        match = re.search(r"\b(USD|EUR|GBP|AUD|CAD|NZD)\s*([0-9][0-9,]*(?:\.[0-9]+)?)(k)?(?:\s*[-–]\s*([0-9][0-9,]*(?:\.[0-9]+)?)(k)?)?\s*(?:/|per\s+)?(month|year|annum|hour|mo|yr)\b", job.salary, re.I)
        if match:
            currency = match[1].upper()
            low = float(match[2].replace(",", "")) * (1000 if match[3] else 1)
            high = float(match[4].replace(",", "")) * (1000 if match[5] else 1) if match[4] else None
            period = {"annum":"year", "mo":"month", "yr":"year"}.get(match[6].lower(),match[6].lower())
    monthly = low / 12 if currency == "USD" and low is not None and period == "year" else low if currency == "USD" and period == "month" else None
    note = "Unknown salary; do not discard"
    if low is not None and currency != "USD":
        note = "Non-USD pay: review using a verified exchange rate; no automatic conversion"
    elif low is not None and period == "hour":
        note = "Hourly pay: contracted hours required before monthly comparison"
    elif monthly is not None:
        note = "At or above soft target; no upper cap" if monthly >= profile.target_monthly_usd else "Below soft target; still retained for review"
    return {"currency":currency, "period":period, "minimum":low, "maximum":high,
            "monthly_usd_minimum":monthly, "target_monthly_usd":profile.target_monthly_usd, "note":note}


def baseline(job, profile):
    state, warnings = eligibility(job, profile)
    text = job.title + " " + job.description
    matches = []
    unsupported = []
    for skill in profile.skills:
        evidence = next(((key, value) for key, value in profile.evidence.items() if contains(value, skill)), None)
        if not evidence:
            unsupported.append(skill)
        elif contains(text, skill):
            matches.append({"skill": skill, "evidence_id": evidence[0], "candidate_quote": evidence[1],
                            "job_quote": next((x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if contains(x, skill)), text)})
    role_matches = [role for role in profile.target_roles if contains(job.title, role)]
    excluded = [term for term in profile.excluded_terms if contains(job.title, term)]
    if excluded:
        state = "ineligible"
        warnings.append("Excluded title terms: " + ", ".join(excluded))
    backed_count = len(profile.skills) - len(unsupported)
    score = round(50 * len(matches) / backed_count) if backed_count else 0
    score += 20 if role_matches else 0
    score += 15 if profile.remote_preferred and job.workplace == "remote" else 0
    score += 5 if job.currency and job.currency in profile.preferred_currencies else 0
    pay = compensation(job, profile)
    score += 5 if job.employer_country and job.employer_country in profile.preferred_locations else 0
    score += 5 if pay["monthly_usd_minimum"] is not None and pay["monthly_usd_minimum"] >= profile.target_monthly_usd else 0
    return {"compensation":pay, "score": min(score, 100), "score_type": "keyword_baseline_not_ai", "scoring_version": SCORING_VERSION, "eligibility": state,
            "warnings": warnings, "matches": matches, "target_role_matches": role_matches,
            "unverified_profile_skills": unsupported, "ai_status": "not_requested", "ai_score": None,
            "missing_requirements": [], "review_status": "needs_human_review"}


def draft_letter(job, profile, matches):
    selected = []
    seen = set()
    for item in matches:
        quote = item["candidate_quote"]
        if quote not in seen:
            seen.add(quote)
            selected.append(quote)
        if len(selected) == 3:
            break
    if not selected:
        return ""
    evidence = "\n".join("- " + quote for quote in selected)
    return (f"Dear Hiring Manager,\n\nI am interested in the {job.title} position at {job.company}. "
            f"The following excerpts from my supplied CV/profile are relevant to reviewing my application:\n\n{evidence}\n\n"
            "I would welcome a discussion about the role, its requirements, and the team's working arrangements.\n\n"
            f"Best regards,\n{profile.name}\n\n[Review draft: verify fit, wording, eligibility, and all details before using.]")
