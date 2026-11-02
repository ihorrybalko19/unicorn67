"""Streamlit dashboard for the live demo: shows what the agent has produced so far.

Read-only: reads inbox/expected_results.json, filed/, students.xlsx and drafts/,
and updates itself every 3 seconds while the agent is working.

Usage: streamlit run app.py
"""
import json
from pathlib import Path

import streamlit as st
from openpyxl import load_workbook

EXPECTED_PATH = Path("inbox/expected_results.json")
FILED_DIR = Path("filed")
DRAFTS_DIR = Path("drafts")
EXCEL_PATH = Path("students.xlsx")


def cell(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_table(headers: list, rows: list) -> str:
    # Markdown tables, not st.dataframe: pandas DLLs can be blocked by Windows Smart App Control.
    lines = ["| " + " | ".join(cell(h) for h in headers) + " |", "|" + " --- |" * len(headers)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def draft_paths(sender: str) -> tuple:
    # Same naming as save_reply_draft in excel_faq_tools.py.
    safe_email = sender.replace("@", "_at_").replace(".", "_")
    return DRAFTS_DIR / f"DRAFT_{safe_email}.txt", DRAFTS_DIR / f"ESCALATE_{safe_email}.txt"


def reply_status(row: dict) -> str:
    if row["reply"] == "none":
        return "No question"
    draft, escalated = draft_paths(row["sender"])
    if row["reply"] == "draft":
        if draft.exists():
            return ":green[**Draft ready**]"
        return ":orange[**Escalated, expected a draft**]" if escalated.exists() else ":gray[Waiting]"
    if escalated.exists():
        return ":red[**Passed to staff**]"
    return ":orange[**Drafted, expected escalation**]" if draft.exists() else ":gray[Waiting]"


def emails_table(expected: list) -> str:
    rows = []
    for row in expected:
        if row["saved_as"]:
            status = ":green[**Filed**]" if (FILED_DIR / row["saved_as"]).exists() else ":gray[Waiting]"
            attachment = f"`{row['attachment']}`"
            doc_type = cell(row["doc_type"])
            filed = f"`{Path(row['saved_as']).name}`"
        else:
            status = attachment = doc_type = filed = "-"
        rows.append([
            f"`{row['email']}`",
            f"{cell(row['student'])}: {cell(row['subject'])}",
            attachment,
            doc_type,
            filed,
            status,
            reply_status(row),
        ])
    headers = ["Email", "Student and subject", "Attachment", "Correct type", "Correct new file name", "File", "Reply"]
    return markdown_table(headers, rows)


def unexpected_files(expected: list) -> list:
    known = {FILED_DIR / row["saved_as"] for row in expected if row["saved_as"]}
    return [p for p in sorted(FILED_DIR.rglob("*")) if p.is_file() and p.name != ".gitkeep" and p not in known]


def spreadsheet_rows() -> list:
    if not EXCEL_PATH.exists():
        return []
    workbook = load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    try:
        return [row for row in workbook.active.iter_rows(values_only=True) if any(c is not None for c in row)]
    finally:
        workbook.close()


def show_spreadsheet(rows: list) -> None:
    st.subheader(f"Student spreadsheet ({EXCEL_PATH})")
    if rows:
        st.markdown(markdown_table(list(rows[0]), [[cell(v) for v in row] for row in rows[1:]]))
    else:
        st.caption(f"{EXCEL_PATH} has no data yet.")


def show_drafts(paths: list) -> None:
    st.subheader("Reply drafts")
    if not paths:
        st.caption("No reply drafts yet.")
        return
    for column, path in zip(st.columns(3) * (len(paths) // 3 + 1), paths):
        with column.container(border=True):
            escalated = path.name.startswith("ESCALATE")
            st.markdown(":red[**Passed to staff**]" if escalated else ":green[**Draft for approval**]")
            st.code(path.read_text(encoding="utf-8", errors="replace"), language=None, wrap_lines=True)


@st.fragment(run_every=3)  # a number: parsing a string like "3s" imports pandas
def dashboard() -> None:
    if not EXPECTED_PATH.exists():
        st.info("No test data found. Run `python data_generator.py` first.")
        return

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    with_documents = [row for row in expected if row["saved_as"]]
    filed = sum((FILED_DIR / row["saved_as"]).exists() for row in with_documents)
    draft_files = sorted(DRAFTS_DIR.glob("*.txt")) if DRAFTS_DIR.exists() else []
    escalated = sum(path.name.startswith("ESCALATE") for path in draft_files)

    sheet_error = None
    try:
        rows = spreadsheet_rows()
    except Exception as error:  # e.g. the agent is writing the file right now
        rows, sheet_error = [], error

    metrics = [
        ("Emails in the inbox", len(expected)),
        ("Documents filed correctly", f"{filed} / {len(with_documents)}"),
        ("Students in the spreadsheet", max(len(rows) - 1, 0)),
        ("Reply drafts for approval", len(draft_files) - escalated),
        ("Passed to staff", escalated),
    ]
    for column, (label, value) in zip(st.columns(len(metrics)), metrics):
        column.metric(label, value)

    st.subheader("Emails and files")
    st.markdown(emails_table(expected))
    extra = unexpected_files(expected)
    if extra:
        names = ", ".join(f"`{p.relative_to(FILED_DIR).as_posix()}`" for p in extra)
        st.warning(f"Not in the expected list: {names}")

    if sheet_error:
        st.warning(f"Could not read {EXCEL_PATH}: {sheet_error}")
    show_spreadsheet(rows)
    show_drafts(draft_files)


st.set_page_config(page_title="Erasmus Inbox Demo", layout="wide")
st.title("Erasmus Inbox Agent")
st.caption("What the agent has produced so far. It only prepares drafts: staff review and send every reply.")
dashboard()
