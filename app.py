import io
import json
import re
from flask import Flask, request, render_template
from pypdf import PdfReader

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

def load_mock_db():
    try:
        with open('curriculum.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# ฟังก์ชันจำลองการดึงเงื่อนไข Prerequisite (คุณสามารถย้ายไปเก็บใน JSON หรือ DB ได้ในอนาคต)
def get_prerequisites():
    return {
        "05506004": ["05506003"],  # OOP ต้องผ่าน Prog Fund ก่อน
        "05506236": ["05506006"],  # Analysis of Algorithms ต้องผ่าน Data Struct ก่อน
        "05506017": ["05506113"],  # Software Eng ต้องผ่าน Software Analysis ก่อน
    }

# ฟังก์ชันดึงรหัสวิชาที่เรียนผ่านแล้วจากข้อความใน Transcript
def extract_passed_courses(text):
    # ค้นหารหัสวิชา 8 หลัก (ตามรูปแบบในหลักสูตร KMITL)
    found_codes = re.findall(r'\b\d{8}\b', text)
    
    # ในอนาคตต้องเขียน Logic เช็คเกรดเพิ่ม เช่น ต้องไม่ใช่ F, W, I
    # ตอนนี้สมมติว่าถ้ารหัสวิชาปรากฏใน Transcript แปลว่าเรียนแล้ว
    return list(set(found_codes)) 

@app.route('/', methods=['GET', 'POST'])
def index():
    file_content = None
    filename = None
    error = None
    dashboard_data = None
    
    mock_db = load_mock_db()
    prereqs = get_prerequisites()

    if request.method == 'POST':
        if 'file' not in request.files:
            error = "ไม่พบไฟล์ที่ส่งมา"
        else:
            file = request.files['file']
            if file.filename == '':
                error = "ไม่ได้เลือกไฟล์"
            elif file:
                filename = file.filename
                try:
                    if filename.lower().endswith('.pdf'):
                        pdf_stream = io.BytesIO(file.read())
                        reader = PdfReader(pdf_stream)
                        text_list = [page.extract_text() or "" for page in reader.pages]
                        file_content = "\n".join(text_list)
                    else:
                        file_content = file.read().decode('utf-8')
                    
                    if not file_content.strip():
                        error = "ไม่พบข้อความในไฟล์"
                    else:
                        # --- เริ่มขั้นตอนการประมวลผลสำหรับ Dashboard ---
                        passed_codes = extract_passed_courses(file_content)
                        
                        total_courses = 0
                        completed_courses = 0
                        total_credits = 0
                        completed_credits = 0
                        remaining_list = []
                        
                        # วนลูปเช็ควิชาทั้งหมดในหลักสูตร
                        for term in mock_db.get('curriculum', []):
                            for course in term.get('courses', []):
                                code = course['course_code']
                                # ดึงเฉพาะตัวเลขหน่วยกิตตัวแรก เช่น "3(2-2-5)" -> 3
                                credit_match = re.match(r'(\d+)', course['credit'])
                                credit_val = int(credit_match.group(1)) if credit_match else 0
                                
                                total_courses += 1
                                total_credits += credit_val
                                
                                # เช็ค Prerequisite ของวิชานี้
                                course_prereqs = prereqs.get(code, [])
                                prereq_status = "ผ่านเงื่อนไขแล้ว"
                                missing_prereqs = [p for p in course_prereqs if p not in passed_codes]
                                if missing_prereqs:
                                    prereq_status = f"ติดวิชาบังคับก่อน: {', '.join(missing_prereqs)}"

                                if code in passed_codes:
                                    completed_courses += 1
                                    completed_credits += credit_val
                                else:
                                    remaining_list.append({
                                        "code": code,
                                        "name_th": course['course_name_th'],
                                        "credit": course['credit'],
                                        "prereq_status": prereq_status
                                    })
                        
                        # สรุปผลลัพธ์ส่งให้หน้าบ้าน
                        dashboard_data = {
                            "progress_percent": round((completed_courses / total_courses) * 100) if total_courses > 0 else 0,
                            "total_courses": total_courses,
                            "completed_courses": completed_courses,
                            "remaining_courses_count": len(remaining_list),
                            "total_credits": total_credits,
                            "completed_credits": completed_credits,
                            "remaining_list": remaining_list
                        }
                        
                except Exception as e:
                    error = f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)}"

    return render_template('index.html', file_content=file_content, filename=filename, error=error, mock_db=mock_db, dashboard=dashboard_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)