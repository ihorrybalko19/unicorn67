from pathlib import Path

EXCEL_PATH = Path("students.xlsx")
FAQ_PATH = Path("faq.md")
DRAFTS_DIR = Path("drafts")

REQUIRED_DOCS = {"LearningAgreement", "Transcript", "Insurance", "CertificateOfArrival"}

def append_or_update_student_row(
    surname: str,
    name: str,
    email_address: str,
    host_university: str,
    start_date: str,
    end_date: str,
    academic_year: str,
    doc_type: str
) -> dict:
    """Adds or updates one row per student in students.xlsx using openpyxl.
    Also calculates missing documents.
    
    TODO (Person 3): Implement real openpyxl read/write and row deduplication by student name or email.
    """
    full_name = f"{surname} {name}"
    missing = sorted(list(REQUIRED_DOCS - {doc_type}))
    
    # Заглушка (Mock), поки Person 3 пише код openpyxl:
    return {
        "status": "updated_mock",
        "student": full_name,
        "host_university": host_university,
        "stay_period": f"{start_date} to {end_date}",
        "documents_received": [doc_type],
        "missing_documents": missing,
        "excel_file": str(EXCEL_PATH)
    }


def read_faq() -> str:
    """Reads the Erasmus FAQ markdown file to answer common student questions."""
    if FAQ_PATH.exists():
        return FAQ_PATH.read_text(encoding="utf-8")
    return "FAQ file not found."


def save_reply_draft(
    to_email: str,
    subject: str,
    draft_body: str,
    needs_human_escalation: bool
) -> dict:
    """Saves a draft reply email into the drafts/ folder for Erasmus staff to review and send."""
    DRAFTS_DIR.mkdir(exist_ok=True)
    safe_email = to_email.replace("@", "_at_").replace(".", "_")
    status_prefix = "ESCALATE" if needs_human_escalation else "DRAFT"
    draft_file = DRAFTS_DIR / f"{status_prefix}_{safe_email}.txt"
    
    content = (
        f"To: {to_email}\n"
        f"Subject: Re: {subject}\n"
        f"Needs Human Escalation: {needs_human_escalation}\n"
        f"{'-'*40}\n"
        f"{draft_body}\n"
    )
    draft_file.write_text(content, encoding="utf-8")
    return {
        "status": "draft_saved",
        "draft_file": str(draft_file),
        "needs_human_escalation": needs_human_escalation
    }