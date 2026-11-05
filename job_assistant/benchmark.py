"""Strict, offline benchmark loading and evaluation. No provider or job-feed imports."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import time
from .models import Job, Profile, contains
from .scoring import baseline, eligibility, compensation, SCORING_VERSION

ELIGIBILITY={'eligible','ineligible','unknown'}
PROVISIONAL='scenario_authored_provisional'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    if path.stat().st_size>10_000_000:
        raise ValueError('Benchmark file exceeds 10 MB')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_lines(path):
    if path.stat().st_size>10_000_000:
        raise ValueError('Benchmark file exceeds 10 MB')
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def member(root, relative):
    if not isinstance(relative,str) or not relative:
        raise ValueError('Manifest paths must be nonempty relative paths')
    target=(root/relative).resolve()
    if Path(relative).is_absolute() or not target.is_relative_to(root.resolve()):
        raise ValueError('Manifest path escapes benchmark directory')
    if not target.is_file():
        raise ValueError('Missing benchmark file: '+relative)
    return target


def load_benchmark(path, annotations=None):
    path=Path(path).resolve();root=path.parent;manifest=read_json(path)
    if not isinstance(manifest,dict) or type(manifest.get('schema_version')) is not int or manifest.get('schema_version')!=1:
        raise ValueError('Unsupported benchmark manifest')
    if manifest.get('split_unit')!='family_id' or set(manifest.get('splits',[]))!={'dev','test'}:
        raise ValueError('Benchmark must declare disjoint dev/test family splits')
    if manifest.get('relevance_threshold')!=2:
        raise ValueError('This evaluator requires relevance_threshold 2')
    candidates=manifest.get('candidates');hashes=manifest.get('hashes')
    if not isinstance(candidates,dict) or not candidates or not isinstance(hashes,dict):
        raise ValueError('Manifest needs candidate paths and frozen file hashes')
    required={manifest.get('jobs'),manifest.get('judgments'),*candidates.values()}
    if not required.issubset(hashes):
        raise ValueError('All input files must have frozen hashes')
    for relative,expected in hashes.items():
        if digest(member(root,relative))!=expected:
            raise ValueError('Frozen input hash mismatch: '+relative)
    profiles={}
    for ident,relative in candidates.items():
        candidate_path=member(root,relative)
        candidate_data=read_json(candidate_path)
        if not isinstance(candidate_data,dict) or candidate_data.get('resume_path'):
            raise ValueError('Benchmark candidates must use self-contained inline evidence, not external resume files')
        profiles[ident]=Profile.load(candidate_path)
    jobs={};families={};urls=set();fingerprints=set()
    for raw in read_lines(member(root,manifest['jobs'])):
        if not isinstance(raw,dict):raise ValueError('Job entries must be objects')
        ident=raw.get('benchmark_id');family=raw.get('family_id');split=raw.get('split')
        if not isinstance(ident,str) or not ident or ident in jobs:
            raise ValueError('Job IDs must be nonempty and unique')
        if not isinstance(family,str) or not family or split not in {'dev','test'}:
            raise ValueError('Each job needs family_id and dev/test split')
        if family in families and families[family]!=split:
            raise ValueError('Family leakage across dev/test: '+family)
        families[family]=split
        tags=raw.get('tags',[])
        if not isinstance(tags,list) or any(not isinstance(t,str) for t in tags):raise ValueError('Invalid slice tags')
        job=Job.from_dict(raw)
        if job.url in urls or job.fingerprint in fingerprints:
            raise ValueError('Duplicate canonical URL or normalized posting content')
        urls.add(job.url);fingerprints.add(job.fingerprint)
        jobs[ident]={'job':job,'family':family,'split':split,'tags':tags}
    if not jobs or {r['split'] for r in jobs.values()}!={'dev','test'}:
        raise ValueError('Both splits must contain jobs')
    if annotations:
        annotation_path=Path(annotations)
        if annotation_path.stat().st_size>10_000_000:raise ValueError('Annotation file exceeds 10 MB')
        with annotation_path.open(encoding='utf-8-sig',newline='') as stream:
            labels=list(csv.DictReader(stream))
        for row in labels:
            if not row.get('reviewer','').strip() or not row.get('rationale','').strip():
                raise ValueError('Reviewer-declared annotations need reviewer and rationale for every row')
            try:row['relevance']=int(row['relevance'])
            except (KeyError,ValueError) as exc:raise ValueError('Fill every annotation relevance grade') from exc
            expected=row.get('expected_monthly_usd','')
            try:row['expected_monthly_usd']=float(expected) if expected.strip() else None
            except ValueError as exc:raise ValueError('Invalid annotated compensation value') from exc
            row['label_origin']='reviewer_declared'
        label_hash=digest(annotation_path);label_origin='reviewer_declared_not_independently_verified'
    else:
        labels=read_lines(member(root,manifest['judgments']))
        label_hash=hashes[manifest['judgments']];label_origin=PROVISIONAL
    judgments={}
    for row in labels:
        if not isinstance(row,dict):raise ValueError('Judgments must be objects')
        key=(row.get('candidate_id'),row.get('job_id'))
        if key[0] not in profiles or key[1] not in jobs or key in judgments:
            raise ValueError('Duplicate or unknown judgment pair')
        grade=row.get('relevance')
        if type(grade) is not int or not 0<=grade<=3 or row.get('eligibility') not in ELIGIBILITY:
            raise ValueError('Invalid relevance or eligibility judgment')
        expected=row.get('expected_monthly_usd')
        if expected is not None and (type(expected) not in (int,float) or not math.isfinite(expected) or expected<0):
            raise ValueError('Expected compensation must be finite nonnegative USD/month or null')
        if not isinstance(row.get('rationale'),str) or not row['rationale'].strip():
            raise ValueError('Every judgment needs a rationale')
        if not annotations and row.get('label_origin')!=PROVISIONAL:
            raise ValueError('Default fixture labels must disclose provisional scenario authorship')
        judgments[key]=row
    expected_pairs={(candidate,job) for candidate in profiles for job in jobs}
    if set(judgments)!=expected_pairs:
        raise ValueError('Judgments must cover every candidate/job pair exactly once')
    return {'path':path,'manifest':manifest,'manifest_hash':digest(path),'profiles':profiles,'jobs':jobs,
            'judgments':judgments,'label_hash':label_hash,'label_origin':label_origin,'families':families}


def title_only(job,profile):
    state,warnings=eligibility(job,profile)
    return {'score':100 if any(contains(job.title,role) for role in profile.target_roles) else 0,
            'eligibility':state,'warnings':warnings,'matches':[],'compensation':compensation(job,profile)}

SCORERS={'keyword':baseline,'title_only':title_only}
SCORER_VERSIONS={'keyword':SCORING_VERSION,'title_only':'title-only-v1'}


def predicted_eligibility(state):
    if state=='ineligible':return 'ineligible'
    if state=='eligible_by_declared_country':return 'eligible'
    return 'unknown'


def mean(values):
    valid=[v for v in values if v is not None]
    return sum(valid)/len(valid) if valid else None


def ranking_metrics(labels,eligibilities,k,threshold=2):
    if type(k) is not int or k<1 or not labels or len(labels)!=len(eligibilities):
        raise ValueError('Ranking needs nonempty paired judgments and positive k')
    if any(type(g) is not int or not 0<=g<=3 for g in labels) or any(e not in ELIGIBILITY for e in eligibilities):
        raise ValueError('Invalid relevance or eligibility metric input')
    actionable=[0 if e=='ineligible' else g for g,e in zip(labels,eligibilities)]
    def dcg(values):return sum((2**g-1)/math.log2(i+2) for i,g in enumerate(values[:k]))
    ideal=dcg(sorted(actionable,reverse=True));take=min(k,len(labels))
    hits=[g>=threshold for g in actionable]
    relevant=sum(hits)
    return {'ndcg_at_k':dcg(actionable)/ideal if ideal else None,
            'precision_at_k':sum(hits[:k])/take,'recall_at_k':sum(hits[:k])/relevant if relevant else None,
            'mrr_at_k':next((1/(i+1) for i,h in enumerate(hits[:k]) if h),0.0),
            'ineligible_at_k':sum(e=='ineligible' for e in eligibilities[:k])/take,
            'unknown_eligibility_at_k':sum(e=='unknown' for e in eligibilities[:k])/take,
            'relevant_jobs':relevant,'retrieved':take}


def quantile(values,p):
    if not values:return None
    ordered=sorted(values);return ordered[max(0,math.ceil(p*len(ordered))-1)]


def evaluate_benchmark(path,split='dev',k=5,annotations=None,scorer_names=None):
    if split not in {'dev','test'} or type(k) is not int or k<1:raise ValueError('Choose dev/test and positive k')
    bundle=load_benchmark(path,annotations)
    names=scorer_names or ['title_only','keyword']
    if len(set(names))!=len(names) or any(n not in SCORERS for n in names):raise ValueError('Unknown or duplicate scorer')
    selected={i:r for i,r in bundle['jobs'].items() if r['split']==split}
    reports={}
    for name in names:
        rows=[];profiles=[]
        for candidate,profile in sorted(bundle['profiles'].items()):
            cases=[]
            for ident,entry in sorted(selected.items()):
                job=entry['job'];truth=bundle['judgments'][(candidate,ident)];start=time.perf_counter()
                error=None
                try:
                    result=SCORERS[name](job,profile)
                    if not isinstance(result,dict) or not isinstance(result.get('compensation'),dict) or not isinstance(result.get('matches'),list):
                        raise ValueError('Scorer must return structured compensation and matches')
                    score=result['score']
                    if type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=100:
                        raise ValueError('Scorer returned invalid score')
                    if result['eligibility'] not in {'ineligible','eligible_by_declared_country','review_needed'}:
                        raise ValueError('Scorer returned invalid eligibility state')
                except Exception as exc:
                    error=type(exc).__name__;result={'score':0,'eligibility':'review_needed','matches':[],'compensation':{}}
                latency=(time.perf_counter()-start)*1000
                matches=result.get('matches',[])
                if not isinstance(matches,list):matches=[];error=error or 'InvalidMatchList'
                valid=0
                for match in matches:
                    if isinstance(match,dict) and isinstance(match.get('evidence_id'),str) and isinstance(match.get('candidate_quote'),str) and match['candidate_quote'] and \
                       isinstance(match.get('job_quote'),str) and match['job_quote'] and \
                       match['candidate_quote'] in profile.evidence.get(match.get('evidence_id'),'') and \
                       match['job_quote'] in job.title+' '+job.description:
                        valid+=1
                expected=truth['expected_monthly_usd'];actual=result.get('compensation',{}).get('monthly_usd_minimum')
                pay_correct=(actual is None and expected is None) or (type(actual) in (int,float) and expected is not None and math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-6))
                case={'candidate_id':candidate,'job_id':ident,'family_id':entry['family'],'tags':entry['tags'],
                      'title':job.title,'relevance':truth['relevance'],'expected_eligibility':truth['eligibility'],
                      'predicted_eligibility':predicted_eligibility(result['eligibility']),
                      'score':result['score'],'status':'error' if error else 'completed','error_type':error,
                      'latency_ms':latency,'matches':len(matches),'valid_quote_matches':valid,
                      'pay_normalization_correct':bool(pay_correct) if not error else False}
                cases.append(case)
            cases.sort(key=lambda r:(r['status']=='error',r['predicted_eligibility']=='ineligible',-r['score'],r['job_id']))
            for rank,row in enumerate(cases,1):row['rank']=rank
            metrics=ranking_metrics([r['relevance'] for r in cases],[r['expected_eligibility'] for r in cases],k)
            profiles.append({'candidate_id':candidate,**metrics});rows.extend(cases)
        reports[name]=summarize(rows,profiles,k)
    code_dir=Path(__file__).resolve().parent
    return {'schema_version':1,'benchmark_id':bundle['manifest']['benchmark_id'],'split':split,'k':k,
            'created_at':datetime.now(timezone.utc).isoformat(),'jobs':len(selected),'candidates':len(bundle['profiles']),
            'families':len({r['family'] for r in selected.values()}),'judgments':len(selected)*len(bundle['profiles']),
            'label_origin':bundle['label_origin'],'manifest_sha256':bundle['manifest_hash'],'judgments_sha256':bundle['label_hash'],
            'environment':{'python':platform.python_version(),'platform':platform.system()},
            'code_sha256':{n:digest(code_dir/n) for n in ['benchmark.py','models.py','scoring.py']},
            'scorer_versions':{n:SCORER_VERSIONS[n] for n in names},'reports':reports,
            'limitations':['Authored synthetic scenarios and provisional labels; not independent real-world quality evidence.',
              'Candidate CVs are fictional. No private CVs, network access, model calls, or learned semantic matcher are used.',
              'Unknown eligibility remains reviewable; it is not permission to apply. Exact-quote checks do not establish semantic truth.',
              'Once test results are inspected, this split is observed. Future tuning needs a fresh final evaluation set.']}


def summarize(rows,profiles,k):
    keys=['ndcg_at_k','precision_at_k','recall_at_k','mrr_at_k','ineligible_at_k','unknown_eligibility_at_k']
    confusion={expected:{pred:0 for pred in ['eligible','ineligible','unknown','error']} for expected in sorted(ELIGIBILITY)}
    failures=[];failure_counts={}
    for row in rows:
        prediction='error' if row['status']=='error' else row['predicted_eligibility']
        confusion[row['expected_eligibility']][prediction]+=1
        reasons=[]
        if row['status']=='error':reasons.append('scorer_error')
        if prediction!=row['expected_eligibility']:reasons.append('eligibility_mismatch')
        if row['rank']<=k and (row['relevance']<2 or row['expected_eligibility']=='ineligible'):reasons.append('nonrelevant_top_k')
        if row['rank']>k and row['relevance']>=2 and row['expected_eligibility']!='ineligible':reasons.append('relevant_below_k')
        if row['valid_quote_matches']!=row['matches']:reasons.append('invalid_quote')
        if not row['pay_normalization_correct']:reasons.append('pay_normalization_mismatch')
        for reason in reasons:failure_counts[reason]=failure_counts.get(reason,0)+1
        if reasons:failures.append({k:row[k] for k in ['candidate_id','job_id','title','rank','score','relevance','expected_eligibility','predicted_eligibility']}|{'reasons':reasons})
    quote_count=sum(r['matches'] for r in rows)
    ineligible=[r for r in rows if r['expected_eligibility']=='ineligible']
    slices={}
    for tag in sorted({t for r in rows for t in r['tags']}):
        subset=[r for r in rows if tag in r['tags']]
        slices[tag]={'cases':len(subset),'completed':sum(r['status']=='completed' for r in subset),
                     'eligibility_accuracy':mean([float(r['status']=='completed' and r['expected_eligibility']==r['predicted_eligibility']) for r in subset]),
                     'pay_normalization_accuracy':mean([float(r['pay_normalization_correct']) for r in subset])}
    return {'macro':{key:mean([p[key] for p in profiles]) for key in keys},'per_candidate':profiles,
            'attempted':len(rows),'completed':sum(r['status']=='completed' for r in rows),
            'eligibility_accuracy':mean([float(r['status']=='completed' and r['expected_eligibility']==r['predicted_eligibility']) for r in rows]),
            'ineligible_missed_rate':mean([float(r['status']=='error' or r['predicted_eligibility']!='ineligible') for r in ineligible]),
            'eligibility_confusion':confusion,'pay_normalization_accuracy':mean([float(r['pay_normalization_correct']) for r in rows]),
            'quote_support_rate':sum(r['valid_quote_matches'] for r in rows)/quote_count if quote_count else None,
            'quote_match_count':quote_count,'latency_ms':{'p50':quantile([r['latency_ms'] for r in rows],0.5),
                                                       'p95':quantile([r['latency_ms'] for r in rows],0.95)},
            'slices':slices,'failure_counts':failure_counts,'failure_examples':failures[:20],'cases':rows}


def annotation_template(path,output):
    bundle=load_benchmark(path)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    fields=['candidate_id','job_id','split','family_id','candidate_evidence','job_title','job_description',
            'workplace','eligible_countries','salary','relevance','eligibility','expected_monthly_usd','reviewer','rationale']
    def safe(value):
        text=str(value)
        return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
    with output.open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for candidate,profile in sorted(bundle['profiles'].items()):
            for ident,entry in sorted(bundle['jobs'].items()):
                job=entry['job']
                row={'candidate_id':candidate,'job_id':ident,'split':entry['split'],'family_id':entry['family'],
                     'candidate_evidence':'\n'.join(profile.evidence.values()),'job_title':job.title,'job_description':job.description,
                     'workplace':job.workplace,'eligible_countries':';'.join(job.eligible_countries),'salary':job.salary}
                writer.writerow({k:safe(v) for k,v in row.items()})
    return output


def number(value):
    return 'n/a' if value is None else f'{value:.4f}'


def markdown_report(result):
    lines=[f"# JobFit v1: {result['split']} baseline report",'',
           f"Generated: {result['created_at']}",f"Labels: {result['label_origin']}",'',
           f"{result['jobs']} authored postings / {result['families']} families / {result['candidates']} fictional CVs / {result['judgments']} judgments.",'',
           '**Synthetic evaluation only. These are not real vacancies, independent human ratings, or measured hiring outcomes.**','',
           '| Scorer | NDCG@k | Precision@k | Recall@k | MRR@k | Ineligible@k | Unknown@k |',
           '|---|---|---|---|---|---|---|']
    for name,report in result['reports'].items():
        m=report['macro'];lines.append('| '+name+' | '+' | '.join(number(m[key]) for key in ['ndcg_at_k','precision_at_k','recall_at_k','mrr_at_k','ineligible_at_k','unknown_eligibility_at_k'])+' |')
    lines+=['',f"k = {result['k']}. Macro averages give equal weight to each candidate. Relevance threshold is 2. Known-ineligible jobs have zero actionable relevance; unknown eligibility stays reviewable and is reported separately.",'']
    for name,report in result['reports'].items():
        lines += ['## '+name,'',f"Completed: {report['completed']}/{report['attempted']}; eligibility accuracy: {number(report['eligibility_accuracy'])}; missed-ineligible rate: {number(report['ineligible_missed_rate'])}.",
                  f"Pay-normalization accuracy: {number(report['pay_normalization_accuracy'])}; exact-quote support: {number(report['quote_support_rate'])} over {report['quote_match_count']} excerpts.",
                  f"Local scoring latency (ms): p50 {number(report['latency_ms']['p50'])}, p95 {number(report['latency_ms']['p95'])}. This excludes network/model latency.",'',
                  '| Candidate | NDCG@k | Precision@k | Recall@k | MRR@k |','|---|---|---|---|---|']
        for p in report['per_candidate']:
            lines.append('| '+p['candidate_id']+' | '+' | '.join(number(p[key]) for key in ['ndcg_at_k','precision_at_k','recall_at_k','mrr_at_k'])+' |')
        lines+=['','### Eligibility confusion','', '| Expected | Predicted eligible | Predicted ineligible | Predicted unknown | Error |','|---|---|---|---|---|']
        for expected,counts in report['eligibility_confusion'].items():
            lines.append('| '+expected+' | '+' | '.join(str(counts[k]) for k in ['eligible','ineligible','unknown','error'])+' |')
        lines+=['','### Error and risk slices','', '| Slice | Cases | Eligibility accuracy | Pay accuracy |','|---|---|---|---|']
        for tag,slice_ in report['slices'].items():
            lines.append(f"| {tag} | {slice_['cases']} | {number(slice_['eligibility_accuracy'])} | {number(slice_['pay_normalization_accuracy'])} |")
        lines+=['','### Failure analysis','', 'Counts: '+json.dumps(report['failure_counts'],sort_keys=True),'',
                'First 20 flagged candidate/job cases are included below; the JSONL export contains every attempted case. Multiple reasons can apply to one case.','']
        for failure in report['failure_examples']:
            lines.append(f"- {failure['candidate_id']} / {failure['job_id']}: rank {failure['rank']}, grade {failure['relevance']}, reasons: {', '.join(failure['reasons'])}.")
    lines+=['','## Reproducibility','',f"Manifest SHA-256: `{result['manifest_sha256']}`",f"Judgments SHA-256: `{result['judgments_sha256']}`",'',
            'Code hashes:','```json',json.dumps(result['code_sha256'],indent=2),'```','',
            'Both scorers use the same eligibility and pay rules. Title-only uses role-title matching, while keyword uses the existing evidence-backed baseline. This is not an AI-model comparison.','',
            'Missing/failed cases remain in denominators. NDCG is n/a when all reference gains are zero; recall is n/a when no actionable grade-2/3 items exist. Exact quote support only validates provenance, not semantic entailment or truth.','',
            '## Limitations','']
    lines+=['- '+x for x in result['limitations']]
    return '\n'.join(lines)+'\n'


def save_result(result,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (output/'report.md').write_text(markdown_report(result),encoding='utf-8')
    with (output/'cases.jsonl').open('w',encoding='utf-8') as stream:
        for name,report in result['reports'].items():
            for row in report['cases']:stream.write(json.dumps({'scorer':name,**row},allow_nan=False)+'\n')
    return output/'report.md'


def main(argv=None):
    parser=argparse.ArgumentParser(description='Offline, versioned CV/job ranking benchmark. No network or model calls.')
    parser.add_argument('--manifest',default=str(Path(__file__).resolve().parent.parent/'benchmarks/jobfit_v1/manifest.json'))
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('validate',help='Verify hashes, input schemas, family isolation, and complete judgments')
    a=sub.add_parser('annotations',help='Export a blank blind-review worksheet; refuses overwrite')
    a.add_argument('--output',default='output/benchmark-annotations.csv')
    e=sub.add_parser('evaluate',help='Compare offline title and keyword baselines')
    e.add_argument('--split',choices=['dev','test'],default='dev');e.add_argument('--k',type=int,default=5)
    e.add_argument('--scorers',nargs='+',choices=sorted(SCORERS),default=['title_only','keyword'])
    e.add_argument('--annotations',help='Complete reviewer-declared CSV; default uses provisional authored labels')
    e.add_argument('--output',help='Default: output/benchmark-SPLIT')
    args=parser.parse_args(argv)
    try:
        if args.command=='validate':
            bundle=load_benchmark(args.manifest)
            print(json.dumps({'jobs':len(bundle['jobs']),'families':len(bundle['families']),'candidates':len(bundle['profiles']),
                              'judgments':len(bundle['judgments']),'label_origin':bundle['label_origin'],
                              'splits':{s:sum(j['split']==s for j in bundle['jobs'].values()) for s in ['dev','test']}}))
        elif args.command=='annotations':
            print('Blind worksheet: '+str(annotation_template(args.manifest,args.output)))
        else:
            result=evaluate_benchmark(args.manifest,args.split,args.k,args.annotations,args.scorers)
            print('Report: '+str(save_result(result,args.output or f'output/benchmark-{args.split}')))
            print(json.dumps({n:r['macro'] for n,r in result['reports'].items()},indent=2,allow_nan=False))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('Benchmark error: '+str(exc));return 2
