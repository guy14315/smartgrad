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
            credit_match = CREDIT_RE.match(str(course["credit"]))
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
    remaining = [c for c in curriculum if c["code"] not in passed_codes and c["code"] not in current_codes and c.get("year") is not None and c.get("semester") is not None]
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

    # Sort courses chronologically
    sorted_courses = sorted(
        transcript_courses,
        key=lambda c: (c.get("academic_year") or 9999, c.get("semester") or 99)
    )

    for c in sorted_courses:
        grade = (c.get("grade") or "").upper()
        is_current = c.get("is_current", False)
        if is_current or (not grade) or grade in NON_PASSING_GRADES:
            continue  # only count passed
        
        cat = _classify_course(c["code"], curriculum_codes)
        credit = c.get("credit", 0)
        
        # Spillover logic: If ge or elective category is full, move to free elective
        if cat in ["ge", "elective"] and category_credits[cat] >= CATEGORIES[cat]["target"]:
            cat = "free"
            
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
            # Find courses that require this course as a prerequisite
            impacts = []
            for curr_course in curriculum:
                if c["code"] in curr_course.get("prereqs", []):
                    impacts.append({
                        "code": curr_course["code"],
                        "name_en": curr_course.get("name_en") or curr_course.get("name_th", ""),
                        "name_th": curr_course.get("name_th", "")
                    })

            in_progress_list.append({
                "code": c["code"],
                "name_en": c.get("name_en", c.get("name_th", "")),
                "name_th": c.get("name_th", ""),
                "credit": c.get("credit", 0),
                "category": _classify_course(c["code"], curriculum_codes),
                "impacts": impacts
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


# ---------------------------------------------------------------------------
# Study Plan Computation
# ---------------------------------------------------------------------------

def compute_study_plan(transcript_courses: list[dict], curriculum_data: dict, plan_type: str = "normal") -> dict:
    """Compute a semester-by-semester study plan for remaining semesters.
    
    Args:
        transcript_courses: Parsed courses from transcript (same as compute_dashboard)
        curriculum_data: Curriculum dict loaded from DB
        plan_type: 'normal' (ปัญหาพิเศษ) or 'coop' (สหกิจศึกษา)
    
    Returns:
        Dict with plan_terms, summary stats, warnings, and suggestions.
    """
    MAX_CREDITS = 22

    # determine which coop course to use (default to 05506117 unless 05506118 is in transcript)
    coop_taken = "05506117"
    for c in transcript_courses:
        if c.get("code") == "05506118":
            coop_taken = "05506118"
            break

    # --- flatten curriculum with plan_type filter ---
    flat: list[dict] = []
    for term in curriculum_data["curriculum"]:
        tp = term.get("plan_type", "")
        if plan_type == "normal" and "Co-op" in tp:
            continue
        if plan_type == "coop" and "Normal" in tp:
            continue
        for course in term["courses"]:
            code = course["course_code"]
            if plan_type == "coop":
                if code == "05506117" and coop_taken == "05506118":
                    continue
                if code == "05506118" and coop_taken == "05506117":
                    continue

            credit_match = CREDIT_RE.match(course["credit"])
            flat.append({
                "code": code,
                "name_th": course["course_name_th"],
                "name_en": course.get("course_name_en", ""),
                "credit": int(credit_match.group(1)) if credit_match else 0,
                "prereqs": course.get("prerequisites", []),
                "year": term["year"],
                "semester": term["semester"],
            })

    curriculum_codes = {c["code"] for c in flat}

    # --- passed / current sets ---
    passed_codes: set[str] = set()
    current_codes: set[str] = set()
    for c in transcript_courses:
        grade = (c.get("grade") or "").upper()
        is_current = c.get("is_current", False)
        if is_current or not grade:
            current_codes.add(c["code"])
        elif grade not in NON_PASSING_GRADES:
            passed_codes.add(c["code"])

    # --- category credits earned so far ---
    cat_earned: dict[str, int] = {k: 0 for k in CATEGORIES}
    # Sort for consistent spillover
    sorted_for_plan = sorted(
        transcript_courses,
        key=lambda c: (c.get("academic_year") or 9999, c.get("semester") or 99)
    )
    for c in sorted_for_plan:
        grade = (c.get("grade") or "").upper()
        is_current = c.get("is_current", False)
        if is_current or (not grade) or grade in NON_PASSING_GRADES:
            continue
        cat = _classify_course(c["code"], curriculum_codes)
        
        if cat in ["ge", "elective"] and cat_earned[cat] >= CATEGORIES[cat]["target"]:
            cat = "free"
            
        cat_earned[cat] += c.get("credit", 0)

    remaining_elective = max(0, CATEGORIES["elective"]["target"] - cat_earned["elective"])
    remaining_free = max(0, CATEGORIES["free"]["target"] - cat_earned["free"])
    remaining_ge = max(0, CATEGORIES["ge"]["target"] - cat_earned["ge"])

    # --- remaining core courses ---
    remaining_core = [
        c for c in flat
        if c["code"] not in passed_codes 
        and c["code"] not in current_codes
        and c.get("year") is not None
        and c.get("semester") is not None
    ]

    # --- determine starting semester from transcript ---
    enrolled_sems = set(
        (c["academic_year"], c["semester"])
        for c in transcript_courses
        if c.get("academic_year") and c.get("semester") in (1, 2)
    )
    num_sems = len(enrolled_sems)

    if num_sems == 0:
        start_year, start_sem = 1, 1
    else:
        current_year = (num_sems - 1) // 2 + 1
        current_sem = (num_sems - 1) % 2 + 1
        if current_sem == 1:
            start_year, start_sem = current_year, 2
        else:
            start_year, start_sem = current_year + 1, 1

    # --- generate future semesters (up to year 4 sem 2) ---
    future_sems: list[tuple[int, int]] = []
    for y in range(1, 5):
        for s in (1, 2):
            if (y, s) >= (start_year, start_sem):
                future_sems.append((y, s))

    # --- forward simulation ---
    planned_passed = set(passed_codes) | set(current_codes)
    remaining_set = list(remaining_core)  # mutable copy
    plan_terms: list[dict] = []

    for y, s in future_sems:
        # find courses that CAN be taken: prereqs met AND scheduled <= this semester
        can_take = []
        still_remaining = []
        for c in remaining_set:
            prereqs_met = all(p in planned_passed for p in c["prereqs"])
            scheduled_by_now = (c["year"] or 99, c["semester"] or 99) <= (y, s)
            if prereqs_met and scheduled_by_now:
                can_take.append(c)
            else:
                still_remaining.append(c)

        # sort: prioritize courses from earlier semesters, then by code
        can_take.sort(key=lambda c: (c["year"] or 99, c["semester"] or 99, c["code"]))

        # fit into MAX_CREDITS
        term_courses = []
        credits_used = 0
        overflow = []
        for c in can_take:
            if credits_used + c["credit"] <= MAX_CREDITS:
                term_courses.append(c)
                credits_used += c["credit"]
            else:
                overflow.append(c)

        # mark planned courses as passed for future semesters
        for c in term_courses:
            planned_passed.add(c["code"])

        remaining_set = still_remaining + overflow

        available_credits = MAX_CREDITS - credits_used

        plan_terms.append({
            "year": y,
            "semester": s,
            "label": f"ปีที่ {y} เทอม {s}",
            "core_courses": [
                {
                    "code": c["code"],
                    "name_en": c["name_en"],
                    "name_th": c["name_th"],
                    "credit": c["credit"],
                    "is_deferred": (c["year"] or 99, c["semester"] or 99) < (y, s),
                }
                for c in term_courses
            ],
            "core_credits": credits_used,
            "available_credits": available_credits,
            "max_credits": MAX_CREDITS,
        })

    # --- summary & warnings ---
    total_non_core_needed = remaining_elective + remaining_free + remaining_ge
    total_available_slots = sum(t["available_credits"] for t in plan_terms)
    unplanned_core = sum(c["credit"] for c in remaining_set)  # courses that couldn't fit
    can_graduate = (len(remaining_set) == 0) and (total_non_core_needed <= total_available_slots)

    warnings: list[str] = []
    suggestions: list[str] = []

    if len(remaining_set) > 0:
        names = ", ".join(c["name_en"] for c in remaining_set[:5])
        warnings.append(
            f"มีวิชาบังคับ {len(remaining_set)} วิชา ({unplanned_core} หน่วยกิต) "
            f"ที่ไม่สามารถจัดลงในแผน 4 ปีได้: {names}"
        )

    if total_non_core_needed > total_available_slots:
        deficit = total_non_core_needed - total_available_slots
        warnings.append(
            f"หน่วยกิตวิชาเลือก/เสรี/ศึกษาทั่วไปที่ยังต้องเรียนอีก {total_non_core_needed} หน่วยกิต "
            f"แต่มีช่องว่างในแผนเพียง {total_available_slots} หน่วยกิต (ขาดอีก {deficit} หน่วยกิต)"
        )

    if not can_graduate:
        warnings.append("⚠️ จากแผนปัจจุบัน อาจต้องใช้เวลาเรียนมากกว่า 4 ปี")
        suggestions.append("พิจารณาลงเรียนภาคฤดูร้อน (Summer) เพื่อเพิ่มหน่วยกิต")
        suggestions.append("ปรึกษาอาจารย์ที่ปรึกษาเพื่อขอลงทะเบียนเกินเพดาน 22 หน่วยกิตต่อเทอม")
        suggestions.append("วางแผนลงวิชาเลือกที่หน่วยกิตสูงเพื่อลดจำนวนวิชาที่ต้องลง")

    if len(future_sems) == 0:
        warnings.append("ไม่พบเทอมที่เหลือในหลักสูตร 4 ปี กรุณาตรวจสอบข้อมูล Transcript")

    return {
        "plan_terms": plan_terms,
        "remaining_elective_credits": remaining_elective,
        "remaining_free_credits": remaining_free,
        "remaining_ge_credits": remaining_ge,
        "total_remaining_non_core": total_non_core_needed,
        "total_available_slots": total_available_slots,
        "can_graduate_on_time": can_graduate,
        "warnings": warnings,
        "suggestions": suggestions,
    }
