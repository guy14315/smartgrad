from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, computed_field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import CATEGORIES, DEFAULT_CURRICULUM_ID
from app.database import get_db
from app.models import Course, Curriculum, CurriculumCategory, CurriculumCourse, Prerequisite
from app.services import DEFAULT_CATEGORY_LABELS, classify_course

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class PrereqOut(BaseModel):
    prereq_code: str

    model_config = {"from_attributes": True}


class CurriculumCategoryIn(BaseModel):
    category_name: str
    required_credits: int
    category_code: str | None = None

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "category_name" not in data:
                if "category_code" in data:
                    data["category_name"] = data["category_code"]
                elif "key" in data:
                    data["category_name"] = data["key"]
                elif "label" in data:
                    data["category_name"] = data["label"]
            if "required_credits" not in data and "target_credits" in data:
                data["required_credits"] = data["target_credits"]
        return data


class CurriculumCategoryOut(BaseModel):
    category_name: str
    required_credits: int

    @computed_field
    @property
    def category_code(self) -> str:
        return self.category_name

    @computed_field
    @property
    def key(self) -> str:
        return self.category_name

    @computed_field
    @property
    def label(self) -> str:
        return DEFAULT_CATEGORY_LABELS.get(self.category_name, self.category_name)

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

def _course_to_out(
    c: Course,
    curriculum_codes: dict[str, Any] | None = None,
    cc: "CurriculumCourse | None" = None,
) -> CourseOut:
    curr_map = curriculum_codes if curriculum_codes is not None else {}
    category = (cc.category if cc else None) or classify_course(c.course_code, curr_map)
    cat_label = DEFAULT_CATEGORY_LABELS.get(category, CATEGORIES.get(category, {}).get("label", category))
    return CourseOut(
        course_code=c.course_code,
        course_name_th=c.course_name_th,
        course_name_en=c.course_name_en,
        credit_str=c.credit_str,
        credit=c.credit,
        year=cc.year if cc else None,
        semester=cc.semester if cc else None,
        url=c.url,
        plan_type=cc.plan_type if cc else None,
        category=category,
        category_label=cat_label,
        prerequisites=[p.prereq_code for p in c.prerequisites],
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
    existing_cc = await db.get(CurriculumCourse, (body.curriculum_id, body.course_code))
    if existing_cc:
        raise HTTPException(status_code=409, detail=f"รหัสวิชา {body.course_code} มีอยู่ในหลักสูตร {body.curriculum_id} แล้ว")

    course = await db.get(Course, body.course_code)
    if not course:
        course = Course(
            course_code=body.course_code,
            course_name_th=body.course_name_th,
            course_name_en=body.course_name_en,
            credit=body.credit,
            credit_str=body.credit_str or f"{body.credit}(3-0-6)",
            url=body.url,
        )
        db.add(course)
        await db.flush()

    # Junction table: link course to curriculum with context
    cc = CurriculumCourse(
        curriculum_id=body.curriculum_id,
        course_code=body.course_code,
        year=body.year,
        semester=body.semester,
        plan_type=body.plan_type,
        category=body.category,
    )
    db.add(cc)

    for prereq in body.prerequisites:
        db.add(Prerequisite(course_code=body.course_code, prereq_code=prereq))

    await db.commit()

    result = await db.execute(
        select(Course)
        .options(selectinload(Course.prerequisites))
        .where(Course.course_code == body.course_code)
    )
    c = result.scalars().first()
    return _course_to_out(c, cc=cc)


@router.get("", response_model=list[TermOut], summary="ดูหลักสูตรทั้งหมด แยกตาม Year/Semester")
async def get_curriculum(
    curriculum_id: str | None = Query(None, description="รหัสหลักสูตร เช่น CS2564"),
    db: AsyncSession = Depends(get_db),
):
    """ดึงรายวิชาทั้งหมดในหลักสูตรจัดกลุ่มตาม ปี/เทอม (สามารถกรองตามหลักสูตรได้)"""
    curr_id = curriculum_id or DEFAULT_CURRICULUM_ID
    stmt = (
        select(CurriculumCourse)
        .join(Course)
        .options(
            selectinload(CurriculumCourse.course).selectinload(Course.prerequisites),
        )
        .where(CurriculumCourse.curriculum_id == curr_id)
        .order_by(CurriculumCourse.year, CurriculumCourse.semester, CurriculumCourse.course_code)
    )

    result = await db.execute(stmt)
    cc_rows = result.scalars().all()
    curriculum_codes = {cc.course_code: cc.year for cc in cc_rows}

    # group into terms
    terms: dict[tuple[int | None, int | None, str | None], list[CourseOut]] = {}
    for cc in cc_rows:
        key = (cc.year, cc.semester, cc.plan_type)
        terms.setdefault(key, []).append(_course_to_out(cc.course, curriculum_codes, cc=cc))

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
    curr_id = curriculum_id or DEFAULT_CURRICULUM_ID
    stmt = (
        select(CurriculumCourse)
        .join(Course)
        .options(
            selectinload(CurriculumCourse.course).selectinload(Course.prerequisites),
        )
        .where(CurriculumCourse.curriculum_id == curr_id)
    )

    if year is not None:
        stmt = stmt.where(CurriculumCourse.year == year)
    if semester is not None:
        stmt = stmt.where(CurriculumCourse.semester == semester)
    if search:
        term = f"%{search}%"
        stmt = stmt.where(
            Course.course_code.ilike(term)
            | Course.course_name_th.ilike(term)
            | Course.course_name_en.ilike(term)
        )

    sort_col = {
        "code": CurriculumCourse.course_code,
        "credit": Course.credit,
        "year": CurriculumCourse.year,
    }.get(sort, CurriculumCourse.course_code)
    stmt = stmt.order_by(sort_col)

    result = await db.execute(stmt)
    cc_rows = result.scalars().all()
    curriculum_codes = {cc.course_code: cc.year for cc in cc_rows}
    return [_course_to_out(cc.course, curriculum_codes, cc=cc) for cc in cc_rows]


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

    # Try to find junction record for context
    cc_result = await db.execute(
        select(CurriculumCourse).where(CurriculumCourse.course_code == course_code).limit(1)
    )
    cc = cc_result.scalars().first()
    return _course_to_out(course, cc=cc)

