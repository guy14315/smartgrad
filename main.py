"""SmartGrad – FastAPI application entry point.

Startup:
  1. Create all DB tables (SQLite)
  2. Seed curriculum data from init.sql script (first run only)

HTML Routes:
  - GET  /          → index page (upload form)
  - POST /review    → parse PDF → return JSON for review/edit
  - POST /confirm   → receive edited courses JSON → return full dashboard

REST API:
  - /api/curriculum, /api/students, /api/advisors
"""

import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import delete

from dashboard import compute_dashboard, compute_study_plan
from database import AsyncSessionLocal, engine
from models import Base, Course, Student, TranscriptCourse
from parser import parse_student_info, parse_transcript
from routers import advisors, curriculum, students
from seed import seed_curriculum
from services import load_curriculum_dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_curriculum(session)
    yield
    await engine.dispose()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SmartGrad API",
    description=(
        "ระบบตรวจสอบสถานะการสำเร็จการศึกษา SmartGrad\n\n"
        "- **นักศึกษา**: ตรวจสอบความก้าวหน้า, prerequisite, วางแผน, จำลองสถานะ\n"
        "- **อาจารย์ที่ปรึกษา**: ดูนักศึกษา, รายงาน, บันทึกคำแนะนำ"
    ),
    version="3.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "smartgrad-demo-session-secret"),
    https_only=os.environ.get("SESSION_HTTPS_ONLY", "false").lower() == "true",
)

from fastapi.middleware.cors import CORSMiddleware

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"error": "เกิดข้อผิดพลาดภายในระบบ"})

templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# HTML routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/advisor", include_in_schema=False)
def advisor_page(request: Request):
    return templates.TemplateResponse(request, "advisor.html")


@app.get("/search", include_in_schema=False)
def search_page(request: Request):
    return templates.TemplateResponse(request, "search.html")


@app.post("/review", include_in_schema=False)
async def review_transcript(request: Request, file: UploadFile = File(...)):
    """Step 1: Parse PDF → return JSON list of courses for user to review/edit."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        return JSONResponse(status_code=400, content={"error": "กรุณาอัปโหลดไฟล์ .pdf เท่านั้น"})

    try:
        student = parse_student_info(file.file)
        courses = parse_transcript(file.file)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"อ่านไฟล์ไม่สำเร็จ: {e}"})

    return JSONResponse(content={"courses": courses, "student": student})


@app.post("/confirm", include_in_schema=False)
async def confirm_courses(request: Request):
    """Step 2: Receive edited courses list as JSON → compute full dashboard."""
    try:
        body = await request.json()
        courses = body.get("courses", [])
        curriculum_id = body.get("curriculum_id")
        student_id = body.get("student_id")
    except Exception:
        return JSONResponse(status_code=400, content={"error": "ข้อมูลไม่ถูกต้อง"})

    async with AsyncSessionLocal() as session:
        curriculum_dict = await load_curriculum_dict(session, curriculum_id=curriculum_id)

        if student_id:
            student = await session.get(Student, student_id)
            if student:
                await session.execute(
                    delete(TranscriptCourse).where(TranscriptCourse.student_id == student_id)
                )
                for c in courses:
                    code = (c.get("code") or "").strip()
                    if not code:
                        continue
                    course_obj = await session.get(Course, code)
                    if not course_obj:
                        course_obj = Course(
                            course_code=code,
                            course_name_th=c.get("name_th") or c.get("name_en") or code,
                            course_name_en=c.get("name_en") or c.get("name_th") or code,
                            credit=int(c.get("credit") or 0),
                        )
                        session.add(course_obj)
                        await session.flush()
                    tc = TranscriptCourse(
                        student_id=student_id,
                        course_code=code,
                        course_name_raw=c.get("name_th") or c.get("name_en") or code,
                        credit=int(c.get("credit") or 0),
                        grade=c.get("grade") or None,
                        semester=c.get("semester"),
                        academic_year=c.get("academic_year"),
                        is_overridden=bool(c.get("is_overridden", False)),
                    )
                    session.add(tc)
                await session.commit()

    dashboard = compute_dashboard(courses, curriculum_dict)
    return JSONResponse(content=dashboard)


@app.post("/plan", include_in_schema=False)
async def study_plan(request: Request):
    """Compute a semester-by-semester study plan for remaining courses."""
    try:
        body = await request.json()
        courses = body.get("courses", [])
        plan_type = body.get("plan_type", "normal")
        curriculum_id = body.get("curriculum_id")
    except Exception:
        return JSONResponse(status_code=400, content={"error": "ข้อมูลไม่ถูกต้อง"})

    async with AsyncSessionLocal() as session:
        curriculum_dict = await load_curriculum_dict(session, curriculum_id=curriculum_id)
    plan = compute_study_plan(courses, curriculum_dict, plan_type)
    return JSONResponse(content=plan)


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

app.include_router(curriculum.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(advisors.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

