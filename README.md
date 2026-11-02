# unicorn67: Erasmus Inbox Agent

An agent for university Erasmus offices, built for GDG Riga's [Erasmus Inbox Agent challenge](https://hack.gdgriga.com/challenges/erasmus-inbox-agent). It reads student emails, files their documents under one naming pattern, keeps one spreadsheet row per student, and drafts answers to common questions. Staff review and send every reply, and anything the agent is unsure about goes to a person.

| Output | Where |
| --- | --- |
| Renamed documents | `filed/<Surname_Name>/<Surname>_<Name>_<DocType>_<YYYY-YY>.<ext>` |
| One row per student | `students.xlsx` |
| Replies for staff to approve | `drafts/DRAFT_*.txt` |
| Questions passed to staff | `drafts/ESCALATE_*.txt` |

## Setup

```bash
python -m venv .venv
```

Activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` elsewhere), then:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `erasmus_inbox/.env` and add a Gemini API key from [AI Studio](https://aistudio.google.com/).

## Run the demo

Generate the test emails:

```bash
python data_generator.py
```

Open the demo view in a second terminal. It updates by itself while the agent works:

```bash
python demo_view.py
```

Start the agent, choose `erasmus_inbox` and ask it to process the inbox:

```bash
adk web
```

> The generated `.eml` files are not committed. As soon as `inbox/` contains them, the agent stops using its built-in mock email, so the real `.eml` parser in `email_tools.py` must be in place.

## Test data

`data_generator.py` writes 10 emails to `inbox/`, plus `expected_results.json` with the correct outcome for each. All people, documents and rules are fictional, including Nordbaltic University.

| Email | Student | What it tests | Attachment | Expected result |
| --- | --- | --- | --- | --- |
| 01 | Anna Kalniņa | Messy file name, diacritics | `scan_0042.pdf` | Learning Agreement filed |
| 02 | Marek Nowak | Messy file name, vague subject | `doc_final_v2.pdf` | Transcript filed |
| 03 | Sofia Rossi | Type only visible inside the document | `LA (1) copy.pdf` | Learning Agreement filed |
| 04 | Anna Kalniņa | Second document, no duplicate row | `polise_skan.pdf` | Insurance added to Anna's row |
| 05 | Jonas Petrauskas | Blurry, rotated photo with `(no subject)` | `IMG_2231.jpg` | Certificate of Arrival filed |
| 06 | Tomáš Novák | Question in the FAQ | None | Draft: insurance deadline |
| 07 | Elena García | Question in the FAQ | None | Draft: who signs the Learning Agreement |
| 08 | Katrin Tamm | Question not in the FAQ (pet ferret) | None | "I'll pass this to staff" |
| 09 | Ieva Liepa | Document and FAQ question | `Erasmus_LA_signed_FINAL.pdf` | Learning Agreement filed, draft: grant payment |
| 10 | Marek Nowak | Document and FAQ question, existing student | `ins.pdf` | Insurance added to Marek's row, draft: ECTS |

The FAQ the agent answers from is in [`faq.md`](faq.md).

## Demo view

`demo_view.py` serves a local, read-only page at <http://127.0.0.1:8067/>. It compares `filed/` and `drafts/` with `inbox/expected_results.json`, shows `students.xlsx` as it is, and marks any result that differs from what was expected. It changes nothing and sends nothing.
