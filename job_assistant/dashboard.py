"""Loopback-only review dashboard; explicit bounded collection and optional inference."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import secrets
import tempfile
import uuid

from .cli import ROOT, parser, run, sorted_records, version, example_profile
from .models import Job, Profile
from .store import Store, STATUSES

ASSETS = Path(__file__).parent / 'dashboard_assets'
MAX_BODY = 12_000_000


class Workspace:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.profiles = self.root / 'profiles'
        self.profiles.mkdir(exist_ok=True)
        self.db = self.root / 'jobs.sqlite3'

    def profile_paths(self):
        return sorted(self.profiles.glob('*.json'))

    def selected(self, ids):
        if not isinstance(ids, list) or not 1 <= len(ids) <= 20 or len(set(ids)) != len(ids):
            raise ValueError('Select 1–20 distinct CV profiles')
        available = {p.stem: p for p in self.profile_paths()}
        if any(x not in available for x in ids):
            raise ValueError('Unknown CV profile')
        return [available[x] for x in ids]

    def add_profile(self, data, cv=None, previous=None):
        if not isinstance(data, dict) or data.get('resume_path'):
            raise ValueError('Use uploaded CV text or inline evidence; resume_path must be empty')
        if previous:
            self.selected([previous])
        # Copy and validate privately before publishing a profile into the workspace.
        data = dict(data)
        data.pop('previous_profile_id', None)
        with tempfile.TemporaryDirectory(dir=self.root) as folder:
            folder = Path(folder)
            if cv:
                suffix, content = cv
                if suffix not in {'.txt', '.md', '.pdf'} or len(content) > 10_000_000:
                    raise ValueError('CV must be TXT, Markdown, or PDF, at most 10 MB')
                (folder / ('cv' + suffix)).write_bytes(content)
                data['resume_path'] = 'cv' + suffix
            path = folder / 'profile.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            profile = Profile.load(path)
            # Freeze extracted evidence: no persistent uploads or external file references.
            data['resume_path'] = ''
            data['evidence'] = [{'id': k, 'text': v} for k, v in profile.evidence.items()]
            existing = next((p for p in self.profile_paths() if Profile.load(p).hash == profile.hash), None)
            if existing:
                return existing.stem
            if previous:
                data['previous_profile_id'] = previous
            target = self.profiles / (uuid.uuid4().hex + '.json')
            with target.open('x', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return target.stem

    def options(self, options=None):
        options = options or {}
        if not isinstance(options, dict):
            raise ValueError('Invalid matching settings')
        ai = options.get('ai', False)
        maximum = options.get('max_jobs', 30)
        budget = options.get('max_ai_calls', 3)
        if type(ai) is not bool or type(maximum) is not int or not 1 <= maximum <= 100:
            raise ValueError('Job cap must be 1–100; AI opt-in must be boolean')
        if type(budget) is not int or not 1 <= budget <= 5:
            raise ValueError('AI call budget must be 1–5')
        model = options.get('model', '')
        if not isinstance(model, str) or (model and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}', model)):
            raise ValueError('Invalid model name')
        if ai and (not options.get('consent') is True or not model.strip()):
            raise ValueError('Choose a model and explicitly consent to processing selected CV/job evidence with the chosen AI provider')
        provider = options.get('provider', 'openai')
        if provider not in {'openai', 'ollama'}:
            raise ValueError('Choose OpenAI or local Ollama')
        args = ['--max-jobs', str(maximum), '--provider', provider]
        if ai:
            if maximum > 30:
                raise ValueError('AI mode supports at most 30 jobs per run')
            args += ['--ai', '--model', model.strip(), '--max-ai-calls', str(budget)]
        return args

    def execute(self, ids, source_args, options=None):
        profiles = self.selected(ids)
        settings = self.options(options)
        args = parser().parse_args(['run', '--db', str(self.db),
                                   '--output', str(self.root / 'reports')] + settings + source_args +
                                  [arg for p in profiles for arg in ('--profile', str(p))])
        output = io.StringIO()
        try:
            with redirect_stdout(output), redirect_stderr(output):
                run(args)
        except ValueError as exc:
            notes = output.getvalue().strip()
            raise ValueError(str(exc) + ('; ' + notes[:800] if notes else '')) from exc
        return json.loads(output.getvalue().splitlines()[-1])

    def import_jobs(self, ids, suffix, content, options=None):
        if suffix not in {'.json', '.jsonl', '.csv', '.html', '.htm'}:
            raise ValueError('Import JSON, JSONL, CSV, or saved JobPosting HTML')
        with tempfile.TemporaryDirectory(dir=self.root) as folder:
            path = Path(folder) / ('jobs' + suffix)
            path.write_bytes(content)
            return self.execute(ids, ['--input', str(path)], options)

    def collect(self, data):
        # Fixed providers and board tokens only: never accept arbitrary fetch URLs.
        args = []
        for provider in ('greenhouse', 'lever', 'feeds'):
            values = data.get(provider, [])
            if not isinstance(values, list) or len(values) > (2 if provider == 'feeds' else 3):
                raise ValueError('Use at most 3 boards per provider and 2 public feeds')
            if any(not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', v) for v in values):
                raise ValueError('Use board identifiers, not URLs')
            if provider == 'feeds' and any(v not in {'remotive', 'arbeitnow'} for v in values):
                raise ValueError('Unsupported public feed')
            if values:
                args += ['--' + provider] + list(dict.fromkeys(values))
        queries = data.get('queries', [])
        if not isinstance(queries, list) or len(queries) > 5 or any(not isinstance(q, str) or not q.strip() or len(q) > 100 or q.startswith('-') for q in queries):
            raise ValueError('Supply at most 5 role queries')
        if queries:
            args += ['--queries'] + queries
        if not args or not any(data.get(p) for p in ('greenhouse', 'lever', 'feeds')):
            raise ValueError('Select a public feed or employer board')
        return self.execute(data.get('profiles'), args, data.get('options'))

    def reassess(self, data):
        if not self.db.exists():
            raise ValueError('Import jobs before reassessing')
        store = Store(self.db)
        try:
            jobs = [r['job'] for r in store.records()]
        finally:
            store.close()
        return self.import_jobs(data.get('profiles'), '.json', json.dumps(jobs).encode(), data.get('options'))

    def profile_detail(self, identifier):
        path = self.selected([identifier])[0]
        return json.loads(path.read_text(encoding='utf-8'))

    def draft(self, data):
        text = data.get('text')
        if not isinstance(text, str) or len(text) > 30000:
            raise ValueError('Draft must be text, at most 30,000 characters')
        if not self.db.exists():
            raise ValueError('Import jobs first')
        store = Store(self.db)
        try:
            known = {json.loads(row[0])['profile_hash'] for row in store.connection.execute(
                'SELECT result FROM analyses WHERE job_id=?', (data.get('job_id'),))}
            if data.get('profile_hash') not in known:
                raise ValueError('Unknown job/CV pair')
            self.draft_table(store)
            with store.connection:
                cur = store.connection.execute('INSERT INTO draft_revisions(job_id,profile_hash,text,created_at) VALUES(?,?,?,?)',
                    (data['job_id'], data['profile_hash'], text, datetime.now(timezone.utc).isoformat()))
            return {'revision': cur.lastrowid}
        finally:
            store.close()

    @staticmethod
    def draft_table(store):
        store.connection.execute('CREATE TABLE IF NOT EXISTS draft_revisions (revision INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, profile_hash TEXT NOT NULL, text TEXT NOT NULL, created_at TEXT NOT NULL)')

    def demo(self):
        data = json.loads((ROOT / 'examples/demo_profile.json').read_text(encoding='utf-8'))
        identifier = self.add_profile(data)
        return self.import_jobs([identifier], '.json', (ROOT / 'examples/jobs.json').read_bytes())

    def state(self):
        profiles = []
        for path in self.profile_paths():
            p = Profile.load(path)
            profiles.append({'id': path.stem, 'name': p.name, 'label': p.label, 'hash': p.hash,
                             'roles': p.target_roles})
        superseded = {self.profile_detail(p['id']).get('previous_profile_id') for p in profiles}
        for profile in profiles:
            profile['archived'] = profile['id'] in superseded
        records = []
        if self.db.exists():
            store = Store(self.db)
            try:
                self.draft_table(store)
                drafts = {(r['job_id'], r['profile_hash']): dict(r) for r in store.connection.execute('SELECT * FROM draft_revisions ORDER BY revision')}
                for row in store.records():
                    current = version(Job.from_dict(row['job']))
                    latest = {}
                    for result in row['analyses']:
                        if result['job_version'] == current:
                            latest.setdefault(result['profile_hash'], result)
                    for result in latest.values():
                        records.append({'id': row['id'], 'job': row['job'], 'assessment': result, 'draft': drafts.get((row['id'], result['profile_hash'])),
                                        **row['applications'].get(result['profile_hash'], {'status': 'new', 'notes': ''})})
            finally:
                store.close()
        return {'profiles': profiles, 'records': sorted_records(records), 'statuses': sorted(STATUSES), 'ai_configured': bool(os.environ.get('OPENAI_API_KEY')), 'default_model': os.environ.get('OPENAI_MODEL', '')}

    def status(self, data):
        notes = data.get('notes', '')
        if not isinstance(notes, str) or len(notes) > 10000:
            raise ValueError('Notes must be text, at most 10,000 characters')
        if not self.db.exists():
            raise ValueError('Import jobs first')
        store = Store(self.db)
        try:
            store.update_status(data['job_id'], data['status'], notes, data['profile_hash'])
        finally:
            store.close()


def make_server(workspace, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(20)

        def log_message(self, *_args):
            pass  # Avoid private job/profile values in access logs.

        def trusted(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def respond(self, status, body, mime='application/json'):
            if mime == 'application/json':
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.trusted():
                return self.respond(403, {'error': 'Untrusted host'})
            try:
                if self.path == '/api/state':
                    return self.respond(200, workspace.state())
                if self.path == '/api/template':
                    data = example_profile()
                    data['name'] = 'Your name'
                    return self.respond(200, data)
                paths = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
                if self.path not in paths:
                    return self.respond(404, {'error': 'Not found'})
                name, mime = paths[self.path]
                body = (ASSETS / name).read_bytes().replace(b'__TOKEN__', token.encode())
                return self.respond(200, body, mime)
            except (ValueError, OSError):
                return self.respond(400, {'error': 'Unable to read dashboard data'})

        def do_POST(self):
            origins = {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}
            if not self.trusted() or self.headers.get('Origin') not in origins or not secrets.compare_digest(self.headers.get('X-Dashboard-Token', ''), token):
                return self.respond(403, {'error': 'Request rejected; reload the dashboard'})
            try:
                if self.headers.get('Transfer-Encoding'):
                    raise ValueError('Streaming uploads are not supported')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY:
                    return self.respond(413, {'error': 'Upload exceeds 12 MB or is empty'})
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError('Incomplete upload')
                if self.path in {'/api/profile', '/api/import'}:
                    ct = self.headers.get('Content-Type', '')
                    if not ct.startswith('multipart/form-data;'):
                        raise ValueError('Expected a file upload')
                    message = BytesParser(policy=default).parsebytes(b'Content-Type: ' + ct.encode() + b'\r\nMIME-Version: 1.0\r\n\r\n' + body)
                    fields, files = {}, {}
                    for part in message.iter_parts():
                        key = part.get_param('name', header='content-disposition')
                        content = part.get_payload(decode=True)
                        if not key or content is None or key in fields or key in files:
                            raise ValueError('Invalid or duplicate upload field')
                        if part.get_filename():
                            files[key] = (Path(part.get_filename()).suffix.lower(), content)
                        else:
                            fields[key] = content.decode('utf-8')
                    if self.path == '/api/profile':
                        result = {'id': workspace.add_profile(json.loads(fields['profile']), files.get('cv'), fields.get('previous') or None)}
                    else:
                        suffix, content = files['jobs']
                        result = workspace.import_jobs(json.loads(fields['profiles']), suffix, content, json.loads(fields.get('options', '{}')))
                elif self.path == '/api/collect':
                    result = workspace.collect(json.loads(body))
                elif self.path == '/api/reassess':
                    result = workspace.reassess(json.loads(body))
                elif self.path == '/api/profile-detail':
                    result = workspace.profile_detail(json.loads(body)['id'])
                elif self.path == '/api/draft':
                    result = workspace.draft(json.loads(body))
                elif self.path == '/api/demo':
                    result = workspace.demo()
                elif self.path == '/api/status':
                    workspace.status(json.loads(body))
                    result = {'saved': True}
                else:
                    return self.respond(404, {'error': 'Not found'})
                return self.respond(200, result)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                return self.respond(400, {'error': str(exc)[:400]})
            except Exception:
                return self.respond(500, {'error': 'Operation failed; check the input and optional PDF dependency'})

    return HTTPServer(('127.0.0.1', port), Handler)


def main(argv=None):
    p = argparse.ArgumentParser(description='Private local JobsApplier dashboard')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--workspace', type=Path, default=ROOT / 'data/dashboard')
    args = p.parse_args(argv)
    server = make_server(Workspace(args.workspace), args.port)
    print(f'JobsApplier dashboard: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
