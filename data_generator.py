"""Generates 10 fake Erasmus student emails (.eml) with PDF/JPG attachments in inbox/.

Also writes inbox/expected_results.json, the correct outcome for every email,
which app.py compares with what the agent actually produced.
All people, policies and Nordbaltic University are fictional.

Usage: python data_generator.py
"""
import io
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INBOX_DIR = Path("inbox")
OFFICE_EMAIL = "erasmus@nordbaltic.example"
HOME_UNIVERSITY = "Nordbaltic University, Tallinn, Estonia"
ACADEMIC_YEAR = "2026-27"
COORDINATOR = "Dr. Laura Ozoliņa"
TZ = timezone(timedelta(hours=3))

# Standard PDF fonts have no "ņ" or "š", so a TTF font is needed for real names.
FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]
FONT_PATHS = next(
    (pair for pair in FONT_CANDIDATES if Path(pair[0]).exists() and Path(pair[1]).exists()),
    None,
)
if FONT_PATHS:
    pdfmetrics.registerFont(TTFont("DocFont", FONT_PATHS[0]))
    pdfmetrics.registerFont(TTFont("DocFont-Bold", FONT_PATHS[1]))
    pdfmetrics.registerFontFamily("DocFont", normal="DocFont", bold="DocFont-Bold", italic="DocFont", boldItalic="DocFont-Bold")
    FONT, FONT_BOLD = "DocFont", "DocFont-Bold"
else:
    print("WARNING: no TTF font found, names in documents will lose their diacritics.")
    FONT, FONT_BOLD = "Helvetica", "Helvetica-Bold"


def to_ascii(text: str) -> str:
    """Kalniņa -> Kalnina, the same conversion the agent applies to filenames."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def doc_text(text: str) -> str:
    return text if FONT_PATHS else to_ascii(text)


@dataclass
class Student:
    name: str
    surname: str
    email: str
    host: str
    start: str
    end: str
    student_id: str
    planned_courses: tuple = ()

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"

    @property
    def filed_prefix(self) -> str:
        return f"{to_ascii(self.surname)}_{to_ascii(self.name)}"


ANNA = Student(
    "Anna", "Kalniņa", "anna.kalnina@student.example", "TU Delft",
    "01 Feb 2027", "30 Jun 2027", "NB-204417",
    (("CSE2510", "Machine Learning", 10), ("CSE2525", "Data Management", 10), ("WM0320", "Ethics of Technology", 10)),
)
MAREK = Student(
    "Marek", "Nowak", "m.nowak@student.example", "KU Leuven",
    "08 Feb 2027", "02 Jul 2027", "NB-198832",
)
SOFIA = Student(
    "Sofia", "Rossi", "sofia.rossi98@student.example", "RTU (Riga Technical University)",
    "14 Sep 2026", "31 Jan 2027", "NB-211056",
    (("DIP384", "Software Engineering", 12), ("DMI327", "Computer Networks", 9), ("HSP472", "Latvian for Beginners", 3)),
)
JONAS = Student(
    "Jonas", "Petrauskas", "jonas.p97@student.example", "University of Porto",
    "14 Sep 2026", "22 Jan 2027", "NB-207790",
)
TOMAS = Student("Tomáš", "Novák", "tomas.novak@student.example", "", "", "", "NB-202671")
ELENA = Student("Elena", "García", "elena.garcia@student.example", "", "", "", "NB-215340")
KATRIN = Student("Katrin", "Tamm", "katrin.tamm@student.example", "", "", "", "NB-209128")
IEVA = Student(
    "Ieva", "Liepa", "ieva.liepa@student.example", "University of Porto",
    "03 Feb 2027", "26 Jun 2027", "NB-213904",
    (("EIC0028", "Distributed Systems", 12), ("EIC0104", "Computer Graphics", 12), ("LLE0031", "Portuguese A1", 6)),
)


def styles() -> dict:
    return {
        "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=16, leading=20, spaceAfter=4),
        "sub": ParagraphStyle("sub", fontName=FONT, fontSize=10, leading=13, textColor=colors.HexColor("#555555")),
        "h": ParagraphStyle("h", fontName=FONT_BOLD, fontSize=11, leading=14, spaceBefore=12, spaceAfter=4),
        "p": ParagraphStyle("p", fontName=FONT, fontSize=10, leading=14),
    }


def table(rows: list, widths: list, header: bool = False) -> Table:
    rows = [[doc_text(str(cell)) for cell in row] for row in rows]
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        commands += [
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8ECF1")),
        ]
    else:
        commands.append(("FONTNAME", (0, 0), (0, -1), FONT_BOLD))
    result = Table(rows, colWidths=[w * mm for w in widths], hAlign="LEFT")
    result.setStyle(TableStyle(commands))
    return result


def build_pdf(title: str, subtitle: str, story: list) -> bytes:
    s = styles()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, title=title,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
    )
    document.build([Paragraph(title, s["title"]), Paragraph(subtitle, s["sub"]), Spacer(1, 6 * mm)] + story)
    return buffer.getvalue()


def student_rows(student: Student) -> list:
    return [
        ["Student", student.full_name],
        ["Student ID", student.student_id],
        ["Home institution", HOME_UNIVERSITY],
        ["Host institution", student.host],
    ]


def learning_agreement_pdf(student: Student) -> bytes:
    s = styles()
    courses = [["Code", "Component at host institution", "ECTS"]] + [list(c) for c in student.planned_courses]
    courses.append(["", "Total", sum(c[2] for c in student.planned_courses)])
    return build_pdf(
        "Learning Agreement",
        f"Erasmus+ Student Mobility for Studies, academic year {ACADEMIC_YEAR.replace('-', '/20')}",
        [
            table(student_rows(student), [45, 120]),
            Paragraph("Planned period of the mobility", s["h"]),
            Paragraph(f"From <b>{student.start}</b> to <b>{student.end}</b>", s["p"]),
            Paragraph("Study programme at the host institution", s["h"]),
            table(courses, [28, 117, 20], header=True),
            Paragraph("Signatures", s["h"]),
            table(
                [
                    ["Student", student.full_name, "signed"],
                    ["Home coordinator", COORDINATOR, "signed"],
                    ["Receiving coordinator", f"International Office, {student.host}", "signed"],
                ],
                [45, 100, 20],
            ),
        ],
    )


def transcript_pdf(student: Student) -> bytes:
    s = styles()
    results = [
        ["Code", "Course", "ECTS", "Grade"],
        ["CS201", "Algorithms and Data Structures", 6, "9"],
        ["CS214", "Operating Systems", 6, "8"],
        ["CS230", "Databases", 6, "10"],
        ["MA205", "Probability and Statistics", 6, "7"],
        ["CS245", "Web Technologies", 6, "9"],
        ["HU110", "Academic Writing", 3, "8"],
        ["", "Total", 33, ""],
    ]
    return build_pdf(
        "Transcript of Records",
        f"Issued for Erasmus+ mobility, academic year {ACADEMIC_YEAR.replace('-', '/20')}",
        [
            table(student_rows(student), [45, 120]),
            Paragraph("Period of the Erasmus+ mobility", s["h"]),
            Paragraph(f"From <b>{student.start}</b> to <b>{student.end}</b>", s["p"]),
            Paragraph("Results of the previous academic year (2025/2026)", s["h"]),
            table(results, [28, 97, 20, 20], header=True),
        ],
    )


def insurance_pdf(student: Student, policy: str) -> bytes:
    s = styles()
    return build_pdf(
        "Certificate of Insurance",
        "BalticCare Student Insurance, health and third-party liability cover",
        [
            table(
                [
                    ["Insured person", student.full_name],
                    ["Policy number", policy],
                    ["Purpose of travel", f"Erasmus+ mobility, academic year {ACADEMIC_YEAR.replace('-', '/20')}"],
                    ["Host institution", student.host],
                    ["Cover starts", student.start],
                    ["Cover ends", student.end],
                ],
                [45, 120],
            ),
            Paragraph("Scope of cover", s["h"]),
            Paragraph(
                "Emergency medical treatment, hospitalisation, repatriation and "
                "third-party liability in all EU and EEA countries.",
                s["p"],
            ),
        ],
    )


def image_font(size: int, bold: bool = False):
    if FONT_PATHS:
        return ImageFont.truetype(FONT_PATHS[1 if bold else 0], size)
    return ImageFont.load_default(size)


def certificate_of_arrival_jpg(student: Student) -> bytes:
    """A phone photo of a stamped paper form: slightly rotated, blurry, still readable."""
    width, height = 1240, 1754
    page = Image.new("RGB", (width, height), (250, 249, 244))
    draw = ImageDraw.Draw(page)
    ink = (35, 35, 40)

    draw.text((120, 130), "CERTIFICATE OF ARRIVAL", font=image_font(62, bold=True), fill=ink)
    draw.text(
        (120, 220), f"Erasmus+ Student Mobility, academic year {ACADEMIC_YEAR.replace('-', '/20')}",
        font=image_font(32), fill=ink,
    )
    draw.line((120, 285, 1120, 285), fill=ink, width=3)

    rows = [
        ("Student:", student.full_name),
        ("Student ID:", student.student_id),
        ("Home institution:", "Nordbaltic University, Estonia"),
        ("Host institution:", student.host),
        ("Date of arrival:", student.start),
        ("Expected end of stay:", student.end),
    ]
    y = 370
    for label, value in rows:
        draw.text((120, y), label, font=image_font(36, bold=True), fill=ink)
        draw.text((540, y), doc_text(value), font=image_font(38), fill=ink)
        y += 90

    draw.text(
        (120, y + 50), "We confirm that the student named above has arrived\nat our institution on the date stated.",
        font=image_font(34), fill=ink, spacing=14,
    )

    # Signature and the international office stamp.
    signature_y = 1330
    points = [(150 + i * 7, signature_y + int(26 * ((i % 9) - 4) / 4)) for i in range(46)]
    draw.line(points, fill=(30, 45, 120), width=4)
    draw.line((120, signature_y + 60, 560, signature_y + 60), fill=ink, width=2)
    draw.text((120, signature_y + 75), "International Office", font=image_font(30), fill=ink)

    stamp_color = (60, 80, 170)
    draw.ellipse((780, 1220, 1090, 1530), outline=stamp_color, width=7)
    draw.ellipse((810, 1250, 1060, 1500), outline=stamp_color, width=3)
    draw.text((841, 1340), "RECEIVED", font=image_font(34, bold=True), fill=stamp_color)
    draw.text((865, 1395), student.start, font=image_font(28), fill=stamp_color)

    rotated = page.rotate(3.5, resample=Image.BICUBIC, expand=True, fillcolor=(92, 88, 82))
    grain = Image.effect_noise(rotated.size, 18).convert("RGB")
    noisy = Image.blend(rotated, grain, 0.06)
    blurry = noisy.filter(ImageFilter.GaussianBlur(1.6))

    buffer = io.BytesIO()
    blurry.save(buffer, format="JPEG", quality=68)
    return buffer.getvalue()


# One entry per email: sender, subject, body, date, attachment and the correct outcome.
EMAILS = [
    {
        "student": ANNA,
        "subject": "signed LA",
        "body": "Hi!\n\nAttached is my signed Learning Agreement.\n\nBest,\nAnna Kalniņa",
        "date": datetime(2026, 9, 2, 10, 14, tzinfo=TZ),
        "doc_type": "LearningAgreement",
        "filename": "scan_0042.pdf",
        "render": lambda: learning_agreement_pdf(ANNA),
        "reply": "none",
    },
    {
        "student": MAREK,
        "subject": "documents",
        "body": "Hello,\n\nsending the transcript as requested.\n\nMarek",
        "date": datetime(2026, 9, 4, 16, 41, tzinfo=TZ),
        "doc_type": "Transcript",
        "filename": "doc_final_v2.pdf",
        "render": lambda: transcript_pdf(MAREK),
        "reply": "none",
    },
    {
        "student": SOFIA,
        "subject": "Fwd: for the erasmus office",
        "body": "Good morning,\n\nplease find my document attached.\n\nKind regards,\nSofia Rossi",
        "date": datetime(2026, 9, 8, 9, 3, tzinfo=TZ),
        "doc_type": "LearningAgreement",
        "filename": "LA (1) copy.pdf",
        "render": lambda: learning_agreement_pdf(SOFIA),
        "reply": "none",
    },
    {
        "student": ANNA,
        "subject": "Re: signed LA",
        "body": "Hi again,\n\nhere is my insurance as well.\n\nAnna",
        "date": datetime(2026, 9, 15, 13, 27, tzinfo=TZ),
        "doc_type": "Insurance",
        "filename": "polise_skan.pdf",
        "render": lambda: insurance_pdf(ANNA, "BC-2026-558120"),
        "reply": "none",
    },
    {
        "student": JONAS,
        "subject": "(no subject)",
        "body": "Sent from my iPhone",
        "date": datetime(2026, 9, 17, 18, 52, tzinfo=TZ),
        "doc_type": "CertificateOfArrival",
        "filename": "IMG_2231.jpg",
        "render": lambda: certificate_of_arrival_jpg(JONAS),
        "reply": "none",
    },
    {
        "student": TOMAS,
        "subject": "insurance question",
        "body": "Hello,\n\nWhen is the deadline for insurance? I am leaving for the Spring semester.\n\nThank you,\nTomáš Novák",
        "date": datetime(2026, 9, 22, 11, 8, tzinfo=TZ),
        "reply": "draft",
    },
    {
        "student": ELENA,
        "subject": "Learning Agreement",
        "body": "Hi,\n\nWho signs my Learning Agreement? I filled it in but I'm not sure who to send it to first.\n\nElena García",
        "date": datetime(2026, 9, 29, 15, 36, tzinfo=TZ),
        "reply": "draft",
    },
    {
        "student": KATRIN,
        "subject": "dorm question",
        "body": "Hello!\n\nCan I bring my pet ferret to the student dorm in Munich? He is very calm and vaccinated.\n\nThanks,\nKatrin Tamm",
        "date": datetime(2026, 10, 6, 20, 19, tzinfo=TZ),
        "reply": "escalate",
    },
    {
        "student": IEVA,
        "subject": "my LA + question about money",
        "body": (
            "Hello,\n\nmy Learning Agreement is attached.\n"
            "Also, when will I get the first grant payment? I'm going in the Spring semester.\n\n"
            "Paldies,\nIeva Liepa"
        ),
        "date": datetime(2026, 10, 14, 12, 45, tzinfo=TZ),
        "doc_type": "LearningAgreement",
        "filename": "Erasmus_LA_signed_FINAL.pdf",
        "render": lambda: learning_agreement_pdf(IEVA),
        "reply": "draft",
    },
    {
        "student": MAREK,
        "subject": "insurance + ECTS?",
        "body": (
            "Hello,\n\nattaching my insurance.\n"
            "One more thing: how many ECTS must my transcript show?\n\nMarek Nowak"
        ),
        "date": datetime(2026, 10, 20, 9, 58, tzinfo=TZ),
        "doc_type": "Insurance",
        "filename": "ins.pdf",
        "render": lambda: insurance_pdf(MAREK, "BC-2026-601947"),
        "reply": "draft",
    },
]


def build_email(number: int, spec: dict) -> tuple:
    """Returns the .eml bytes and the expected outcome for one email."""
    student = spec["student"]
    message = EmailMessage()
    message["From"] = f"{student.full_name} <{student.email}>"
    message["To"] = OFFICE_EMAIL
    message["Subject"] = spec["subject"]
    message["Date"] = format_datetime(spec["date"])
    message["Message-ID"] = f"<demo-{number:02d}@student.example>"
    message.set_content(spec["body"])

    expected = {
        "email": f"email_{number:02d}.eml",
        "student": student.full_name,
        "sender": student.email,
        "subject": spec["subject"],
        "attachment": None,
        "doc_type": None,
        "host_university": None,
        "start_date": None,
        "end_date": None,
        "saved_as": None,
        "reply": spec["reply"],
    }

    if "filename" in spec:
        data = spec["render"]()
        extension = Path(spec["filename"]).suffix
        if extension == ".jpg":
            message.add_attachment(data, maintype="image", subtype="jpeg", filename=spec["filename"])
        else:
            message.add_attachment(data, maintype="application", subtype="pdf", filename=spec["filename"])
        saved_name = f"{student.filed_prefix}_{spec['doc_type']}_{ACADEMIC_YEAR}{extension}"
        expected.update(
            attachment=spec["filename"],
            doc_type=spec["doc_type"],
            host_university=student.host,
            start_date=student.start,
            end_date=student.end,
            saved_as=f"{student.filed_prefix}/{saved_name}",
        )
    return message.as_bytes(), expected


def main() -> None:
    INBOX_DIR.mkdir(exist_ok=True)
    results = []
    for number, spec in enumerate(EMAILS, start=1):
        data, expected = build_email(number, spec)
        (INBOX_DIR / expected["email"]).write_bytes(data)
        results.append(expected)
        document = expected["saved_as"] or f"(question: {expected['reply']})"
        print(f"{expected['email']}  {len(data) // 1024:>4} KB  {document}")

    (INBOX_DIR / "expected_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n{len(results)} emails and expected_results.json written to {INBOX_DIR}/")


if __name__ == "__main__":
    main()
