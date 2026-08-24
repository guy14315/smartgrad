"""Shared business-logic helpers used across routers and main.

รวม function ที่ใช้ร่วมกันเพื่อลด code duplication:
- load_curriculum_dict: โหลดหลักสูตรจาก DB
- get_active_transcript: ดึง Transcript ล่าสุดที่ active
- classify_course: จัดหมวดหมู่รายวิชา
"""

import hashlib
import hmac
import logging
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import (
    ALTERNATIVE_CODES,
    CORE_CS_PREFIX,
    CORE_MATH_CODES,
    GE_PREFIX,
    NON_PASSING_GRADES,
)
from models import Course, Transcript, TranscriptCourse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security & Password Utilities
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000,
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash (supports PBKDF2 and legacy SHA256)."""
    if not hashed_password or not plain_password:
        return False
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4:
                return False
            _, iters_str, salt, key_hex = parts
            iters = int(iters_str)
            computed_key = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations=iters,
            )
            return hmac.compare_digest(computed_key.hex(), key_hex)
        except Exception:
            return False
    # Legacy SHA-256 fallback
    legacy_sha256 = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_sha256, hashed_password)


# ---------------------------------------------------------------------------
# Curriculum loader
# ---------------------------------------------------------------------------

async def load_curriculum_dict(
    db: AsyncSession,
    curriculum_id: str | None = None,
) -> dict:
    """Load curriculum from DB, formatted for dashboard functions.

    Optionally filter by curriculum_id.  Used by both HTML routes
    (main.py) and REST API (students router).
    """
    stmt = select(Course).options(selectinload(Course.prerequisites))
    if curriculum_id:
        stmt = stmt.where(Course.curriculum_id == curriculum_id)
    stmt = stmt.order_by(Course.year, Course.semester)

    result = await db.execute(stmt)
    courses = result.scalars().all()

    terms: dict[tuple, list] = {}
    for c in courses:
        key = (c.year, c.semester, c.plan_type)
        terms.setdefault(key, []).append(c)

    curriculum_list = []
    for (year, semester, plan_type), term_courses in sorted(
        terms.items(),
        key=lambda item: (item[0][0] or 99, item[0][1] or 99, item[0][2] or ""),
    ):
        curriculum_list.append({
            "year": year,
            "semester": semester,
            "plan_type": plan_type or "",
            "courses": [
                {
                    "course_code": c.course_code,
                    "course_name_th": c.course_name_th,
                    "course_name_en": c.course_name_en,
                    "credit": c.credit_str or str(c.credit),
                    "url": c.url,
                    "prerequisites": [p.prereq_code for p in c.prerequisites],
                    "prereq_source": c.prereq_source,
                }
                for c in term_courses
            ],
        })
    return {"curriculum": curriculum_list}


# ---------------------------------------------------------------------------
# Transcript helpers
# ---------------------------------------------------------------------------

async def get_active_transcript(
    student_id: str,
    db: AsyncSession,
) -> Transcript | None:
    """Return the latest active transcript for a student, with courses eager-loaded."""
    result = await db.execute(
        select(Transcript)
        .options(selectinload(Transcript.courses))
        .where(Transcript.student_id == student_id, Transcript.is_active == True)
        .order_by(Transcript.uploaded_at.desc())
    )
    return result.scalars().first()


def compute_credits(courses: list[TranscriptCourse]) -> tuple[int, int]:
    """Return (passed_credits, total_attempted_credits) from a list of TranscriptCourse."""
    passed_by_code: dict[str, int] = {}
    total = sum(c.credit for c in courses)
    for c in courses:
        grade = (c.grade or "").upper()
        if grade and grade not in NON_PASSING_GRADES:
            passed_by_code[c.course_code] = c.credit
    return sum(passed_by_code.values()), total


def transcript_courses_to_list(tc_list: list[TranscriptCourse]) -> list[dict]:
    """Convert ORM TranscriptCourse objects to plain dicts for dashboard functions."""
    return [
        {
            "code": tc.course_code,
            "name_th": tc.course_name_raw,
            "credit": tc.credit,
            "grade": tc.grade,
        }
        for tc in tc_list
    ]


# ---------------------------------------------------------------------------
# Course classification
# ---------------------------------------------------------------------------

def classify_course(code: str, curriculum_codes: dict[str, Any]) -> str:
    """Classify a course code into one of the category keys.

    Categories: ge, core_math, core_cs, elective, free, alternative.
    """
    if code.startswith(GE_PREFIX):
        return "ge"
    if code in CORE_MATH_CODES:
        return "core_math"
    if code in ALTERNATIVE_CODES:
        return "alternative"
    if code.startswith(CORE_CS_PREFIX):
        if code in curriculum_codes and curriculum_codes[code] is not None:
            return "core_cs"
        return "elective"   # วิชาเลือกเฉพาะสาขา (05506xxx ที่ไม่มีปีระบุชัดเจน)
    return "free"           # วิชาอื่นๆ → เลือกเสรี
