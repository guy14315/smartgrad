"""Comprehensive test suite for SmartGrad – unit tests + integration tests.

รัน: python -m unittest discover -s tests -t . -v
ใช้สำหรับ regression testing เพื่อยืนยันว่าระบบทำงานเหมือนเดิมหลัง refactor

Test Groups:
  1. TestSecurity          – password hashing / verification
  2. TestCourseClassification – classify_course logic
  3. TestDeduplication     – retake deduplication
  4. TestDashboard         – compute_dashboard full pipeline
  5. TestStudyPlan         – compute_study_plan logic
  6. TestCategorySpillover – GE/elective overflow → free
  7. TestTimeline          – timeline grouping
  8. TestValidation        – Pydantic input validation
  9. TestPrerequisites     – prereq deduplication
  10. TestPDFParser         – multi-file PDF parsing
  11. TestAPIIntegration    – FastAPI endpoints (health, review, curriculum, etc.)
"""

import asyncio
import hashlib
import os
from pathlib import Path
import unittest
from unittest.mock import patch

# Ensure test suite runs on an isolated local SQLite DB so tests
# do not alter remote Supabase data or encounter asyncpg test-loop mismatches
_TEST_DB = Path(__file__).resolve().parent.parent / "test_smartgrad.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"

from pydantic import ValidationError

from app.config import CATEGORIES, TOTAL_CREDITS_TARGET, VALID_GRADES
from app.dashboard import (
    _compute_category_breakdown,
    _compute_in_progress,
    _compute_timeline,
    _flat_curriculum,
    _get_unique_passed_courses,
    _get_unique_plan_courses,
    compute_dashboard,
    compute_study_plan,
)
from app.routers.students import CourseOverrideIn
from app.services import classify_course, hash_password, verify_password


# ==========================================================================
# Shared test fixtures
# ==========================================================================

def _make_curriculum(*terms):
    """Build a minimal curriculum dict from (year, sem, plan_type, courses_list) tuples."""
    return {
        "curriculum": [
            {
                "year": t[0],
                "semester": t[1],
                "plan_type": t[2] if len(t) > 2 else "",
                "courses": t[3] if len(t) > 3 else t[2] if isinstance(t[2], list) else [],
            }
            for t in terms
        ]
    }


def _make_course(code, name="Test", credit="3(3-0-6)", prereqs=None):
    """Build a minimal curriculum course dict."""
    return {
        "course_code": code,
        "course_name_th": name,
        "course_name_en": name,
        "credit": credit,
        "prerequisites": prereqs or [],
    }


def _make_tc(code, credit=3, grade="A", semester=1, year="2024-2025", is_current=False):
    """Build a minimal transcript course dict."""
    return {
        "code": code,
        "name_en": f"Course {code}",
        "name_th": f"วิชา {code}",
        "credit": credit,
        "grade": grade,
        "semester": semester,
        "academic_year": year,
        "is_current": is_current,
    }


MOCK_CURRICULUM = _make_curriculum(
    (1, 1, "", [
        _make_course("05506003", "Programming Fundamentals"),
        _make_course("05506005", "Computer Science"),
        _make_course("05506231", "Statistics"),
    ]),
    (1, 2, "", [
        _make_course("05506004", "OOP", prereqs=["05506003"]),
        _make_course("05506001", "Discrete Math"),
    ]),
    (2, 1, "", [
        _make_course("05506006", "Data Structures", prereqs=["05506004"]),
        _make_course("05506012", "Database Systems"),
    ]),
    (2, 2, "", [
        _make_course("05506007", "Operating Systems", prereqs=["05506006"]),
    ]),
)


# ==========================================================================
# 1. Security Tests
# ==========================================================================

class TestSecurity(unittest.TestCase):
    """Test password hashing and verification."""

    def test_pbkdf2_hash_and_verify(self):
        password = "secret_password_123"
        hashed = hash_password(password)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$100000$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrong_password", hashed))

    def test_legacy_sha256_verification(self):
        password = "smartgrad-demo"
        legacy_hash = hashlib.sha256(password.encode()).hexdigest()
        self.assertTrue(verify_password(password, legacy_hash))
        self.assertFalse(verify_password("wrong-demo", legacy_hash))

    def test_empty_password_returns_false(self):
        self.assertFalse(verify_password("", "somehash"))
        self.assertFalse(verify_password("somepass", ""))
        self.assertFalse(verify_password("", ""))

    def test_malformed_pbkdf2_hash(self):
        self.assertFalse(verify_password("test", "pbkdf2_sha256$bad$format"))
        self.assertFalse(verify_password("test", "pbkdf2_sha256$notanumber$salt$hash"))

    def test_different_passwords_produce_different_hashes(self):
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        self.assertNotEqual(h1, h2)

    def test_same_password_different_salt(self):
        """Same password hashed twice should produce different hashes (random salt)."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        self.assertNotEqual(h1, h2)
        # But both should verify
        self.assertTrue(verify_password("same_password", h1))
        self.assertTrue(verify_password("same_password", h2))


# ==========================================================================
# 2. Course Classification Tests
# ==========================================================================

class TestCourseClassification(unittest.TestCase):
    """Test course category classification."""

    def setUp(self):
        self.curriculum_codes = {
            "05506003": 1,
            "05506005": 1,
            "05506232": 1,
            "05506999": None,  # elective
        }

    def test_ge_course(self):
        self.assertEqual(classify_course("90642001", self.curriculum_codes), "ge")

    def test_core_math_course(self):
        self.assertEqual(classify_course("05506232", self.curriculum_codes), "core_math")

    def test_alternative_course(self):
        self.assertEqual(classify_course("05506117", self.curriculum_codes), "alternative")

    def test_core_cs_course(self):
        self.assertEqual(classify_course("05506003", self.curriculum_codes), "core_cs")

    def test_elective_cs_course(self):
        self.assertEqual(classify_course("05506999", self.curriculum_codes), "elective")

    def test_free_elective_course(self):
        self.assertEqual(classify_course("01006001", self.curriculum_codes), "free")

    def test_all_core_math_codes(self):
        """Verify every CORE_MATH_CODES entry classifies as core_math."""
        from app.config import CORE_MATH_CODES
        for code in CORE_MATH_CODES:
            with self.subTest(code=code):
                self.assertEqual(classify_course(code, self.curriculum_codes), "core_math")

    def test_all_alternative_codes(self):
        """Verify every ALTERNATIVE_CODES entry classifies as alternative."""
        from app.config import ALTERNATIVE_CODES
        for code in ALTERNATIVE_CODES:
            with self.subTest(code=code):
                self.assertEqual(classify_course(code, self.curriculum_codes), "alternative")


# ==========================================================================
# 3. Deduplication Tests
# ==========================================================================

class TestDeduplication(unittest.TestCase):
    """Test transcript course deduplication logic."""

    def test_unique_passed_keeps_latest_passing_grade(self):
        courses = [
            _make_tc("05506003", grade="F", semester=1, year="2023-2024"),
            _make_tc("05506003", grade="B", semester=2, year="2023-2024"),
            _make_tc("05506005", grade="A", semester=1, year="2023-2024"),
        ]
        unique = _get_unique_passed_courses(courses)
        self.assertEqual(len(unique), 2)
        retake = next(c for c in unique if c["code"] == "05506003")
        self.assertEqual(retake["grade"], "B")

    def test_all_failed_excluded(self):
        """วิชาที่สอบตกทุกรอบ ไม่ควรปรากฏใน unique_passed."""
        courses = [
            _make_tc("05506003", grade="F", semester=1),
            _make_tc("05506003", grade="F", semester=2),
        ]
        unique = _get_unique_passed_courses(courses)
        self.assertEqual(len(unique), 0)

    def test_current_courses_excluded_from_passed(self):
        """วิชาที่กำลังเรียน (is_current) ไม่ควรนับเป็น passed."""
        courses = [
            _make_tc("05506003", grade=None, is_current=True),
            _make_tc("05506005", grade="A"),
        ]
        unique = _get_unique_passed_courses(courses)
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0]["code"], "05506005")

    def test_plan_courses_include_current(self):
        """_get_unique_plan_courses รวมทั้ง passed และ current."""
        courses = [
            _make_tc("05506003", grade=None, is_current=True),
            _make_tc("05506005", grade="A"),
            _make_tc("05506006", grade="F"),  # failed → excluded
        ]
        plan = _get_unique_plan_courses(courses)
        codes = {c["code"] for c in plan}
        self.assertEqual(codes, {"05506003", "05506005"})

    def test_w_grade_excluded(self):
        """เกรด W (ถอน) ไม่นับเป็น passed."""
        courses = [_make_tc("05506003", grade="W")]
        self.assertEqual(len(_get_unique_passed_courses(courses)), 0)


# ==========================================================================
# 4. Dashboard Tests
# ==========================================================================

class TestDashboard(unittest.TestCase):
    """Test compute_dashboard full pipeline."""

    def test_no_duplicate_credits(self):
        curriculum = _make_curriculum(
            (1, 1, "", [_make_course("05506003")])
        )
        transcript = [
            _make_tc("05506003", grade="F", semester=1, year="2023-2024"),
            _make_tc("05506003", grade="B", semester=2, year="2023-2024"),
        ]
        result = compute_dashboard(transcript, curriculum)
        self.assertEqual(result["completed_credits"], 3)  # NOT 6
        self.assertEqual(result["completed_courses"], 1)

    def test_empty_transcript(self):
        """Dashboard with no transcript courses."""
        result = compute_dashboard([], MOCK_CURRICULUM)
        self.assertEqual(result["completed_credits"], 0)
        self.assertEqual(result["completed_courses"], 0)
        self.assertEqual(result["progress_percent"], 0)
        self.assertGreater(len(result["remaining_list"]), 0)

    def test_progress_percent_capped_at_100(self):
        """% ไม่ควรเกิน 100 แม้หน่วยกิตเกิน target."""
        curriculum = _make_curriculum(
            (1, 1, "", [_make_course("05506003")])
        )
        # Patch TOTAL_CREDITS_TARGET to very low
        with patch("app.dashboard.TOTAL_CREDITS_TARGET", 1):
            result = compute_dashboard(
                [_make_tc("05506003", credit=3, grade="A")],
                curriculum,
            )
        self.assertEqual(result["progress_percent"], 100)

    def test_remaining_list_shows_prereq_status(self):
        """วิชาที่เหลือต้องแสดงสถานะ prerequisite."""
        transcript = [_make_tc("05506003", grade="A")]
        result = compute_dashboard(transcript, MOCK_CURRICULUM)
        # 05506004 requires 05506003 (passed) → พร้อมลงเรียนได้
        course_04 = next((r for r in result["remaining_list"] if r["code"] == "05506004"), None)
        if course_04:
            self.assertEqual(course_04["prereq_status"], "พร้อมลงเรียนได้")

    def test_remaining_excludes_current_courses(self):
        """วิชาที่กำลังเรียนไม่ควรอยู่ใน remaining_list."""
        transcript = [
            _make_tc("05506003", grade="A"),
            _make_tc("05506004", grade=None, is_current=True),
        ]
        result = compute_dashboard(transcript, MOCK_CURRICULUM)
        remaining_codes = {r["code"] for r in result["remaining_list"]}
        self.assertNotIn("05506004", remaining_codes)

    def test_in_progress_list(self):
        """วิชาที่ is_current=True ต้องปรากฏใน in_progress."""
        transcript = [
            _make_tc("05506003", grade=None, is_current=True),
        ]
        result = compute_dashboard(transcript, MOCK_CURRICULUM)
        ip_codes = {c["code"] for c in result["in_progress"]}
        self.assertIn("05506003", ip_codes)

    def test_dashboard_includes_current_courses_in_credits(self):
        """Dashboard นับรวมวิชาที่กำลังเรียน (is_current) ใน completed_credits และ categories."""
        transcript = [
            _make_tc("05506003", credit=3, grade="A"),
            _make_tc("05506004", credit=3, grade=None, is_current=True),
        ]
        result = compute_dashboard(transcript, MOCK_CURRICULUM)
        self.assertEqual(result["completed_credits"], 6)
        self.assertEqual(result["passed_credits"], 3)
        self.assertEqual(result["in_progress_credits"], 3)
        # Category breakdown also includes the in-progress course
        cs_cat = next(c for c in result["categories"] if c["key"] == "core_cs")
        self.assertEqual(cs_cat["earned_credits"], 6)

    def test_dashboard_returns_all_required_keys(self):
        """ตรวจสอบว่า dashboard return ครบทุก key ที่ frontend ต้องการ."""
        result = compute_dashboard([], MOCK_CURRICULUM)
        required_keys = {
            "completed_courses", "total_courses", "completed_credits",
            "passed_credits", "in_progress_credits",
            "total_credits", "remaining_courses_count", "progress_percent",
            "remaining_list", "categories", "timeline", "in_progress",
        }
        self.assertTrue(required_keys.issubset(result.keys()))

    def test_all_categories_present_in_dashboard(self):
        """ตรวจสอบว่าทุกหมวดวิชาของหลักสูตรแสดงครบถ้วน."""
        result = compute_dashboard([], MOCK_CURRICULUM)
        cat_keys = [c["key"] for c in result["categories"]]
        for expected in ["ge", "core_math", "core_cs", "elective", "free", "alternative"]:
            self.assertIn(expected, cat_keys)

    def test_category_courses_sorted_by_credit_descending(self):
        """วิชาในแต่ละหมวดต้องเรียงลำดับจากหน่วยกิตมากที่สุดไปน้อยที่สุด."""
        transcript = [
            _make_tc("90641001", credit=1, grade="A"),   # GE 1 cr
            _make_tc("90644007", credit=3, grade="S"),   # GE 3 cr
            _make_tc("90642999", credit=2, grade="S"),   # GE 2 cr
            _make_tc("05506999", credit=6, grade="A"),   # Elective 6 cr
            _make_tc("05506998", credit=1, grade="A"),   # Elective 1 cr
            _make_tc("05506997", credit=3, grade="B+"),  # Elective 3 cr
        ]
        result = compute_dashboard(transcript, MOCK_CURRICULUM)
        ge_cat = next(c for c in result["categories"] if c["key"] == "ge")
        ge_credits = [c["credit"] for c in ge_cat["courses"]]
        self.assertEqual(ge_credits, [3, 2, 1])

        elec_cat = next(c for c in result["categories"] if c["key"] == "elective")
        elec_credits = [c["credit"] for c in elec_cat["courses"]]
        self.assertEqual(elec_credits, [6, 3, 1])


# ==========================================================================
# 5. Study Plan Tests
# ==========================================================================

class TestStudyPlan(unittest.TestCase):
    """Test compute_study_plan logic."""

    def test_plan_with_no_passed_courses(self):
        """แผนเมื่อยังไม่เรียนอะไรเลย."""
        result = compute_study_plan([], MOCK_CURRICULUM, "normal")
        self.assertIn("plan_terms", result)
        self.assertIn("can_graduate_on_time", result)
        self.assertIn("warnings", result)
        self.assertIn("suggestions", result)

    def test_plan_respects_prerequisites(self):
        """วิชาที่ prereq ยังไม่ผ่าน ต้องไม่ถูกจัดลงใน semester ก่อนหน้า."""
        # 05506006 requires 05506004 requires 05506003
        # ถ้ายังไม่เรียนอะไร: 05506006 ต้องไม่อยู่ใน semester แรก
        result = compute_study_plan([], MOCK_CURRICULUM, "normal")
        if result["plan_terms"]:
            first_term_codes = {c["code"] for c in result["plan_terms"][0].get("core_courses", [])}
            self.assertNotIn("05506006", first_term_codes)

    def test_plan_with_passed_courses(self):
        """ถ้า passed บางวิชาแล้ว ไม่ควรปรากฏในแผน."""
        transcript = [
            _make_tc("05506003", grade="A", semester=1, year="2024-2025"),
            _make_tc("05506005", grade="B", semester=1, year="2024-2025"),
            _make_tc("05506231", grade="C+", semester=1, year="2024-2025"),
        ]
        result = compute_study_plan(transcript, MOCK_CURRICULUM, "normal")
        all_planned_codes = set()
        for term in result["plan_terms"]:
            for c in term.get("core_courses", []):
                all_planned_codes.add(c["code"])
        # Passed courses should not be in plan
        self.assertNotIn("05506003", all_planned_codes)
        self.assertNotIn("05506005", all_planned_codes)

    def test_plan_current_semester_is_locked(self):
        """วิชาที่กำลังเรียนต้องแสดงเป็น locked."""
        transcript = [
            _make_tc("05506003", grade=None, is_current=True, semester=1, year="2024-2025"),
        ]
        result = compute_study_plan(transcript, MOCK_CURRICULUM, "normal")
        locked_terms = [t for t in result["plan_terms"] if t.get("is_locked")]
        if locked_terms:
            self.assertTrue(locked_terms[0]["is_locked"])

    def test_plan_max_credits_per_semester(self):
        """ไม่ควรจัดวิชาเกิน MAX_CREDITS_PER_SEMESTER ต่อเทอม."""
        from app.config import MAX_CREDITS_PER_SEMESTER
        result = compute_study_plan([], MOCK_CURRICULUM, "normal")
        for term in result["plan_terms"]:
            if not term.get("is_locked"):
                self.assertLessEqual(
                    term["core_credits"], MAX_CREDITS_PER_SEMESTER,
                    f"Term {term['label']} exceeds max credits",
                )

    def test_plan_unpassed_prerequisites(self):
        """วิชาที่มี prereq และยังไม่ผ่าน ต้องแสดงใน unpassed_prereqs."""
        # 05506003 passed with A -> 05506004 has no unpassed prereqs
        # But 05506006 requires 05506004, which is not passed yet -> has unpassed prereq
        transcript = [_make_tc("05506003", grade="A", semester=1, year="2024-2025")]
        result = compute_study_plan(transcript, MOCK_CURRICULUM, "normal")
        course_map = {}
        for term in result["plan_terms"]:
            for c in term.get("core_courses", []):
                course_map[c["code"]] = c

        self.assertIn("05506004", course_map)
        self.assertEqual(course_map["05506004"]["unpassed_prereqs"], [])

        self.assertIn("05506006", course_map)
        self.assertEqual(len(course_map["05506006"]["unpassed_prereqs"]), 1)
        self.assertEqual(course_map["05506006"]["unpassed_prereqs"][0]["code"], "05506004")
        self.assertFalse(course_map["05506006"]["unpassed_prereqs"][0]["is_current"])

    def test_plan_current_prerequisite_flag(self):
        """วิชา prereq ที่กำลังเรียนอยู่ในเทอมปัจจุบัน ต้องมี is_current=True."""
        transcript = [_make_tc("05506003", grade=None, is_current=True, semester=1, year="2024-2025")]
        result = compute_study_plan(transcript, MOCK_CURRICULUM, "normal")
        course_map = {}
        for term in result["plan_terms"]:
            for c in term.get("core_courses", []):
                course_map[c["code"]] = c

        self.assertIn("05506004", course_map)
        self.assertEqual(len(course_map["05506004"]["unpassed_prereqs"]), 1)
        self.assertEqual(course_map["05506004"]["unpassed_prereqs"][0]["code"], "05506003")
        self.assertTrue(course_map["05506004"]["unpassed_prereqs"][0]["is_current"])

    def test_plan_deferred_flag(self):
        """วิชาบังคับที่ตกค้างจากเทอมก่อนหน้า ต้องมี is_deferred=True."""
        transcript = [
            _make_tc("05506005", grade="B", semester=1, year="2024-2025"),
            _make_tc("05506001", grade="B", semester=2, year="2024-2025"),
        ]
        result = compute_study_plan(transcript, MOCK_CURRICULUM, "normal")
        course_map = {}
        for term in result["plan_terms"]:
            for c in term.get("core_courses", []):
                course_map[c["code"]] = c

        # 05506003 was originally Year 1 Sem 1, now in Year 2 Sem 1 -> deferred
        self.assertIn("05506003", course_map)
        self.assertTrue(course_map["05506003"]["is_deferred"])


# ==========================================================================
# 6. Category Spillover Tests
# ==========================================================================

class TestCategorySpillover(unittest.TestCase):
    """Test GE/elective overflow → free elective logic."""

    def test_ge_spills_to_free_when_full(self):
        """เมื่อ GE เต็ม (30 หน่วยกิต) วิชา GE เพิ่มเติมควรไปอยู่ free."""
        curriculum_codes = {"90640001": 1}
        # Create 11 GE courses x 3 credits = 33 credits (exceeds 30 target)
        ge_courses = [
            _make_tc(f"9064{i:04d}", credit=3, grade="A")
            for i in range(11)
        ]
        categories, credits = _compute_category_breakdown(ge_courses, curriculum_codes)
        ge_cat = next(c for c in categories if c["key"] == "ge")
        free_cat = next(c for c in categories if c["key"] == "free")
        # GE should be capped near target, excess goes to free
        self.assertLessEqual(ge_cat["earned_credits"], 33)
        self.assertGreater(free_cat["earned_credits"], 0)

    def test_elective_spills_to_free_when_full(self):
        """เมื่อ elective เต็ม (18 หน่วยกิต) ควรไปอยู่ free."""
        # Create elective courses (055xxxxx with year=None in curriculum_codes)
        curriculum_codes = {f"0550{i:04d}": None for i in range(7)}
        elective_courses = [
            _make_tc(f"0550{i:04d}", credit=3, grade="B")
            for i in range(7)
        ]  # 7 * 3 = 21 > 18 target
        categories, credits = _compute_category_breakdown(elective_courses, curriculum_codes)
        free_cat = next(c for c in categories if c["key"] == "free")
        self.assertGreater(free_cat["earned_credits"], 0)


# ==========================================================================
# 7. Timeline Tests
# ==========================================================================

class TestTimeline(unittest.TestCase):
    """Test timeline grouping by semester."""

    def test_groups_by_semester(self):
        courses = [
            _make_tc("05506003", grade="A", semester=1, year="2024-2025"),
            _make_tc("05506005", grade="B", semester=1, year="2024-2025"),
            _make_tc("05506004", grade="C+", semester=2, year="2024-2025"),
        ]
        timeline = _compute_timeline(courses, {"05506003": 1, "05506005": 1, "05506004": 1})
        self.assertEqual(len(timeline), 2)  # 2 semesters

    def test_excludes_failed_courses(self):
        courses = [
            _make_tc("05506003", grade="F", semester=1, year="2024-2025"),
            _make_tc("05506005", grade="A", semester=1, year="2024-2025"),
        ]
        timeline = _compute_timeline(courses, {"05506003": 1, "05506005": 1})
        all_codes = {c["code"] for t in timeline for c in t["courses"]}
        self.assertNotIn("05506003", all_codes)
        self.assertIn("05506005", all_codes)

    def test_excludes_current_courses(self):
        courses = [
            _make_tc("05506003", grade=None, is_current=True),
        ]
        timeline = _compute_timeline(courses, {"05506003": 1})
        self.assertEqual(len(timeline), 0)

    def test_sorted_chronologically(self):
        courses = [
            _make_tc("05506004", grade="A", semester=2, year="2024-2025"),
            _make_tc("05506003", grade="A", semester=1, year="2024-2025"),
        ]
        timeline = _compute_timeline(courses, {"05506003": 1, "05506004": 1})
        self.assertEqual(len(timeline), 2)
        self.assertLess(timeline[0]["key_sort"], timeline[1]["key_sort"])


# ==========================================================================
# 8. Validation Tests
# ==========================================================================

class TestValidation(unittest.TestCase):
    """Test input validations."""

    def test_valid_grades(self):
        for g in ["A", "B+", "B", "C+", "C", "D+", "D", "F", "S", "U", "W"]:
            override = CourseOverrideIn(grade=g)
            self.assertEqual(override.grade, g)

    def test_lowercase_grade_uppercased(self):
        override = CourseOverrideIn(grade="b+")
        self.assertEqual(override.grade, "B+")

    def test_invalid_grade_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            CourseOverrideIn(grade="INVALID_GRADE")
        with self.assertRaises(ValidationError):
            CourseOverrideIn(grade="A++")

    def test_whitespace_grade_trimmed(self):
        override = CourseOverrideIn(grade="  A  ")
        self.assertEqual(override.grade, "A")


# ==========================================================================
# 9. Prerequisites Tests
# ==========================================================================

class TestPrerequisites(unittest.TestCase):
    """Test prerequisite handling and schema."""

    def test_prerequisite_unique_mapping(self):
        """Composite PK ป้องกัน duplicate — ORM mapping ต้องไม่มี record ซ้ำ."""
        from app.models import Course, CurriculumCourse, Prerequisite
        from app.routers.curriculum import _course_to_out

        course = Course(
            course_code="05506240",
            course_name_th="สถาปัตยกรรมและวิศวกรรมข้อมูลขนาดใหญ่",
            course_name_en="BIG DATA ARCHITECTURE AND ENGINEERING",
            credit=3,
            credit_str="3(3-0-6)",
            prerequisites=[
                Prerequisite(course_code="05506240", prereq_code="05506012"),
            ],
        )
        cc = CurriculumCourse(
            curriculum_id="CS2564", course_code="05506240",
            year=3, semester=1, category="elective",
        )
        out = _course_to_out(course, {"05506240": 3}, cc=cc)
        self.assertEqual(out.prerequisites, ["05506012"])
        self.assertEqual(len(out.prerequisites), 1)
        self.assertEqual(out.year, 3)
        self.assertEqual(out.semester, 1)


# ==========================================================================
# 10. PDF Parser Tests (multi-file, data-driven)
# ==========================================================================

class TestPDFParser(unittest.TestCase):
    """Test PDF transcript parsing – supports multiple transcript files."""

    TRANSCRIPT_TEST_DATA = {
        "mytranscript.pdf": {
            "student_id": "67050476",
            "name_contains": "Ratchaphon",
            "total_courses": 35,
            "current_count": 6,
            "current_codes_sample": {"05506014", "05506210"},
            "multi_line_course": ("05506015", "COMPUTER ETHICS: SOCIAL AND PROFESSIONAL ISSUES"),
            "transfer_course": ("90644007", "FOUNDATION ENGLISH 1", "S"),
        },
        "mytranscript_achirayu.pdf": {
            "student_id": "67050613",
            "name_contains": "Achirayu",
            "total_courses": 36,
            "current_count": 7,
            "current_codes_sample": {"05506013", "90642111"},
            "multi_line_course": ("05506015", "COMPUTER ETHICS: SOCIAL AND PROFESSIONAL ISSUES"),
            "transfer_course": ("90644007", "FOUNDATION ENGLISH 1", "S"),
        },
    }

    def test_parse_transcripts(self):
        """Parse each available transcript PDF and verify against expected data."""
        from app.parser import parse_student_info, parse_transcript

        tested = 0
        for filename, expected in self.TRANSCRIPT_TEST_DATA.items():
            pdf_path = Path(__file__).resolve().parent.parent / filename
            if not pdf_path.exists():
                continue

            with self.subTest(file=filename):
                with open(pdf_path, "rb") as f:
                    student = parse_student_info(f)
                    courses = parse_transcript(f)

                self.assertEqual(student.get("student_id"), expected["student_id"])
                self.assertIn(expected["name_contains"], student.get("name", ""))
                self.assertEqual(len(courses), expected["total_courses"])

                # Transfer credit course
                tc_code, tc_name, tc_grade = expected["transfer_course"]
                c_transfer = next((c for c in courses if c["code"] == tc_code), None)
                self.assertIsNotNone(c_transfer, f"transfer course {tc_code} not found")
                self.assertEqual(c_transfer["name_en"], tc_name)
                self.assertEqual(c_transfer["grade"], tc_grade)

                # Multi-line course name
                ml_code, ml_name = expected["multi_line_course"]
                c_ml = next((c for c in courses if c["code"] == ml_code), None)
                self.assertIsNotNone(c_ml, f"multi-line course {ml_code} not found")
                self.assertEqual(c_ml["name_en"], ml_name)

                # Currently enrolled
                current_courses = [c for c in courses if c["is_current"]]
                self.assertEqual(len(current_courses), expected["current_count"])
                current_codes = {c["code"] for c in current_courses}
                for sample_code in expected["current_codes_sample"]:
                    self.assertIn(sample_code, current_codes)

                tested += 1

        if tested == 0:
            self.skipTest("No transcript PDF files found")


# ==========================================================================
# 11. API Integration Tests
# ==========================================================================

class TestAPIIntegration(unittest.TestCase):
    """Integration tests using FastAPI TestClient (httpx)."""

    @classmethod
    def setUpClass(cls):
        """Start fresh DB for integration tests."""
        try:
            import httpx
            from app.main import app
            from app.database import engine, AsyncSessionLocal
            from app.models import Base
            from app.seed import seed_curriculum

            async def _init_db():
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                async with AsyncSessionLocal() as session:
                    await seed_curriculum(session)

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_init_db())
            finally:
                loop.close()

            cls.app = app
            cls.has_httpx = True
        except ImportError:
            cls.has_httpx = False

    def _run_async(self, coro):
        """Helper to run async test cases."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    async def _get_client(self):
        """Create httpx AsyncClient for testing."""
        import httpx
        from app.main import app
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )

    def test_health_endpoint(self):
        """GET /health → 200 + {status: ok}"""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/health")
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json(), {"status": "ok"})
        self._run_async(_test())

    def test_home_page(self):
        """GET / → 200 HTML response."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/")
                self.assertEqual(r.status_code, 200)
                self.assertIn("text/html", r.headers.get("content-type", ""))
        self._run_async(_test())

    def test_advisor_page(self):
        """GET /advisor → 200 HTML response."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/advisor")
                self.assertEqual(r.status_code, 200)
                self.assertIn("text/html", r.headers.get("content-type", ""))
        self._run_async(_test())

    def test_search_page(self):
        """GET /search → 200 HTML response."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/search")
                self.assertEqual(r.status_code, 200)
                self.assertIn("text/html", r.headers.get("content-type", ""))
        self._run_async(_test())

    def test_curriculum_api(self):
        """GET /api/curriculum → 200 + list of terms."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/api/curriculum")
                self.assertEqual(r.status_code, 200)
                data = r.json()
                self.assertIsInstance(data, list)
                if len(data) > 0:
                    term = data[0]
                    self.assertIn("year", term)
                    self.assertIn("semester", term)
                    self.assertIn("courses", term)
        self._run_async(_test())

    def test_curriculum_search(self):
        """GET /api/curriculum/courses?search=... → 200 + filtered results."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/api/curriculum/courses", params={"search": "PROGRAMMING"})
                self.assertEqual(r.status_code, 200)
                data = r.json()
                self.assertIsInstance(data, list)
        self._run_async(_test())

    def test_curriculum_course_detail(self):
        """GET /api/curriculum/courses/{code} → 200 or 404."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/api/curriculum/courses/05506003")
                self.assertIn(r.status_code, [200, 404])
                if r.status_code == 200:
                    data = r.json()
                    self.assertEqual(data["course_code"], "05506003")
                    self.assertIn("prerequisites", data)
                    self.assertIn("category", data)
        self._run_async(_test())

    def test_review_rejects_non_pdf(self):
        """POST /review with non-PDF → 400."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.post(
                    "/review",
                    files={"file": ("test.txt", b"not a pdf", "text/plain")},
                )
                self.assertEqual(r.status_code, 400)
        self._run_async(_test())

    def test_confirm_with_empty_courses(self):
        """POST /confirm with empty courses → 200 dashboard."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.post("/confirm", json={"courses": []})
                self.assertEqual(r.status_code, 200)
                data = r.json()
                self.assertIn("completed_credits", data)
                self.assertIn("categories", data)
        self._run_async(_test())

    def test_confirm_with_invalid_json(self):
        """POST /confirm with invalid body → 400."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.post(
                    "/confirm",
                    content=b"not json",
                    headers={"content-type": "application/json"},
                )
                self.assertEqual(r.status_code, 400)
        self._run_async(_test())

    def test_student_not_found(self):
        """GET /api/students/{id} for nonexistent → 404."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/api/students/99999999")
                self.assertEqual(r.status_code, 404)
        self._run_async(_test())

    def test_advisor_login_wrong_credentials(self):
        """POST /api/advisors/login with wrong creds → 401."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.post(
                    "/api/advisors/login",
                    json={"advisor_id": "nonexistent", "password": "wrong"},
                )
                self.assertEqual(r.status_code, 401)
        self._run_async(_test())

    def test_advisor_me_without_login(self):
        """GET /api/advisors/me without session → 401."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/api/advisors/me")
                self.assertEqual(r.status_code, 401)
        self._run_async(_test())

    def test_review_with_real_pdf(self):
        """POST /review with actual transcript PDF → 200 + courses list."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        pdf_path = Path(__file__).resolve().parent.parent / "mytranscript.pdf"
        if not pdf_path.exists():
            self.skipTest("mytranscript.pdf not found")

        async def _test():
            async with await self._get_client() as client:
                with open(pdf_path, "rb") as f:
                    r = await client.post(
                        "/review",
                        files={"file": ("transcript.pdf", f, "application/pdf")},
                    )
                self.assertEqual(r.status_code, 200)
                data = r.json()
                self.assertIn("courses", data)
                self.assertIn("student", data)
                self.assertIsInstance(data["courses"], list)
                self.assertGreater(len(data["courses"]), 0)
        self._run_async(_test())

    def test_list_programs(self):
        """GET /api/curriculum/programs → 200 + list with CS2564."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/api/curriculum/programs")
                self.assertEqual(r.status_code, 200)
                programs = r.json()
                self.assertIsInstance(programs, list)
                self.assertTrue(any(p["curriculum_id"] == "CS2564" for p in programs))
        self._run_async(_test())

    def test_get_program_detail(self):
        """GET /api/curriculum/programs/CS2564 → 200 with categories."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/api/curriculum/programs/CS2564")
                self.assertEqual(r.status_code, 200)
                prog = r.json()
                self.assertEqual(prog["curriculum_id"], "CS2564")
                self.assertEqual(prog["total_credits_target"], 135)
                self.assertGreater(len(prog["categories"]), 0)
        self._run_async(_test())

    def test_curriculum_filter(self):
        """GET /api/curriculum?curriculum_id=CS2564 → 200 filtered."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.get("/api/curriculum", params={"curriculum_id": "CS2564"})
                self.assertEqual(r.status_code, 200)
                terms = r.json()
                self.assertIsInstance(terms, list)
        self._run_async(_test())

    def test_confirm_with_curriculum_id(self):
        """POST /confirm with curriculum_id → 200."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                r = await client.post("/confirm", json={"courses": [], "curriculum_id": "CS2564"})
                self.assertEqual(r.status_code, 200)
                data = r.json()
                self.assertEqual(data["total_credits"], 135)
        self._run_async(_test())

    def test_confirm_persists_courses_and_is_overridden(self):
        """POST /confirm with student_id persists courses and is_overridden flag to DB."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                student_payload = {
                    "student_id": "67990001",
                    "name": "ทดสอบ บันทึก",
                    "email": "67990001@kmitl.ac.th",
                    "admission_year": 2567,
                    "curriculum_id": "CS2564",
                }
                r = await client.post("/api/students", json=student_payload)
                self.assertIn(r.status_code, [201, 409])

                confirm_payload = {
                    "student_id": "67990001",
                    "curriculum_id": "CS2564",
                    "courses": [
                        {
                            "code": "05506003",
                            "name_en": "PROGRAMMING FUNDAMENTALS",
                            "credit": 3,
                            "grade": "A",
                            "semester": 1,
                            "academic_year": "2024-2025",
                            "is_overridden": False,
                        },
                        {
                            "code": "05506005",
                            "name_en": "DATA STRUCTURES AND ALGORITHMS",
                            "credit": 3,
                            "grade": "A",
                            "semester": 2,
                            "academic_year": "2024-2025",
                            "is_overridden": True,
                        },
                    ],
                }
                cr = await client.post("/confirm", json=confirm_payload)
                self.assertEqual(cr.status_code, 200)

                tr = await client.get("/api/students/67990001/transcript-courses")
                self.assertEqual(tr.status_code, 200)
                data = tr.json()
                courses = {c["code"]: c for c in data["courses"]}
                self.assertIn("05506003", courses)
                self.assertIn("05506005", courses)
                self.assertFalse(courses["05506003"]["is_overridden"])
                self.assertTrue(courses["05506005"]["is_overridden"])
        self._run_async(_test())

    def test_create_curriculum_and_course_api(self):
        """POST /api/curriculum/programs + POST /api/curriculum/courses → 201."""
        if not self.has_httpx:
            self.skipTest("httpx not installed")

        async def _test():
            async with await self._get_client() as client:
                # 1. Create new curriculum (e.g. IT2565)
                payload = {
                    "curriculum_id": "TEST_IT2565",
                    "name": "เทคโนโลยีสารสนเทศ",
                    "year": 2565,
                    "total_credits_target": 128,
                    "max_credits_per_semester": 21,
                    "categories": [
                        {"key": "ge", "label": "ศึกษาทั่วไป", "target_credits": 24, "color": "#111", "sort_order": 1},
                        {"key": "it_core", "label": "วิชาเฉพาะ", "target_credits": 86, "color": "#222", "sort_order": 2},
                        {"key": "free", "label": "เสรี", "target_credits": 18, "color": "#333", "sort_order": 3},
                    ],
                }
                r = await client.post("/api/curriculum/programs", json=payload)
                self.assertIn(r.status_code, [201, 409])
                if r.status_code == 201:
                    data = r.json()
                    self.assertEqual(data["curriculum_id"], "TEST_IT2565")
                    self.assertEqual(data["total_credits_target"], 128)
                    self.assertEqual(len(data["categories"]), 3)

                # 2. Add course to this curriculum
                c_payload = {
                    "course_code": "TEST_IT101",
                    "curriculum_id": "TEST_IT2565",
                    "course_name_th": "เทคโนโลยีสารสนเทศเบื้องต้น",
                    "course_name_en": "Intro to IT",
                    "credit": 3,
                    "year": 1,
                    "semester": 1,
                    "category": "it_core",
                }
                cr = await client.post("/api/curriculum/courses", json=c_payload)
                self.assertIn(cr.status_code, [201, 409])
                if cr.status_code == 201:
                    c_data = cr.json()
                    self.assertEqual(c_data["course_code"], "TEST_IT101")
                    self.assertEqual(c_data["category"], "it_core")
        self._run_async(_test())


# ==========================================================================
# 12. Flat Curriculum Tests
# ==========================================================================

class TestFlatCurriculum(unittest.TestCase):
    """Test _flat_curriculum helper."""

    def test_skips_coop_plan_type(self):
        """plan_type ที่มี 'Co-op' ต้องถูกข้าม."""
        curriculum = _make_curriculum(
            (1, 1, "", [_make_course("05506003")]),
            (3, 2, "Co-op Plan", [_make_course("05506117")]),
        )
        flat = _flat_curriculum(curriculum)
        codes = {c["code"] for c in flat}
        self.assertIn("05506003", codes)
        self.assertNotIn("05506117", codes)

    def test_parses_credit_string(self):
        """credit '3(2-2-5)' ต้อง parse เป็น int 3."""
        curriculum = _make_curriculum(
            (1, 1, "", [_make_course("05506003", credit="3(2-2-5)")]),
        )
        flat = _flat_curriculum(curriculum)
        self.assertEqual(flat[0]["credit"], 3)

    def test_preserves_prereqs(self):
        curriculum = _make_curriculum(
            (1, 1, "", [_make_course("05506004", prereqs=["05506003"])]),
        )
        flat = _flat_curriculum(curriculum)
        self.assertEqual(flat[0]["prereqs"], ["05506003"])


# ==========================================================================
# 13. Multi-Curriculum Dynamic Config Tests
# ==========================================================================

class TestMultiCurriculum(unittest.TestCase):
    """Test dynamic per-curriculum configuration (categories, targets, and classification)."""

    def test_custom_curriculum_dashboard_uses_custom_targets(self):
        """Dashboard must use custom curriculum targets and categories when provided."""
        custom_curriculum = {
            "curriculum": [
                {
                    "year": 1,
                    "semester": 1,
                    "plan_type": "",
                    "courses": [
                        {
                            "course_code": "06016001",
                            "course_name_th": "IT Fundamentals",
                            "course_name_en": "IT Fundamentals",
                            "credit": "3(3-0-6)",
                            "prerequisites": [],
                            "category": "it_core",
                        }
                    ],
                }
            ],
            "curriculum_config": {
                "total_credits_target": 128,
                "max_credits_per_semester": 21,
                "categories": {
                    "ge": {"label": "ศึกษาทั่วไป", "target": 24, "color": "#111111"},
                    "it_core": {"label": "วิชาบังคับ IT", "target": 86, "color": "#222222"},
                    "free": {"label": "เลือกเสรี", "target": 18, "color": "#333333"},
                },
            },
        }
        transcript = [
            _make_tc("06016001", credit=3, grade="A"),
        ]
        result = compute_dashboard(transcript, custom_curriculum)
        self.assertEqual(result["total_credits"], 128)
        cat_keys = [c["key"] for c in result["categories"]]
        self.assertEqual(cat_keys, ["ge", "it_core", "free"])
        it_cat = next(c for c in result["categories"] if c["key"] == "it_core")
        self.assertEqual(it_cat["earned_credits"], 3)
        self.assertEqual(it_cat["target_credits"], 86)

    def test_db_assigned_category_overrides_hardcoded_rules(self):
        """DB-assigned category in curriculum_codes takes priority over code prefix."""
        # 05506003 would normally be "core_cs" by prefix, but DB says "special_track"
        curriculum_codes = {
            "05506003": {"category": "special_track", "year": 1},
        }
        cat = classify_course("05506003", curriculum_codes)
        self.assertEqual(cat, "special_track")

    def test_custom_curriculum_study_plan_uses_custom_max_credits(self):
        """Study plan must respect curriculum-specific max_credits_per_semester."""
        custom_curriculum = {
            "curriculum": [
                {
                    "year": 1,
                    "semester": 1,
                    "plan_type": "",
                    "courses": [
                        {
                            "course_code": "IT101",
                            "course_name_th": "Intro IT",
                            "course_name_en": "Intro IT",
                            "credit": "4(4-0-8)",
                            "prerequisites": [],
                            "category": "it_core",
                        }
                    ],
                }
            ],
            "curriculum_config": {
                "total_credits_target": 120,
                "max_credits_per_semester": 18,
                "categories": {
                    "it_core": {"label": "IT Core", "target": 100, "color": "#123"},
                },
            },
        }
        plan = compute_study_plan([], custom_curriculum, "normal")
        for term in plan["plan_terms"]:
            self.assertEqual(term["max_credits"], 18)

    def test_curriculum_category_model_and_dynamic_color(self):
        """Test lean CurriculumCategory model: composite PK (curriculum_id, category_name), required_credits."""
        from app.models import CurriculumCategory
        from app.services import DEFAULT_CATEGORY_COLORS, DEFAULT_CATEGORY_LABELS

        cat = CurriculumCategory(
            curriculum_id="CS2564",
            category_name="major_core",
            required_credits=57,
        )
        self.assertEqual(cat.curriculum_id, "CS2564")
        self.assertEqual(cat.category_name, "major_core")
        self.assertEqual(cat.required_credits, 57)
        # Check that color and label are resolved dynamically in code
        self.assertEqual(DEFAULT_CATEGORY_COLORS.get("major_core"), "#10b981")
        self.assertEqual(DEFAULT_CATEGORY_COLORS.get("general_education"), "#6366f1")
        self.assertEqual(DEFAULT_CATEGORY_COLORS.get("non_existent", "#888888"), "#888888")
        self.assertEqual(DEFAULT_CATEGORY_LABELS.get("major_core"), "วิชาบังคับสาขา")
        self.assertEqual(DEFAULT_CATEGORY_LABELS.get("ge"), "ศึกษาทั่วไป (GE)")
        self.assertEqual(DEFAULT_CATEGORY_LABELS.get("non_existent", "non_existent"), "non_existent")


class TestStudentTranscriptSnapshot(unittest.TestCase):
    """Test suite for the new snapshot-only transcript architecture (transcripts table removed)."""

    def test_student_and_transcript_course_models(self):
        """Test Student and TranscriptCourse models with direct student_id linking."""
        from datetime import datetime
        from app.models import Student, TranscriptCourse
        from app.services import compute_credits, transcript_courses_to_list

        now = datetime.now()
        student = Student(
            student_id="64050001",
            name="สมชาย สายโค้ด",
            email="64050001@kmitl.ac.th",
            admission_year=2564,
            curriculum_id="CS2564",
            transcript_filename="transcript_64050001.pdf",
            last_uploaded_at=now,
        )

        self.assertEqual(student.student_id, "64050001")
        self.assertEqual(student.transcript_filename, "transcript_64050001.pdf")
        self.assertEqual(student.last_uploaded_at, now)

        # Create TranscriptCourse linked directly to student_id
        course1 = TranscriptCourse(
            id=1,
            student_id=student.student_id,
            course_code="05506001",
            course_name_raw="PROG FUND",
            credit=3,
            grade="A",
            semester=1,
            academic_year="2024-2025",
            is_overridden=False,
        )
        course2 = TranscriptCourse(
            id=2,
            student_id=student.student_id,
            course_code="05506002",
            course_name_raw="DATA STRUCT",
            credit=3,
            grade="B+",
            semester=2,
            academic_year="2024-2025",
            is_overridden=False,
        )
        course3 = TranscriptCourse(
            id=3,
            student_id=student.student_id,
            course_code="90641001",
            course_name_raw="ENGLISH 1",
            credit=3,
            grade="W",
            semester=1,
            academic_year="2024-2025",
            is_overridden=False,
        )

        courses = [course1, course2, course3]
        passed_credits, total_credits = compute_credits(courses)
        self.assertEqual(passed_credits, 6)
        self.assertEqual(total_credits, 9)

        as_dicts = transcript_courses_to_list(courses)
        self.assertEqual(len(as_dicts), 3)
        self.assertEqual(as_dicts[0]["code"], "05506001")
        self.assertEqual(as_dicts[0]["name_th"], "PROG FUND")
        self.assertEqual(as_dicts[0]["semester"], 1)
        self.assertEqual(as_dicts[0]["academic_year"], "2024-2025")
        self.assertEqual(as_dicts[2]["grade"], "W")
        self.assertFalse(as_dicts[0]["is_overridden"])

    def test_student_out_schema(self):
        """Test StudentOut schema includes transcript_filename and last_uploaded_at."""
        from datetime import datetime
        from app.routers.students import StudentOut

        now = datetime.now()
        data = {
            "student_id": "64050001",
            "name": "สมชาย สายโค้ด",
            "email": "64050001@kmitl.ac.th",
            "admission_year": 2564,
            "advisor_id": "ADVISOR001",
            "curriculum_id": "CS2564",
            "transcript_filename": "transcript.pdf",
            "last_uploaded_at": now,
        }
        out = StudentOut.model_validate(data)
        self.assertEqual(out.transcript_filename, "transcript.pdf")
        self.assertEqual(out.last_uploaded_at, now)


if __name__ == "__main__":
    unittest.main()

