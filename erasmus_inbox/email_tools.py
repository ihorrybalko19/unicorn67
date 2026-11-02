import os
from pathlib import Path

INBOX_DIR = Path("inbox")
FILED_DIR = Path("filed")
TEMP_DIR = Path("temp_attachments")

def list_emails() -> dict:
    """Returns a list of all .eml filenames in the inbox/ folder."""
    INBOX_DIR.mkdir(exist_ok=True)
    files = sorted([f.name for f in INBOX_DIR.glob("*.eml")])
    # Якщо папка порожня, повертаємо тестовий приклад для перевірки скелета
    if not files:
        return {"status": "mock_mode", "emails": ["sample_01_anna.eml"]}
    return {"status": "ok", "emails": files}


def read_email_and_extract(eml_filename: str) -> dict:
    """Reads an .eml file, extracts sender, subject, body, and saves attachments to temp_attachments/.
    
    TODO (Person 2): Replace mock logic with Python's `email` module + Gemini multimodal PDF/JPG extraction.
    """
    # Заглушка (Mock), поки Person 2 пише парсер .eml:
    if eml_filename == "sample_01_anna.eml" and not (INBOX_DIR / eml_filename).exists():
        return {
            "filename": eml_filename,
            "sender": "anna.kalnina@student.example",
            "subject": "signed LA",
            "body": "Hi! Attached is my signed Learning Agreement. Also, when is the deadline for the insurance document?",
            "attachments": [
                {
                    "original_name": "scan_0042.pdf",
                    "temp_path": "temp_attachments/scan_0042.pdf",
                    "extracted_text_or_summary": (
                        "Document: Learning Agreement 2026/2027. "
                        "Student: Anna Kalniņa. Host institution: TU Delft. "
                        "Planned period of the mobility: from 01 Feb 2027 to 30 Jun 2027."
                    )
                }
            ]
        }
    
    # Тут Person 2 додасть реальне читання файлу inbox/<eml_filename>
    return {"error": f"Real parser not implemented yet for {eml_filename}"}


def save_attachment(
    temp_path: str,
    surname: str,
    name: str,
    doc_type: str,
    academic_year: str
) -> dict:
    """Saves the attachment under filed/<Surname>_<Name>/<Surname>_<Name>_<DocType>_<YYYY-YY>.pdf.
    
    TODO (Person 2): Copy real file from temp_path to destination using shutil.copy2.
    """
    student_folder = FILED_DIR / f"{surname}_{name}"
    student_folder.mkdir(parents=True, exist_ok=True)
    
    ext = Path(temp_path).suffix or ".pdf"
    new_filename = f"{surname}_{name}_{doc_type}_{academic_year}{ext}"
    dest_path = student_folder / new_filename
    
    # Якщо реального файлу ще немає (mock режим), створюємо порожній файл для перевірки
    if not Path(temp_path).exists():
        dest_path.write_text(f"Mock file content for {new_filename}", encoding="utf-8")
    else:
        import shutil
        shutil.copy2(temp_path, dest_path)
        
    return {
        "status": "saved",
        "saved_path": str(dest_path)
    }