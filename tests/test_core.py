from pathlib import Path
import hashlib
import json

import pytest

from emailchronicle.parser import parse_date, parse_eml
from emailchronicle.store import Store

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


@pytest.fixture
def store(tmp_path):
    db = Store(tmp_path / "workspace")
    yield db
    db.close()


def test_out_of_order_chain_and_timezones(store):
    case = store.create_investigation("Synthetic case")
    store.import_eml(case, SAMPLES / "03-followup.eml")
    store.import_eml(case, SAMPLES / "01-initial.eml")
    rows = store.timeline(case)
    assert [r["date_utc"] for r in rows] == ["2026-07-07T10:30:00+00:00", "2026-07-07T10:30:00+00:00", "2026-07-07T11:00:00+00:00"]
    quoted = next(r for r in rows if r["kind"] == "quoted")
    assert "quoted_headers_unverified" in json.loads(quoted["flags"])
    assert quoted["locator"].startswith("Decoded body lines")
    assert quoted["duplicate_count"] == 1


@pytest.mark.parametrize("raw,flag", [(None, "missing_date"), ("nonsense", "unparsed_date"),
    ("Tue, 07 Jul 2026 09:00:00", "ambiguous_timezone"),
    ("Tue, 07 Jul 2026 09:00:00 -0000", "ambiguous_timezone")])
def test_uncertain_dates(raw, flag):
    assert parse_date(raw) == (None, [flag])


def test_missing_date_sorted_last_and_not_invented(store):
    case = store.create_investigation("Case")
    store.import_eml(case, SAMPLES / "04-undated.eml")
    store.import_eml(case, SAMPLES / "01-initial.eml")
    rows = store.timeline(case)
    assert rows[-1]["date_utc"] is None
    assert rows[-1]["raw_date"] is None
    assert "missing_date" in rows[-1]["flags"]
    assert len(store.timeline(case, date_from="2027-01-01")) == 1


def test_duplicates_preservation_and_case_isolation(store, tmp_path):
    a, b = store.create_investigation("A"), store.create_investigation("B")
    original = tmp_path / "original.eml"
    data = (SAMPLES / "01-initial.eml").read_bytes()
    original.write_bytes(data)
    assert store.import_eml(a, original) == 1
    assert store.import_eml(a, original) == 0
    store.import_eml(a, SAMPLES / "02-same-message.eml")
    assert all(r["duplicate_count"] == 1 for r in store.timeline(a))
    assert not store.timeline(b)
    assert store.import_eml(b, original) == 1
    assert store.timeline(b)[0]["duplicate_count"] == 0
    assert original.read_bytes() == data
    row = store.timeline(a)[0]
    original.unlink()
    assert store.verified_source(row["id"]).read_bytes() == data
    assert row["sha256"] == hashlib.sha256(data).hexdigest()
    Path(row["stored_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        store.verified_source(row["id"])
    actions = [r[0] for r in store.db.execute("SELECT action FROM audit")]
    assert "duplicate_file_skipped" in actions
    assert "integrity_check_failed" in actions


def test_filters(store):
    case = store.create_investigation("Case")
    store.import_eml(case, SAMPLES / "03-followup.eml")
    assert len(store.timeline(case, sender="BOB", keyword="synthetic")) == 1
    assert not store.timeline(case, keyword="absent")
    assert len(store.timeline(case, date_to="2026-07-06")) == 0


def test_missing_sender_html_and_quoted_prefix():
    parsed = parse_eml(b"Subject: example\nContent-Type: text/html\n\n<p>Hello</p><script>hidden</script>")
    assert parsed[0].sender is None
    assert "missing_sender" in parsed[0].flags
    assert parsed[0].body == "Hello"
    parsed = parse_eml(b"From: a@example.test\n\nIntro\n> From: b@example.test\n> Date: Tue, 07 Jul 2026 10:00:00 +0000\n> Subject: Earlier\n>\n> Body")
    assert len(parsed) == 2
    assert parsed[1].kind == "quoted"
    assert parsed[1].sender == "b@example.test"


def test_unrecognized_file_and_invalid_case_leave_no_copy(store):
    case = store.create_investigation("Case")
    with pytest.raises(ValueError, match="EML and MSG"):
        store.import_eml(case, "not.pdf")
    with pytest.raises(ValueError, match="Unknown investigation"):
        store.import_eml(999, SAMPLES / "01-initial.eml")
    assert not list(store.evidence.rglob("*.eml"))


def test_persistence(tmp_path):
    store = Store(tmp_path)
    case = store.create_investigation("Persisted")
    store.import_eml(case, SAMPLES / "01-initial.eml")
    store.close()
    reopened = Store(tmp_path)
    assert len(reopened.timeline(case)) == 1
    assert reopened.investigations()[0]["name"] == "Persisted"
    reopened.close()
