"""Email & file-system tools (owned by Person 2).

Pipeline: inbox/*.eml -> parse (stdlib email) -> Gemini inspects attachments ->
bytes cached in memory -> save_attachment writes to filed/<Surname_Name>/...
"""
import re
import unicodedata
from email import message_from_binary_file
from email.policy import default
from pathlib import Path

from .schemas import ExtractedDocumentInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INBOX_DIR = PROJECT_ROOT / "inbox"
FILED_DIR = PROJECT_ROOT / "filed"

ALLOWED_MIME = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
GEMINI_MODEL = "gemini-2.5-flash"

# attachment_id -> {"bytes": ..., "ext": ...}; entries are removed on save.
_ATTACHMENT_CACHE: dict[str, dict] = {}

_client = None


def _get_client():
    """Lazily create the GenAI client (so imports work without an API key)."""
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client()
    return _client


def sanitize_name(text: str) -> str:
    """Strips diacritics and unsafe characters: 'Kalniņa' -> 'Kalnina', 'Jānis Bērziņš' -> 'Janis_Berzins'."""
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ASCII", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip()
    text = re.sub(r"[\s_]+", "_", text).strip("_")
    return text


def _unknown_info() -> ExtractedDocumentInfo:
    return ExtractedDocumentInfo(
        surname="Unknown", name="Student", doc_type="Unknown",
        academic_year="Unknown", host_university="Unknown",
        start_date="Unknown", end_date="Unknown",
    )


def inspect_attachment(file_bytes: bytes, mime_type: str) -> ExtractedDocumentInfo:
    """Calls Gemini directly to extract structured data from a PDF/JPG/PNG.

    Never raises: on any failure returns an 'Unknown' placeholder so the
    pipeline continues and the coordinator can review manually.
    """
    try:
        from google.genai import types
        response = _get_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                "Extract Erasmus student mobility document details. Normalize names "
                "to Latin letters without diacritics. If any field is unclear or "
                "unreadable, set its value to 'Unknown'.",
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExtractedDocumentInfo,
                temperature=0.1,
            ),
        )
        if isinstance(response.parsed, ExtractedDocumentInfo):
            return response.parsed
        return ExtractedDocumentInfo.model_validate_json(response.text)
    except Exception:
        return _unknown_info()


def list_emails(inbox_dir: str = "") -> dict:
    """Returns a sorted list of all .eml filenames waiting in the inbox/ folder.

    Args:
        inbox_dir: Optional inbox directory; defaults to the project's inbox/.
    """
    path = Path(inbox_dir) if inbox_dir else INBOX_DIR
    path.mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "emails": sorted(f.name for f in path.glob("*.eml"))}


def _extract_body(msg) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    content = part.get_content()
    if part.get_content_type() == "text/html":
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()
    return content


def read_email_and_extract(eml_filename: str) -> dict:
    """Reads an .eml file from inbox/ and returns sender, subject, body and attachments.

    Each PDF/JPG/PNG attachment is analysed by Gemini and returned as compact
    `extracted_info` plus an `attachment_id` to pass to `save_attachment`.
    Emails without attachments return an empty `attachments` list.

    Args:
        eml_filename: File name (e.g. 'sample_01_anna.eml') or path of the email.
    """
    path = Path(eml_filename)
    if not path.is_absolute() and not path.exists():
        path = INBOX_DIR / eml_filename
    if not path.exists():
        return {"status": "error", "error": f"File not found: {eml_filename}"}

    try:
        with open(path, "rb") as f:
            msg = message_from_binary_file(f, policy=default)
    except Exception as e:
        return {"status": "error", "error": f"Cannot parse {eml_filename}: {e}"}

    # Drop stale cache entries from previous runs of the same email.
    prefix = f"{path.stem}_"
    for key in [k for k in _ATTACHMENT_CACHE if k.startswith(prefix)]:
        del _ATTACHMENT_CACHE[key]

    attachments = []
    for idx, part in enumerate(msg.iter_attachments()):
        mime = part.get_content_type()
        if mime not in ALLOWED_MIME:
            continue
        data = part.get_payload(decode=True)
        if not data:
            continue
        original = part.get_filename() or f"attachment_{idx}{ALLOWED_MIME[mime]}"
        ext = Path(original).suffix.lower() or ALLOWED_MIME[mime]
        attachment_id = f"{path.stem}_{sanitize_name(Path(original).stem) or idx}{ext}"
        _ATTACHMENT_CACHE[attachment_id] = {"bytes": data, "ext": ext}
        info = inspect_attachment(data, mime)
        attachments.append({
            "attachment_id": attachment_id,
            "original_filename": original,
            "mime_type": mime,
            "extracted_info": info.model_dump(),
        })

    sender = msg["From"]
    addr = ""
    if sender is not None:
        addresses = getattr(sender, "addresses", None)
        addr = addresses[0].addr_spec if addresses else str(sender)

    return {
        "status": "ok",
        "filename": path.name,
        "sender": addr,
        "sender_full": str(sender) if sender is not None else "",
        "subject": str(msg["Subject"] or ""),
        "body": _extract_body(msg),
        "attachments": attachments,
    }


def save_attachment(
    attachment_id: str,
    surname: str,
    name: str,
    doc_type: str,
    academic_year: str,
) -> dict:
    """Saves a cached attachment to filed/<Surname>_<Name>/<Surname>_<Name>_<DocType>_<YYYY-YY>.<ext>.

    Diacritics are stripped (Kalniņa -> Kalnina). Use the `attachment_id`
    returned by `read_email_and_extract`.

    Args:
        attachment_id: ID from read_email_and_extract's attachments list.
        surname: Student's surname.
        name: Student's first name.
        doc_type: e.g. LearningAgreement, Transcript, Insurance, CertificateOfArrival.
        academic_year: Format YYYY-YY, e.g. 2026-27.
    """
    entry = _ATTACHMENT_CACHE.get(attachment_id)
    if entry is None:
        return {"status": "error", "error": f"Unknown or already saved attachment_id: {attachment_id}"}

    s = sanitize_name(surname) or "Unknown"
    n = sanitize_name(name) or "Student"
    d = sanitize_name(doc_type) or "Unknown"
    y = sanitize_name(academic_year) or "Unknown"

    folder = FILED_DIR / f"{s}_{n}"
    folder.mkdir(parents=True, exist_ok=True)
    base = f"{s}_{n}_{d}_{y}"
    ext = entry["ext"]
    dest = folder / f"{base}{ext}"
    version = 2
    while dest.exists():  # never overwrite silently
        dest = folder / f"{base}_v{version}{ext}"
        version += 1

    dest.write_bytes(entry["bytes"])
    del _ATTACHMENT_CACHE[attachment_id]  # free memory
    try:
        shown = str(dest.relative_to(PROJECT_ROOT))
    except ValueError:
        shown = str(dest)
    return {"status": "saved", "saved_path": shown}
