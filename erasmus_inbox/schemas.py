from pydantic import BaseModel, Field
from typing import Literal

DocType = Literal[
    "LearningAgreement",
    "Transcript",
    "Insurance",
    "CertificateOfArrival",
    "Unknown"
]

class ExtractedDocumentInfo(BaseModel):
    surname: str = Field(description="Student's last name in Latin characters without diacritics, e.g., Kalnina")
    name: str = Field(description="Student's first name in Latin characters, e.g., Anna")
    doc_type: DocType = Field(description="Type of the Erasmus document")
    academic_year: str = Field(description="Academic year in YYYY-YY format, e.g., 2026-27")
    host_university: str = Field(description="Name of the host university, e.g., TU Delft, or 'Unknown'")
    start_date: str = Field(description="Start date of mobility (YYYY-MM-DD or DD MMM YYYY), or 'Unknown'")
    end_date: str = Field(description="End date of mobility (YYYY-MM-DD or DD MMM YYYY), or 'Unknown'")