from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import CATEGORIES
from database import get_db
from models import Course, Prerequisite
from services import classify_course

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


# ---------------------------------------------------------------------------
# Pydantic schemas (response models)
# ---------------------------------------------------------------------------

class PrereqOut(BaseModel):
    prereq_code: str

    model_config = {"from_attributes": True}


class CourseOut(BaseModel):
    course_code: str
    course_name_th: str
    course_name_en: str
    credit_str: str | None = None
    credit: int
    year: int | None = None
    semester: int | None = None
    url: str | None = None
    plan_type: str | None
    category: str
    category_label: str
    prerequisites: list[str]

    model_config = {"from_attributes": True}


class TermOut(BaseModel):
    year: int | None = None
    semester: int | None = None
    plan_type: str | None
    courses: list[CourseOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _course_to_out(c: Course, curriculum_codes: dict[str, Any] | None = None) -> CourseOut:
    curr_map = curriculum_codes if curriculum_codes is not None else {c.course_code: c.year}
    cat = classify_course(c.course_code, curr_map)
    cat_meta = CATEGORIES.get(cat, {"label": "วิชาเลือกเสรี"})
    return CourseOut(
        course_code=c.course_code,
        course_name_th=c.course_name_th,
        course_name_en=c.course_name_en,
        credit_str=c.credit_str,
        credit=c.credit,
        year=c.year,
        semester=c.semester,
        url=c.url,
        plan_type=c.plan_type,
        category=cat,
        category_label=cat_meta["label"],
        prerequisites=[p.prereq_code for p in c.prerequisites],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[TermOut], summary="ดูหลักสูตรทั้งหมด แยกตาม Year/Semester")
async def get_curriculum(db: AsyncSession = Depends(get_db)):
    """ดึงรายวิชาทั้งหมดในหลักสูตรจัดกลุ่มตาม ปี/เทอม"""
    result = await db.execute(
        select(Course)
        .options(selectinload(Course.prerequisites))
        .order_by(Course.year, Course.semester, Course.course_code)
    )
    courses = result.scalars().all()
    curriculum_codes = {c.course_code: c.year for c in courses}

    # group into terms
    terms: dict[tuple[int | None, int | None, str | None], list[CourseOut]] = {}
    for c in courses:
        key = (c.year, c.semester, c.plan_type)
        terms.setdefault(key, []).append(_course_to_out(c, curriculum_codes))

    return [
        TermOut(year=k[0], semester=k[1], plan_type=k[2], courses=v)
        for k, v in sorted(terms.items(), key=lambda item: (item[0][0] or 99, item[0][1] or 99, item[0][2] or ""))
    ]


@router.get("/courses", response_model=list[CourseOut], summary="ค้นหาและกรองรายวิชา")
async def search_courses(
    search: str | None = Query(None, description="ค้นหาชื่อหรือรหัสวิชา"),
    year: int | None = Query(None, description="กรองตามชั้นปี (1-4)"),
    semester: int | None = Query(None, description="กรองตามเทอม (1-2)"),
    sort: Literal["code", "credit", "year"] = Query("code", description="เรียงตาม"),
    db: AsyncSession = Depends(get_db),
):
    """ค้นหา/กรองรายวิชา – รองรับ requirement ค้นหาและจัดเรียงตามประเภทวิชา"""
    stmt = select(Course).options(selectinload(Course.prerequisites))

    if year is not None:
        stmt = stmt.where(Course.year == year)
    if semester is not None:
        stmt = stmt.where(Course.semester == semester)
    if search:
        term = f"%{search}%"
        stmt = stmt.where(
            Course.course_code.ilike(term)
            | Course.course_name_th.ilike(term)
            | Course.course_name_en.ilike(term)
        )

    sort_col = {
        "code": Course.course_code,
        "credit": Course.credit,
        "year": Course.year,
    }.get(sort, Course.course_code)
    stmt = stmt.order_by(sort_col)

    result = await db.execute(stmt)
    courses = result.scalars().all()
    curriculum_codes = {c.course_code: c.year for c in courses}
    return [_course_to_out(c, curriculum_codes) for c in courses]


@router.get("/courses/{course_code}", response_model=CourseOut, summary="รายละเอียดวิชา + Prerequisite")
async def get_course(course_code: str, db: AsyncSession = Depends(get_db)):
    """ดูรายละเอียดวิชาเดียว รวมถึงเงื่อนไขวิชาบังคับก่อน"""
    result = await db.execute(
        select(Course)
        .options(selectinload(Course.prerequisites))
        .where(Course.course_code == course_code)
    )
    course = result.scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail=f"ไม่พบรายวิชา {course_code}")
    return _course_to_out(course)
