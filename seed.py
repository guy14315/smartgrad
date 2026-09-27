"""Seed the database using init.sql script.

อ่านและรันสคริปต์ SQL จากไฟล์ init.sql เพื่อสร้าง Schema และ Seed ข้อมูลรายวิชา
"""

import logging
from pathlib import Path

from sqlalchemy import inspect, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    ALTERNATIVE_CODES,
    CORE_MATH_CODES,
    GE_PREFIX,
    CORE_CS_PREFIX,
    TOTAL_CREDITS_TARGET,
    MAX_CREDITS_PER_SEMESTER,
)
from models import Course, Curriculum, CurriculumCategory, CurriculumCourse, TranscriptCourse

logger = logging.getLogger(__name__)

INIT_SQL_PATH = Path(__file__).parent / "init.sql"


async def _get_table_columns(session: AsyncSession, table_name: str) -> set[str]:
    """Get column names for a table using SQLAlchemy inspect (database-agnostic)."""
    def _inspect_sync(sync_session):
        insp = inspect(sync_session.connection())
        if not insp.has_table(table_name):
            return set()
        return {col["name"] for col in insp.get_columns(table_name)}
    return await session.run_sync(_inspect_sync)


async def _table_exists(session: AsyncSession, table_name: str) -> bool:
    """Check if a table exists (database-agnostic)."""
    def _inspect_sync(sync_session):
        insp = inspect(sync_session.connection())
        return insp.has_table(table_name)
    return await session.run_sync(_inspect_sync)


async def run_migrations(session: AsyncSession) -> None:
    """Migrate existing schema if new columns/tables are missing.

    Uses SQLAlchemy inspect() API instead of raw SQL for cross-database compatibility.
    """
    # --- Migrate: ensure curriculum_courses junction table exists ---
    if not await _table_exists(session, "curriculum_courses"):
        logger.info("[seed] Creating curriculum_courses junction table")
        await session.run_sync(
            lambda sync_session: CurriculumCourse.__table__.create(sync_session.connection(), checkfirst=True)
        )

    # --- Migrate curriculums table: add new columns if missing ---
    curr_cols = await _get_table_columns(session, "curriculums")
    if curr_cols:
        if "total_credits_target" not in curr_cols:
            logger.info("[seed] Adding total_credits_target column to curriculums table")
            await session.execute(text("ALTER TABLE curriculums ADD COLUMN total_credits_target INTEGER"))
        if "max_credits_per_semester" not in curr_cols:
            logger.info("[seed] Adding max_credits_per_semester column to curriculums table")
            await session.execute(text("ALTER TABLE curriculums ADD COLUMN max_credits_per_semester INTEGER"))

    # --- Migrate students table: add transcript metadata columns if missing ---
    student_cols = await _get_table_columns(session, "students")
    if student_cols:
        if "transcript_filename" not in student_cols:
            logger.info("[seed] Adding transcript_filename column to students table")
            await session.execute(text("ALTER TABLE students ADD COLUMN transcript_filename VARCHAR(255)"))
        if "last_uploaded_at" not in student_cols:
            logger.info("[seed] Adding last_uploaded_at column to students table")
            await session.execute(text("ALTER TABLE students ADD COLUMN last_uploaded_at DATETIME"))

    # --- Migrate transcript_courses table: recreate if using old transcript_id schema or add columns ---
    tc_cols = await _get_table_columns(session, "transcript_courses")
    if tc_cols and ("transcript_id" in tc_cols or "student_id" not in tc_cols):
        logger.info("[seed] Migrating transcript_courses table to student_id schema")
        await session.execute(text("DROP TABLE IF EXISTS transcript_courses"))
        await session.execute(text("DROP TABLE IF EXISTS transcripts"))
        await session.run_sync(
            lambda sync_session: TranscriptCourse.__table__.create(sync_session.connection(), checkfirst=True)
        )
    elif tc_cols:
        if "semester" not in tc_cols:
            logger.info("[seed] Adding semester column to transcript_courses table")
            await session.execute(text("ALTER TABLE transcript_courses ADD COLUMN semester INTEGER"))
        if "academic_year" not in tc_cols:
            logger.info("[seed] Adding academic_year column to transcript_courses table")
            await session.execute(text("ALTER TABLE transcript_courses ADD COLUMN academic_year VARCHAR(20)"))


    # --- Ensure curriculum_categories table exists and matches new lean schema ---
    cat_cols = await _get_table_columns(session, "curriculum_categories")
    if cat_cols and ("category_code" in cat_cols or "id" in cat_cols or "category_name" not in cat_cols):
        logger.info("[seed] Migrating curriculum_categories table to category_name schema")
        await session.execute(text("DROP TABLE IF EXISTS curriculum_categories"))
        await session.run_sync(
            lambda sync_session: CurriculumCategory.__table__.create(sync_session.connection(), checkfirst=True)
        )
    elif not cat_cols:
        logger.info("[seed] Creating curriculum_categories table")
        await session.run_sync(
            lambda sync_session: CurriculumCategory.__table__.create(sync_session.connection(), checkfirst=True)
        )

    # --- Populate NULL categories on curriculum_courses using ORM update ---
    try:
        null_count_result = await session.execute(
            select(CurriculumCourse).where(CurriculumCourse.category.is_(None))
        )
        null_entries = null_count_result.scalars().all()
        if null_entries:
            count = len(null_entries)
            logger.info(f"[seed] Populating category for {count} curriculum_courses with NULL category")

            # Core math courses
            await session.execute(
                update(CurriculumCourse)
                .where(CurriculumCourse.course_code.in_(CORE_MATH_CODES))
                .values(category="core_math")
            )
            # Alternative courses
            await session.execute(
                update(CurriculumCourse)
                .where(CurriculumCourse.course_code.in_(ALTERNATIVE_CODES))
                .values(category="alternative")
            )
            # GE courses (prefix-based)
            await session.execute(
                update(CurriculumCourse)
                .where(CurriculumCourse.course_code.startswith(GE_PREFIX), CurriculumCourse.category.is_(None))
                .values(category="ge")
            )
            # Core CS courses (prefix-based, with year assigned)
            await session.execute(
                update(CurriculumCourse)
                .where(
                    CurriculumCourse.course_code.startswith(CORE_CS_PREFIX),
                    CurriculumCourse.category.is_(None),
                    CurriculumCourse.year.isnot(None),
                )
                .values(category="core_cs")
            )
            # Elective CS courses (prefix-based, no year)
            await session.execute(
                update(CurriculumCourse)
                .where(
                    CurriculumCourse.course_code.startswith(CORE_CS_PREFIX),
                    CurriculumCourse.category.is_(None),
                )
                .values(category="elective")
            )
            # Everything else → free elective
            await session.execute(
                update(CurriculumCourse)
                .where(CurriculumCourse.category.is_(None))
                .values(category="free")
            )

        # Set default curriculum config for CS2564
        await session.execute(
            update(Curriculum)
            .where(
                Curriculum.curriculum_id == "CS2564",
                (Curriculum.total_credits_target.is_(None)) | (Curriculum.max_credits_per_semester.is_(None)),
            )
            .values(
                total_credits_target=TOTAL_CREDITS_TARGET,
                max_credits_per_semester=MAX_CREDITS_PER_SEMESTER,
            )
        )
    except Exception as e:
        logger.debug(f"[seed] Migration category populate: {e}")

    await session.commit()


async def seed_curriculum(session: AsyncSession) -> None:
    """อ่านไฟล์ init.sql และรันคำสั่ง SQL เพื่อสร้าง Schema และข้อมูลหลักสูตร"""
    await run_migrations(session)

    # ตรวจสอบว่ามีข้อมูลวิชาและ junction table อยู่แล้วหรือยัง (ใช้ ORM query)
    result = await session.execute(select(Course).limit(1))
    has_curriculum = result.scalars().first() is not None

    result_cc = await session.execute(select(CurriculumCourse).limit(1))
    has_curriculum_courses = result_cc.scalars().first() is not None

    if not INIT_SQL_PATH.exists():
        logger.warning(f"[seed] Warning: {INIT_SQL_PATH} not found.")
        return

    sql_script = INIT_SQL_PATH.read_text(encoding="utf-8")
    
    # แยกแต่ละคำสั่ง SQL ด้วยเครื่องหมาย ;
    # NOTE: init.sql ยังคงใช้ raw SQL เพราะเป็น seed data จำนวนมาก
    # ที่ไม่เหมาะจะแปลงเป็น ORM objects ทีละ row
    statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]
    for statement in statements:
        # ข้ามคำสั่งสร้าง TABLE หาก SQLAlchemy สร้างไปแล้ว
        if statement.upper().startswith("CREATE TABLE"):
            continue
        # หากมีหลักสูตรแล้ว ให้ seed เฉพาะบัญชีอาจารย์, categories, junction table, และ prerequisites
        statement_upper = statement.upper()
        is_always_seed = (
            "INSERT OR IGNORE INTO ADVISORS" in statement_upper
            or "INSERT OR IGNORE INTO ADVISOR_CREDENTIALS" in statement_upper
            or "UPDATE ADVISORS SET COHORT_YEAR" in statement_upper
            or "INSERT OR IGNORE INTO CURRICULUM_CATEGORIES" in statement_upper
            or "INSERT OR IGNORE INTO CURRICULUM_COURSES" in statement_upper
            or "INSERT OR IGNORE INTO PREREQUISITES" in statement_upper
        )
        if has_curriculum and has_curriculum_courses and not is_always_seed:
            continue
        try:
            await session.execute(text(statement))
        except Exception as e:
            logger.error(f"[seed] Failed to execute SQL statement: {e}")
            logger.debug(f"[seed] Statement: {statement[:200]}")
            continue

    await session.commit()
    logger.info(f"[seed] Executed SQL statements from {INIT_SQL_PATH.name} successfully.")
