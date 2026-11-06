"""Local model transport never bypasses grounded evidence checks."""
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from job_assistant.local_ai import OllamaAssessor
from job_assistant.models import Job, Profile
from job_assistant.cli import analysis_key, main

ROOT = Path(__file__).resolve().parents[1]


def response(output, **extra):
    return BytesIO(json.dumps({'message': {'content': json.dumps(output)}, 'done': True, 'done_reason': 'stop', **extra}).encode())


def test_local_transport_schema_fixed_endpoint_and_evidence():
    profile = Profile.load(ROOT/'examples/demo_profile.json')
    job = Job.from_dict(json.loads((ROOT/'examples/jobs.json').read_text())[0])
    output = {'score': 72, 'matches': [{'skill': 'Python', 'evidence_id': 'project_api', 'candidate_quote': 'Built a Python API', 'job_quote': 'Build Python APIs'}], 'missing_requirements': []}
    calls = []
    def opener(request, timeout):
        calls.append((request, timeout))
        return response(output)
    assessor = OllamaAssessor('qwen3:4b', 1, opener)
    result = assessor.assess(job, profile)
    assert result['ai_status'] == 'completed'
    assert result['ai_score'] == 72
    request, timeout = calls[0]
    assert request.full_url == 'http://127.0.0.1:11434/api/chat'
    assert timeout == 60
    data = json.loads(request.data)
    assert data['format']['type'] == 'object' and data['stream'] is False
    assert data['options']['num_predict'] == 2000
    assert assessor.assess(job, profile)['ai_status'] == 'budget_exhausted'
    assert len(calls) == 1


def test_local_fabrication_and_incomplete_generation_fail_closed():
    profile = Profile.load(ROOT/'examples/demo_profile.json')
    job = Job.from_dict(json.loads((ROOT/'examples/jobs.json').read_text())[0])
    bad = {'score': 95, 'matches': [{'skill': 'Python', 'evidence_id': 'project_api', 'candidate_quote': 'Managed 500 engineers', 'job_quote': 'Build Python APIs'}], 'missing_requirements': []}
    for output in [lambda *a, **k: response(bad), lambda *a, **k: response({}, done_reason='length')]:
        assessor = OllamaAssessor('qwen3:4b', 2, output)
        assert assessor.assess(job, profile)['ai_status'] == 'error'
        assert assessor.assess(job, profile)['ai_status'] == 'unavailable_after_error'
        assert assessor.calls == 1
    with pytest.raises(ValueError):
        OllamaAssessor('qwen3:cloud', 1)


def test_local_request_rejects_oversize_without_network():
    profile = Profile.load(ROOT/'examples/demo_profile.json')
    job = Job.from_dict({'title':'Backend Engineer','url':'https://example.com/long','description':'Python ' * 2500})
    def no_network(*args, **kwargs):
        raise AssertionError('No request should be sent')
    result = OllamaAssessor('qwen3:4b', 1, no_network).assess(job, profile)
    assert result['ai_status'] == 'error' and result['ai_error_type'] == 'ValueError'
    assert analysis_key(job,profile,'qwen3:4b') != analysis_key(job,profile,'ollama:qwen3:4b')
