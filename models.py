"""SQLAlchemy ORM models for SmartGrad."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
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

    courses: Mapped[list["Course"]] = relationship(back_populates="curriculum")
    students: Mapped[list["Student"]] = relationship(back_populates="curriculum")


class Course(Base):
    """รายวิชาในหลักสูตร – SQL เป็น Source of Truth"""
    __tablename__ = "courses"

    course_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    curriculum_id: Mapped[str | None] = mapped_column(ForeignKey("curriculums.curriculum_id"), nullable=True)
    course_name_th: Mapped[str] = mapped_column(String(255), nullable=False)
    course_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    credit_str: Mapped[str] = mapped_column(String(20), nullable=False)   # e.g. "3(2-2-5)"
    credit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # parsed credit hours
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # None = normal
    prereq_source: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # relationships
    curriculum: Mapped["Curriculum | None"] = relationship(back_populates="courses")

    # relationships
    prerequisites: Mapped[list["Prerequisite"]] = relationship(
        "Prerequisite", foreign_keys="Prerequisite.course_code", back_populates="course", cascade="all, delete-orphan"
    )
    transcript_courses: Mapped[list["TranscriptCourse"]] = relationship(back_populates="course_ref")


class Prerequisite(Base):
    """ความสัมพันธ์ prereq: course_code ต้องการ prereq_code ก่อน"""
    __tablename__ = "prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(ForeignKey("courses.course_code"), nullable=False)
    prereq_code: Mapped[str] = mapped_column(String(20), nullable=False)

    course: Mapped["Course"] = relationship("Course", foreign_keys=[course_code], back_populates="prerequisites")


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


class Student(Base):
    """นักศึกษา"""
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admission_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    advisor_id: Mapped[str | None] = mapped_column(ForeignKey("advisors.advisor_id"), nullable=True)
    curriculum_id: Mapped[str | None] = mapped_column(ForeignKey("curriculums.curriculum_id"), nullable=True)

    advisor: Mapped["Advisor | None"] = relationship(back_populates="students")
    curriculum: Mapped["Curriculum | None"] = relationship(back_populates="students")
    transcripts: Mapped[list["Transcript"]] = relationship(back_populates="student", order_by="Transcript.uploaded_at.desc()")


# ---------------------------------------------------------------------------
# Transcripts
# ---------------------------------------------------------------------------

class Transcript(Base):
    """ประวัติการ upload transcript"""
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)  # latest = True

    student: Mapped["Student"] = relationship(back_populates="transcripts")
    courses: Mapped[list["TranscriptCourse"]] = relationship(back_populates="transcript", cascade="all, delete-orphan")


class TranscriptCourse(Base):
    """รายวิชาที่ parse จาก transcript"""
    __tablename__ = "transcript_courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transcript_id: Mapped[int] = mapped_column(ForeignKey("transcripts.id"), nullable=False)
    course_code: Mapped[str] = mapped_column(ForeignKey("courses.course_code"), nullable=False)
    course_name_raw: Mapped[str] = mapped_column(String(255), nullable=False)  # name as-parsed
    credit: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_overridden: Mapped[bool] = mapped_column(default=False)  # แก้ไขโดยนักศึกษา

    transcript: Mapped["Transcript"] = relationship(back_populates="courses")
    course_ref: Mapped["Course | None"] = relationship(back_populates="transcript_courses")



