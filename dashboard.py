import re

NON_PASSING_GRADES = {"F", "W", "WU", "U"}
CREDIT_RE = re.compile(r"^(\d+)")


def _flat_curriculum(curriculum_data: dict) -> list[dict]:
    flat = []
    term_index = 0
    for term in curriculum_data["curriculum"]:
        # Co-op/overseas training is an alternate track to the normal-plan
        # senior project courses, not an additional requirement.
        if "Co-op" in term.get("plan_type", ""):
            continue
        for course in term["courses"]:
            credit_match = CREDIT_RE.match(course["credit"])
            flat.append({
                "code": course["course_code"],
                "name_th": course["course_name_th"],
                "credit": int(credit_match.group(1)) if credit_match else 0,
                "term_index": term_index,
            })
        term_index += 1
    return flat


def compute_dashboard(transcript_courses: list[dict], curriculum_data: dict) -> dict:
    curriculum = _flat_curriculum(curriculum_data)

    passed_codes = {
        c["code"]
        for c in transcript_courses
        if c["grade"] and c["grade"].upper() not in NON_PASSING_GRADES
    }

    completed = [c for c in curriculum if c["code"] in passed_codes]
    remaining = [c for c in curriculum if c["code"] not in passed_codes]

    total_credits = sum(c["credit"] for c in curriculum)
    completed_credits = sum(c["credit"] for c in completed)

    remaining_list = []
    for course in remaining:
        earlier_incomplete = [
            c
            for c in curriculum
            if c["term_index"] < course["term_index"] and c["code"] not in passed_codes
        ]
        if earlier_incomplete:
            prereq_status = f"ติดวิชาก่อนหน้า {len(earlier_incomplete)} วิชา"
        else:
            prereq_status = "พร้อมลงเรียนได้"

        remaining_list.append({
            "code": course["code"],
            "name_th": course["name_th"],
            "credit": course["credit"],
            "prereq_status": prereq_status,
        })

    return {
        "completed_courses": len(completed),
        "total_courses": len(curriculum),
        "completed_credits": completed_credits,
        "total_credits": total_credits,
        "remaining_courses_count": len(remaining),
        "progress_percent": round(completed_credits / total_credits * 100) if total_credits else 0,
        "remaining_list": remaining_list,
    }
