"""Optional local Ollama transport; the same evidence validator as hosted AI."""
import json
import re
from types import SimpleNamespace
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from .ai import Assessor


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError('Local model redirects are refused')


class OllamaTransport:
    def __init__(self, opener=None):
        self.opener = opener or build_opener(ProxyHandler({}), NoRedirect()).open
        self.responses = self

    def create(self, *, model, input, text, **_kwargs):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}', model) or 'cloud' in model.casefold():
            raise ValueError('Use an installed local model name, not a cloud model')
        if sum(len(m['content']) for m in input) > 12000:
            raise ValueError('Local model input exceeds 12,000 characters; use a concise CV and posting')
        payload = {'model': model, 'messages': input, 'format': text['format']['schema'],
                   'stream': False, 'think': False, 'keep_alive': '5m',
                   'options': {'temperature': 0, 'num_ctx': 16384, 'num_predict': 2000}}
        request = Request('http://127.0.0.1:11434/api/chat', data=json.dumps(payload).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        with self.opener(request, timeout=60) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError('Local response exceeds 1 MB')
        data = json.loads(raw)
        if data.get('done') is not True or data.get('done_reason') != 'stop':
            raise ValueError('Local model response was incomplete or exceeded its output limit')
        return SimpleNamespace(status='completed', output_text=data.get('message', {}).get('content', ''))


class OllamaAssessor(Assessor):
    def __init__(self, model, max_calls, opener=None):
        if not model or 'cloud' in model.casefold():
            raise ValueError('Select an installed local Ollama model')
        super().__init__(model, max_calls, client=OllamaTransport(opener))
