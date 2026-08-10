"""Shared business-logic helpers used across routers and main.

รวม function ที่ใช้ร่วมกันเพื่อลด code duplication:
- load_curriculum_dict: โหลดหลักสูตรจาก DB
- get_active_transcript: ดึง Transcript ล่าสุดที่ active
- classify_course: จัดหมวดหมู่รายวิชา
"""

import logging
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
    passed = sum(c.credit for c in courses if c.grade and c.grade.upper() not in NON_PASSING_GRADES)
    total = sum(c.credit for c in courses)
    return passed, total


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
