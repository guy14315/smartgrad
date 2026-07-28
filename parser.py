import re

import pdfplumber

COURSE_RE = re.compile(
    # Group 1 : Course ID, Group 2: Course Name, Group 3: Credits, Group 4: Grade
    r"^(\d{5,9})\s+(.+?)\s+(\d+)(?:\s+([A-Za-z][A-Za-z+\-]{0,2}))?$"
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
)


def parse_transcript(file) -> list[dict]:
    courses: list[dict] = []
    current: dict | None = None

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                match = COURSE_RE.match(line)
                if match:
                    code, name, credit, grade = match.groups()
                    current = {
                        "code": code,
                        "name_th": name.strip(),
                        "credit": int(credit),
                        "grade": grade,
                    }
                    courses.append(current)
                    continue

                upper = line.upper()
                if "SEMESTER" in upper or upper.startswith(SKIP_PREFIXES) or "TRANSCRIPT CLOSED" in upper:
                    current = None
                    continue

                if current is not None:
                    current["name_th"] += " " + line

    return courses
