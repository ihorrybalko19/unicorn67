# unicorn67: Erasmus Inbox Agent

An agent for university Erasmus offices, built for GDG Riga's [Erasmus Inbox Agent challenge](https://hack.gdgriga.com/challenges/erasmus-inbox-agent).

## Pitch

Erasmus offices open every student email by hand, work out who sent what, rename the file, type the dates into Excel, and answer the same questions again and again. This agent does that routine work. It files documents under one naming pattern, keeps one spreadsheet row per student, and drafts answers from the office's FAQ. Staff review and send every reply, and anything the agent is unsure about goes to a person.

## Architecture

```text
inbox/*.eml --> erasmus_inbox agent (Google ADK + Gemini)
                  |-- email_tools.py       --> filed/<Surname_Name>/<Surname>_<Name>_<DocType>_<YYYY-YY>.<ext>
                  |-- excel_faq_tools.py   --> students.xlsx, one row per student
                  |-- faq.md               --> drafts/DRAFT_*.txt for staff to approve
                  `-- not in the FAQ       --> drafts/ESCALATE_*.txt, "I'll pass this to staff"

pages/Results.py reads those outputs and shows them on a read-only page of the app.py Streamlit UI.
```

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

Open the Streamlit UI and choose **Results** in the sidebar. The page updates by itself while the agent works:

```bash
streamlit run app.py --server.address 127.0.0.1
```

In a second terminal, start the agent, choose `erasmus_inbox` and ask it to process the inbox:

```bash
adk web
```

To reset the test emails, run `python data_generator.py`. It rewrites the files in `inbox/`. Empty `filed/` before a repeat run, because `save_attachment` never overwrites and adds a `_v2` file instead.

> On Windows with Smart App Control on, the `pandas` DLLs can be blocked and the `app.py` page fails to load. The Results page does not use `pandas`, so it still works from the sidebar or directly with `streamlit run pages/Results.py`.

## Test data

`inbox/` holds 10 generated emails and `expected_results.json`, the correct outcome for each. All people, documents and rules are fictional, including Nordbaltic University.

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

## Results page

`pages/Results.py` compares `filed/` and `drafts/` with `inbox/expected_results.json`, shows `students.xlsx` as it is, and marks any result that differs from what was expected. It changes nothing and sends nothing.
