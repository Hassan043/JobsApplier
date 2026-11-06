"""End-to-end dashboard workflow and loopback request boundaries."""
import http.client
import json
from pathlib import Path
import re
import threading

import pytest
from job_assistant.dashboard import Workspace, make_server, ROOT


def multipart(fields, files=None):
    boundary = 'dashboard-test-boundary'
    chunks = []
    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    for key, (name, content) in (files or {}).items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + content + b'\r\n')
    return b''.join(chunks) + f'--{boundary}--\r\n'.encode(), f'multipart/form-data; boundary={boundary}'


@pytest.fixture
def client(tmp_path):
    workspace = Workspace(tmp_path / 'workspace')
    server = make_server(workspace, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_port
    def call(method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        content = response.read()
        result = (response.status, dict(response.getheaders()), content)
        conn.close()
        return result
    status, _, html = call('GET', '/')
    assert status == 200
    token = re.search(rb'name="dashboard-token" content="([^"]+)"', html)[1].decode()
    auth = {'Origin': f'http://127.0.0.1:{port}', 'X-Dashboard-Token': token, 'Content-Type': 'application/json'}
    yield call, auth, workspace
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_demo_track_and_reload(client):
    call, auth, _ = client
    status, _, payload = call('POST', '/api/demo', b'{}', auth)
    assert status == 200, payload
    assert json.loads(payload)['unique_jobs'] == 3
    data = json.loads(call('GET', '/api/state')[2])
    assert len(data['records']) == 3
    record = data['records'][0]
    update = {'job_id': record['id'], 'profile_hash': record['assessment']['profile_hash'], 'status': 'shortlisted', 'notes': 'Follow up Friday'}
    assert call('POST', '/api/status', json.dumps(update), auth)[0] == 200
    state = json.loads(call('GET', '/api/state')[2])
    saved = next(r for r in state['records'] if r['id'] == record['id'])
    assert saved['status'] == 'shortlisted'
    assert saved['notes'] == 'Follow up Friday'
    assert call('POST', '/api/demo', b'{}', auth)[0] == 200
    assert len(json.loads(call('GET', '/api/state')[2])['profiles']) == 1


def test_upload_cv_match_multiple_profiles_and_isolate_status(client):
    call, auth, _ = client
    ids = []
    for name in ['First Candidate', 'Second Candidate']:
        profile = json.loads((ROOT / 'examples/demo_profile.json').read_text())
        profile.update(name=name, evidence=[])
        body, ct = multipart({'profile': json.dumps(profile)}, {'cv': ('cv.txt', b'Built Python APIs with SQL and Docker.')})
        status, _, result = call('POST', '/api/profile', body, {**auth, 'Content-Type': ct})
        assert status == 200, result
        ids.append(json.loads(result)['id'])
    body, ct = multipart({'profiles': json.dumps(ids)}, {'jobs': ('jobs.json', (ROOT / 'examples/jobs.json').read_bytes())})
    status, _, payload = call('POST', '/api/import', body, {**auth, 'Content-Type': ct})
    assert status == 200, payload
    state = json.loads(call('GET', '/api/state')[2])
    assert len(state['records']) == 6
    first = state['records'][0]
    status, _, _ = call('POST', '/api/status', json.dumps({'job_id': first['id'], 'profile_hash': first['assessment']['profile_hash'], 'status': 'applied', 'notes': 'Manual application'}), auth)
    assert status == 200
    records = json.loads(call('GET', '/api/state')[2])['records']
    assert sum(r['status'] == 'applied' for r in records) == 1
    assert len([r for r in records if r['id'] == first['id']]) == 2


def test_request_boundaries_and_no_arbitrary_files(client):
    call, auth, _ = client
    assert call('POST', '/api/demo', b'{}')[0] == 403
    assert call('POST', '/api/demo', b'{}', {**auth, 'Origin': 'https://evil.example'})[0] == 403
    assert call('POST', '/api/demo', b'{}', {**auth, 'X-Dashboard-Token': 'bad'})[0] == 403
    assert call('GET', '/api/state', headers={'Host': 'evil.example'})[0] == 403
    assert call('GET', '/../../config.py')[0] == 404
    assert call('GET', '/data/jobs.sqlite3')[0] == 404
    status, headers, html = call('GET', '/')
    assert status == 200 and b'__TOKEN__' not in html
    assert headers['Cache-Control'] == 'no-store'
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    assert call('POST', '/api/demo', b'', {**auth, 'Content-Length': '12000001'})[0] == 413


def test_bad_inputs_do_not_create_profiles(client):
    call, auth, workspace = client
    for profile in [{'resume_path': '../../secret.txt'}, {'name': 'Empty', 'evidence': []}]:
        body, ct = multipart({'profile': json.dumps(profile)})
        assert call('POST', '/api/profile', body, {**auth, 'Content-Type': ct})[0] == 400
    assert workspace.profile_paths() == []
    assert call('POST', '/api/status', b'not-json', auth)[0] == 400


def test_upload_names_cannot_escape_workspace(client, tmp_path):
    call, auth, workspace = client
    data = json.loads((ROOT / 'examples/demo_profile.json').read_text())
    data['evidence'] = []
    body, ct = multipart({'profile': json.dumps(data)}, {'cv': ('../../outside.txt', b'Python and SQL development')})
    assert call('POST', '/api/profile', body, {**auth, 'Content-Type': ct})[0] == 200
    assert not (workspace.root.parent / 'outside.txt').exists()
    stored = json.loads(workspace.profile_paths()[0].read_text())
    assert stored['resume_path'] == '' and stored['evidence']


def test_static_assets_and_broken_job_file(client):
    call, auth, _ = client
    for path, mime in [('/app.js', 'text/javascript'), ('/style.css', 'text/css')]:
        status, headers, content = call('GET', path)
        assert status == 200 and headers['Content-Type'].startswith(mime) and content
    call('POST', '/api/demo', b'{}', auth)
    profile = json.loads(call('GET', '/api/state')[2])['profiles'][0]['id']
    body, ct = multipart({'profiles': json.dumps([profile])}, {'jobs': ('bad.json', b'{bad')})
    assert call('POST', '/api/import', body, {**auth, 'Content-Type': ct})[0] == 400
    assert len(json.loads(call('GET', '/api/state')[2])['records']) == 3


def test_draft_revisions_survive_reload_and_are_isolated(client):
    call, auth, workspace = client
    call('POST', '/api/demo', b'{}', auth)
    records = json.loads(call('GET', '/api/state')[2])['records']
    record = records[0]
    data = {'job_id': record['id'], 'profile_hash': record['assessment']['profile_hash'], 'text': 'First verified draft'}
    assert call('POST', '/api/draft', json.dumps(data), auth)[0] == 200
    data['text'] = 'Revised verified draft'
    assert call('POST', '/api/draft', json.dumps(data), auth)[0] == 200
    reloaded = Workspace(workspace.root).state()['records']
    saved = next(r for r in reloaded if r['id'] == record['id'])
    assert saved['draft']['text'] == 'Revised verified draft'
    assert all(r['draft'] is None for r in reloaded if r['id'] != record['id'])
    from job_assistant.store import Store
    store = Store(workspace.db)
    try:
        assert store.connection.execute('SELECT COUNT(*) FROM draft_revisions').fetchone()[0] == 2
    finally:
        store.close()
    data['profile_hash'] = 'unknown'
    assert call('POST', '/api/draft', json.dumps(data), auth)[0] == 400


def test_profile_edit_creates_revision_preserving_old_profile_and_tracking(client):
    call, auth, workspace = client
    call('POST', '/api/demo', b'{}', auth)
    old = workspace.state()['profiles'][0]
    detail = json.loads(call('POST', '/api/profile-detail', json.dumps({'id': old['id']}), auth)[2])
    detail['profile_label'] = 'Updated target preferences'
    detail['target_monthly_usd'] = 2500
    body, ct = multipart({'profile': json.dumps(detail), 'previous': old['id']})
    status, _, payload = call('POST', '/api/profile', body, {**auth, 'Content-Type': ct})
    assert status == 200, payload
    assert len(workspace.profile_paths()) == 2
    state = workspace.state()
    assert next(p for p in state['profiles'] if p['id'] == old['id'])['archived']
    assert len(state['records']) == 3  # Earlier assessments remain available.
    assert len([p for p in state['profiles'] if not p['archived']]) == 1
    assert workspace.profile_detail(old['id'])['target_monthly_usd'] == 2000


def test_ai_requires_consent_model_and_bounded_budget(client):
    call, auth, workspace = client
    call('POST', '/api/demo', b'{}', auth)
    identifier = workspace.state()['profiles'][0]['id']
    for options in [
        {'ai': True, 'model': 'test-model'},
        {'ai': True, 'consent': True, 'model': ''},
        {'ai': True, 'consent': True, 'model': 'test-model', 'max_jobs': 31},
        {'max_ai_calls': 6}, {'max_jobs': 101}, {'model': '--invalid'}, {'ai': 'true'},
    ]:
        status, _, _ = call('POST', '/api/reassess', json.dumps({'profiles': [identifier], 'options': options}), auth)
        assert status == 400


def test_dashboard_ai_grounding_and_global_budget(client):
    from types import SimpleNamespace
    from unittest.mock import patch
    from job_assistant.ai import Assessor
    call, auth, workspace = client
    call('POST', '/api/demo', b'{}', auth)
    profile = workspace.state()['profiles'][0]['id']
    output = {'score': 70, 'matches': [{'skill': 'Python', 'evidence_id': 'project_api',
              'candidate_quote': 'Built a Python API', 'job_quote': 'Build Python APIs'}], 'missing_requirements': []}
    fake = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(status='completed', output_text=json.dumps(output))))
    with patch('job_assistant.cli.Assessor', side_effect=lambda model, budget: Assessor(model, budget, client=fake)):
        status, _, payload = call('POST', '/api/reassess', json.dumps({'profiles': [profile], 'options': {
            'ai': True, 'consent': True, 'model': 'fixture-model', 'max_jobs': 2, 'max_ai_calls': 1}}), auth)
    assert status == 200, payload
    assert json.loads(payload)['ai_calls'] == 1
    records = workspace.state()['records']
    completed = [r for r in records if r['assessment']['ai_status'] == 'completed']
    assert len(completed) == 1
    assert completed[0]['assessment']['ai_score'] == 70
    assert completed[0]['assessment']['ai_matches'][0]['candidate_quote'] == 'Built a Python API'
    assert any(r['assessment']['ai_status'] == 'budget_exhausted' for r in records)


def test_collect_uses_fixed_providers_and_surfaces_warnings(client):
    from unittest.mock import patch
    from job_assistant.models import Job
    call, auth, workspace = client
    call('POST', '/api/demo', b'{}', auth)
    profile = workspace.state()['profiles'][0]['id']
    job = Job.from_dict({'title': 'Backend Engineer', 'company': 'Fixture employer',
                        'url': 'https://example.org/fixture', 'description': 'Build Python APIs', 'source': 'fixture'})
    payload = {'profiles': [profile], 'greenhouse': ['fixtureboard'], 'feeds': ['remotive'], 'queries': ['backend']}
    with patch('job_assistant.cli.fetch_boards', return_value=([job], [])) as board, patch('job_assistant.cli.fetch_public_feed', return_value=([], ['Fixture feed unavailable'])) as feed:
        status, _, raw = call('POST', '/api/collect', json.dumps(payload), auth)
    assert status == 200, raw
    assert board.call_args.args[0:2] == ('greenhouse', ['fixtureboard'])
    assert feed.call_args.args[0] == 'remotive'
    assert json.loads(raw)['source_warnings'] == ['Fixture feed unavailable']
    for bad in [{'feeds':['unknown']}, {'greenhouse':['https://evil.example']}, {'lever':['--bad']}, {'greenhouse':['a','b','c','d']}, {'queries':['--bad'], 'feeds':['remotive']}]:
        assert call('POST', '/api/collect', json.dumps({'profiles':[profile], **bad}), auth)[0] == 400
