"""Local SQLite store with immutable analysis keys and explicit application state."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .models import Job

STATUSES = {"new", "shortlisted", "applied", "interview", "rejected", "withdrawn"}


class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=10)
        self.connection.row_factory = sqlite3.Row
        schema = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if schema not in (0, 1):
            self.connection.close()
            raise ValueError("Unsupported database schema; refusing migration")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
            payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new',
            notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS analyses (
            job_id TEXT NOT NULL REFERENCES jobs(id), analysis_key TEXT NOT NULL,
            result TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(job_id, analysis_key));
        CREATE TABLE IF NOT EXISTS applications (
            job_id TEXT NOT NULL REFERENCES jobs(id), profile_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new', notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
            PRIMARY KEY(job_id, profile_hash));
        CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(fingerprint);
        PRAGMA user_version = 1;
        """)
        self.connection.execute("PRAGMA foreign_keys=ON")

    def close(self):
        self.connection.close()

    def find(self, job):
        row = self.connection.execute("SELECT id FROM jobs WHERE url=? OR fingerprint=? ORDER BY CASE WHEN url=? THEN 0 ELSE 1 END LIMIT 1",
                                      (job.url, job.fingerprint, job.url)).fetchone()
        return row["id"] if row else None

    def save_job(self, job):
        # Same-content cross-source postings share one review record. Original URL remains canonical.
        existing = self.find(job)
        if existing and existing != job.id:
            return existing
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute("""INSERT INTO jobs(id,url,fingerprint,payload,updated_at) VALUES(?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET fingerprint=excluded.fingerprint,payload=excluded.payload,
                updated_at=excluded.updated_at""", (job.id, job.url, job.fingerprint, json.dumps(job.to_dict()), now))
        return job.id

    def get_job(self, job_id):
        row = self.connection.execute("SELECT payload FROM jobs WHERE id=?",(job_id,)).fetchone()
        return Job.from_dict(json.loads(row["payload"]))

    def cached(self, job_id, key):
        row = self.connection.execute("SELECT result FROM analyses WHERE job_id=? AND analysis_key=?", (job_id,key)).fetchone()
        result=json.loads(row["result"]) if row else None
        if result and result.get("ai_status") in {"error","unavailable_after_error","budget_exhausted"}:
            return None
        return result

    def save_analysis(self, job_id, key, result):
        with self.connection:
            self.connection.execute("INSERT OR REPLACE INTO analyses VALUES(?,?,?,?)",
                (job_id,key,json.dumps(result),datetime.now(timezone.utc).isoformat()))

    def update_status(self, job_id, status, notes=None, profile_hash=None):
        if status not in STATUSES:
            raise ValueError("Unknown application status")
        if not self.connection.execute("SELECT 1 FROM jobs WHERE id=?",(job_id,)).fetchone():
            raise ValueError("Unknown job ID; use the full ID shown in the report")
        hashes={json.loads(row[0])["profile_hash"] for row in self.connection.execute(
            "SELECT result FROM analyses WHERE job_id=?",(job_id,))}
        if profile_hash is None:
            if len(hashes)!=1:
                raise ValueError("Multiple or no candidate profiles; specify --candidate PROFILE_HASH from the report")
            profile_hash=next(iter(hashes))
        if profile_hash not in hashes:
            raise ValueError("Unknown candidate for this job")
        now=datetime.now(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute("""INSERT INTO applications VALUES(?,?,?,?,?)
                ON CONFLICT(job_id,profile_hash) DO UPDATE SET status=excluded.status,
                notes=CASE WHEN ? IS NULL THEN applications.notes ELSE excluded.notes END,updated_at=excluded.updated_at""",
                (job_id,profile_hash,status,notes or "",now,notes))

    def records(self):
        result=[]
        for row in self.connection.execute("SELECT * FROM jobs ORDER BY updated_at DESC"):
            record=dict(row)
            record["job"]=json.loads(record.pop("payload"))
            record["analyses"]=[json.loads(a[0]) for a in self.connection.execute(
                "SELECT result FROM analyses WHERE job_id=? ORDER BY created_at DESC",(row["id"],))]
            record["applications"]={a["profile_hash"]:{"status":a["status"],"notes":a["notes"]} for a in self.connection.execute(
                "SELECT * FROM applications WHERE job_id=?",(row["id"],))}
            result.append(record)
        return result
