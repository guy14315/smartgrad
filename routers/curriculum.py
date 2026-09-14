from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, computed_field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import CATEGORIES
from database import get_db
from models import Course, Curriculum, CurriculumCategory, Prerequisite
from services import classify_course

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class PrereqOut(BaseModel):
    prereq_code: str

    model_config = {"from_attributes": True}


class CurriculumCategoryIn(BaseModel):
    category_code: str
    category_name: str
    required_credits: int

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "category_code" not in data and "key" in data:
                data["category_code"] = data["key"]
            if "category_name" not in data and "label" in data:
                data["category_name"] = data["label"]
            if "required_credits" not in data and "target_credits" in data:
                data["required_credits"] = data["target_credits"]
        return data


class CurriculumCategoryOut(BaseModel):
    category_code: str
    category_name: str
    required_credits: int

    @computed_field
    @property
    def key(self) -> str:
        return self.category_code

    @computed_field
    @property
    def label(self) -> str:
        return self.category_name

    @computed_field
    @property
    def target_credits(self) -> int:
        return self.required_credits

    model_config = {"from_attributes": True}


class CurriculumCreateIn(BaseModel):
    curriculum_id: str
    name: str
    year: int
    total_credits_target: int = 135
    max_credits_per_semester: int = 22
    categories: list[CurriculumCategoryIn] = []


class CurriculumInfoOut(BaseModel):
    curriculum_id: str
    name: str
    year: int
    total_credits_target: int | None = None
    max_credits_per_semester: int | None = None
    categories: list[CurriculumCategoryOut] = []

    model_config = {"from_attributes": True}


class CourseCreateIn(BaseModel):
    course_code: str
    curriculum_id: str
    course_name_th: str
    course_name_en: str
    credit: int
    credit_str: str | None = None
    year: int | None = None
    semester: int | None = None
    url: str | None = None
    plan_type: str | None = None
    category: str | None = None
    prerequisites: list[str] = []


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
    cat = c.category or classify_course(c.course_code, curr_map)
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
        prerequisites=list(dict.fromkeys(p.prereq_code for p in c.prerequisites)),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/programs", response_model=list[CurriculumInfoOut], summary="รายการหลักสูตรทั้งหมดในระบบ")
async def list_curriculums(db: AsyncSession = Depends(get_db)):
    """ดึงรายชื่อหลักสูตรทั้งหมดพร้อมเกณฑ์หน่วยกิตและหมวดวิชา"""
    result = await db.execute(
        select(Curriculum)
        .options(selectinload(Curriculum.categories))
        .order_by(Curriculum.year.desc(), Curriculum.curriculum_id)
    )
    return result.scalars().all()


@router.get("/programs/{curriculum_id}", response_model=CurriculumInfoOut, summary="รายละเอียดหลักสูตรและเกณฑ์หน่วยกิต")
async def get_curriculum_info(curriculum_id: str, db: AsyncSession = Depends(get_db)):
    """ดูข้อมูลและโครงสร้างหมวดวิชาของหลักสูตรเฉพาะ"""
    result = await db.execute(
        select(Curriculum)
        .options(selectinload(Curriculum.categories))
        .where(Curriculum.curriculum_id == curriculum_id)
    )
    curr = result.scalars().first()
    if not curr:
        raise HTTPException(status_code=404, detail=f"ไม่พบหลักสูตร {curriculum_id}")
    return curr


@router.post("/programs", response_model=CurriculumInfoOut, status_code=201, summary="สร้างหรือเพิ่มหลักสูตรใหม่")
async def create_curriculum(body: CurriculumCreateIn, db: AsyncSession = Depends(get_db)):
    """เพิ่มหลักสูตรใหม่พร้อมโครงสร้างหมวดวิชาและเป้าหมายหน่วยกิต"""
    existing = await db.get(Curriculum, body.curriculum_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"หลักสูตร {body.curriculum_id} มีอยู่ในระบบแล้ว")

    curr = Curriculum(
        curriculum_id=body.curriculum_id,
        name=body.name,
        year=body.year,
        total_credits_target=body.total_credits_target,
        max_credits_per_semester=body.max_credits_per_semester,
    )
    db.add(curr)
    await db.flush()

    for cat in body.categories:
        c_cat = CurriculumCategory(
            curriculum_id=curr.curriculum_id,
            category_code=cat.category_code,
            category_name=cat.category_name,
            required_credits=cat.required_credits,
        )
        db.add(c_cat)

    await db.commit()

    result = await db.execute(
        select(Curriculum)
        .options(selectinload(Curriculum.categories))
        .where(Curriculum.curriculum_id == body.curriculum_id)
    )
    return result.scalars().first()


@router.post("/courses", response_model=CourseOut, status_code=201, summary="เพิ่มรายวิชาในหลักสูตร")
async def create_course(body: CourseCreateIn, db: AsyncSession = Depends(get_db)):
    """เพิ่มรายวิชาใหม่เข้าสู่หลักสูตร"""
    existing = await db.get(Course, body.course_code)
    if existing:
        raise HTTPException(status_code=409, detail=f"รหัสวิชา {body.course_code} มีอยู่ในระบบแล้ว")

    course = Course(
        course_code=body.course_code,
        curriculum_id=body.curriculum_id,
        course_name_th=body.course_name_th,
        course_name_en=body.course_name_en,
        credit=body.credit,
        credit_str=body.credit_str or f"{body.credit}(3-0-6)",
        year=body.year,
        semester=body.semester,
        url=body.url,
        plan_type=body.plan_type,
        category=body.category,
    )
    db.add(course)
    await db.flush()

    for prereq in body.prerequisites:
        db.add(Prerequisite(course_code=body.course_code, prereq_code=prereq))

    await db.commit()

    result = await db.execute(
        select(Course)
        .options(selectinload(Course.prerequisites))
        .where(Course.course_code == body.course_code)
    )
    c = result.scalars().first()
    return _course_to_out(c)


@router.get("", response_model=list[TermOut], summary="ดูหลักสูตรทั้งหมด แยกตาม Year/Semester")
async def get_curriculum(
    curriculum_id: str | None = Query(None, description="รหัสหลักสูตร เช่น CS2564"),
    db: AsyncSession = Depends(get_db),
):
    """ดึงรายวิชาทั้งหมดในหลักสูตรจัดกลุ่มตาม ปี/เทอม (สามารถกรองตามหลักสูตรได้)"""
    stmt = (
        select(Course)
        .options(selectinload(Course.prerequisites))
        .order_by(Course.year, Course.semester, Course.course_code)
    )
    if curriculum_id is not None:
        stmt = stmt.where(Course.curriculum_id == curriculum_id)

    result = await db.execute(stmt)
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
    curriculum_id: str | None = Query(None, description="รหัสหลักสูตร เช่น CS2564"),
    search: str | None = Query(None, description="ค้นหาชื่อหรือรหัสวิชา"),
    year: int | None = Query(None, description="กรองตามชั้นปี (1-4)"),
    semester: int | None = Query(None, description="กรองตามเทอม (1-2)"),
    sort: Literal["code", "credit", "year"] = Query("code", description="เรียงตาม"),
    db: AsyncSession = Depends(get_db),
):
    """ค้นหา/กรองรายวิชา – รองรับ requirement ค้นหาและจัดเรียงตามประเภทวิชา"""
    stmt = select(Course).options(selectinload(Course.prerequisites))

    if curriculum_id is not None:
        stmt = stmt.where(Course.curriculum_id == curriculum_id)
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
