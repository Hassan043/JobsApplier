"""Benchmark invariants and grading tests; all data is synthetic and all runs offline."""
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
from unittest.mock import patch
import pytest
from job_assistant import benchmark as b

ROOT=Path(__file__).resolve().parent.parent
MANIFEST=ROOT/'benchmarks/jobfit_v1/manifest.json'

@pytest.fixture
def copied(tmp_path):
    root=tmp_path/'fixture'
    shutil.copytree(MANIFEST.parent,root)
    return root/'manifest.json'


def rewrite(manifest,name,objects):
    path=manifest.parent/name
    path.write_text(''.join(json.dumps(x)+'\n' for x in objects),encoding='utf-8')
    data=json.loads(manifest.read_text())
    data['hashes'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(data),encoding='utf-8')


def test_frozen_benchmark_shape_and_family_isolation():
    bundle=b.load_benchmark(MANIFEST)
    assert len(bundle['jobs'])==60 and len(bundle['profiles'])==5 and len(bundle['judgments'])==300
    dev={j['family'] for j in bundle['jobs'].values() if j['split']=='dev'}
    test={j['family'] for j in bundle['jobs'].values() if j['split']=='test'}
    assert not dev&test and len(dev|test)==30
    assert {j['split'] for j in bundle['jobs'].values()}=={'dev','test'}
    assert all(not p.name.startswith('Hassan') for p in bundle['profiles'].values())


def test_hash_change_rejected(copied):
    jobs=copied.parent/'jobs.jsonl';jobs.write_bytes(jobs.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='hash mismatch'):b.load_benchmark(copied)


def test_cross_split_family_leak_rejected_even_with_new_hash(copied):
    jobs=b.read_lines(copied.parent/'jobs.jsonl');jobs[1]['split']='test' if jobs[0]['split']=='dev' else 'dev'
    rewrite(copied,'jobs.jsonl',jobs)
    with pytest.raises(ValueError,match='Family leakage'):b.load_benchmark(copied)


def test_duplicate_job_identity_rejected(copied):
    jobs=b.read_lines(copied.parent/'jobs.jsonl');jobs[1]['url']=jobs[0]['url']+'?utm_source=duplicate'
    rewrite(copied,'jobs.jsonl',jobs)
    with pytest.raises(ValueError,match='Duplicate canonical'):b.load_benchmark(copied)


def test_missing_judgment_rejected(copied):
    labels=b.read_lines(copied.parent/'judgments.jsonl')[:-1]
    rewrite(copied,'judgments.jsonl',labels)
    with pytest.raises(ValueError,match='cover every'):b.load_benchmark(copied)


def test_duplicate_judgment_rejected(copied):
    labels=b.read_lines(copied.parent/'judgments.jsonl');labels.append(labels[0])
    rewrite(copied,'judgments.jsonl',labels)
    with pytest.raises(ValueError,match='Duplicate or unknown'):b.load_benchmark(copied)

@pytest.mark.parametrize('grade',[True,-1,4,1.5,'3'])
def test_bad_grade_rejected(copied,grade):
    labels=b.read_lines(copied.parent/'judgments.jsonl');labels[0]['relevance']=grade
    rewrite(copied,'judgments.jsonl',labels)
    with pytest.raises(ValueError,match='Invalid relevance'):b.load_benchmark(copied)


def test_path_traversal_rejected(copied):
    data=json.loads(copied.read_text());data['hashes']['../outside.json']='bad'
    copied.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='escapes'):b.load_benchmark(copied)


def test_compensation_label_nan_rejected(copied):
    labels=b.read_lines(copied.parent/'judgments.jsonl');labels[0]['expected_monthly_usd']=float('nan')
    rewrite(copied,'judgments.jsonl',labels)
    with pytest.raises(ValueError,match='finite'):b.load_benchmark(copied)


def test_metric_hand_calculated_and_unknown_not_dropped():
    result=b.ranking_metrics([3,3,1],['ineligible','unknown','eligible'],2)
    assert result['precision_at_k']==0.5 and result['recall_at_k']==1
    assert result['mrr_at_k']==0.5 and result['ineligible_at_k']==0.5
    assert result['unknown_eligibility_at_k']==0.5
    expected=(7/math.log2(3))/(7+1/math.log2(3))
    assert result['ndcg_at_k']==pytest.approx(expected)


def test_metrics_no_relevant_items_and_short_pool():
    result=b.ranking_metrics([1,0],['unknown','eligible'],5)
    assert result['ndcg_at_k']==1 and result['recall_at_k'] is None
    assert b.ranking_metrics([0,0],['unknown','eligible'],5)['ndcg_at_k'] is None
    assert result['precision_at_k']==0 and result['retrieved']==2

@pytest.mark.parametrize('k',[0,-1,True,1.5])
def test_invalid_metric_cutoff(k):
    with pytest.raises(ValueError):b.ranking_metrics([3],['eligible'],k)


def test_offline_development_evaluation_and_full_denominator():
    with patch('socket.socket',side_effect=AssertionError('Network is forbidden')):
        result=b.evaluate_benchmark(MANIFEST,'dev',5)
    assert result['jobs']==36 and result['judgments']==180
    assert result['label_origin']=='scenario_authored_provisional'
    for report in result['reports'].values():
        assert report['attempted']==180 and len(report['cases'])==180
        assert len(report['per_candidate'])==5
        assert sum(sum(c.values()) for c in report['eligibility_confusion'].values())==180
        assert report['completed']==180
    assert result['reports']['title_only']['quote_support_rate'] is None


def test_scorer_failure_is_not_silently_dropped():
    def broken(job,profile):raise RuntimeError('simulated failure')
    with patch.dict(b.SCORERS,{'keyword':broken}):
        result=b.evaluate_benchmark(MANIFEST,'dev',scorer_names=['keyword'])
    report=result['reports']['keyword']
    assert report['attempted']==180 and report['completed']==0
    assert report['failure_counts']['scorer_error']==180
    assert report['eligibility_accuracy']==0


def test_malformed_evidence_is_reported_not_executed():
    def malformed(job,profile):
        return {'score':50,'eligibility':'review_needed','matches':[{'candidate_quote':123,'job_quote':'fabricated'}],
                'compensation':{'monthly_usd_minimum':None}}
    with patch.dict(b.SCORERS,{'keyword':malformed}):
        result=b.evaluate_benchmark(MANIFEST,'dev',scorer_names=['keyword'])
    report=result['reports']['keyword']
    assert report['quote_support_rate']==0 and report['failure_counts']['invalid_quote']==180


def test_report_export_and_annotation_blinding(tmp_path):
    result=b.evaluate_benchmark(MANIFEST,'dev',scorer_names=['keyword'])
    report=b.save_result(result,tmp_path/'run')
    assert report.exists() and 'Synthetic evaluation only' in report.read_text()
    assert len((tmp_path/'run/cases.jsonl').read_text().splitlines())==180
    worksheet=b.annotation_template(MANIFEST,tmp_path/'annotations.csv')
    with worksheet.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==300
    assert all(r['relevance']==r['eligibility']==r['reviewer']==r['rationale']=='' for r in rows)
    assert all('score' not in row for row in rows)
    with pytest.raises(FileExistsError):b.annotation_template(MANIFEST,worksheet)
    with pytest.raises(ValueError,match='reviewer'):b.load_benchmark(MANIFEST,worksheet)


def test_reviewed_annotations_validate_and_disclose_provenance(tmp_path):
    bundle=b.load_benchmark(MANIFEST)
    path=b.annotation_template(MANIFEST,tmp_path/'completed.csv')
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    for row in rows:
        label=bundle['judgments'][(row['candidate_id'],row['job_id'])]
        row.update(relevance=label['relevance'],eligibility=label['eligibility'],
                   expected_monthly_usd=label['expected_monthly_usd'] if label['expected_monthly_usd'] is not None else '',
                   reviewer='test-fixture-not-a-human',rationale='Integration fixture; no real review claim.')
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    reviewed=b.load_benchmark(MANIFEST,path)
    assert reviewed['label_origin']=='reviewer_declared_not_independently_verified'
    assert reviewed['label_hash']!=bundle['label_hash']


def test_cli_validation_error_and_split_outputs(tmp_path,capsys):
    assert b.main(['evaluate','--k','0','--output',str(tmp_path/'bad')])==2
    assert not (tmp_path/'bad').exists()
    assert b.main(['validate'])==0
    assert '"judgments": 300' in capsys.readouterr().out


def test_benchmark_cannot_indirectly_read_external_cv(copied):
    data=json.loads(copied.read_text());relative=data['candidates']['dotnet']
    p=copied.parent/relative;candidate=json.loads(p.read_text());candidate['resume_path']='../../private-cv.txt'
    p.write_text(json.dumps(candidate),encoding='utf-8')
    data['hashes'][relative]=hashlib.sha256(p.read_bytes()).hexdigest();copied.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='self-contained'):b.load_benchmark(copied)


def test_deterministic_ranking_and_macro_calculation():
    first=b.evaluate_benchmark(MANIFEST,'dev',scorer_names=['keyword'])['reports']['keyword']
    second=b.evaluate_benchmark(MANIFEST,'dev',scorer_names=['keyword'])['reports']['keyword']
    assert [(r['candidate_id'],r['job_id'],r['rank'],r['score']) for r in first['cases']]==[
        (r['candidate_id'],r['job_id'],r['rank'],r['score']) for r in second['cases']]
    assert first['macro']['precision_at_k']==pytest.approx(sum(p['precision_at_k'] for p in first['per_candidate'])/5)


def test_invalid_compensation_shape_is_an_error_not_a_crash():
    def malformed(job,profile):
        return {'score':50,'eligibility':'review_needed','matches':[],'compensation':None}
    with patch.dict(b.SCORERS,{'keyword':malformed}):
        report=b.evaluate_benchmark(MANIFEST,'dev',scorer_names=['keyword'])['reports']['keyword']
    assert report['completed']==0 and report['attempted']==180


def test_unhashable_evidence_reference_is_flagged():
    def malformed(job,profile):
        return {'score':50,'eligibility':'review_needed','matches':[{'evidence_id':[],'candidate_quote':'a','job_quote':'a'}],
                'compensation':{'monthly_usd_minimum':None}}
    with patch.dict(b.SCORERS,{'keyword':malformed}):
        report=b.evaluate_benchmark(MANIFEST,'dev',scorer_names=['keyword'])['reports']['keyword']
    assert report['failure_counts']['invalid_quote']==180
