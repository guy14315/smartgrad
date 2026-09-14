"""API router: นักศึกษา – transcript upload, dashboard, planning, simulation"""

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dashboard import compute_dashboard
from models import (
    Advisor,
    Course,
    Curriculum,
    Prerequisite,
    Student,
    Transcript,
    TranscriptCourse,
)
from parser import parse_transcript
from config import BUDDHIST_ERA_OFFSET, COURSE_CODE_PATTERN, DEFAULT_CURRICULUM_ID, MAX_UPLOAD_SIZE_BYTES, NON_PASSING_GRADES, VALID_GRADES_PATTERN
from services import get_active_transcript, load_curriculum_dict, transcript_courses_to_list

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/students", tags=["Students"])



# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class StudentCreate(BaseModel):
    student_id: str
    name: str
    email: str | None = None
    admission_year: int | None = None
    advisor_id: str | None = None
    curriculum_id: str | None = None


class StudentOut(BaseModel):
    student_id: str
    name: str
    email: str | None
    admission_year: int | None
    advisor_id: str | None
    curriculum_id: str | None

    model_config = {"from_attributes": True}


class TranscriptHistoryOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class CourseOverrideIn(BaseModel):
    grade: str

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v: str) -> str:
        v_clean = v.strip().upper()
        if not VALID_GRADES_PATTERN.match(v_clean):
            raise ValueError("รูปแบบเกรดไม่ถูกต้อง (เช่น A, B+, B, C+, C, D+, D, F, S, U, W)")
        return v_clean


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




# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=StudentOut, status_code=201, summary="สร้างโปรไฟล์นักศึกษาใหม่")
async def create_student(body: StudentCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Student).where(Student.student_id == body.student_id))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="นักศึกษานี้มีอยู่แล้วในระบบ")
    student = Student(
        student_id=body.student_id,
        name=body.name,
        email=body.email,
        admission_year=body.admission_year,
        advisor_id=body.advisor_id,
        curriculum_id=body.curriculum_id
    )
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
    student_name: str = Form(""),
    curriculum_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """อัปโหลดได้โดยไม่ต้องมีบัญชีนักศึกษา และเลือกอาจารย์จากปีในรหัสนักศึกษา"""
    if not student_id.isdigit() or len(student_id) != 8:
        raise HTTPException(status_code=400, detail="กรุณาระบุรหัสนักศึกษาเป็นตัวเลข 8 หลัก")

    result = await db.execute(select(Student).where(Student.student_id == student_id))
    student = result.scalars().first()
    if not student:
        admission_year = BUDDHIST_ERA_OFFSET + int(student_id[:2])
        advisor_result = await db.execute(
            select(Advisor).where(Advisor.cohort_year == admission_year)
        )
        advisor = advisor_result.scalars().first()

        # Resolve curriculum: user-supplied > latest curriculum with year <= admission_year > default
        resolved_curriculum_id = curriculum_id
        if not resolved_curriculum_id:
            curr_res = await db.execute(
                select(Curriculum)
                .where(Curriculum.year <= admission_year)
                .order_by(Curriculum.year.desc())
            )
            matched_curr = curr_res.scalars().first()
            resolved_curriculum_id = matched_curr.curriculum_id if matched_curr else DEFAULT_CURRICULUM_ID
        
        student = Student(
            student_id=student_id,
            name=student_name.strip() or f"นักศึกษา {student_id}",
            email=f"{student_id}@kmitl.ac.th",
            admission_year=admission_year,
            advisor_id=advisor.advisor_id if advisor else None,
            curriculum_id=resolved_curriculum_id,
        )
        db.add(student)
        await db.flush()
    elif curriculum_id and student.curriculum_id != curriculum_id:
        student.curriculum_id = curriculum_id

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="กรุณาอัปโหลดไฟล์ .pdf เท่านั้น")

    # Check file size
    file.file.seek(0, 2)  # seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # seek back to start
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"ไฟล์มีขนาดใหญ่เกินไป (สูงสุด {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB)")

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
            # parser returns the English transcript title; accept either key
            # to support manually reviewed/imported course records as well.
            course_name_raw=pc.get("name_th") or pc.get("name_en") or pc["code"],
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
        "advisor_id": student.advisor_id,
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
    student = await _get_student_or_404(student_id, db)
    transcript = await get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript ในระบบ กรุณาอัปโหลดก่อน")

    parsed_courses = transcript_courses_to_list(transcript.courses)
    curriculum = await load_curriculum_dict(db, curriculum_id=student.curriculum_id)
    return compute_dashboard(parsed_courses, curriculum)


@router.get("/{student_id}/transcript-courses", summary="ดูรายวิชาที่ parse จาก Transcript ล่าสุด")
async def get_transcript_courses(student_id: str, db: AsyncSession = Depends(get_db)):
    """ดูรายการวิชาที่ระบบ parse ได้ – สามารถตรวจสอบความถูกต้องก่อนประมวลผล"""
    await _get_student_or_404(student_id, db)
    transcript = await get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript")
    return {
        "transcript_id": transcript.id,
        "filename": transcript.filename,
        "uploaded_at": transcript.uploaded_at,
        "courses": transcript_courses_to_list(transcript.courses),
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
    transcript = await get_active_transcript(student_id, db)
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
    student = await _get_student_or_404(student_id, db)
    transcript = await get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript")

    passed_codes = {
        tc.course_code
        for tc in transcript.courses
        if tc.grade and tc.grade.upper() not in NON_PASSING_GRADES
    }

    stmt = (
        select(Course)
        .options(selectinload(Course.prerequisites))
        .order_by(Course.year, Course.semester, Course.course_code)
    )
    if student.curriculum_id:
        stmt = stmt.where(Course.curriculum_id == student.curriculum_id)
    result = await db.execute(stmt)
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
    student = await _get_student_or_404(student_id, db)
    for code in body.current_course_codes:
        if not COURSE_CODE_PATTERN.match(code):
            raise HTTPException(status_code=400, detail=f"รหัสวิชาไม่ถูกต้อง: {code}")

    transcript = await get_active_transcript(student_id, db)
    if not transcript:
        raise HTTPException(status_code=404, detail="ยังไม่มี Transcript")

    parsed_courses = transcript_courses_to_list(transcript.courses)

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
    curriculum = await load_curriculum_dict(db, curriculum_id=student.curriculum_id)
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
