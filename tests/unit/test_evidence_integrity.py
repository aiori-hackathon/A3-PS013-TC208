import pytest
from app.services.integrity_service import compute_sha256_bytes, verify_evidence_file
from app.services.evidence_service import collect_evidence_file, sanitize_filename

def test_compute_sha256_bytes():
    data = b"Oct 27 10:30:01 host01 sshd[1234]: Failed password for admin\n"
    # Stable digest computation
    digest1 = compute_sha256_bytes(data)
    digest2 = compute_sha256_bytes(data)
    assert digest1 == digest2
    assert len(digest1) == 64
    assert digest1.islower()

def test_sanitize_filename_prevents_traversal():
    bad_name = "../../../etc/passwd"
    safe = sanitize_filename(bad_name)
    assert ".." not in safe
    assert "/" not in safe
    assert "\\" not in safe
    assert safe == "passwd"

    shell_name = "evidence; rm -rf /; .log"
    safe_shell = sanitize_filename(shell_name)
    assert ";" not in safe_shell
    assert " " not in safe_shell

def test_collect_evidence_and_verify_match(db_session):
    data = b"Sample raw evidence bytes\n"
    ev = collect_evidence_file(
        db=db_session,
        filename="test_auth.log",
        file_bytes=data,
        scenario_tag="test"
    )
    assert ev.evidence_id.startswith("EV-")
    assert ev.file_size_bytes == len(data)
    assert ev.sha256_baseline == compute_sha256_bytes(data)

    # Initial verification should be MATCH
    ver = verify_evidence_file(db_session, ev.evidence_id)
    assert ver.result == "MATCH"
    assert ver.observed_hash == ev.sha256_baseline

def test_duplicate_filename_preserves_unique_storage(db_session):
    data1 = b"Evidence stream 1\n"
    data2 = b"Evidence stream 2\n"
    ev1 = collect_evidence_file(db_session, "common.log", data1)
    ev2 = collect_evidence_file(db_session, "common.log", data2)

    assert ev1.evidence_id != ev2.evidence_id
    assert ev1.stored_path != ev2.stored_path
