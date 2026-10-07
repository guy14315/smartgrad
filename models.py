"""SQLAlchemy ORM models for SmartGrad."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ---------------------------------------------------------------------------
# Curriculum
# ---------------------------------------------------------------------------

class Curriculum(Base):
    """หลักสูตร (แยกตามปี)"""
    __tablename__ = "curriculums"

    curriculum_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_credits_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_credits_per_semester: Mapped[int | None] = mapped_column(Integer, nullable=True)

    courses: Mapped[list["Course"]] = relationship(
        secondary="curriculum_courses", back_populates="curriculums", viewonly=True,
    )
    curriculum_courses: Mapped[list["CurriculumCourse"]] = relationship(
        back_populates="curriculum", cascade="all, delete-orphan",
    )
    students: Mapped[list["Student"]] = relationship(back_populates="curriculum")
    categories: Mapped[list["CurriculumCategory"]] = relationship(
        back_populates="curriculum", cascade="all, delete-orphan",
    )


class CurriculumCategory(Base):
    """หมวดวิชาของหลักสูตร – กำหนดเกณฑ์หน่วยกิตขั้นต่ำต่อหมวดในแต่ละหลักสูตร"""
    __tablename__ = "curriculum_categories"

    curriculum_id: Mapped[str] = mapped_column(ForeignKey("curriculums.curriculum_id"), primary_key=True)
    category_name: Mapped[str] = mapped_column(String(50), primary_key=True)      # e.g. "ge", "core_cs", "major_core"
    required_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    curriculum: Mapped["Curriculum"] = relationship(back_populates="categories")


class Course(Base):
    """รายวิชา – ข้อมูลวิชาแท้ๆ (ไม่ขึ้นกับหลักสูตร)"""
    __tablename__ = "courses"

    course_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    course_name_th: Mapped[str] = mapped_column(String(255), nullable=False)
    course_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    credit_str: Mapped[str | None] = mapped_column(String(20), nullable=True)   # e.g. "3(2-2-5)"
    credit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # parsed credit hours
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # relationships
    curriculums: Mapped[list["Curriculum"]] = relationship(
        secondary="curriculum_courses", back_populates="courses", viewonly=True,
    )
    curriculum_courses: Mapped[list["CurriculumCourse"]] = relationship(
        back_populates="course", cascade="all, delete-orphan",
    )
    prerequisites: Mapped[list["Prerequisite"]] = relationship(
        "Prerequisite", foreign_keys="Prerequisite.course_code", back_populates="course", cascade="all, delete-orphan"
    )
    transcript_courses: Mapped[list["TranscriptCourse"]] = relationship(back_populates="course_ref")


class CurriculumCourse(Base):
    """Junction table: วิชาอยู่ในหลักสูตรไหน พร้อมข้อมูลเฉพาะหลักสูตร (M:N)"""
    __tablename__ = "curriculum_courses"

    curriculum_id: Mapped[str] = mapped_column(
        ForeignKey("curriculums.curriculum_id", ondelete="CASCADE"), primary_key=True,
    )
    course_code: Mapped[str] = mapped_column(
        ForeignKey("courses.course_code", ondelete="CASCADE"), primary_key=True,
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plan_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    curriculum: Mapped["Curriculum"] = relationship(back_populates="curriculum_courses")
    course: Mapped["Course"] = relationship(back_populates="curriculum_courses")


class Prerequisite(Base):
    """ความสัมพันธ์ prereq: course_code ต้องการ prereq_code ก่อน (Recursive M:N)"""
    __tablename__ = "prerequisites"

    course_code: Mapped[str] = mapped_column(
        ForeignKey("courses.course_code", ondelete="CASCADE"), primary_key=True,
    )
    prereq_code: Mapped[str] = mapped_column(
        ForeignKey("courses.course_code", ondelete="CASCADE"), primary_key=True,
    )

    course: Mapped["Course"] = relationship(
        "Course", foreign_keys=[course_code], back_populates="prerequisites",
    )
    prereq_course: Mapped["Course"] = relationship(
        "Course", foreign_keys=[prereq_code],
    )


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

class Advisor(Base):
    """อาจารย์ที่ปรึกษา"""
    __tablename__ = "advisors"

    advisor_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cohort_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    students: Mapped[list["Student"]] = relationship(back_populates="advisor")


class AdvisorCredential(Base):
    """ข้อมูลเข้าสู่ระบบสำหรับอาจารย์ที่ปรึกษา (ใช้เฉพาะ demo ในปัจจุบัน)"""
    __tablename__ = "advisor_credentials"

    advisor_id: Mapped[str] = mapped_column(
        ForeignKey("advisors.advisor_id"), primary_key=True
    )
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class Student(Base):
    """นักศึกษา"""
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admission_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisor_id: Mapped[str | None] = mapped_column(ForeignKey("advisors.advisor_id"), nullable=True)
    curriculum_id: Mapped[str | None] = mapped_column(ForeignKey("curriculums.curriculum_id"), nullable=True)
    transcript_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    advisor: Mapped["Advisor | None"] = relationship(back_populates="students")
    curriculum: Mapped["Curriculum | None"] = relationship(back_populates="students")
    student_courses: Mapped[list["TranscriptCourse"]] = relationship(
        back_populates="student", cascade="all, delete-orphan",
    )



# ---------------------------------------------------------------------------
# Student courses (parsed from transcript PDF)
# ---------------------------------------------------------------------------

class TranscriptCourse(Base):
    """รายวิชาที่ parse จาก transcript – ผูกตรงกับนักศึกษา (ไม่เก็บประวัติรอบอัปโหลด)"""
    __tablename__ = "transcript_courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False)
    course_code: Mapped[str] = mapped_column(ForeignKey("courses.course_code"), nullable=False)
    course_name_raw: Mapped[str] = mapped_column(String(255), nullable=False)  # name as-parsed
    credit: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_overridden: Mapped[bool] = mapped_column(default=False)  # แก้ไขโดยนักศึกษา

    student: Mapped["Student"] = relationship(back_populates="student_courses")
    course_ref: Mapped["Course | None"] = relationship(back_populates="transcript_courses")



