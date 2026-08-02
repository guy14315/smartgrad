"""API router: นักศึกษา – transcript upload, dashboard, planning, simulation"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dashboard import compute_dashboard
from models import (
    Course,
    Prerequisite,
    Student,
    Transcript,
    TranscriptCourse,
)
from parser import parse_transcript

router = APIRouter(prefix="/students", tags=["Students"])

NON_PASSING = {"F", "W", "WU", "U"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class StudentCreate(BaseModel):
    student_id: str
    name: str
    advisor_id: str | None = None


class StudentOut(BaseModel):
    student_id: str
    name: str
    advisor_id: str | None

    model_config = {"from_attributes": True}


class TranscriptHistoryOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class CourseOverrideIn(BaseModel):
    grade: str


class SimulateIn(BaseModel):
    current_course_codes: list[str]  # วิชาที่กำลังเรียนอยู่ (นับว่าผ่าน)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_student_or_404(student_id: str, db: AsyncSession) -> Student:
    result = await db.execute(select(Student).where(Student.student_id == student_id))
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail=f"ไม่พบนักศึกษา {student_id}")
    return student


async def _get_active_transcript(student_id: str, db: AsyncSession) -> Transcript | None:
    result = await db.execute(
        select(Transcript)
        .options(selectinload(Transcript.courses))
        .where(Transcript.student_id == student_id, Transcript.is_active == True)
        .order_by(Transcript.uploaded_at.desc())
    )
    return result.scalars().first()


async def _load_curriculum_dict(db: AsyncSession) -> dict:
    """โหลด curriculum จาก DB แล้ว format ให้ dashboard.compute_dashboard รับได้"""
    result = await db.execute(
        select(Course).options(selectinload(Course.prerequisites)).order_by(Course.year, Course.semester)
    )
    courses = result.scalars().all()

    terms: dict[tuple, list] = {}
    for c in courses:
        key = (c.year, c.semester, c.plan_type)
        terms.setdefault(key, []).append(c)

    curriculum_list = []
    for (year, semester, plan_type), term_courses in sorted(terms.items()):
        curriculum_list.append({
            "year": year,
            "semester": semester,
            "plan_type": plan_type or "",
            "courses": [
                {
                    "course_code": c.course_code,
                    "course_name_th": c.course_name_th,
                    "course_name_en": c.course_name_en,
                    "credit": c.credit_str,
                    "prerequisites": [p.prereq_code for p in c.prerequisites],
                    "prereq_source": c.prereq_source,
                }
                for c in term_courses
            ],
        })
    return {"curriculum": curriculum_list}


def _transcript_courses_to_list(tc_list: list[TranscriptCourse]) -> list[dict]:
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
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=StudentOut, status_code=201, summary="สร้างโปรไฟล์นักศึกษาใหม่")
async def create_student(body: StudentCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Student).where(Student.student_id == body.student_id))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="นักศึกษานี้มีอยู่แล้วในระบบ")
    student = Student(student_id=body.student_id, name=body.name, advisor_id=body.advisor_id)
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentOut, summary="ดูข้อมูลนักศึกษา")
async def get_student(student_id: str, db: AsyncSession = Depends(get_db)):
    return await _get_student_or_404(student_id, db)


@router.post("/{student_id}/transcript", summary="อัปโหลด Transcript PDF")
async def upload_transcript(
    student_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """อัปโหลด Transcript PDF ใหม่ – ปิด active เดิม แล้วสร้างอันใหม่"""
    await _get_student_or_404(student_id, db)

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="กรุณาอัปโหลดไฟล์ .pdf เท่านั้น")

    # parse PDF
    parsed_courses = parse_transcript(file.file)

    # deactivate old transcripts
    old = await db.execute(
        select(Transcript).where(Transcript.student_id == student_id, Transcript.is_active == True)
    )
    for t in old.scalars().all():
        t.is_active = False

    # create new transcript record
    transcript = Transcript(
        student_id=student_id,
        filename=file.filename or "transcript.pdf",
        is_active=True,
    )
    db.add(transcript)
    await db.flush()

    # save parsed courses
    for pc in parsed_courses:
        tc = TranscriptCourse(
            transcript_id=transcript.id,
            course_code=pc["code"],
            course_name_raw=pc["name_th"],
            credit=pc["credit"],
            grade=pc.get("grade"),
        )
        db.add(tc)

    await db.commit()
    return {
        "message": "อัปโหลด Transcript สำเร็จ",
        "transcript_id": transcript.id,
        "courses_parsed": len(parsed_courses),
        "uploaded_at": transcript.uploaded_at,
    }


@router.get("/{student_id}/transcripts", response_model=list[TranscriptHistoryOut], summary="ประวัติการอัปโหลด Transcript")
async def list_transcripts(student_id: str, db: AsyncSession = Depends(get_db)):
    await _get_student_or_404(student_id, db)
    result = await db.execute(
        select(Transcript)
        .where(Transcript.student_id == student_id)
        .order_by(Transcript.uploaded_at.desc())
    )
    return result.scalars().all()


@router.get("/{student_id}/dashboard", summary="ดู Dashboard ความก้าวหน้าการเรียน")
async def get_dashboard(student_id: str, db: AsyncSession = Depends(get_db)):
    """
    แสดง:
    - วิชาที่ผ่านแล้ว / ทั้งหมด
    - หน่วยกิตสะสม / เป้าหมาย
    - % ความก้าวหน้า
    - รายวิชาที่เหลือพร้อมสถานะ Prerequisite
    """
    await _get_student_or_404(student_id, db)
    transcript = await _get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript ในระบบ กรุณาอัปโหลดก่อน")

    parsed_courses = _transcript_courses_to_list(transcript.courses)
    curriculum = await _load_curriculum_dict(db)
    return compute_dashboard(parsed_courses, curriculum)


@router.get("/{student_id}/transcript-courses", summary="ดูรายวิชาที่ parse จาก Transcript ล่าสุด")
async def get_transcript_courses(student_id: str, db: AsyncSession = Depends(get_db)):
    """ดูรายการวิชาที่ระบบ parse ได้ – สามารถตรวจสอบความถูกต้องก่อนประมวลผล"""
    await _get_student_or_404(student_id, db)
    transcript = await _get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript")
    return {
        "transcript_id": transcript.id,
        "filename": transcript.filename,
        "uploaded_at": transcript.uploaded_at,
        "courses": _transcript_courses_to_list(transcript.courses),
    }


@router.put("/{student_id}/transcript-courses/{course_code}", summary="แก้ไขผลเรียนที่ parse ผิดพลาด")
async def override_course_grade(
    student_id: str,
    course_code: str,
    body: CourseOverrideIn,
    db: AsyncSession = Depends(get_db),
):
    """แก้ไขเกรดของวิชาที่ระบบ parse ผิด – is_overridden จะถูก set เป็น True"""
    await _get_student_or_404(student_id, db)
    transcript = await _get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript")

    for tc in transcript.courses:
        if tc.course_code == course_code:
            tc.grade = body.grade
            tc.is_overridden = True
            await db.commit()
            return {"message": f"อัปเดตเกรดวิชา {course_code} เป็น {body.grade} สำเร็จ"}

    raise HTTPException(status_code=404, detail=f"ไม่พบวิชา {course_code} ใน Transcript ล่าสุด")


@router.get("/{student_id}/plan", summary="แนะนำวิชาสำหรับลงทะเบียนเทอมถัดไป")
async def get_next_semester_plan(student_id: str, db: AsyncSession = Depends(get_db)):
    """
    วางแผนการศึกษาล่วงหน้า:
    - กรองเฉพาะวิชาที่ Prerequisite ครบแล้ว
    - เรียงตามลำดับ year/semester ของหลักสูตร
    """
    await _get_student_or_404(student_id, db)
    transcript = await _get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript")

    passed_codes = {
        tc.course_code
        for tc in transcript.courses
        if tc.grade and tc.grade.upper() not in NON_PASSING
    }

    result = await db.execute(
        select(Course)
        .options(selectinload(Course.prerequisites))
        .order_by(Course.year, Course.semester, Course.course_code)
    )
    all_courses = result.scalars().all()

    recommendations = []
    for c in all_courses:
        if c.course_code in passed_codes:
            continue
        if c.plan_type and "Co-op" in c.plan_type:
            continue
        missing_prereqs = [p.prereq_code for p in c.prerequisites if p.prereq_code not in passed_codes]
        if not missing_prereqs:
            recommendations.append({
                "course_code": c.course_code,
                "course_name_th": c.course_name_th,
                "credit": c.credit,
                "year": c.year,
                "semester": c.semester,
                "prereq_status": "พร้อมลงเรียนได้",
            })

    return {"recommended_courses": recommendations, "total": len(recommendations)}


@router.post("/{student_id}/simulate", summary="จำลองสถานะโดยนับรวมวิชาที่กำลังเรียน")
async def simulate_progress(
    student_id: str,
    body: SimulateIn,
    db: AsyncSession = Depends(get_db),
):
    """
    จำลองสถานะความก้าวหน้าหากวิชาที่กำลังเรียนถูกนับเป็น 'ผ่าน'
    ช่วย requirement: นักศึกษาต้องสามารถจำลองสถานะความก้าวหน้าโดยนับรวมรายวิชาที่กำลังศึกษา
    """
    await _get_student_or_404(student_id, db)
    transcript = await _get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript")

    parsed_courses = _transcript_courses_to_list(transcript.courses)

    # inject simulated courses with grade "S" (passing)
    existing_codes = {c["code"] for c in parsed_courses}
    result = await db.execute(
        select(Course).where(Course.course_code.in_(body.current_course_codes))
    )
    current_courses = result.scalars().all()

    for c in current_courses:
        if c.course_code not in existing_codes:
            parsed_courses.append({
                "code": c.course_code,
                "name_th": c.course_name_th,
                "credit": c.credit,
                "grade": "S",  # simulated pass
            })

    curriculum = await _load_curriculum_dict(db)
    dashboard = compute_dashboard(parsed_courses, curriculum)
    dashboard["simulated"] = True
    dashboard["simulated_courses"] = body.current_course_codes
    return dashboard


@router.get("/{student_id}/withdrawal-impact/{course_code}", summary="ผลกระทบหากถอนวิชา")
async def withdrawal_impact(
    student_id: str,
    course_code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    แสดงผลกระทบของการถอนวิชา:
    - วิชาอื่นที่ใช้วิชานี้เป็น Prerequisite และยังไม่ได้เรียน
    ช่วย requirement: นักศึกษาต้องสามารถทราบผลกระทบก่อนตัดสินใจถอนรายวิชา
    """
    await _get_student_or_404(student_id, db)

    # find courses that have this course as prereq
    result = await db.execute(
        select(Prerequisite).where(Prerequisite.prereq_code == course_code)
    )
    prereq_entries = result.scalars().all()

    impacted_codes = [p.course_code for p in prereq_entries]
    impacted_courses = []
    if impacted_codes:
        res2 = await db.execute(
            select(Course).where(Course.course_code.in_(impacted_codes))
        )
        impacted_courses = [
            {"course_code": c.course_code, "course_name_th": c.course_name_th, "credit": c.credit}
            for c in res2.scalars().all()
        ]

    return {
        "course_code": course_code,
        "impacted_courses": impacted_courses,
        "impact_count": len(impacted_courses),
        "warning": f"การถอนวิชา {course_code} อาจส่งผลต่อ {len(impacted_courses)} วิชาที่ใช้เป็น Prerequisite" if impacted_courses else "ไม่มีวิชาอื่นที่ได้รับผลกระทบ",
    }
