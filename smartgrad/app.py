import io
from flask import Flask, request, render_template
from pypdf import PdfReader

app = Flask(__name__)
# กำหนดขนาดไฟล์สูงสุดที่อัปโหลดได้ (Transcript ทั่วไปไม่เกิน 16 MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

@app.route('/', methods=['GET', 'POST'])
def index():
    file_content = None
    filename = None
    error = None

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
                    # ตรวจสอบว่าเป็นไฟล์ PDF หรือไม่
                    if filename.lower().endswith('.pdf'):
                        # อ่านไฟล์เข้า Memory Stream (RAM) โดยไม่บันทึกลง Hard drive
                        pdf_stream = io.BytesIO(file.read())
                        reader = PdfReader(pdf_stream)
                        
                        # วนลูปดึงข้อความจากทุกหน้าใน PDF มารวมกัน
                        text_list = []
                        for page in reader.pages:
                            text_list.append(page.extract_text() or "")
                        
                        file_content = "\n--- (จบหน้า) ---\n".join(text_list)
                        if not file_content.strip():
                            error = "ไม่พบข้อความในไฟล์ PDF นี้ (ไฟล์อาจเป็นรูปภาพสแกนที่ไม่มีเลเยอร์ข้อความ)"
                    else:
                        # ถ้าเป็นไฟล์ข้อความทั่วไป (.txt, .csv, .json) ให้ใช้แบบเดิม
                        file_content = file.read().decode('utf-8')
                        
                except UnicodeDecodeError:
                    error = "ไม่สามารถอ่านไฟล์ได้ (รองรับไฟล์ PDF หรือไฟล์ข้อความที่เป็น UTF-8)"
                except Exception as e:
                    error = f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)}"

    return render_template('index.html', file_content=file_content, filename=filename, error=error)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)