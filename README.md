# SmartGrad

SmartGrad เป็นแอปพลิเคชันบนเว็บที่ช่วยให้นักศึกษาตรวจสอบความก้าวหน้าในการเรียน คำนวณเปอร์เซ็นต์ความสำเร็จตามโครงสร้างหลักสูตร และวางแผนการลงทะเบียนเรียนในเทอมถัดไปได้อัตโนมัติ โดยใช้ข้อมูลจากไฟล์ Transcript (PDF) ที่ได้จากสำนักทะเบียน นอกจากนี้ยังมีระบบสำหรับอาจารย์ที่ปรึกษาเพื่อติดตามผลการเรียนของนักศึกษาในความดูแล

## ฟีเจอร์ (Features)

### สำหรับนักศึกษา

1. **อัปโหลดและตรวจสอบ:** ดึงข้อมูลจาก Transcript (.pdf) ได้ทันที และแก้ไขรายวิชาที่อ่านผิดก่อนคำนวณได้
2. **Dashboard สรุปผล:** แสดงหน่วยกิตที่ได้แยกตามหมวดหมู่ (วิชาแกน, เลือกสาขา, GE, เลือกเสรี) พร้อมแถบ % ความก้าวหน้า
3. **วางแผนการเรียน (Study Plan):** ระบบแนะนำการลงวิชาในแต่ละเทอม (Drag & Drop เพื่อย้ายเทอมได้)
4. **Export PDF:** บันทึกแผนการเรียนที่จัดเสร็จแล้วออกมาเป็นไฟล์ PDF
5. **จำลองการถอน (Withdraw):** จำลองสถานการณ์ถอนรายวิชา (W) ในเทอมปัจจุบัน เพื่อดูผลกระทบ
6. **ค้นหารายวิชา:** ค้นหาและกรองรายวิชาทั้งหมดในหลักสูตร พร้อมดูวิชาบังคับก่อน (Prerequisite)

### สำหรับอาจารย์ที่ปรึกษา

- เข้าสู่ระบบด้วยรหัสอาจารย์และรหัสผ่าน
- ดูรายชื่อนักศึกษาในความดูแล พร้อมสถานะการอัปโหลด Transcript
- ดูรายงานสรุปรายบุคคล และรายงานภาพรวมของนักศึกษาทั้งปีการศึกษา
- ดูรายชื่อนักศึกษาที่หน่วยกิตครบเกณฑ์สำเร็จการศึกษา

## เทคโนโลยีที่ใช้ (Tech Stack)

- **Backend:** Python 3.12, FastAPI, Uvicorn
- **ฐานข้อมูล:** SQLAlchemy (async) — Supabase PostgreSQL (asyncpg) หรือ SQLite (aiosqlite) สำหรับรันในเครื่อง
- **อ่าน Transcript:** pdfplumber
- **Frontend:** HTML / JavaScript / CSS ร่วมกับ Jinja2 Templates
- **Deploy:** Docker / Docker Compose

## เริ่มต้นใช้งาน (Quick Start)

### สิ่งที่ต้องมี (Prerequisites)

- Git
- Python 3.12+ (สำหรับรันแบบ pip)
- Docker (สำหรับรันแบบ Docker)

### 1. Clone โปรเจกต์

```bash
git clone <repository-url>
cd smartgrad
```

### 2. ตั้งค่าไฟล์ `.env`

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

จากนั้นเปิด `.env` แล้วเลือกอย่างใดอย่างหนึ่ง:

- **ใช้ฐานข้อมูลกลางของทีม (Supabase):** แก้ค่า `DATABASE_URL` เป็นของจริง (ขอจากเพื่อนร่วมทีม)
- **ทดลองในเครื่องตัวเอง (SQLite):** ใส่เครื่องหมาย `#` หน้าบรรทัด `DATABASE_URL` เพื่อปิดการใช้งาน (ค่าในไฟล์ตัวอย่างเป็นเพียง placeholder ใช้เชื่อมต่อจริงไม่ได้)

> **คำเตือน:** ทุกครั้งที่แอปเริ่มทำงาน จะสร้างตารางและ Seed ข้อมูลจาก `app/init.sql` ลงในฐานข้อมูลที่ตั้งค่าไว้ ถ้า `DATABASE_URL` ชี้ไปที่ Supabase ของทีม การรันแอปในเครื่องจะ **เขียนข้อมูลลงฐานข้อมูลกลางที่ใช้ร่วมกันทั้งทีม** (รวมถึงข้อมูลที่ได้จากการอัปโหลด Transcript ในหน้าเว็บ) หากต้องการทดลองเฉยๆ ให้ปิด `DATABASE_URL` ไว้เพื่อใช้ SQLite

### 3. รันแอป

#### วิธีที่ 1: Docker Compose

ต้องมีไฟล์ `.env` ก่อน (ขั้นตอนที่ 2) เพราะ `docker-compose.yml` อ่านค่าจากไฟล์นี้

```bash
docker compose up --build
```

เข้าใช้งานได้ที่ `http://localhost:8000` (ภายในคอนเทนเนอร์ใช้พอร์ต 8080 ซึ่งกำหนดผ่านตัวแปร `PORT`)

โฟลเดอร์ `./app` ถูก mount เข้าคอนเทนเนอร์และเปิด `--reload` ไว้ แก้โค้ดแล้วระบบจะรีโหลดให้เอง ส่วนไฟล์ `smartgrad.db` (กรณีใช้ SQLite) จะอยู่ในคอนเทนเนอร์และหายไปเมื่อสร้างคอนเทนเนอร์ใหม่

#### วิธีที่ 2: รันในเครื่องด้วย pip

```bash
python -m venv .venv
# Windows:    .venv\Scripts\activate
# Mac/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

เข้าใช้งานได้ที่ `http://localhost:8000` (รันคำสั่งจากโฟลเดอร์หลักของโปรเจกต์) ถ้าไม่ได้ตั้ง `DATABASE_URL` ระบบจะสร้างไฟล์ SQLite ชื่อ `smartgrad.db` ที่โฟลเดอร์หลักให้อัตโนมัติ

## การตั้งค่า (Configuration)

ระบบโหลดไฟล์ `.env` อัตโนมัติผ่าน python-dotenv ตัวแปรที่โค้ดอ่านมีดังนี้

| ตัวแปร | ค่าเริ่มต้น | คำอธิบาย |
|---|---|---|
| `DATABASE_URL` | ไม่ตั้ง (ใช้ SQLite `smartgrad.db`) | Connection string ของฐานข้อมูล รองรับ Supabase PostgreSQL ผ่าน asyncpg โดยแปลง prefix `postgres://` และ `postgresql://` เป็น `postgresql+asyncpg://` ให้อัตโนมัติ (Supabase: Connect > Connection Pooler > Mode: Session) |
| `SESSION_SECRET` | ค่า demo ในโค้ด | กุญแจเซ็นต์ Session ของอาจารย์ที่ปรึกษา ควรตั้งค่าเองเมื่อใช้งานจริง สร้างได้ด้วย `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ENV` | ไม่ตั้ง | ชื่อ environment (เช่น `production`) ดูหมายเหตุด้านล่าง |
| `SESSION_HTTPS_ONLY` | `false` | ตั้งเป็น `true` เพื่อให้ cookie ของ Session ส่งผ่าน HTTPS เท่านั้น |
| `ALLOWED_ORIGINS` | `localhost` / `127.0.0.1` พอร์ต 8000 และ 8080 | รายการ origin ที่อนุญาตให้เรียก API (CORS) คั่นด้วยเครื่องหมายจุลภาค เช่น `https://a.example.com,https://b.example.com` (origin แบบ `localhost` / `127.0.0.1` ทุกพอร์ตได้รับอนุญาตเสมอ) |
| `PORT` | `8080` (ใน Docker) | พอร์ตที่ใช้ใน `Dockerfile` เท่านั้น ไม่ได้ถูกอ่านโดยโค้ดแอป |

หมายเหตุ: ฟังก์ชัน `get_session_secret()` ใน `app/config.py` ถูกเขียนให้ error เมื่อ `ENV=production` แต่ไม่ได้ตั้ง `SESSION_SECRET` แต่ปัจจุบัน `app/main.py` ยังไม่ได้เรียกใช้ฟังก์ชันนี้ จึงยังใช้ค่า demo แทนได้แม้ตั้ง `ENV=production` ดังนั้นต้องตั้ง `SESSION_SECRET` เองทุกครั้งเมื่อนำไปใช้งานจริง

## การรันเทสต์ (Run Tests)

รันจากโฟลเดอร์หลักของโปรเจกต์ (หลังเปิดใช้งาน virtual environment และติดตั้งแพ็กเกจแล้ว):

```bash
python -m unittest discover -s tests -t . -v
```

มีเทสต์ทั้งหมด 78 รายการ โดยเทสต์จะใช้ไฟล์ SQLite ของตัวเอง (`test_smartgrad.db` ที่โฟลเดอร์หลัก) และบังคับตั้ง `DATABASE_URL` เอง จึงไม่แตะต้องฐานข้อมูลจริงแม้ใน `.env` จะชี้ไปที่ Supabase

## โครงสร้างโปรเจกต์ (Project Structure)

```
smartgrad/
├── app/                      # โค้ดหลักของแอปพลิเคชัน (Python package)
│   ├── main.py               # จุดเริ่มต้นของ FastAPI: ตั้งค่าแอป, Session/CORS, หน้าเว็บ (/, /search, /advisor, /health)
│   │                         #   และ route ที่หน้าเว็บเรียกใช้ (/review, /confirm, /plan)
│   ├── config.py             # ค่าคงที่และการตั้งค่ากลาง (Single Source of Truth) เช่น เกรดที่ผ่าน, หน่วยกิตเป้าหมาย
│   ├── database.py           # สร้าง async engine และ session; เลือก PostgreSQL หรือ SQLite จาก DATABASE_URL
│   ├── models.py             # โมเดลตารางฐานข้อมูล (SQLAlchemy)
│   ├── seed.py               # รัน app/init.sql และ migration เบื้องต้นตอนเริ่มระบบ
│   ├── init.sql              # SQL สำหรับ Seed หลักสูตร, รายวิชา และบัญชีอาจารย์ตัวอย่าง
│   ├── parser.py             # อ่าน Transcript PDF ด้วย pdfplumber (รหัสนักศึกษา, ชื่อ, รายวิชา, เกรด, ภาคเรียน)
│   ├── dashboard.py          # คำนวณความก้าวหน้าการเรียนและสร้างแผนการเรียน (Study Plan)
│   ├── services.py           # ฟังก์ชันตัวช่วยที่ใช้ร่วมกัน เช่น โหลดหลักสูตร, จัดหมวดวิชา, hash รหัสผ่าน
│   ├── routers/              # REST API (Pydantic schema ของแต่ละ API อยู่ในไฟล์ router นั้นๆ)
│   │   ├── students.py       # API นักศึกษา: โปรไฟล์, อัปโหลด Transcript, Dashboard, แผนการเรียน, จำลอง/ผลกระทบการถอน
│   │   ├── curriculum.py     # API หลักสูตร: รายการหลักสูตร, ค้นหารายวิชา, Prerequisite
│   │   └── advisors.py       # API อาจารย์ที่ปรึกษา: เข้า/ออกจากระบบ, รายชื่อนักศึกษา, รายงาน
│   ├── templates/            # หน้าเว็บ (Jinja2 + HTML)
│   │   ├── index.html        # หน้านักศึกษา: อัปโหลด, ตรวจสอบ/แก้ไข, Dashboard, แผนการเรียน, Export PDF
│   │   ├── search.html       # หน้าค้นหารายวิชา
│   │   └── advisor.html      # หน้าอาจารย์ที่ปรึกษา
│   └── static/               # ไฟล์ที่เสิร์ฟที่ /static
│       ├── css/              # สไตล์ของแต่ละหน้า (index.css, search.css, advisor.css)
│       └── js/               # สคริปต์ของแต่ละหน้า (index.js, search.js, advisor.js)
├── tests/
│   └── test_smartgrad.py     # Unit test และ Integration test ทั้งหมด (78 รายการ)
├── requirements.txt          # แพ็กเกจ Python ที่ต้องติดตั้ง (ระบุเวอร์ชันตายตัว)
├── Dockerfile                # Image แบบ python:3.12-slim รันด้วย non-root user
├── docker-compose.yml        # รันผ่าน Docker Compose (อ่านค่าจาก .env, mount ./app, เปิด --reload)
├── .env.example              # ตัวอย่างไฟล์ตั้งค่า (คัดลอกเป็น .env)
└── UserRequirements.txt      # เอกสารความต้องการของผู้ใช้ (User Requirements)
```

## หน้าเว็บและ API (Pages & API)

เปิด `http://localhost:8000/docs` เพื่อดูเอกสาร API แบบโต้ตอบ (Swagger UI) พร้อมทดลองเรียกใช้ได้

### หน้าเว็บ

| Path | คำอธิบาย |
|---|---|
| `/` | หน้านักศึกษา: อัปโหลด Transcript, ตรวจสอบ/แก้ไข, Dashboard, แผนการเรียน, Export PDF |
| `/search` | ค้นหารายวิชาในหลักสูตร |
| `/advisor` | หน้าอาจารย์ที่ปรึกษา |
| `/health` | ตรวจสอบสถานะระบบ (Health Check) |
| `/docs` | เอกสาร API แบบโต้ตอบ (FastAPI) |

### REST API (prefix `/api`)

| กลุ่ม | Endpoint หลัก | ใช้ทำอะไร |
|---|---|---|
| `/api/curriculum` | `GET /api/curriculum` | ดูหลักสูตรแยกตามชั้นปี/เทอม |
| | `GET /api/curriculum/programs`, `GET /api/curriculum/programs/{id}` | รายการหลักสูตรและเกณฑ์หน่วยกิต |
| | `GET /api/curriculum/courses`, `GET /api/curriculum/courses/{code}` | ค้นหา/กรองรายวิชา และดูรายละเอียดพร้อม Prerequisite |
| | `POST /api/curriculum/programs`, `POST /api/curriculum/courses` | เพิ่มหลักสูตรหรือรายวิชาใหม่ |
| `/api/students` | `POST /api/students`, `GET /api/students/{id}` | สร้าง/ดูโปรไฟล์นักศึกษา |
| | `POST /api/students/{id}/transcript` | อัปโหลด Transcript PDF |
| | `GET /api/students/{id}/dashboard` | Dashboard ความก้าวหน้า |
| | `GET /api/students/{id}/transcript-courses`, `PUT .../transcript-courses/{code}` | ดู/แก้ไขรายวิชาที่ parse ได้ |
| | `GET /api/students/{id}/plan` | แนะนำวิชาสำหรับเทอมถัดไป |
| | `POST /api/students/{id}/simulate` | จำลองสถานะโดยนับวิชาที่กำลังเรียน |
| | `GET /api/students/{id}/withdrawal-impact/{code}` | ผลกระทบหากถอนวิชา |
| `/api/advisors` | `POST /api/advisors/login`, `POST .../logout`, `GET .../me` | เข้า/ออกจากระบบ และดูบัญชีปัจจุบัน |
| | `GET /api/advisors/{id}/students` | รายชื่อนักศึกษาในความดูแล |
| | `GET /api/advisors/{id}/students/{student_id}` | รายงานสรุปรายบุคคล |
| | `GET /api/advisors/{id}/ready-to-graduate` | นักศึกษาที่หน่วยกิตครบ |
| | `GET /api/advisors/{id}/summary` | รายงานภาพรวม |

หมายเหตุ: endpoint `/api/advisors/{id}/...` ต้องเข้าสู่ระบบด้วยบัญชีอาจารย์คนนั้นก่อน นอกจากนี้ `main.py` ยังมี `POST /review`, `/confirm`, `/plan` ที่หน้า `/` เรียกใช้โดยตรง (ไม่แสดงใน `/docs`)

## บัญชีอาจารย์ตัวอย่าง (Demo Advisor Account)

เปิด `http://localhost:8000/advisor` แล้วเข้าสู่ระบบด้วยบัญชีเริ่มต้นจากระบบ Seed ข้อมูล:

- **รหัสอาจารย์:** `ADVISOR001`
- **รหัสผ่าน:** `smartgrad-demo`
- **ปีการศึกษาที่ดูแล:** `2567` (นักศึกษาที่รหัสขึ้นต้นด้วย `67`)
