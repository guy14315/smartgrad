"""API router: อาจารย์ที่ปรึกษา – ดูนักศึกษา, รายงาน, คำแนะนำ"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Advisor, Student, Transcript, TranscriptCourse

router = APIRouter(prefix="/advisors", tags=["Advisors"])

NON_PASSING = {"F", "W", "WU", "U"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AdvisorCreate(BaseModel):
    advisor_id: str
    name: str
    email: str | None = None
    cohort_year: int | None = None


class AdvisorOut(BaseModel):
    advisor_id: str
    name: str
    email: str | None
    cohort_year: int | None

    model_config = {"from_attributes": True}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_advisor_or_404(advisor_id: str, db: AsyncSession) -> Advisor:
    result = await db.execute(select(Advisor).where(Advisor.advisor_id == advisor_id))
    advisor = result.scalars().first()
    if not advisor:
        raise HTTPException(status_code=404, detail=f"ไม่พบอาจารย์ {advisor_id}")
    return advisor


async def _get_active_transcript(student_id: str, db: AsyncSession) -> Transcript | None:
    result = await db.execute(
        select(Transcript)
        .options(selectinload(Transcript.courses))
        .where(Transcript.student_id == student_id, Transcript.is_active == True)
        .order_by(Transcript.uploaded_at.desc())
    )
    return result.scalars().first()


def _compute_credits(courses: list[TranscriptCourse]) -> tuple[int, int]:
    """คืน (passed_credits, total_attempted_credits)"""
    passed = sum(c.credit for c in courses if c.grade and c.grade.upper() not in NON_PASSING)
    total = sum(c.credit for c in courses)
    return passed, total


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=AdvisorOut, status_code=201, summary="สร้างโปรไฟล์อาจารย์ที่ปรึกษา")
async def create_advisor(body: AdvisorCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Advisor).where(Advisor.advisor_id == body.advisor_id))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="อาจารย์นี้มีอยู่แล้วในระบบ")
    advisor = Advisor(advisor_id=body.advisor_id, name=body.name, email=body.email)
    db.add(advisor)
    await db.commit()
    await db.refresh(advisor)
    return advisor


@router.get("/{advisor_id}", response_model=AdvisorOut, summary="ดูข้อมูลอาจารย์")
async def get_advisor(advisor_id: str, db: AsyncSession = Depends(get_db)):
    return await _get_advisor_or_404(advisor_id, db)


@router.get("/{advisor_id}/students", summary="รายชื่อนักศึกษาในความดูแล พร้อมสถานะ Transcript")
async def list_students(advisor_id: str, db: AsyncSession = Depends(get_db)):
    """
    ดูรายชื่อนักศึกษาในความดูแลทั้งหมด พร้อม:
    - สถานะการอัปโหลด Transcript (มี/ยังไม่มี)
    - วันที่อัปโหลดล่าสุด
    - หน่วยกิตผ่าน vs หน่วยกิตที่หลักสูตรกำหนด
    ครอบคลุม requirement: ทราบวันที่อัปโหลดล่าสุด, ดูรายชื่อพร้อมสถานะ
    """
    await _get_advisor_or_404(advisor_id, db)
    result = await db.execute(
        select(Student).where(Student.advisor_id == advisor_id)
    )
    students = result.scalars().all()

    response = []
    for s in students:
        transcript = await _get_active_transcript(s.student_id, db)
        if transcript:
            passed, _ = _compute_credits(transcript.courses)
            response.append({
                "student_id": s.student_id,
                "name": s.name,
                "has_transcript": True,
                "last_uploaded_at": transcript.uploaded_at,
                "passed_credits": passed,
                "courses_in_transcript": len(transcript.courses),
            })
        else:
            response.append({
                "student_id": s.student_id,
                "name": s.name,
                "has_transcript": False,
                "last_uploaded_at": None,
                "passed_credits": 0,
                "courses_in_transcript": 0,
            })
    return {"advisor_id": advisor_id, "students": response, "total": len(response)}


@router.get("/{advisor_id}/students/{student_id}", summary="รายงานสรุปนักศึกษารายคน")
async def get_student_report(
    advisor_id: str,
    student_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    รายงานสรุปสำหรับอาจารย์:
    - หน่วยกิตสะสม
    - วิชาที่ผ่าน แยกตามปี/เทอม
    - วิชาที่สอบไม่ผ่านหรือถอน
    ครอบคลุม requirement: ค้นหาด้วยรหัสนักศึกษา, วิชาที่สอบไม่ผ่าน/ถอน
    """
    await _get_advisor_or_404(advisor_id, db)

    s_result = await db.execute(
        select(Student).where(Student.student_id == student_id, Student.advisor_id == advisor_id)
    )
    student = s_result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="ไม่พบนักศึกษา หรือนักศึกษาไม่ได้อยู่ในความดูแลของอาจารย์ท่านนี้")

    transcript = await _get_active_transcript(student_id, db)
    if not transcript:
        return {"student_id": student_id, "name": student.name, "message": "ยังไม่มี Transcript"}

    passed_courses = [
        {"code": tc.course_code, "name": tc.course_name_raw, "credit": tc.credit, "grade": tc.grade}
        for tc in transcript.courses
        if tc.grade and tc.grade.upper() not in NON_PASSING
    ]
    failed_courses = [
        {"code": tc.course_code, "name": tc.course_name_raw, "credit": tc.credit, "grade": tc.grade}
        for tc in transcript.courses
        if tc.grade and tc.grade.upper() in NON_PASSING
    ]

    passed_credits = sum(c["credit"] for c in passed_courses)

    return {
        "student_id": student_id,
        "name": student.name,
        "passed_credits": passed_credits,
        "passed_courses_count": len(passed_courses),
        "failed_or_withdrawn_count": len(failed_courses),
        "passed_courses": passed_courses,
        "failed_or_withdrawn_courses": failed_courses,
        "transcript_uploaded_at": transcript.uploaded_at,
    }


@router.get("/{advisor_id}/ready-to-graduate", summary="รายชื่อนักศึกษาที่หน่วยกิตครบ")
async def ready_to_graduate(
    advisor_id: str,
    min_credits: int = 120,
    db: AsyncSession = Depends(get_db),
):
    """
    นักศึกษาที่ผ่านหน่วยกิตครบ min_credits (ค่าเริ่มต้น 120)
    ครอบคลุม requirement: ทราบรายชื่อนักศึกษาที่หน่วยกิตครบตามเงื่อนไข
    """
    await _get_advisor_or_404(advisor_id, db)
    result = await db.execute(select(Student).where(Student.advisor_id == advisor_id))
    students = result.scalars().all()

    ready = []
    for s in students:
        transcript = await _get_active_transcript(s.student_id, db)
        if not transcript:
            continue
        passed_credits, _ = _compute_credits(transcript.courses)
        if passed_credits >= min_credits:
            ready.append({
                "student_id": s.student_id,
                "name": s.name,
                "passed_credits": passed_credits,
            })

    return {
        "advisor_id": advisor_id,
        "min_credits_threshold": min_credits,
        "ready_to_graduate": ready,
        "total": len(ready),
    }





@router.get("/{advisor_id}/summary", summary="รายงานภาพรวมนักศึกษาในความดูแล")
async def advisor_summary(advisor_id: str, db: AsyncSession = Depends(get_db)):
    """
    ภาพรวมทั้งหมดของนักศึกษาในความดูแล:
    - จำนวนทั้งหมด / มี transcript / ยังไม่มี
    ครอบคลุม requirement: ดูรายงานสรุปภาพรวมของนักศึกษาในความดูแล
    """
    await _get_advisor_or_404(advisor_id, db)
    result = await db.execute(select(Student).where(Student.advisor_id == advisor_id))
    students = result.scalars().all()

    total = len(students)
    with_transcript = 0
    without_transcript = 0
    total_passed_credits = 0

    for s in students:
        transcript = await _get_active_transcript(s.student_id, db)
        if transcript:
            with_transcript += 1
            passed, _ = _compute_credits(transcript.courses)
            total_passed_credits += passed
        else:
            without_transcript += 1

    return {
        "advisor_id": advisor_id,
        "total_students": total,
        "students_with_transcript": with_transcript,
        "students_without_transcript": without_transcript,
        "average_passed_credits": round(total_passed_credits / with_transcript, 1) if with_transcript else 0,
    }
