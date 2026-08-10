"""Seed the database using init.sql script.

อ่านและรันสคริปต์ SQL จากไฟล์ init.sql เพื่อสร้าง Schema และ Seed ข้อมูลรายวิชา
"""

import logging
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from models import Course

logger = logging.getLogger(__name__)

INIT_SQL_PATH = Path(__file__).parent / "init.sql"


async def seed_curriculum(session: AsyncSession) -> None:
    """อ่านไฟล์ init.sql และรันคำสั่ง SQL เพื่อสร้าง Schema และข้อมูลหลักสูตร"""
    # ตรวจสอบว่ามีข้อมูลวิชาอยู่แล้วหรือยัง
    result = await session.execute(text("SELECT course_code FROM courses LIMIT 1"))
    has_curriculum = result.first() is not None

    if not INIT_SQL_PATH.exists():
        logger.warning(f"[seed] Warning: {INIT_SQL_PATH} not found.")
        return

    sql_script = INIT_SQL_PATH.read_text(encoding="utf-8")
    
    # แยกแต่ละคำสั่ง SQL ด้วยเครื่องหมาย ;
    statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]
    for statement in statements:
        # ข้ามคำสั่งสร้าง TABLE หาก SQLAlchemy สร้างไปแล้ว
        if statement.upper().startswith("CREATE TABLE"):
            continue
        # หากมีหลักสูตรแล้ว ให้ seed เฉพาะบัญชีอาจารย์ใน init.sql
        statement_upper = statement.upper()
        is_advisor_seed = (
            "INSERT OR IGNORE INTO ADVISORS" in statement_upper
            or "INSERT OR IGNORE INTO ADVISOR_CREDENTIALS" in statement_upper
            or "UPDATE ADVISORS SET COHORT_YEAR" in statement_upper
        )
        if has_curriculum and not is_advisor_seed:
            continue
        try:
            await session.execute(text(statement))
        except Exception as e:
            logger.error(f"[seed] Failed to execute SQL statement: {e}")
            logger.debug(f"[seed] Statement: {statement[:200]}")
            continue

    await session.commit()
    logger.info(f"[seed] Executed SQL statements from {INIT_SQL_PATH.name} successfully.")
