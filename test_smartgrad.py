"""Unit tests for SmartGrad core modules."""

import unittest
from pydantic import ValidationError

from config import CATEGORIES, VALID_GRADES
from dashboard import _get_unique_passed_courses, compute_dashboard, compute_study_plan
from routers.students import CourseOverrideIn
from services import classify_course, hash_password, verify_password


class TestSecurity(unittest.TestCase):
    """Test password hashing and verification."""

    def test_pbkdf2_hash_and_verify(self):
        password = "secret_password_123"
        hashed = hash_password(password)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$100000$"))
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrong_password", hashed))

    def test_legacy_sha256_verification(self):
        import hashlib
        password = "smartgrad-demo"
        legacy_hash = hashlib.sha256(password.encode()).hexdigest()
        self.assertTrue(verify_password(password, legacy_hash))
        self.assertFalse(verify_password("wrong-demo", legacy_hash))


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


class TestDeduplicationAndDashboard(unittest.TestCase):
    """Test dashboard calculation and retake deduplication."""

    def test_unique_passed_courses_deduplication(self):
        transcript_courses = [
            {"code": "05506003", "credit": 3, "grade": "F", "semester": 1, "academic_year": "2023-2024", "is_current": False},
            {"code": "05506003", "credit": 3, "grade": "B", "semester": 2, "academic_year": "2023-2024", "is_current": False},
            {"code": "05506005", "credit": 3, "grade": "A", "semester": 1, "academic_year": "2023-2024", "is_current": False},
        ]
        unique_passed = _get_unique_passed_courses(transcript_courses)
        self.assertEqual(len(unique_passed), 2)
        codes = [c["code"] for c in unique_passed]
        self.assertIn("05506003", codes)
        self.assertIn("05506005", codes)
        # Should have grade B for 05506003
        retake_course = next(c for c in unique_passed if c["code"] == "05506003")
        self.assertEqual(retake_course["grade"], "B")

    def test_compute_dashboard_no_duplicate_credits(self):
        mock_curriculum = {
            "curriculum": [
                {
                    "year": 1,
                    "semester": 1,
                    "plan_type": "",
                    "courses": [
                        {"course_code": "05506003", "course_name_th": "Intro Prog", "course_name_en": "Intro Prog", "credit": "3(2-2-5)", "prerequisites": []},
                    ]
                }
            ]
        }
        transcript_courses = [
            {"code": "05506003", "credit": 3, "grade": "F", "semester": 1, "academic_year": "2023-2024", "is_current": False},
            {"code": "05506003", "credit": 3, "grade": "B", "semester": 2, "academic_year": "2023-2024", "is_current": False},
        ]
        result = compute_dashboard(transcript_courses, mock_curriculum)
        self.assertEqual(result["completed_credits"], 3)  # 3 credits, NOT 6
        self.assertEqual(result["completed_courses"], 1)


class TestValidation(unittest.TestCase):
    """Test input validations."""

    def test_valid_grades(self):
        for g in ["A", "B+", "B", "C+", "C", "D+", "D", "F", "S", "U", "W"]:
            override = CourseOverrideIn(grade=g)
            self.assertEqual(override.grade, g)

    def test_invalid_grade_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            CourseOverrideIn(grade="INVALID_GRADE")
        with self.assertRaises(ValidationError):
            CourseOverrideIn(grade="A++")


class TestPrerequisites(unittest.TestCase):
    """Test prerequisite handling and schema."""

    def test_prerequisite_deduplication(self):
        from models import Course, Prerequisite
        from routers.curriculum import _course_to_out

        course = Course(
            course_code="05506240",
            course_name_th="สถาปัตยกรรมและวิศวกรรมข้อมูลขนาดใหญ่",
            course_name_en="BIG DATA ARCHITECTURE AND ENGINEERING",
            credit=3,
            credit_str="3(3-0-6)",
            year=3,
            semester=1,
            prerequisites=[
                Prerequisite(course_code="05506240", prereq_code="05506012"),
                Prerequisite(course_code="05506240", prereq_code="05506012"),
            ],
        )
        out = _course_to_out(course, {"05506240": 3})
        self.assertEqual(out.prerequisites, ["05506012"])
        self.assertEqual(len(out.prerequisites), 1)


class TestPDFParser(unittest.TestCase):
    """Test PDF transcript parsing – supports multiple transcript files."""

    # ------------------------------------------------------------------
    # Expected data per transcript file.
    # เพิ่มไฟล์ใหม่ได้โดยเพิ่ม entry ที่นี่ + วางไฟล์ PDF ไว้ข้าง test
    # ------------------------------------------------------------------
    TRANSCRIPT_TEST_DATA = {
        "mytranscript.pdf": {
            "student_id": "67050476",
            "name_contains": "Ratchaphon",
            "total_courses": 35,
            "current_count": 6,
            "current_codes_sample": {"05506014", "05506210"},
            # วิชาที่ต้อง parse ชื่อยาวข้ามบรรทัดให้ถูกต้อง
            "multi_line_course": ("05506015", "COMPUTER ETHICS: SOCIAL AND PROFESSIONAL ISSUES"),
            # วิชาเทียบโอน
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
        from pathlib import Path
        from parser import parse_student_info, parse_transcript

        tested = 0
        for filename, expected in self.TRANSCRIPT_TEST_DATA.items():
            pdf_path = Path(__file__).parent / filename
            if not pdf_path.exists():
                continue

            with self.subTest(file=filename):
                with open(pdf_path, "rb") as f:
                    student = parse_student_info(f)
                    courses = parse_transcript(f)

                # --- Student identity ---
                self.assertEqual(
                    student.get("student_id"), expected["student_id"],
                    f"[{filename}] student_id mismatch",
                )
                self.assertIn(
                    expected["name_contains"], student.get("name", ""),
                    f"[{filename}] name should contain '{expected['name_contains']}'",
                )

                # --- Total courses parsed ---
                self.assertEqual(
                    len(courses), expected["total_courses"],
                    f"[{filename}] total courses mismatch",
                )

                # --- Transfer credit course ---
                tc_code, tc_name, tc_grade = expected["transfer_course"]
                c_transfer = next((c for c in courses if c["code"] == tc_code), None)
                self.assertIsNotNone(c_transfer, f"[{filename}] transfer course {tc_code} not found")
                self.assertEqual(c_transfer["name_en"], tc_name)
                self.assertEqual(c_transfer["grade"], tc_grade)

                # --- Multi-line course name ---
                ml_code, ml_name = expected["multi_line_course"]
                c_ml = next((c for c in courses if c["code"] == ml_code), None)
                self.assertIsNotNone(c_ml, f"[{filename}] multi-line course {ml_code} not found")
                self.assertEqual(c_ml["name_en"], ml_name)

                # --- Currently enrolled (in-progress) ---
                current_courses = [c for c in courses if c["is_current"]]
                self.assertEqual(
                    len(current_courses), expected["current_count"],
                    f"[{filename}] in-progress count mismatch",
                )
                current_codes = {c["code"] for c in current_courses}
                for sample_code in expected["current_codes_sample"]:
                    self.assertIn(
                        sample_code, current_codes,
                        f"[{filename}] expected {sample_code} in current courses",
                    )

                tested += 1

        if tested == 0:
            self.skipTest("No transcript PDF files found")


if __name__ == "__main__":
    unittest.main()
