"""Dashboard computation: progress, category breakdown, timeline."""

import re
from typing import Any

NON_PASSING_GRADES = {"F", "W", "WU", "U"}
CREDIT_RE = re.compile(r"^(\d+)")

# ---------------------------------------------------------------------------
# Course category classification (based on KMITL CS curriculum 2564)
# ---------------------------------------------------------------------------

# หมวดศึกษาทั่วไป: รหัส 90xxxxxx + รายวิชาที่ระบุไว้
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


def _classify_course(code: str, curriculum_codes: set[str]) -> str:
    """Classify a course code into one of the category keys."""
    if code.startswith(GE_PREFIX):
        return "ge"
    if code in CORE_MATH_CODES:
        return "core_math"
    if code in ALTERNATIVE_CODES:
        return "alternative"
    if code.startswith(CORE_CS_PREFIX) and code in curriculum_codes:
        return "core_cs"
    if code.startswith(CORE_CS_PREFIX) and code not in curriculum_codes:
        return "elective"   # วิชาเลือกเฉพาะสาขา (05506xxx ที่ไม่ได้อยู่ใน core)
    return "free"           # วิชาอื่นๆ → เลือกเสรี


# ---------------------------------------------------------------------------
# Flatten curriculum
# ---------------------------------------------------------------------------

def _flat_curriculum(curriculum_data: dict) -> list[dict]:
    flat = []
    term_index = 0
    for term in curriculum_data["curriculum"]:
        if "Co-op" in term.get("plan_type", ""):
            continue
        for course in term["courses"]:
            credit_match = CREDIT_RE.match(course["credit"])
            flat.append({
                "code": course["course_code"],
                "name_th": course["course_name_th"],
                "name_en": course.get("course_name_en"),
                "credit": int(credit_match.group(1)) if credit_match else 0,
                "term_index": term_index,
                "prereqs": course.get("prerequisites", []),
                "year": term["year"],
                "semester": term["semester"],
            })
        term_index += 1
    return flat


# ---------------------------------------------------------------------------
# Main dashboard computation
# ---------------------------------------------------------------------------

def compute_dashboard(transcript_courses: list[dict], curriculum_data: dict) -> dict:
    curriculum = _flat_curriculum(curriculum_data)
    curriculum_codes = {c["code"] for c in curriculum}
    name_by_code = {c["code"]: c.get("name_en") or c.get("name_th", "") for c in curriculum}

    # separate passed vs current (กำลังเรียน)
    passed_codes: set[str] = set()
    current_codes: set[str] = set()

    for c in transcript_courses:
        grade = (c.get("grade") or "").upper()
        is_current = c.get("is_current", False)
        if is_current or not grade:
            current_codes.add(c["code"])
        elif grade not in NON_PASSING_GRADES:
            passed_codes.add(c["code"])

    # Overall progress
    completed = [c for c in curriculum if c["code"] in passed_codes]
    remaining = [c for c in curriculum if c["code"] not in passed_codes and c["code"] not in current_codes]
    in_progress = [c for c in curriculum if c["code"] in current_codes]

    total_credits_target = 135 # ตามหลักสูตร พ.ศ. 2564
    
    # Calculate completed credits from transcript (not from curriculum definition to include free electives)
    completed_credits = sum(c.get("credit", 0) for c in transcript_courses if (c.get("grade") or "").upper() not in NON_PASSING_GRADES and not c.get("is_current", False))

    # Remaining list with prereq status
    remaining_list = []
    for course in remaining:
        missing = [p for p in course["prereqs"] if p not in passed_codes]
        if missing:
            blockers = ", ".join(
                f"{name_by_code.get(p, p)} ({p})" for p in missing
            )
            prereq_status = f"ติดวิชาบังคับก่อน: {blockers}"
        else:
            prereq_status = "พร้อมลงเรียนได้"

        remaining_list.append({
            "code": course["code"],
            "name_en": course.get("name_en") or course.get("name_th", ""),
            "credit": course["credit"],
            "prereq_status": prereq_status,
        })

    # --- Category breakdown ---
    category_credits: dict[str, int] = {k: 0 for k in CATEGORIES}
    category_courses: dict[str, list] = {k: [] for k in CATEGORIES}

    for c in transcript_courses:
        grade = (c.get("grade") or "").upper()
        is_current = c.get("is_current", False)
        if is_current or (not grade) or grade in NON_PASSING_GRADES:
            continue  # only count passed
        cat = _classify_course(c["code"], curriculum_codes)
        credit = c.get("credit", 0)
        category_credits[cat] += credit
        category_courses[cat].append({
            "code": c["code"],
            "name_en": c.get("name_en", c.get("name_th", "")),
            "credit": credit,
            "grade": c.get("grade"),
        })

    categories_out = []
    for key, meta in CATEGORIES.items():
        earned = category_credits[key]
        target = meta["target"]
        categories_out.append({
            "key": key,
            "label": meta["label"],
            "color": meta["color"],
            "earned_credits": earned,
            "target_credits": target,
            "percent": round(min(earned / target * 100, 100)) if target else 0,
            "courses": category_courses[key],
        })

    # --- Timeline: group passed courses by actual semester from transcript ---
    timeline: dict[str, list] = {}
    for c in transcript_courses:
        sem = c.get("semester")
        yr = c.get("academic_year")
        grade = (c.get("grade") or "").upper()
        is_current = c.get("is_current", False)

        if is_current or not grade or grade in NON_PASSING_GRADES:
            continue  # only show passed

        label = f"เทอม {sem} ปีการศึกษา {yr}" if sem and yr else "ไม่ระบุเทอม"
        key_sort = f"{yr}_{sem:02d}" if sem and yr else "9999_99"

        if label not in timeline:
            timeline[label] = {"key_sort": key_sort, "label": label, "courses": []}
        timeline[label]["courses"].append({
            "code": c["code"],
            "name_en": c.get("name_en", c.get("name_th", "")),
            "credit": c.get("credit", 0),
            "grade": c.get("grade"),
            "category": _classify_course(c["code"], curriculum_codes),
        })

    timeline_list = sorted(timeline.values(), key=lambda x: x["key_sort"])

    # --- Currently enrolled ---
    in_progress_list = []
    for c in transcript_courses:
        if c.get("is_current"):
            in_progress_list.append({
                "code": c["code"],
                "name_en": c.get("name_en", c.get("name_th", "")),
                "credit": c.get("credit", 0),
                "category": _classify_course(c["code"], curriculum_codes),
            })

    return {
        "completed_courses": len([c for c in transcript_courses if (c.get("grade") or "").upper() not in NON_PASSING_GRADES and not c.get("is_current")]),
        "total_courses": len(curriculum),
        "completed_credits": completed_credits,
        "total_credits": total_credits_target,
        "remaining_courses_count": len(remaining),
        "progress_percent": round(min(completed_credits / total_credits_target * 100, 100)),
        "remaining_list": remaining_list,
        "categories": categories_out,
        "timeline": timeline_list,
        "in_progress": in_progress_list,
    }
