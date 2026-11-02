import os
import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = PROJECT_ROOT / "students.xlsx"
FAQ_PATH = PROJECT_ROOT / "faq.md"
DRAFTS_DIR = PROJECT_ROOT / "drafts"

REQUIRED_DOCS = ["LearningAgreement", "Transcript", "Insurance", "CertificateOfArrival"]

HEADERS = [
    "Surname",
    "Name",
    "Email",
    "Host University",
    "Start Date",
    "End Date",
    "Academic Year",
    "Documents Received",
    "Missing Documents",
    "Status"
]


def _normalize_str(text: Optional[str]) -> str:
    """Normalize string and strip accents for reliable comparison."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text)
    return norm.encode("ASCII", "ignore").decode("ascii").strip().lower()


def _get_or_create_workbook() -> tuple[openpyxl.Workbook, Any]:
    """Loads existing students.xlsx or creates a new stylized workbook."""
    if EXCEL_PATH.exists():
        try:
            wb = openpyxl.load_workbook(EXCEL_PATH)
            ws = wb.active
            return wb, ws
        except Exception:
            pass

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Erasmus Students"

    # Header styling
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC")
    )
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.append(HEADERS)
    for col_idx in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center
        cell.border = thin_border

    ws.row_dimensions[1].height = 28
    return wb, ws


def _auto_adjust_columns(ws):
    """Adjusts column widths based on content."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = str(cell.value or "")
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)


def append_or_update_student_row(
    surname: str,
    name: str,
    email_address: str,
    host_university: str,
    start_date: str,
    end_date: str,
    academic_year: str,
    doc_type: str
) -> Dict[str, Any]:
    """Adds or updates one row per student in students.xlsx using openpyxl.

    Deduplicates students by (surname, name) or email.
    Accumulates received documents and updates missing document list.
    """
    wb, ws = _get_or_create_workbook()

    target_surname_norm = _normalize_str(surname)
    target_name_norm = _normalize_str(name)
    target_email_norm = _normalize_str(email_address)

    found_row_idx = None
    existing_docs: Set[str] = set()

    # Search existing data rows (skipping header row 1)
    for row_idx in range(2, ws.max_row + 1):
        row_surname = str(ws.cell(row=row_idx, column=1).value or "").strip()
        row_name = str(ws.cell(row=row_idx, column=2).value or "").strip()
        row_email = str(ws.cell(row=row_idx, column=3).value or "").strip()

        row_surname_norm = _normalize_str(row_surname)
        row_name_norm = _normalize_str(row_name)
        row_email_norm = _normalize_str(row_email)

        is_match = False
        if target_email_norm and row_email_norm and target_email_norm == row_email_norm:
            is_match = True
        elif target_surname_norm and target_name_norm and (
            (target_surname_norm == row_surname_norm and target_name_norm == row_name_norm)
            or (target_surname_norm in row_surname_norm and target_name_norm in row_name_norm)
        ):
            is_match = True

        if is_match:
            found_row_idx = row_idx
            docs_cell_val = str(ws.cell(row=row_idx, column=8).value or "")
            if docs_cell_val:
                for d in docs_cell_val.split(","):
                    d_clean = d.strip()
                    if d_clean:
                        existing_docs.add(d_clean)
            break

    # Add new doc_type
    if doc_type and doc_type != "Unknown":
        existing_docs.add(doc_type)

    docs_list = [d for d in REQUIRED_DOCS if d in existing_docs]
    # In case there are extra doc types
    for d in existing_docs:
        if d not in docs_list:
            docs_list.append(d)

    missing_docs = [d for d in REQUIRED_DOCS if d not in existing_docs]
    docs_received_str = ", ".join(docs_list)
    missing_docs_str = ", ".join(missing_docs)
    status_str = "Complete" if not missing_docs else f"Pending ({len(missing_docs)} missing)"

    thin_border = Border(
        left=Side(style="thin", color="E0E0E0"),
        right=Side(style="thin", color="E0E0E0"),
        top=Side(style="thin", color="E0E0E0"),
        bottom=Side(style="thin", color="E0E0E0")
    )
    data_font = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    if found_row_idx:
        # Update existing row
        row = found_row_idx
        # Preserve original clean names/data unless new values are better
        if host_university and host_university != "Unknown":
            ws.cell(row=row, column=4, value=host_university)
        if start_date and start_date != "Unknown":
            ws.cell(row=row, column=5, value=start_date)
        if end_date and end_date != "Unknown":
            ws.cell(row=row, column=6, value=end_date)
        if academic_year and academic_year != "Unknown":
            ws.cell(row=row, column=7, value=academic_year)

        ws.cell(row=row, column=8, value=docs_received_str)
        ws.cell(row=row, column=9, value=missing_docs_str)
        ws.cell(row=row, column=10, value=status_str)
        action = "updated"
    else:
        # Append new row
        row = ws.max_row + 1
        values = [
            surname,
            name,
            email_address,
            host_university if host_university != "Unknown" else "",
            start_date if start_date != "Unknown" else "",
            end_date if end_date != "Unknown" else "",
            academic_year if academic_year != "Unknown" else "2026-27",
            docs_received_str,
            missing_docs_str,
            status_str
        ]
        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.font = data_font
            cell.border = thin_border
            cell.alignment = center_align if col_idx in [5, 6, 7, 10] else left_align

        ws.row_dimensions[row].height = 20
        action = "created"

    # Status column color formatting
    status_cell = ws.cell(row=row, column=10)
    if not missing_docs:
        status_cell.fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
        status_cell.font = Font(name="Calibri", size=10, bold=True, color="274E13")
    else:
        status_cell.fill = PatternFill(start_color="FCE5CD", end_color="FCE5CD", fill_type="solid")
        status_cell.font = Font(name="Calibri", size=10, bold=True, color="783F04")

    _auto_adjust_columns(ws)
    EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(EXCEL_PATH)

    return {
        "status": action,
        "student": f"{surname} {name}",
        "email": email_address,
        "host_university": host_university,
        "stay_period": f"{start_date} to {end_date}",
        "documents_received": docs_list,
        "missing_documents": missing_docs,
        "excel_file": str(EXCEL_PATH)
    }


def flag_missing_docs(surname: str = "", name: str = "", email_address: str = "") -> Dict[str, Any]:
    """Inspects students.xlsx and returns missing documents for a given student or all students."""
    if not EXCEL_PATH.exists():
        return {"status": "error", "message": "students.xlsx does not exist yet."}

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb.active

    results = []
    target_email_norm = _normalize_str(email_address)
    target_surname_norm = _normalize_str(surname)

    for row_idx in range(2, ws.max_row + 1):
        r_surname = str(ws.cell(row=row_idx, column=1).value or "").strip()
        r_name = str(ws.cell(row=row_idx, column=2).value or "").strip()
        r_email = str(ws.cell(row=row_idx, column=3).value or "").strip()
        r_missing = str(ws.cell(row=row_idx, column=9).value or "").strip()
        r_status = str(ws.cell(row=row_idx, column=10).value or "").strip()

        missing_list = [d.strip() for d in r_missing.split(",") if d.strip()]

        if target_email_norm and target_email_norm == _normalize_str(r_email):
            return {
                "student": f"{r_surname} {r_name}",
                "email": r_email,
                "missing_documents": missing_list,
                "status": r_status
            }
        elif target_surname_norm and target_surname_norm == _normalize_str(r_surname):
            return {
                "student": f"{r_surname} {r_name}",
                "email": r_email,
                "missing_documents": missing_list,
                "status": r_status
            }

        results.append({
            "student": f"{r_surname} {r_name}",
            "email": r_email,
            "missing_documents": missing_list,
            "status": r_status
        })

    return {"status": "ok", "students": results}


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
) -> Dict[str, Any]:
    """Saves a draft reply email into drafts/ for Erasmus staff to review and send.

    Naming convention:
      - DRAFT_<safe_email>.txt when an automated FAQ answer is drafted.
      - ESCALATE_<safe_email>.txt when staff attention is required.
    """
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_email = to_email.replace("@", "_at_").replace(".", "_")
    prefix = "ESCALATE" if needs_human_escalation else "DRAFT"
    draft_file = DRAFTS_DIR / f"{prefix}_{safe_email}.txt"

    content = (
        f"To: {to_email}\n"
        f"Subject: Re: {subject}\n"
        f"Needs Human Escalation: {'YES' if needs_human_escalation else 'NO'}\n"
        f"{'='*50}\n\n"
        f"{draft_body.strip()}\n"
    )
    draft_file.write_text(content, encoding="utf-8")

    return {
        "status": "draft_saved",
        "draft_file": str(draft_file),
        "filename": draft_file.name,
        "needs_human_escalation": needs_human_escalation
    }
