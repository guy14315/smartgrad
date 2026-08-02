"""Parser for KMITL transcript PDFs – extracts courses WITH semester/year context."""

import re
from typing import Optional

import pdfplumber

COURSE_RE = re.compile(
    # Group 1: Course ID, Group 2: Course Name, Group 3: Credits, Group 4: Grade (optional)
    r"^(\d{5,9})\s+(.+?)\s+(\d+)(?:\s+([A-Za-z][A-Za-z+\-]{0,2}))?$"
)

# Semester header patterns: "1st Semester, Year, 2024-2025"
SEMESTER_RE = re.compile(
    r"(\d+)(?:st|nd|rd|th)\s+semester[,\s]+year[,\s]+(\d{4})[–\-](\d{4})",
    re.IGNORECASE,
)

SKIP_PREFIXES = (
    "GPS",
    "GPA",
    "COURSE TITLE",
    "TRANSFER CREDIT",
    "CHECKED BY",
    "TOTAL NUMBER OF CREDIT",
    "CUMULATIVE GPA",
    "DATE ISSUED",
    "THIS DOCUMENT",
    "PHOTO",
    "NAME",
    "DATE OF",
    "DEGREE",
    "PROGRAM",
    "(XX",
)

STUDENT_ID_PATTERNS = (
    re.compile(r"\bSTUDENT\s*(?:ID|NO\.?)\s*[:#]?\s*(\d{8})\b", re.IGNORECASE),
    re.compile(r"รหัสนักศึกษา\s*[:：]?\s*(\d{8})"),
)
STUDENT_NAME_PATTERNS = (
    re.compile(
        r"\b(?:STUDENT\s+)?NAME\s*[:：]?\s*(.+?)(?=\s+(?:STUDENT\s*(?:ID|NO\.?)|FACULTY|PROGRAM|DATE\s+OF)\b|$)",
        re.IGNORECASE,
    ),
    re.compile(r"ชื่อ(?:-นามสกุล)?\s*[:：]?\s*(.+?)(?=\s+รหัสนักศึกษา|$)"),
)


def _parse_student_info_from_text(text: str) -> dict:
    """Extract KMITL student identity from transcript header text."""
    normalized = " ".join(text.split())
    student_id = next((m.group(1) for p in STUDENT_ID_PATTERNS if (m := p.search(normalized))), None)
    name = None
    # Try each extracted line first: this prevents a name field from consuming
    # the rest of the PDF when the header is split over multiple lines.
    for line in text.splitlines():
        compact_line = " ".join(line.split())
        for pattern in STUDENT_NAME_PATTERNS:
            match = pattern.search(compact_line)
            if match:
                candidate = match.group(1).strip(" :")
                if candidate and len(candidate) <= 150:
                    name = candidate
                    break
        if name:
            break
    if not name:
        for pattern in STUDENT_NAME_PATTERNS:
            match = pattern.search(normalized)
            if match:
                candidate = match.group(1).strip(" :")
                if candidate and len(candidate) <= 150:
                    name = candidate
                    break
    return {"student_id": student_id, "name": name}


def parse_student_info(file) -> dict:
    """Read student ID and name from a transcript PDF."""
    file.seek(0)
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    file.seek(0)
    return _parse_student_info_from_text(text)


def parse_transcript(file) -> list[dict]:
    """Parse a KMITL transcript PDF.

    Returns a list of course dicts:
        {
            code: str,
            name_en: str,          # course name as printed in transcript
            credit: int,
            grade: str | None,
            semester: int | None,  # 1, 2, or 3 (summer)
            academic_year: str | None,  # e.g. "2024-2025"
            is_current: bool,       # True if last semester (no grade yet)
        }
    """
    courses: list[dict] = []
    current_course: dict | None = None
    current_semester: int | None = None
    current_year: str | None = None
    last_semester_key: tuple | None = None
    seen_semesters: list[tuple] = []

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                # detect semester header
                sem_match = SEMESTER_RE.search(line)
                if sem_match:
                    current_semester = int(sem_match.group(1))
                    current_year = f"{sem_match.group(2)}-{sem_match.group(3)}"
                    key = (current_semester, current_year)
                    if key not in seen_semesters:
                        seen_semesters.append(key)
                    last_semester_key = key
                    current_course = None
                    continue

                # skip known noise lines
                upper = line.upper()
                if upper.startswith(SKIP_PREFIXES) or "TRANSCRIPT CLOSED" in upper:
                    current_course = None
                    continue

                # try to parse course line
                m = COURSE_RE.match(line)
                if m:
                    code, name, credit, grade = m.groups()
                    current_course = {
                        "code": code,
                        "name_en": name.strip(),
                        "credit": int(credit),
                        "grade": grade,
                        "semester": current_semester,
                        "academic_year": current_year,
                        "is_current": False,  # will set after we find last semester
                    }
                    courses.append(current_course)
                    continue

                # continuation line for multi-line course name
                if current_course is not None and not upper.startswith(SKIP_PREFIXES):
                    current_course["name_en"] += " " + line

    # mark courses in the last semester with no grades as "current" (กำลังเรียน)
    if last_semester_key:
        for c in courses:
            if (c["semester"], c["academic_year"]) == last_semester_key and not c["grade"]:
                c["is_current"] = True

    return courses
