"""Local-first commands; external collection/inference are explicit opt-ins."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
from .ai import Assessor, PROMPT_VERSION
from .models import Profile
from .sources import load_jobs, fetch_pangian, fetch_boards
from .scoring import baseline, draft_letter, SCORING_VERSION
from .store import Store, STATUSES
from .public_feeds import fetch_public_feed
from .portals import select_portals
from .report import write_reports

ROOT=Path(__file__).resolve().parent.parent


def example_profile():
    return {"name":"Hassan Ali","base_country":"PK","remote_preferred":True,"remote_only":False,
            "open_to_relocation":True,"target_monthly_usd":2000,"preferred_currencies":["USD","EUR"],
            "preferred_locations":["US","CA","GB","IE","DE","FR","NL","BE","LU","CH","AT","DK","SE","NO","FI","AU","NZ","SG","JP","KR","AE"],
            "target_roles":["software engineer","full stack","full-stack","backend developer","backend engineer",
                            ".NET developer","applied AI","AI engineer","agentic AI","mobile developer","Android developer"],
            "skills":["Python",".NET","C#","JavaScript","TypeScript","React","SQL","Kotlin"],
            "excluded_terms":["executive assistant","customer success"],"resume_path":"","evidence":[]}


def version(job):
    return hashlib.sha256(json.dumps(job.to_dict(),sort_keys=True).encode()).hexdigest()


def analysis_key(job,profile,model):
    return hashlib.sha256((version(job)+profile.hash+model+PROMPT_VERSION+SCORING_VERSION).encode()).hexdigest()


def sorted_records(records):
    return sorted(records,key=lambda r:(r["assessment"]["eligibility"]!="ineligible",
        r["assessment"]["ai_score"] if r["assessment"]["ai_score"] is not None else r["assessment"]["score"],
        r["assessment"]["compensation"]["monthly_usd_minimum"] or 0),reverse=True)


def run(args):
    if args.max_jobs is not None and not 1<=args.max_jobs<=1000:
        raise ValueError("--max-jobs must be between 1 and 1000")
    if args.ai and args.max_jobs is None:
        raise ValueError("--ai requires an explicit --max-jobs global limit")
    if args.dry_run and (args.ai or args.sites or args.greenhouse or args.lever or args.feeds):
        raise ValueError("--dry-run is strictly offline: use --input without --ai or --sites")
    if not args.input and not args.sites and not args.greenhouse and not args.lever and not args.feeds:
        raise ValueError("Supply --input files, --greenhouse BOARD, --lever BOARD, or --feeds remotive arbeitnow or --sites pangian")
    if args.cv and len(args.profile)!=1:
        raise ValueError("--cv override requires exactly one --profile; use resume_path for multiple CV profiles")
    profiles=[Profile.load(p,args.cv) for p in args.profile]
    if len({p.hash for p in profiles})!=len(profiles):
        raise ValueError("Duplicate candidate profiles")
    if len(profiles)>20:
        raise ValueError("At most 20 candidate profiles per run")
    limit=args.max_jobs or 30
    all_roles=list(dict.fromkeys(role for profile in profiles for role in profile.target_roles))
    jobs=[];errors=[]
    for path in args.input or []:
        imported,invalid=load_jobs(path);jobs.extend(imported);errors.extend(invalid)
    if args.sites:
        queries=args.queries or all_roles[:3]
        if not queries or len(queries)>5:
            raise ValueError("Live collection requires 1-5 explicit queries or target roles")
        collected,invalid=fetch_pangian(queries,limit)
        jobs.extend(collected);errors.extend(invalid)
    for provider,boards in (("greenhouse",args.greenhouse),("lever",args.lever)):
        if boards:
            collected,invalid=fetch_boards(provider,boards,args.queries or all_roles,limit)
            jobs.extend(collected);errors.extend(invalid)
    for provider in args.feeds or []:
        collected,invalid=fetch_public_feed(provider,args.queries or all_roles,limit,Path(args.db).parent/"source_cache")
        jobs.extend(collected);errors.extend(invalid)
    unique=[];seen_urls=set();seen_content=set();duplicates=0
    for job in jobs:
        if job.url in seen_urls or job.fingerprint in seen_content:
            duplicates+=1;continue
        seen_urls.add(job.url);seen_content.add(job.fingerprint);unique.append(job)
    def preliminary(job):
        scores=[baseline(job,profile) for profile in profiles]
        eligible=[r for r in scores if r["eligibility"]!="ineligible"]
        return (bool(eligible),max((r["score"] for r in eligible),default=0),
                max((r["compensation"]["monthly_usd_minimum"] or 0 for r in eligible),default=0))
    unique.sort(key=preliminary,reverse=True)
    truncated=max(0,len(unique)-limit)
    unique=unique[:limit]
    if not unique:
        for message in errors:print("Warning: "+message,file=sys.stderr)
        raise ValueError("No valid jobs collected; no model calls, database writes, or report updates performed")
    assessor=Assessor(args.model,args.max_ai_calls) if args.ai else None
    store=None if args.dry_run else Store(args.db)
    records=[];cache_hits=0
    try:
        for job in unique:
            job_id=store.save_job(job) if store else job.id
            if store and job_id != job.id:
                job=store.get_job(job_id)
            for profile in profiles:
                key=analysis_key(job,profile,args.model if args.ai else "offline")
                result=store.cached(job_id,key) if store else None
                if result is not None:
                    cache_hits+=1
                else:
                    result=baseline(job,profile)
                    if assessor and result["eligibility"]!="ineligible":
                        result.update(assessor.assess(job,profile))
                    elif assessor:
                        result["ai_status"]="skipped_ineligible"
                    matches=result.get("ai_matches") if result["ai_status"]=="completed" else result["matches"]
                    result.update(candidate=profile.name+(" / "+profile.label if profile.label else ""),profile_hash=profile.hash,job_version=version(job),
                                  cover_letter=draft_letter(job,profile,matches))
                    if store:
                        store.save_analysis(job_id,key,result)
                records.append({"id":job_id,"job":job.to_dict(),"assessment":result,"status":"new","notes":""})
        if store:
            states={r["id"]:r for r in store.records()}
            for record in records:
                record.update(states[record["id"]]["applications"].get(record["assessment"]["profile_hash"],{"status":"new","notes":""}))
        records=sorted_records(records)
        if not args.dry_run:
            report=write_reports(records,args.output)
            print("Review report: "+str(report.resolve()))
        else:
            print(json.dumps(records,indent=2,ensure_ascii=False))
        print(json.dumps({"unique_jobs":len(unique),"candidate_assessments":len(records),"duplicates_skipped":duplicates,
                          "jobs_outside_cap":truncated,"cache_hits":cache_hits,"ai_calls":assessor.calls if assessor else 0,
                          "source_warnings":errors,"dry_run":args.dry_run,
                          "ai_failures":sum(r["assessment"]["ai_status"] in {"error","unavailable_after_error"} for r in records)},ensure_ascii=False))
        return 0
    finally:
        if store:store.close()


def parser():
    p=argparse.ArgumentParser(description="Job discovery and evidence-based review. No auto-submission.")
    sub=p.add_subparsers(dest="command",required=True)
    r=sub.add_parser("run",help="Import/collect, match CV profiles, and prepare a local review report")
    r.add_argument("--profile",action="append",required=True,help="Repeat for team members or CV variants")
    r.add_argument("--cv",help="Text/PDF CV override for one profile")
    r.add_argument("--input",nargs="+",help="JSON/JSONL/CSV or saved JobPosting JSON-LD HTML")
    r.add_argument("--sites",nargs="+",choices=["pangian"],help="Explicit read-only live collection")
    r.add_argument("--greenhouse",nargs="+",help="Public employer Greenhouse board tokens, at most ten")
    r.add_argument("--lever",nargs="+",help="Public employer Lever site identifiers, at most ten")
    r.add_argument("--feeds",nargs="+",choices=["remotive","arbeitnow"],help="Read-only public feeds with persistent refresh cache")
    r.add_argument("--queries",nargs="+")
    r.add_argument("--max-jobs",type=int,help="Global unique-job cap; required for AI")
    r.add_argument("--ai",action="store_true",help="Send supplied CV/job evidence to OpenAI; explicit opt-in")
    r.add_argument("--model",default=os.environ.get("OPENAI_MODEL",""))
    r.add_argument("--max-ai-calls",type=int,default=5,help="Hard call cap across all jobs and profiles; SDK retries disabled")
    r.add_argument("--dry-run",action="store_true",help="Offline preview; no AI, network, database, or output writes")
    r.add_argument("--db",default=str(ROOT/"data/jobs.sqlite3"))
    r.add_argument("--output",default=str(ROOT/"output"))
    catalog=sub.add_parser("portals",help="Show researched versus implemented portal coverage; does not log in")
    catalog.add_argument("--group");catalog.add_argument("--country");catalog.add_argument("--status")
    catalog.add_argument("--json",action="store_true",help="Print structured catalog metadata")
    i=sub.add_parser("init-profile",help="Write an editable software/AI/mobile target profile")
    i.add_argument("path")
    t=sub.add_parser("status",help="Track your own review/application status locally")
    t.add_argument("job_id");t.add_argument("status",choices=sorted(STATUSES));t.add_argument("--notes");t.add_argument("--candidate",help="Profile hash required if job has several candidates")
    t.add_argument("--db",default=str(ROOT/"data/jobs.sqlite3"))
    e=sub.add_parser("report",help="Rebuild report from current stored assessments")
    e.add_argument("--db",default=str(ROOT/"data/jobs.sqlite3"));e.add_argument("--output",default=str(ROOT/"output"))
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.command=="run":return run(args)
        if args.command=="portals":
            rows=select_portals(args.group,args.country,args.status)
            if args.json:print(json.dumps(rows,indent=2,ensure_ascii=False))
            else:
                for row in rows:print(f"{row['id']}: {row['name']} | {row['status']} | {row['access']}")
                print(f"{len(rows)} sources. Catalog coverage does not imply a working native connector.")
            return 0
        if args.command=="init-profile":
            path=Path(args.path);path.parent.mkdir(parents=True,exist_ok=True)
            with path.open("x",encoding="utf-8") as f:json.dump(example_profile(),f,indent=2)
            print("Created "+str(path)+". Add your CV/evidence before running.")
            return 0
        if not Path(args.db).is_file():raise ValueError("Database does not exist; run an import first")
        store=Store(args.db)
        try:
            if args.command=="status":
                store.update_status(args.job_id,args.status,args.notes,args.candidate)
                print("Local status updated; run report to refresh exports. No external action was performed.")
            else:
                records=[]
                for row in store.records():
                    latest={}
                    from .models import Job
                    for result in row["analyses"]:
                        if result["job_version"]==version(Job.from_dict(row["job"])):
                            latest.setdefault(result["profile_hash"],result)
                    for result in latest.values():
                        records.append({"id":row["id"],"job":row["job"],"assessment":result,
                                        **row["applications"].get(result["profile_hash"],{"status":"new","notes":""})})
                print("Review report: "+str(write_reports(sorted_records(records),args.output).resolve()))
        finally:store.close()
        return 0
    except (ValueError,OSError,json.JSONDecodeError) as exc:
        print("Error: "+str(exc),file=sys.stderr)
        return 2
