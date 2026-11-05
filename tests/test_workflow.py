import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from job_assistant.models import Job, Profile, canonical_url
from job_assistant.scoring import baseline, compensation
from job_assistant.ai import Assessor, validate_assessment
from job_assistant.sources import load_jobs, parse_pangian, fetch_pangian
from job_assistant.store import Store
from job_assistant.cli import main, version
from job_assistant.report import write_reports

ROOT=Path(__file__).resolve().parent.parent

@pytest.fixture
def profile():
    return Profile.load(ROOT/'examples/demo_profile.json')

@pytest.fixture
def job():
    return Job.from_dict({'title':'Backend Engineer','company':'Tools','url':'https://example.com/job?utm_source=x',
        'description':'Build Python APIs with SQL.','workplace':'remote','eligible_countries':['PK'],
        'currency':'USD','salary_min':100000,'salary_period':'year'})


def test_tracking_dedup_preserves_semantic_query():
    assert canonical_url('https://EXAMPLE.com/job/?id=2&utm_source=x#top')=='https://example.com/job?id=2'
    assert canonical_url('https://example.com/job?id=3')!=canonical_url('https://example.com/job?id=2')

@pytest.mark.parametrize('url',['javascript:alert(1)','file:///secret','https://user:pass@example.com/job','not a url'])
def test_unsafe_urls_rejected(url):
    with pytest.raises(ValueError):canonical_url(url)

@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1,True])
def test_bad_salaries_rejected(job,value):
    data=job.to_dict();data['salary_min']=value
    with pytest.raises(ValueError):Job.from_dict(data)


def test_unknown_remote_eligibility_is_not_worldwide(job,profile):
    result=baseline(replace(job,eligible_countries=[]),profile)
    assert result['eligibility']=='review_needed'
    assert any('worldwide' in x for x in result['warnings'])


def test_explicit_country_restriction(job,profile):
    assert baseline(replace(job,eligible_countries=['US']),profile)['eligibility']=='ineligible'
    assert baseline(replace(job,eligible_countries=[],description='Python role. US-only.'),profile)['eligibility']=='ineligible'


def test_salary_no_upper_cap_or_implicit_fx(job,profile):
    pay=compensation(job,profile)
    assert pay['monthly_usd_minimum']==pytest.approx(100000/12)
    assert 'no upper cap' in pay['note']
    assert compensation(replace(job,currency='EUR'),profile)['monthly_usd_minimum'] is None
    assert compensation(replace(job,salary_period='hour'),profile)['monthly_usd_minimum'] is None

@pytest.mark.parametrize('text,expected',[('USD 24,000-36,000/year',2000),('USD 2500/month',2500),('USD 100k/year',100000/12),('$3000/month',None)])
def test_salary_text_only_when_explicit(job,profile,text,expected):
    pay=compensation(replace(job,salary_min=None,currency='',salary_period='',salary=text),profile)
    if expected is None:assert pay['monthly_usd_minimum'] is None
    else:assert pay['monthly_usd_minimum']==pytest.approx(expected)


def test_low_unknown_and_nonpreferred_markets_retained(job,profile):
    result=baseline(replace(job,employer_country='VN',salary_min=1800,salary_period='month'),profile)
    assert result['eligibility']!='ineligible'
    assert 'retained' in result['compensation']['note']


def test_profile_claims_require_resume_evidence(job,profile):
    result=baseline(job,profile)
    assert 'Kotlin' in result['unverified_profile_skills']
    assert {m['skill'] for m in result['matches']}=={'Python','SQL'}
    assert result['score_type']=='keyword_baseline_not_ai'


def test_profile_relative_cv_and_empty_error(tmp_path):
    (tmp_path/'cv.txt').write_text('Built Python services.',encoding='utf-8')
    p=tmp_path/'profile.json';p.write_text(json.dumps({'name':'Test','resume_path':'cv.txt','skills':['Python']}))
    assert Profile.load(p).evidence['resume_1']=='Built Python services.'
    p.write_text('{}')
    with pytest.raises(ValueError,match='CV'):Profile.load(p)


def test_jobposting_fixture_import():
    jobs,errors=load_jobs(ROOT/'tests/fixtures/jobposting.html')
    assert not errors and jobs[0].description=='Build Python services.'
    assert jobs[0].workplace=='remote' and jobs[0].eligible_countries==[]


def test_csv_import_with_multiline_description(tmp_path):
    p=tmp_path/'jobs.csv';p.write_text('title,company,url,description\nEngineer,Test,https://example.com/job,"Python\nSQL"\n')
    jobs,errors=load_jobs(p)
    assert not errors and jobs[0].description=='Python SQL'


def test_pangian_schema_drift_is_error():
    with pytest.raises(ValueError):parse_pangian({'unexpected':[]})
    jobs,errors=fetch_pangian(['backend'],1,opener=lambda *a,**k:(_ for _ in ()).throw(TimeoutError()))
    assert jobs==[] and 'unavailable' in errors[0]


def supported_result(job,profile):
    return {'score':70,'matches':[{'skill':'Python','evidence_id':'project_api','candidate_quote':'Built a Python API',
                                 'job_quote':'Build Python APIs'}],'missing_requirements':[]}


def test_ai_rejects_fabricated_evidence(job,profile):
    result=supported_result(job,profile)
    assert validate_assessment(result,job,profile)['score']==70
    result['matches'][0]['candidate_quote']='Managed a team of 50 engineers'
    with pytest.raises(ValueError,match='ungrounded'):validate_assessment(result,job,profile)


def test_ai_error_is_not_fake_medium_score_and_circuit_breaks(job,profile):
    fake=SimpleNamespace(responses=SimpleNamespace(create=lambda **k:(_ for _ in ()).throw(RuntimeError('secret should not leak'))))
    client=Assessor('test-model',2,client=fake)
    first=client.assess(job,profile);second=client.assess(job,profile)
    assert first['ai_status']=='error' and first['ai_score'] is None
    assert second['ai_status']=='unavailable_after_error' and client.calls==1
    assert 'secret' not in json.dumps(first)


def test_ai_call_budget_and_grounded_response(job,profile):
    response=SimpleNamespace(status='completed',output_text=json.dumps(supported_result(job,profile)))
    fake=SimpleNamespace(responses=SimpleNamespace(create=lambda **k:response))
    client=Assessor('test-model',1,client=fake)
    assert client.assess(job,profile)['ai_status']=='completed'
    assert client.assess(job,profile)['ai_status']=='budget_exhausted'
    assert client.calls==1


def test_store_cache_preserves_status_and_updates_content(tmp_path,job,profile):
    store=Store(tmp_path/'jobs.db')
    try:
        ident=store.save_job(job)
        result=baseline(job,profile);result.update(profile_hash=profile.hash,candidate=profile.name,job_version=version(job))
        store.save_analysis(ident,'key',result)
        store.update_status(ident,'applied','Sent manually')
        store.save_job(replace(job,description='Updated Python role'))
        assert store.cached(ident,'key')==result
        assert store.records()[0]['applications'][profile.hash]['status']=='applied'
        assert store.get_job(ident).description=='Updated Python role'
    finally:store.close()


def test_team_statuses_are_independent(tmp_path,job,profile):
    store=Store(tmp_path/'jobs.db')
    try:
        ident=store.save_job(job)
        for key in ['candidate_a','candidate_b']:
            store.save_analysis(ident,key,{'profile_hash':key})
        with pytest.raises(ValueError,match='Multiple'):store.update_status(ident,'applied')
        store.update_status(ident,'applied',profile_hash='candidate_a')
        assert 'candidate_b' not in store.records()[0]['applications']
    finally:store.close()


def test_dry_run_no_network_ai_db_or_output(tmp_path,capsys):
    db=tmp_path/'missing'/'jobs.db';out=tmp_path/'report'
    with patch('socket.socket',side_effect=AssertionError('Network forbidden')):
        assert main(['run','--profile',str(ROOT/'examples/demo_profile.json'),'--input',str(ROOT/'examples/jobs.json'),
                     '--dry-run','--db',str(db),'--output',str(out)])==0
    assert not db.exists() and not out.exists()
    output=capsys.readouterr().out
    assert '"duplicates_skipped": 1' in output and '"ai_calls": 0' in output


def test_dry_run_rejects_live_and_ai(capsys):
    base=['run','--profile',str(ROOT/'examples/demo_profile.json'),'--input',str(ROOT/'examples/jobs.json'),'--dry-run']
    assert main(base+['--ai','--max-jobs','1'])==2
    assert main(base+['--sites','pangian'])==2


def test_full_run_repeated_cache_and_status_report(tmp_path,capsys):
    db=tmp_path/'jobs.db';out=tmp_path/'out'
    args=['run','--profile',str(ROOT/'examples/demo_profile.json'),'--input',str(ROOT/'examples/jobs.json'),
          '--db',str(db),'--output',str(out)]
    assert main(args)==0
    assert main(args)==0
    assert '"cache_hits": 3' in capsys.readouterr().out
    rows=json.loads((out/'jobs.json').read_text())
    assert len(rows)==3 and rows[-1]['assessment']['eligibility']=='ineligible'
    assert main(['status',rows[0]['id'],'shortlisted','--db',str(db)])==0
    assert main(['report','--db',str(db),'--output',str(out)])==0
    assert json.loads((out/'jobs.json').read_text())[0]['status']=='shortlisted'


def test_report_escapes_html_and_spreadsheet_formulas(tmp_path,job,profile):
    job=replace(job,title='<script>alert(1)</script>',company='=HYPERLINK("bad")')
    result=baseline(job,profile);result.update(candidate=profile.name,profile_hash=profile.hash)
    write_reports([{'id':job.id,'job':job.to_dict(),'assessment':result}],tmp_path)
    assert '<script>alert(1)</script>' not in (tmp_path/'index.html').read_text()
    assert "'=HYPERLINK" in (tmp_path/'jobs.csv').read_text(encoding='utf-8-sig')


def test_ai_requires_explicit_cap(capsys):
    assert main(['run','--profile',str(ROOT/'examples/demo_profile.json'),'--input',str(ROOT/'examples/jobs.json'),'--ai'])==2
    assert '--max-jobs' in capsys.readouterr().err


def test_greenhouse_and_lever_offline_contracts():
    from job_assistant.sources import parse_greenhouse,parse_lever,fetch_boards
    gh={'jobs':[{'title':'Backend Engineer','absolute_url':'https://example.com/g','content':'&lt;p&gt;Build Python APIs.&lt;/p&gt;','location':{'name':'Remote'}}]}
    rows=parse_greenhouse(gh,'fixture')
    assert rows[0]['description']=='Build Python APIs.' and rows[0]['workplace']=='remote'
    lv=[{'text':'Software Engineer','hostedUrl':'https://example.com/l','descriptionPlain':'Python role',
         'workplaceType':'remote','salaryRange':{'currency':'USD','min':100000,'max':150000,'interval':'year'}}]
    assert parse_lever(lv,'fixture')[0]['salary_period']=='year'
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps(gh).encode()
    jobs,errors=fetch_boards('greenhouse',['fixture'],['engineer'],5,opener=lambda *a,**k:Response())
    assert len(jobs)==1 and not errors
    with pytest.raises(ValueError):fetch_boards('greenhouse',['../../secrets'],[],5)


def test_dry_run_blocks_ats_network():
    args=['run','--profile',str(ROOT/'examples/demo_profile.json'),'--dry-run','--greenhouse','fixture']
    assert main(args)==2


def test_greenhouse_home_based_labels_not_assumed_worldwide():
    from job_assistant.sources import parse_greenhouse
    payload={'jobs':[{'title':'Engineer','absolute_url':'https://example.com/a','content':'Python role','location':{'name':'Home based - EMEA'}},
                     {'title':'Engineer','absolute_url':'https://example.com/b','content':'Python role','location':{'name':'Home based - Worldwide'}}]}
    rows=parse_greenhouse(payload,'test')
    assert rows[0]['workplace']=='remote' and rows[0]['eligible_countries']==[]
    assert rows[1]['workplace']=='remote' and rows[1]['eligible_countries']==['WORLDWIDE']


def test_failed_ai_assessment_stored_but_not_reused(tmp_path,job,profile):
    store=Store(tmp_path/'error.db')
    try:
        ident=store.save_job(job)
        result={'ai_status':'error','ai_score':None,'profile_hash':profile.hash}
        store.save_analysis(ident,'failed',result)
        assert store.cached(ident,'failed') is None
        store.update_status(ident,'shortlisted')
        assert store.records()[0]['applications'][profile.hash]['status']=='shortlisted'
    finally:store.close()


def test_contact_us_only_is_not_a_country_restriction(job,profile):
    result=baseline(replace(job,description='Build Python APIs. Contact us only through the careers page.'),profile)
    assert result['eligibility']!='ineligible'


def test_evaluation_metric_and_fixture():
    from evaluate import ndcg,evaluate
    assert ndcg([3,1,0],[3,1,0],3)==pytest.approx(1)
    result=evaluate(ROOT/'examples/demo_profile.json',ROOT/'examples/jobs.json',ROOT/'tests/fixtures/relevance.json')
    assert result['cases']==3 and result['ranking'][0]['label']==3
    assert result['ranking'][-1]['eligibility']=='ineligible'


def test_global_ai_budget_across_run(tmp_path,capsys):
    response=SimpleNamespace(status='completed',output_text=json.dumps({
        'score':70,'matches':[{'skill':'Python','evidence_id':'project_api','candidate_quote':'Built a Python API','job_quote':'Build Python APIs'}],
        'missing_requirements':[]}))
    fake=SimpleNamespace(responses=SimpleNamespace(create=lambda **k:response))
    def factory(model,max_calls):return Assessor(model,max_calls,client=fake)
    with patch('job_assistant.cli.Assessor',side_effect=factory):
        result=main(['run','--profile',str(ROOT/'examples/demo_profile.json'),'--input',str(ROOT/'examples/jobs.json'),
                     '--ai','--model','test-model','--max-jobs','2','--max-ai-calls','1',
                     '--db',str(tmp_path/'jobs.db'),'--output',str(tmp_path/'report')])
    assert result==0
    assert '"ai_calls": 1' in capsys.readouterr().out
    rows=json.loads((tmp_path/'report/jobs.json').read_text())
    assert {r['assessment']['ai_status'] for r in rows}=={'completed','budget_exhausted'}
