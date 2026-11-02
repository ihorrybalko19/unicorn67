"""Person 2 tests: Green / Yellow / FAQ paths (Gemini mocked). Run: python -m pytest tests -q"""
from email.message import EmailMessage

import pytest

from erasmus_inbox import email_tools as et
from erasmus_inbox.schemas import ExtractedDocumentInfo


@pytest.fixture(autouse=True)
def dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(et, "INBOX_DIR", tmp_path / "inbox")
    monkeypatch.setattr(et, "FILED_DIR", tmp_path / "filed")
    monkeypatch.setattr(et, "PROJECT_ROOT", tmp_path)
    et._ATTACHMENT_CACHE.clear()
    (tmp_path / "inbox").mkdir()
    return tmp_path


def _eml(path, body, attach=None, name="scan_0042.pdf", mime=("application", "pdf")):
    m = EmailMessage()
    m["From"] = "Anna Kalniņa <anna.kalnina@student.example>"
    m["To"] = "erasmus@uni.example"
    m["Subject"] = "signed LA"
    m.set_content(body)
    if attach:
        m.add_attachment(attach, maintype=mime[0], subtype=mime[1], filename=name)
    path.write_bytes(bytes(m))


GOOD = ExtractedDocumentInfo(
    surname="Kalnina", name="Anna", doc_type="LearningAgreement",
    academic_year="2026-27", host_university="TU Delft",
    start_date="2027-02-01", end_date="2027-06-30")


def test_sanitize():
    assert et.sanitize_name("Kalniņa") == "Kalnina"
    assert et.sanitize_name("Jānis Bērziņš") == "Janis_Berzins"
    assert et.sanitize_name("a/b\\c:d") == "abcd"


def test_green_path(dirs, monkeypatch):
    monkeypatch.setattr(et, "inspect_attachment", lambda b, m: GOOD)
    _eml(dirs / "inbox" / "a.eml", "Attached LA", b"%PDF-1.4 data")
    assert et.list_emails()["emails"] == ["a.eml"]
    r = et.read_email_and_extract("a.eml")
    assert r["sender"] == "anna.kalnina@student.example"
    att = r["attachments"][0]
    assert "raw" not in str(att) and att["extracted_info"]["surname"] == "Kalnina"
    out = et.save_attachment(att["attachment_id"], "Kalniņa", "Anna", "LearningAgreement", "2026-27")
    assert out["status"] == "saved"
    assert (dirs / "filed/Kalnina_Anna/Kalnina_Anna_LearningAgreement_2026-27.pdf").read_bytes() == b"%PDF-1.4 data"
    assert not et._ATTACHMENT_CACHE  # cache freed


def test_collision_suffix(dirs, monkeypatch):
    monkeypatch.setattr(et, "inspect_attachment", lambda b, m: GOOD)
    _eml(dirs / "inbox" / "a.eml", "x", b"1")
    for _ in range(2):
        aid = et.read_email_and_extract("a.eml")["attachments"][0]["attachment_id"]
        res = et.save_attachment(aid, "Kalnina", "Anna", "Insurance", "2026-27")
    assert res["saved_path"].endswith("_v2.pdf")


def test_yellow_path_gemini_failure(dirs, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("api down")
    monkeypatch.setattr(et, "_get_client", boom)
    _eml(dirs / "inbox" / "y.eml", "photo", b"\xff\xd8jpg", "IMG_2231.jpg", ("image", "jpeg"))
    r = et.read_email_and_extract("y.eml")
    info = r["attachments"][0]["extracted_info"]
    assert info["surname"] == "Unknown" and info["doc_type"] == "Unknown"
    assert r["attachments"][0]["attachment_id"].endswith(".jpg")


def test_faq_path_no_attachments(dirs):
    _eml(dirs / "inbox" / "f.eml", "When is the insurance deadline?")
    r = et.read_email_and_extract("f.eml")
    assert r["attachments"] == [] and "insurance" in r["body"]


def test_missing_file():
    assert et.read_email_and_extract("nope.eml")["status"] == "error"

