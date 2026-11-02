"""Local read-only page for the live demo: shows what the agent has produced so far.

Reads inbox/expected_results.json, filed/, students.xlsx and drafts/ on every
request and updates itself every 3 seconds while the agent is working.

Usage: python demo_view.py [--port 8067] [--no-browser]
"""
import argparse
import json
import webbrowser
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from openpyxl import load_workbook

EXPECTED_PATH = Path("inbox/expected_results.json")
FILED_DIR = Path("filed")
DRAFTS_DIR = Path("drafts")
EXCEL_PATH = Path("students.xlsx")

STYLE = """
:root {
  --bg: #f5f6f8; --panel: #ffffff; --text: #1c2430; --muted: #5d6878; --line: #e1e5ea;
  --ok-bg: #dff3e6; --ok: #17643a; --wait-bg: #eceff3; --wait: #5d6878;
  --warn-bg: #fdf0d5; --warn: #8a5a00; --esc-bg: #fbe3e0; --esc: #a3291b;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14181f; --panel: #1d232c; --text: #e8ebf0; --muted: #9aa5b4; --line: #303844;
    --ok-bg: #173a27; --ok: #7bd9a2; --wait-bg: #2a313b; --wait: #9aa5b4;
    --warn-bg: #3d3014; --warn: #f0c56b; --esc-bg: #43211d; --esc: #f4a196;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.45 system-ui, "Segoe UI", sans-serif; }
main { max-width: 1240px; margin: 0 auto; padding: 28px 16px 48px; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 17px; margin: 0 0 12px; }
.lead { color: var(--muted); margin: 0 0 22px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi, .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; }
.kpi { padding: 14px 16px; }
.kpi b { display: block; font-size: 28px; line-height: 1.15; font-variant-numeric: tabular-nums; }
.kpi span { color: var(--muted); font-size: 13px; }
.panel { padding: 18px; margin-bottom: 18px; }
.scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; color: var(--muted); font-size: 12px; font-weight: 600; white-space: nowrap; }
th, td { padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
tr:last-child td { border-bottom: 0; }
code { font: 13px/1.4 ui-monospace, Consolas, monospace; overflow-wrap: anywhere; }
.muted { color: var(--muted); }
.chip { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.ok { background: var(--ok-bg); color: var(--ok); }
.wait { background: var(--wait-bg); color: var(--wait); }
.warn { background: var(--warn-bg); color: var(--warn); }
.esc { background: var(--esc-bg); color: var(--esc); }
.drafts { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.draft { border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-width: 0; }
.draft pre { margin: 8px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; font: 13px/1.45 system-ui, "Segoe UI", sans-serif; }
"""

REFRESH_SCRIPT = """
setInterval(async () => {
  try {
    const response = await fetch(location.href, { cache: "no-store" });
    const page = new DOMParser().parseFromString(await response.text(), "text/html");
    document.querySelector("main").replaceWith(page.querySelector("main"));
  } catch (error) { /* server stopped: keep the last view on screen */ }
}, 3000);
"""


def chip(text: str, kind: str) -> str:
    return f'<span class="chip {kind}">{escape(text)}</span>'


def draft_paths(sender: str) -> tuple:
    # Same naming as save_reply_draft in excel_faq_tools.py.
    safe_email = sender.replace("@", "_at_").replace(".", "_")
    return DRAFTS_DIR / f"DRAFT_{safe_email}.txt", DRAFTS_DIR / f"ESCALATE_{safe_email}.txt"


def reply_status(row: dict) -> str:
    if row["reply"] == "none":
        return '<span class="muted">No question</span>'
    draft, escalated = draft_paths(row["sender"])
    if row["reply"] == "draft":
        if draft.exists():
            return chip("Draft ready", "ok")
        return chip("Escalated, expected a draft", "warn") if escalated.exists() else chip("Waiting", "wait")
    if escalated.exists():
        return chip("Passed to staff", "esc")
    return chip("Drafted, expected escalation", "warn") if draft.exists() else chip("Waiting", "wait")


def emails_table(expected: list) -> str:
    rows = []
    for row in expected:
        if row["saved_as"]:
            attachment = f"<code>{escape(row['attachment'])}</code><br><span class=\"muted\">{escape(row['doc_type'])}</span>"
            status = chip("Filed", "ok") if (FILED_DIR / row["saved_as"]).exists() else chip("Waiting", "wait")
            filed = f"<code>{escape(Path(row['saved_as']).name)}</code><br>{status}"
        else:
            attachment = filed = '<span class="muted">No attachment</span>'
        rows.append(
            f"<tr><td><code>{escape(row['email'])}</code></td>"
            f"<td>{escape(row['student'])}<br><span class=\"muted\">{escape(row['subject'])}</span></td>"
            f"<td>{attachment}</td><td>{filed}</td><td>{reply_status(row)}</td></tr>"
        )
    return (
        '<div class="scroll"><table><thead><tr><th>Email</th><th>Student and subject</th>'
        "<th>Attachment and correct type</th><th>Correct new file name</th><th>Reply</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def unexpected_files(expected: list) -> str:
    known = {FILED_DIR / row["saved_as"] for row in expected if row["saved_as"]}
    extra = [p for p in sorted(FILED_DIR.rglob("*")) if p.is_file() and p.name != ".gitkeep" and p not in known]
    if not extra:
        return ""
    items = "".join(f"<li><code>{escape(p.relative_to(FILED_DIR).as_posix())}</code></li>" for p in extra)
    return f'<p>{chip("Not in the expected list", "warn")}</p><ul>{items}</ul>'


def spreadsheet_rows() -> list:
    if not EXCEL_PATH.exists():
        return []
    workbook = load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    try:
        return [row for row in workbook.active.iter_rows(values_only=True) if any(c is not None for c in row)]
    finally:
        workbook.close()


def spreadsheet_panel() -> tuple:
    """Returns the panel HTML and the number of student rows."""
    try:
        rows = spreadsheet_rows()
    except Exception as error:  # e.g. the agent is writing the file right now
        return f'<p class="muted">Could not read {EXCEL_PATH}: {escape(str(error))}</p>', 0
    if not rows:
        return f'<p class="muted">{EXCEL_PATH} has no data yet.</p>', 0
    cell = lambda value: "" if value is None else escape(str(value))
    head = "".join(f"<th>{cell(value)}</th>" for value in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{cell(v)}</td>" for v in row) + "</tr>" for row in rows[1:])
    table = f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    return table, len(rows) - 1


def drafts_panel(paths: list) -> str:
    if not paths:
        return '<p class="muted">No reply drafts yet.</p>'
    cards = []
    for path in paths:
        badge = chip("Passed to staff", "esc") if path.name.startswith("ESCALATE") else chip("Draft for approval", "ok")
        text = path.read_text(encoding="utf-8", errors="replace")
        cards.append(f'<div class="draft">{badge}<pre>{escape(text)}</pre></div>')
    return f'<div class="drafts">{"".join(cards)}</div>'


def kpi(value, label: str) -> str:
    return f'<div class="kpi"><b>{escape(str(value))}</b><span>{escape(label)}</span></div>'


def render_main() -> str:
    if not EXPECTED_PATH.exists():
        return (
            "<main><h1>Erasmus Inbox Agent</h1>"
            "<p class=\"lead\">No test data found. Run <code>python data_generator.py</code> first.</p></main>"
        )

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    with_documents = [row for row in expected if row["saved_as"]]
    filed = sum((FILED_DIR / row["saved_as"]).exists() for row in with_documents)
    draft_files = sorted(DRAFTS_DIR.glob("*.txt")) if DRAFTS_DIR.exists() else []
    escalated = sum(path.name.startswith("ESCALATE") for path in draft_files)
    spreadsheet, students = spreadsheet_panel()

    return f"""<main>
<h1>Erasmus Inbox Agent</h1>
<p class="lead">What the agent has produced so far. It only prepares drafts: staff review and send every reply.</p>
<section class="kpis">
  {kpi(len(expected), "emails in the inbox")}
  {kpi(f"{filed} / {len(with_documents)}", "documents filed correctly")}
  {kpi(students, "students in the spreadsheet")}
  {kpi(len(draft_files) - escalated, "reply drafts for approval")}
  {kpi(escalated, "passed to staff")}
</section>
<section class="panel"><h2>Emails and files</h2>{emails_table(expected)}{unexpected_files(expected)}</section>
<section class="panel"><h2>Student spreadsheet ({EXCEL_PATH})</h2>{spreadsheet}</section>
<section class="panel"><h2>Reply drafts</h2>{drafts_panel(draft_files)}</section>
</main>"""


def render_page() -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Erasmus Inbox Demo</title><style>{STYLE}</style></head>"
        f"<body>{render_main()}<script>{REFRESH_SCRIPT}</script></body></html>"
    )


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        body = render_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8067)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Demo view: {url} (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
