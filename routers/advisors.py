"""API router: อาจารย์ที่ปรึกษา – login, รายงาน และส่งคำแนะนำ"""

import asyncio
import hashlib
import os
import smtplib
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Advisor, AdvisorCredential, AdvisorNote, Student, Transcript, TranscriptCourse

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


class LoginIn(BaseModel):
    advisor_id: str
    password: str


class NoteIn(BaseModel):
    subject: str
    message: str

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

@router.post("/login", summary="เข้าสู่ระบบอาจารย์ที่ปรึกษา")
async def login(body: LoginIn, request: Request, db: AsyncSession = Depends(get_db)):
    credential = await db.get(AdvisorCredential, body.advisor_id)
    password_hash = hashlib.sha256(body.password.encode()).hexdigest()
    if not credential or credential.password_hash != password_hash:
        raise HTTPException(status_code=401, detail="รหัสอาจารย์หรือรหัสผ่านไม่ถูกต้อง")
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
    """
    ดูรายชื่อนักศึกษาในความดูแลทั้งหมด พร้อม:
    - สถานะการอัปโหลด Transcript (มี/ยังไม่มี)
    - วันที่อัปโหลดล่าสุด
    - หน่วยกิตผ่าน vs หน่วยกิตที่หลักสูตรกำหนด
    ครอบคลุม requirement: ทราบวันที่อัปโหลดล่าสุด, ดูรายชื่อพร้อมสถานะ
    """
    _require_advisor_login(request, advisor_id)
    await _get_advisor_or_404(advisor_id, db)
    result = await db.execute(
        select(Student).where(Student.advisor_id == advisor_id)
    )
    students = result.scalars().all()

    response = []
    for s in students:
        transcript = await _get_active_transcript(s.student_id, db)
        # หน้าอาจารย์เห็นเฉพาะนักศึกษาที่อัปโหลด Transcript แล้ว
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
    request: Request,
    min_credits: int = 120,
    db: AsyncSession = Depends(get_db),
):
    """
    นักศึกษาที่ผ่านหน่วยกิตครบ min_credits (ค่าเริ่มต้น 120)
    ครอบคลุม requirement: ทราบรายชื่อนักศึกษาที่หน่วยกิตครบตามเงื่อนไข
    """
    _require_advisor_login(request, advisor_id)
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
async def advisor_summary(advisor_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """
    ภาพรวมทั้งหมดของนักศึกษาในความดูแล:
    - จำนวนทั้งหมด / มี transcript / ยังไม่มี
    ครอบคลุม requirement: ดูรายงานสรุปภาพรวมของนักศึกษาในความดูแล
    """
    _require_advisor_login(request, advisor_id)
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


def _send_email(recipient: str, subject: str, message: str) -> None:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("ยังไม่ได้ตั้งค่า SMTP_HOST และ SMTP_FROM")

    email = EmailMessage()
    email["From"] = sender
    email["To"] = recipient
    email["Subject"] = subject
    email.set_content(message)
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as server:
        if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
            server.starttls()
        username, password = os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD")
        if username and password:
            server.login(username, password)
        server.send_message(email)


@router.post("/{advisor_id}/students/{student_id}/notes", status_code=201, summary="ส่งคำแนะนำให้นักศึกษาทางอีเมล")
async def send_note(
    advisor_id: str,
    student_id: str,
    body: NoteIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _require_advisor_login(request, advisor_id)
    if not student_id.isdigit() or len(student_id) != 8:
        raise HTTPException(status_code=400, detail="รหัสนักศึกษาต้องเป็นตัวเลข 8 หลัก")
    student_result = await db.execute(
        select(Student).where(Student.student_id == student_id, Student.advisor_id == advisor_id)
    )
    if not student_result.scalars().first() or not await _get_active_transcript(student_id, db):
        raise HTTPException(status_code=404, detail="ไม่พบนักศึกษาที่อัปโหลด Transcript ในความดูแล")

    recipient = f"{student_id}@kmitl.ac.th"
    try:
        await asyncio.to_thread(_send_email, recipient, body.subject, body.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=502, detail="ส่งอีเมลไม่สำเร็จ โปรดตรวจสอบการตั้งค่า SMTP") from exc

    note = AdvisorNote(advisor_id=advisor_id, student_id=student_id, subject=body.subject,
                       message=body.message, recipient_email=recipient)
    db.add(note)
    await db.commit()
    return {"message": "ส่งคำแนะนำทางอีเมลแล้ว", "recipient_email": recipient, "sent_at": note.sent_at}
