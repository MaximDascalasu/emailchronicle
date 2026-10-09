"""SQLite persistence and read-only ingestion of original evidence."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sqlite3
import uuid

from .parser import parse_eml

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS investigations (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources (
 id INTEGER PRIMARY KEY, investigation_id INTEGER NOT NULL REFERENCES investigations(id),
 original_path TEXT NOT NULL, stored_path TEXT NOT NULL, sha256 TEXT NOT NULL,
 size_bytes INTEGER NOT NULL, imported_at TEXT NOT NULL,
 UNIQUE(investigation_id, sha256));
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(id),
 sender TEXT, recipients TEXT, subject TEXT, raw_date TEXT, date_utc TEXT,
 body TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('original','quoted')),
 locator TEXT NOT NULL, message_id TEXT, flags TEXT NOT NULL, fingerprint TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS messages_date ON messages(date_utc);
CREATE INDEX IF NOT EXISTS messages_fingerprint ON messages(fingerprint);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, investigation_id INTEGER REFERENCES investigations(id),
 time_utc TEXT NOT NULL, action TEXT NOT NULL, details TEXT NOT NULL);
PRAGMA user_version=1;
"""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.evidence = self.directory / "evidence"
        self.evidence.mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.directory / "chronicle.sqlite3")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()

    def audit(self, investigation, action, details):
        self.db.execute("INSERT INTO audit(investigation_id,time_utc,action,details) VALUES(?,?,?,?)",
                        (investigation, now(), action, json.dumps(details)))

    def create_investigation(self, name):
        if not name.strip():
            raise ValueError("Investigation name is required")
        with self.db:
            cur = self.db.execute("INSERT INTO investigations(name,created_at) VALUES(?,?)", (name.strip(), now()))
            self.audit(cur.lastrowid, "create_investigation", {"name": name.strip()})
        return cur.lastrowid

    def investigations(self):
        return self.db.execute("SELECT * FROM investigations ORDER BY id").fetchall()

    def import_eml(self, investigation, path):
        path = Path(path).resolve()
        if path.suffix.lower() != ".eml":
            raise ValueError("This release imports EML only")
        if not self.db.execute("SELECT 1 FROM investigations WHERE id=?", (investigation,)).fetchone():
            raise ValueError("Unknown investigation")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        existing = self.db.execute("SELECT id FROM sources WHERE investigation_id=? AND sha256=?",
                                   (investigation, digest)).fetchone()
        if existing:
            with self.db:
                self.audit(investigation, "duplicate_file_skipped", {"path": str(path), "sha256": digest, "source_id": existing[0]})
            return 0
        messages = parse_eml(data)
        # Unique managed copy: never write to the submitted original, including on reimport.
        folder = self.evidence / str(investigation)
        folder.mkdir(exist_ok=True)
        copy = folder / (uuid.uuid4().hex + ".eml")
        try:
            with copy.open("xb") as stream:
                stream.write(data)
            with self.db:
                source = self.db.execute(
                    "INSERT INTO sources(investigation_id,original_path,stored_path,sha256,size_bytes,imported_at) VALUES(?,?,?,?,?,?)",
                    (investigation, str(path), str(copy), digest, len(data), now())).lastrowid
                for msg in messages:
                    self.db.execute("""INSERT INTO messages(source_id,sender,recipients,subject,raw_date,date_utc,
                        body,kind,locator,message_id,flags,fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (source, msg.sender, msg.recipients, msg.subject, msg.raw_date, msg.date_utc, msg.body,
                         msg.kind, msg.locator, msg.message_id, json.dumps(msg.flags), msg.fingerprint))
                self.audit(investigation, "import_eml", {"source_id": source, "sha256": digest, "messages": len(messages)})
        except Exception:
            copy.unlink(missing_ok=True)
            raise
        return len(messages)

    def timeline(self, investigation, sender="", keyword="", date_from="", date_to=""):
        # Undated messages always remain visible for review, even with date filters.
        rows = self.db.execute("""SELECT m.*, s.original_path, s.stored_path, s.sha256,
            (SELECT COUNT(*) FROM messages d JOIN sources ds ON ds.id=d.source_id
             WHERE ds.investigation_id=s.investigation_id AND d.id<>m.id AND
             (d.fingerprint=m.fingerprint OR (m.message_id IS NOT NULL AND d.message_id=m.message_id))) AS duplicate_count
            FROM messages m JOIN sources s ON s.id=m.source_id
            WHERE s.investigation_id=? ORDER BY m.date_utc IS NULL, m.date_utc, m.id""", (investigation,)).fetchall()
        return [r for r in rows if sender.casefold() in (r["sender"] or "").casefold()
                and keyword.casefold() in ((r["subject"] or "") + "\n" + r["body"]).casefold()
                and (not r["date_utc"] or ((not date_from or r["date_utc"][:10] >= date_from)
                     and (not date_to or r["date_utc"][:10] <= date_to)))]

    def verified_source(self, message_id):
        row = self.db.execute("""SELECT s.* FROM sources s JOIN messages m ON m.source_id=s.id
                                 WHERE m.id=?""", (message_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown message")
        path = Path(row["stored_path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            with self.db:
                self.audit(row["investigation_id"], "integrity_check_failed", {"source_id": row["id"]})
            raise ValueError("Evidence copy hash mismatch; opening blocked")
        with self.db:
            self.audit(row["investigation_id"], "open_source", {"source_id": row["id"]})
        return path
