"""SmartGrad configuration and constants.

Single source of truth สำหรับค่า config ทั้งหมดของระบบ
เปลี่ยนค่าที่นี่แทนการแก้ในแต่ละไฟล์
"""

import os
import re

# ---------------------------------------------------------------------------
# Non-passing grades
# ---------------------------------------------------------------------------
NON_PASSING_GRADES = {"F", "W", "WU", "U"}
VALID_GRADES = {"A", "B+", "B", "C+", "C", "D+", "D", "F", "S", "U", "W", "WU", "P", "AUD", "IP", "I"}

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
CREDIT_RE = re.compile(r"^(\d+)")
COURSE_CODE_PATTERN = re.compile(r"^\d{5,9}$")
VALID_GRADES_PATTERN = re.compile(r"^(A|B\+|B|C\+|C|D\+|D|F|S|U|W|WU|P|AUD|IP|I)$", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Curriculum settings (KMITL CS พ.ศ. 2564)
# ---------------------------------------------------------------------------
TOTAL_CREDITS_TARGET = 135
MAX_CREDITS_PER_SEMESTER = 22

# หมวดศึกษาทั่วไป: รหัส 90xxxxxx
GE_PREFIX = "90"

# วิชาคณิตศาสตร์/สถิติบังคับ
CORE_MATH_CODES = {
    "05506001", "05506002", "05506250", "05506231", "05506232", "05506233",
}

# การศึกษาทางเลือก (สหกิจ / ปัญหาพิเศษ / ต่างประเทศ)
ALTERNATIVE_CODES = {
    "05506098", "05506099",   # ปัญหาพิเศษ 1, 2
    "05506117",               # สหกิจศึกษา
    "05506118",               # ฝึกงานต่างประเทศ
}

# หมวดวิชาเฉพาะบังคับ CS (05506xxx ที่ไม่ใช่ Math/Alternative)
CORE_CS_PREFIX = "055"

CATEGORIES = {
    "ge":          {"label": "ศึกษาทั่วไป (GE)",      "target": 30, "color": "#6366f1"},
    "core_math":   {"label": "คณิตศาสตร์/สถิติบังคับ", "target": 18, "color": "#0ea5e9"},
    "core_cs":     {"label": "วิชาบังคับ CS",          "target": 57, "color": "#10b981"},
    "elective":    {"label": "วิชาเลือกเฉพาะสาขา",    "target": 18, "color": "#f59e0b"},
    "free":        {"label": "วิชาเลือกเสรี",          "target": 6,  "color": "#ec4899"},
    "alternative": {"label": "การศึกษาทางเลือก",      "target": 6,  "color": "#8b5cf6"},
}

# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# Application defaults
# ---------------------------------------------------------------------------
DEFAULT_CURRICULUM_ID = "CS2564"
BUDDHIST_ERA_OFFSET = 2500  # พ.ศ. = ค.ศ. + 543, แต่ระบบ KMITL ใช้ 25xx จากรหัสนักศึกษา 2 หลักแรก
_SESSION_SECRET_DEFAULT = "smartgrad-demo-session-secret"  # ใช้เฉพาะ development เท่านั้น


def get_session_secret() -> str:
    """Return session secret, raising in production if not explicitly set."""
    secret = os.environ.get("SESSION_SECRET")
    if secret:
        return secret
    if os.environ.get("ENV", "").lower() == "production":
        raise RuntimeError(
            "SESSION_SECRET environment variable must be set in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    return _SESSION_SECRET_DEFAULT
