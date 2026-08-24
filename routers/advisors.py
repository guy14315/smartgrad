"""API router: อาจารย์ที่ปรึกษา – login, รายงาน"""

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from config import NON_PASSING_GRADES
from services import compute_credits, get_active_transcript, hash_password, verify_password
from models import Advisor, AdvisorCredential, Student, Transcript

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advisors", tags=["Advisors"])


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


class LoginIn(BaseModel):
    advisor_id: str
    password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_advisor_or_404(advisor_id: str, db: AsyncSession) -> Advisor:
    result = await db.execute(select(Advisor).where(Advisor.advisor_id == advisor_id))
    advisor = result.scalars().first()
    if not advisor:
        raise HTTPException(status_code=404, detail=f"ไม่พบอาจารย์ {advisor_id}")
    return advisor


def _require_advisor_login(request: Request, advisor_id: str) -> None:
    """อนุญาตให้อาจารย์ดูได้เฉพาะข้อมูลของบัญชีตนเอง"""
    if request.session.get("advisor_id") != advisor_id:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบด้วยบัญชีอาจารย์ที่ถูกต้อง")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", summary="เข้าสู่ระบบอาจารย์ที่ปรึกษา")
async def login(body: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    credential = await db.get(AdvisorCredential, body.advisor_id)
    if not credential or not verify_password(body.password, credential.password_hash):
        raise HTTPException(status_code=401, detail="รหัสอาจารย์หรือรหัสผ่านไม่ถูกต้อง")
    
    # Auto-upgrade legacy hash to PBKDF2 if verified with legacy format
    if not credential.password_hash.startswith("pbkdf2_sha256$"):
        credential.password_hash = hash_password(body.password)
        await db.commit()

    advisor = await _get_advisor_or_404(body.advisor_id, db)
    request.session["advisor_id"] = advisor.advisor_id
    return {"advisor_id": advisor.advisor_id, "name": advisor.name}


@router.post("/logout", summary="ออกจากระบบอาจารย์ที่ปรึกษา")
async def logout(request: Request):
    request.session.clear()
    return {"message": "ออกจากระบบแล้ว"}


@router.get("/me", summary="ข้อมูลบัญชีที่เข้าสู่ระบบ")
async def current_advisor(request: Request, db: AsyncSession = Depends(get_db)):
    advisor_id = request.session.get("advisor_id")
    if not advisor_id:
        raise HTTPException(status_code=401, detail="กรุณาเข้าสู่ระบบ")
    advisor = await _get_advisor_or_404(advisor_id, db)
    return {"advisor_id": advisor.advisor_id, "name": advisor.name}

@router.post("", response_model=AdvisorOut, status_code=201, summary="สร้างโปรไฟล์อาจารย์ที่ปรึกษา")
async def create_advisor(body: AdvisorCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Advisor).where(Advisor.advisor_id == body.advisor_id))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="อาจารย์นี้มีอยู่แล้วในระบบ")
    advisor = Advisor(advisor_id=body.advisor_id, name=body.name, email=body.email, cohort_year=body.cohort_year)
    db.add(advisor)
    await db.commit()
    await db.refresh(advisor)
    return advisor


@router.get("/{advisor_id}", response_model=AdvisorOut, summary="ดูข้อมูลอาจารย์")
async def get_advisor(advisor_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    _require_advisor_login(request, advisor_id)
    return await _get_advisor_or_404(advisor_id, db)


@router.get("/{advisor_id}/students", summary="รายชื่อนักศึกษาในความดูแล พร้อมสถานะ Transcript")
async def list_students(advisor_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    _require_advisor_login(request, advisor_id)
    await _get_advisor_or_404(advisor_id, db)
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.transcripts).selectinload(Transcript.courses)
        )
        .where(Student.advisor_id == advisor_id)
    )
    students = result.scalars().unique().all()

    response = []
    for s in students:
        active = next(
            (t for t in sorted(s.transcripts, key=lambda t: t.uploaded_at, reverse=True) if t.is_active),
            None,
        )
        if active:
            passed, _ = compute_credits(active.courses)
            response.append({
                "student_id": s.student_id,
                "name": s.name,
                "has_transcript": True,
                "last_uploaded_at": active.uploaded_at,
                "passed_credits": passed,
                "courses_in_transcript": len(active.courses),
            })
    return {"advisor_id": advisor_id, "students": response, "total": len(response)}


@router.get("/{advisor_id}/students/{student_id}", summary="รายงานสรุปนักศึกษารายคน")
async def get_student_report(
    advisor_id: str,
    student_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    รายงานสรุปสำหรับอาจารย์:
    - หน่วยกิตสะสม
    - วิชาที่ผ่าน แยกตามปี/เทอม
    - วิชาที่สอบไม่ผ่านหรือถอน
    ครอบคลุม requirement: ค้นหาด้วยรหัสนักศึกษา, วิชาที่สอบไม่ผ่าน/ถอน
    """
    _require_advisor_login(request, advisor_id)
    await _get_advisor_or_404(advisor_id, db)

    s_result = await db.execute(
        select(Student).where(Student.student_id == student_id, Student.advisor_id == advisor_id)
    )
    student = s_result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="ไม่พบนักศึกษา หรือนักศึกษาไม่ได้อยู่ในความดูแลของอาจารย์ท่านนี้")

    transcript = await get_active_transcript(student_id, db)
    if not transcript:
        return {"student_id": student_id, "name": student.name, "message": "ยังไม่มี Transcript"}

    passed_courses = [
        {"code": tc.course_code, "name": tc.course_name_raw, "credit": tc.credit, "grade": tc.grade}
        for tc in transcript.courses
        if tc.grade and tc.grade.upper() not in NON_PASSING_GRADES
    ]
    failed_courses = [
        {"code": tc.course_code, "name": tc.course_name_raw, "credit": tc.credit, "grade": tc.grade}
        for tc in transcript.courses
        if tc.grade and tc.grade.upper() in NON_PASSING_GRADES
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
    request: Request,
    min_credits: int = 120,
    db: AsyncSession = Depends(get_db),
):
    _require_advisor_login(request, advisor_id)
    await _get_advisor_or_404(advisor_id, db)
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.transcripts).selectinload(Transcript.courses)
        )
        .where(Student.advisor_id == advisor_id)
    )
    students = result.scalars().unique().all()

    ready = []
    for s in students:
        active = next(
            (t for t in sorted(s.transcripts, key=lambda t: t.uploaded_at, reverse=True) if t.is_active),
            None,
        )
        if not active:
            continue
        passed_credits, _ = compute_credits(active.courses)
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
async def advisor_summary(advisor_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    _require_advisor_login(request, advisor_id)
    await _get_advisor_or_404(advisor_id, db)
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.transcripts).selectinload(Transcript.courses)
        )
        .where(Student.advisor_id == advisor_id)
    )
    students = result.scalars().unique().all()

    total = len(students)
    with_transcript = 0
    without_transcript = 0
    total_passed_credits = 0

    for s in students:
        active = next(
            (t for t in sorted(s.transcripts, key=lambda t: t.uploaded_at, reverse=True) if t.is_active),
            None,
        )
        if active:
            with_transcript += 1
            passed, _ = compute_credits(active.courses)
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
