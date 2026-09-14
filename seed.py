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
from models import Course, Curriculum, CurriculumCategory

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
    # --- Migrate courses table: add 'category' column if missing ---
    course_cols = await _get_table_columns(session, "courses")
    if course_cols and "category" not in course_cols:
        logger.info("[seed] Adding category column to courses table")
        await session.execute(text("ALTER TABLE courses ADD COLUMN category VARCHAR(50)"))

    # --- Migrate curriculums table: add new columns if missing ---
    curr_cols = await _get_table_columns(session, "curriculums")
    if curr_cols:
        if "total_credits_target" not in curr_cols:
            logger.info("[seed] Adding total_credits_target column to curriculums table")
            await session.execute(text("ALTER TABLE curriculums ADD COLUMN total_credits_target INTEGER"))
        if "max_credits_per_semester" not in curr_cols:
            logger.info("[seed] Adding max_credits_per_semester column to curriculums table")
            await session.execute(text("ALTER TABLE curriculums ADD COLUMN max_credits_per_semester INTEGER"))

    # --- Ensure curriculum_categories table exists ---
    if not await _table_exists(session, "curriculum_categories"):
        logger.info("[seed] Creating curriculum_categories table")
        await session.run_sync(
            lambda sync_session: CurriculumCategory.__table__.create(sync_session.connection(), checkfirst=True)
        )

    # --- Populate NULL categories using ORM update ---
    try:
        null_count_result = await session.execute(
            select(Course).where(Course.category.is_(None))
        )
        null_courses = null_count_result.scalars().all()
        if null_courses:
            count = len(null_courses)
            logger.info(f"[seed] Populating category for {count} courses with NULL category")

            # Core math courses
            await session.execute(
                update(Course)
                .where(Course.course_code.in_(CORE_MATH_CODES))
                .values(category="core_math")
            )
            # Alternative courses
            await session.execute(
                update(Course)
                .where(Course.course_code.in_(ALTERNATIVE_CODES))
                .values(category="alternative")
            )
            # GE courses (prefix-based)
            await session.execute(
                update(Course)
                .where(Course.course_code.startswith(GE_PREFIX), Course.category.is_(None))
                .values(category="ge")
            )
            # Core CS courses (prefix-based, with year assigned)
            await session.execute(
                update(Course)
                .where(
                    Course.course_code.startswith(CORE_CS_PREFIX),
                    Course.category.is_(None),
                    Course.year.isnot(None),
                )
                .values(category="core_cs")
            )
            # Elective CS courses (prefix-based, no year)
            await session.execute(
                update(Course)
                .where(
                    Course.course_code.startswith(CORE_CS_PREFIX),
                    Course.category.is_(None),
                )
                .values(category="elective")
            )
            # Everything else → free elective
            await session.execute(
                update(Course)
                .where(Course.category.is_(None))
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

    # ตรวจสอบว่ามีข้อมูลวิชาอยู่แล้วหรือยัง (ใช้ ORM query)
    result = await session.execute(select(Course).limit(1))
    has_curriculum = result.scalars().first() is not None

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
        # หากมีหลักสูตรแล้ว ให้ seed เฉพาะบัญชีอาจารย์และ curriculum_categories ใน init.sql
        statement_upper = statement.upper()
        is_always_seed = (
            "INSERT OR IGNORE INTO ADVISORS" in statement_upper
            or "INSERT OR IGNORE INTO ADVISOR_CREDENTIALS" in statement_upper
            or "UPDATE ADVISORS SET COHORT_YEAR" in statement_upper
            or "INSERT OR IGNORE INTO CURRICULUM_CATEGORIES" in statement_upper
        )
        if has_curriculum and not is_always_seed:
            continue
        try:
            await session.execute(text(statement))
        except Exception as e:
            logger.error(f"[seed] Failed to execute SQL statement: {e}")
            logger.debug(f"[seed] Statement: {statement[:200]}")
            continue

    await session.commit()
    logger.info(f"[seed] Executed SQL statements from {INIT_SQL_PATH.name} successfully.")
