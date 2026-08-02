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
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from dashboard import compute_dashboard, compute_study_plan
from database import AsyncSessionLocal, engine
from models import Base, Course
from parser import parse_transcript
from routers import advisors, curriculum, students
from seed import seed_curriculum


# ---------------------------------------------------------------------------
# Helper: load curriculum dict from DB
# ---------------------------------------------------------------------------

async def _load_curriculum_dict_from_db() -> dict:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Course)
            .options(selectinload(Course.prerequisites))
            .order_by(Course.year, Course.semester)
        )
        all_courses = result.scalars().all()

    terms: dict[tuple, list] = {}
    for c in all_courses:
        key = (c.year, c.semester, c.plan_type)
        terms.setdefault(key, []).append(c)

    return {
        "curriculum": [
            {
                "year": k[0],
                "semester": k[1],
                "plan_type": k[2] or "",
                "courses": [
                    {
                        "course_code": c.course_code,
                        "course_name_th": c.course_name_th,
                        "course_name_en": c.course_name_en,
                        "credit": c.credit_str,
                        "prerequisites": [p.prereq_code for p in c.prerequisites],
                    }
                    for c in v
                ],
            }
            for k, v in sorted(terms.items())
        ]
    }


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

templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# HTML routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/review", include_in_schema=False)
async def review_transcript(request: Request, file: UploadFile = File(...)):
    """Step 1: Parse PDF → return JSON list of courses for user to review/edit."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        return JSONResponse(status_code=400, content={"error": "กรุณาอัปโหลดไฟล์ .pdf เท่านั้น"})

    try:
        courses = parse_transcript(file.file)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"อ่านไฟล์ไม่สำเร็จ: {e}"})

    return JSONResponse(content={"courses": courses})


@app.post("/confirm", include_in_schema=False)
async def confirm_courses(request: Request):
    """Step 2: Receive edited courses list as JSON → compute full dashboard."""
    try:
        body = await request.json()
        courses = body.get("courses", [])
    except Exception:
        return JSONResponse(status_code=400, content={"error": "ข้อมูลไม่ถูกต้อง"})

    curriculum_dict = await _load_curriculum_dict_from_db()
    dashboard = compute_dashboard(courses, curriculum_dict)
    return JSONResponse(content=dashboard)


@app.post("/plan", include_in_schema=False)
async def study_plan(request: Request):
    """Compute a semester-by-semester study plan for remaining courses."""
    try:
        body = await request.json()
        courses = body.get("courses", [])
        plan_type = body.get("plan_type", "normal")
    except Exception:
        return JSONResponse(status_code=400, content={"error": "ข้อมูลไม่ถูกต้อง"})

    curriculum_dict = await _load_curriculum_dict_from_db()
    plan = compute_study_plan(courses, curriculum_dict, plan_type)
    return JSONResponse(content=plan)


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

app.include_router(curriculum.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(advisors.router, prefix="/api")
