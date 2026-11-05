"""Portal inventory and public feed contracts; no external account or network access."""
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import pytest
from job_assistant.portals import portal_catalog,select_portals
from job_assistant.public_feeds import parse_remotive,parse_arbeitnow,fetch_public_feed
from job_assistant.models import Job,Profile
from job_assistant.report import write_reports
from job_assistant.scoring import baseline
from job_assistant.cli import main

ROOT=Path(__file__).resolve().parent.parent


def remotive_payload():
    return {'jobs':[{'title':'Backend Engineer','company_name':'Fictional Team',
        'url':'https://remotive.com/remote-jobs/software-dev/fixture?ref=source',
        'description':'<p>Python services.</p>','candidate_required_location':'Worldwide','salary':'$40,000 - $50,000'}]}

class Response:
    def __init__(self,payload):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,*args):return json.dumps(self.payload).encode()


def test_catalog_covers_user_groups_without_false_native_support():
    rows=portal_catalog()
    assert len(rows)>140 and len({r['id'] for r in rows})==len(rows)
    names={r['name'] for r in rows}
    assert {'LinkedIn','Upwork','micro1','Toptal','Himalayas','Remotive','EURES','Arbeitnow','Rozee.pk',
            'Trade Me Jobs','104 Job Bank','Jadarat','Monaco Economic Board','ANPAL'}.issubset(names)
    assert next(r for r in rows if r['name']=='Himalayas')['status']=='documented_not_implemented'
    assert next(r for r in rows if r['name']=='LinkedIn')['status']=='manual_only'
    assert next(r for r in rows if r['name']=='Google')['status']=='discovery_only'
    assert next(r for r in rows if r['name']=='Immigration NZ')['status']=='reference_only'


def test_country_filter_and_deduplicated_shared_board():
    us=select_portals(country='US')
    assert any(r['name']=='Dice' and 'accounts' in r['groups'] and 'country_boards' in r['groups'] for r in us)
    assert len([r for r in portal_catalog() if r['name']=='Dice'])==1
    with pytest.raises(ValueError):select_portals(group='not_a_group')


def test_catalog_cli_is_offline(capsys):
    with patch('socket.socket',side_effect=AssertionError('No network')):
        assert main(['portals','--country','NZ','--json'])==0
    assert 'Trade Me Jobs' in capsys.readouterr().out


def test_remotive_preserves_attribution_without_inventing_salary_or_country():
    rows=parse_remotive(remotive_payload());job=Job.from_dict(rows[0])
    assert job.source=='Remotive' and job.source_url.endswith('?ref=source')
    assert '?ref=' not in job.url and job.eligible_countries==['WORLDWIDE']
    assert job.currency=='' and job.salary_period=='' and job.salary_min is None
    payload=remotive_payload();payload['jobs'][0]['candidate_required_location']='United States'
    assert parse_remotive(payload)[0]['eligible_countries']==[]


def test_arbeitnow_remote_is_not_worldwide():
    payload={'data':[{'title':'Engineer','company_name':'Fixture','url':'https://example.com/job',
                     'description':'<p>Python</p>','remote':True,'location':'Berlin'}]}
    rows=parse_arbeitnow(payload)
    assert rows[0]['workplace']=='remote' and rows[0]['eligible_countries']==[]
    payload['data'][0]['remote']=False
    assert parse_arbeitnow(payload)[0]['workplace']=='unknown'

@pytest.mark.parametrize('parser',[parse_remotive,parse_arbeitnow])
def test_schema_changes_are_errors(parser):
    with pytest.raises(ValueError):parser({'unexpected':[]})


def test_refresh_cache_caps_requests_and_filters_locally(tmp_path):
    calls=[]
    def opener(*args,**kwargs):calls.append(args[0].full_url);return Response(remotive_payload())
    jobs,notes=fetch_public_feed('remotive',['engineer'],10,tmp_path,opener,clock=lambda:100000)
    assert len(jobs)==1 and any('24 hours' in note for note in notes)
    second,_=fetch_public_feed('remotive',['unrelated'],10,tmp_path,opener,clock=lambda:100100)
    assert not second and len(calls)==1
    fetch_public_feed('remotive',['engineer'],10,tmp_path,opener,clock=lambda:130000)
    assert len(calls)==2


def test_failed_request_cooldown_prevents_repeat_network(tmp_path):
    calls=[]
    def opener(*args,**kwargs):calls.append(1);raise TimeoutError()
    first,notes=fetch_public_feed('remotive',[],10,tmp_path,opener,clock=lambda:100000)
    assert not first and any('unavailable' in n for n in notes)
    second,notes=fetch_public_feed('remotive',[],10,tmp_path,opener,clock=lambda:100100)
    assert not second and len(calls)==1 and any('cooldown' in n for n in notes)
    assert not (tmp_path/'remotive.lock').exists()


def test_active_lock_avoids_concurrent_refresh(tmp_path):
    (tmp_path/'remotive.lock').write_text('test')
    def opener(*a,**k):raise AssertionError('Must not request')
    jobs,notes=fetch_public_feed('remotive',[],10,tmp_path,opener)
    assert not jobs and any('lock' in n for n in notes)


def test_bad_cache_fails_without_network(tmp_path):
    (tmp_path/'remotive.json').write_text('{bad json')
    def opener(*a,**k):raise AssertionError('Must not request')
    jobs,notes=fetch_public_feed('remotive',[],10,tmp_path,opener)
    assert not jobs and any('unavailable' in n for n in notes)


def test_feed_dry_run_blocked_before_network():
    args=['run','--profile',str(ROOT/'examples/demo_profile.json'),'--feeds','remotive','--dry-run']
    assert main(args)==2


def test_attribution_link_visible_and_source_url_validated(tmp_path):
    job=Job.from_dict(parse_remotive(remotive_payload())[0])
    profile=Profile.load(ROOT/'examples/demo_profile.json')
    result=baseline(job,profile);result.update(candidate=profile.name,profile_hash=profile.hash)
    write_reports([{'id':job.id,'job':job.to_dict(),'assessment':result}],tmp_path)
    text=(tmp_path/'index.html').read_text()
    assert 'href="https://remotive.com/remote-jobs/software-dev/fixture?ref=source"' in text
    assert '>Remotive</a>' in text
    data=job.to_dict();data['source_url']='javascript:alert(1)'
    with pytest.raises(ValueError):Job.from_dict(data)


def test_source_attribution_not_part_of_duplicate_content_identity():
    job=Job.from_dict(parse_remotive(remotive_payload())[0])
    assert replace(job,source_url='https://example.com/another-source').fingerprint==job.fingerprint
