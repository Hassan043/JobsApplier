"""Offline ranking evaluation. Synthetic fixture scores are smoke checks, not quality claims."""
import argparse
import json
import math
from pathlib import Path
from job_assistant.models import Profile
from job_assistant.sources import load_jobs
from job_assistant.scoring import baseline


def ndcg(labels, ideal, k):
    def dcg(values):
        return sum((2**v-1)/math.log2(i+2) for i,v in enumerate(values[:k]))
    denominator=dcg(sorted(ideal,reverse=True))
    return dcg(labels)/denominator if denominator else 0.0


def evaluate(profile_path,jobs_path,labels_path,k=3):
    if k<1:raise ValueError('k must be positive')
    profile=Profile.load(profile_path)
    jobs,errors=load_jobs(jobs_path)
    if errors:raise ValueError('Invalid job input: '+ '; '.join(errors))
    labels=json.loads(Path(labels_path).read_text(encoding='utf-8-sig'))
    unique={j.url:j for j in jobs}
    if not unique:raise ValueError('No evaluation jobs')
    if set(labels)!=set(unique):raise ValueError('Labels must cover exactly the canonical unique job URLs')
    if any(type(v) is not int or not 0<=v<=3 for v in labels.values()):
        raise ValueError('Relevance labels must be integers from 0 to 3')
    assessed=[(job,baseline(job,profile)) for job in unique.values()]
    assessed.sort(key=lambda pair:(pair[1]['eligibility']!='ineligible',pair[1]['score']),reverse=True)
    relevance=[labels[j.url] for j,result in assessed]
    take=min(k,len(relevance))
    return {'evaluation_type':'offline_keyword_baseline','fixture_warning':'Synthetic examples establish reproducibility only; no general matching-quality claim.',
            'cases':len(assessed),'k':k,'ndcg_at_k':ndcg(relevance,list(labels.values()),k),
            'precision_at_k':sum(v>0 for v in relevance[:k])/take,
            'ranking':[{'url':j.url,'label':labels[j.url],'score':r['score'],'eligibility':r['eligibility']} for j,r in assessed]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',default='examples/demo_profile.json')
    parser.add_argument('--jobs',default='examples/jobs.json')
    parser.add_argument('--labels',default='tests/fixtures/relevance.json')
    parser.add_argument('--k',type=int,default=3)
    parser.add_argument('--output',default='output/evaluation.json')
    args=parser.parse_args()
    result=evaluate(args.profile,args.jobs,args.labels,args.k)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
