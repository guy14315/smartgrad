# SmartGrad

- `main.py` — FastAPI routes (upload form + result page)
- `parser.py` — extracts course code/credit/grade rows out of the transcript PDF with `pdfplumber`
- `dashboard.py` — matches parsed courses against `curriculum.json` and computes progress
- `templates/index.html` — the single upload/results page (Jinja2)
- `templates/advisor.html` — หน้าสำหรับอาจารย์ที่ปรึกษา (`/advisor`)

## Prerequisites

- Python 3.12
- Docker (optional)

## Option A: Run locally with plain pip

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install fastapi[standard] jinja2 pdfplumber
fastapi dev main.py
```

This starts the dev server with auto-reload at http://localhost:8000.

To run it production-style instead:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Option A2: Run locally with uv

If you already use [uv](https://docs.astral.sh/uv/), it'll install the exact pinned versions from `uv.lock`:

```bash
uv sync
uv run fastapi dev main.py
```

## Option B: Run with Docker

No local Python setup needed at all:

```bash
docker compose up --build
```

The app is served at http://localhost:8000 (mapped to container port 8080). The compose file mounts your source into the container for live-reload, so code edits pick up without rebuilding.

To run the production image directly, without compose:

```bash
docker build -t smartgrad .
docker run -p 8080:8080 smartgrad
```

## Deployment

The `Dockerfile` reads the `PORT` env var (defaulting to 8080), which matches what Google Cloud Run expects — build and deploy the image there via `gcloud run deploy`.

## หน้าสำหรับอาจารย์ที่ปรึกษา

เปิด `http://localhost:8000/advisor` แล้วเข้าสู่ระบบด้วยบัญชีสาธิตที่ระบบสร้างในฐานข้อมูลให้อัตโนมัติเมื่อเริ่มต้น:

- รหัสอาจารย์: `ADVISOR001`
- รหัสผ่าน: `smartgrad-demo`
- ปีการศึกษาที่ดูแล: `2567` (รหัสนักศึกษาที่ขึ้นต้นด้วย `67`)

หน้านี้จะแสดงเฉพาะนักศึกษาในความดูแลที่อัปโหลด Transcript แล้วเท่านั้น และการส่งคำแนะนำจะส่งไปยัง `{รหัสนักศึกษา 8 หลัก}@kmitl.ac.th`

นักศึกษาไม่ต้องมีบัญชี: ที่หน้าอัปโหลดหลักเพียงเลือกไฟล์ Transcript ระบบจะอ่านรหัสนักศึกษาและชื่อจาก PDF สร้างข้อมูลนักศึกษา และผูกอาจารย์ตาม `cohort_year` ของบัญชีอาจารย์ใน `init.sql` โดยอัตโนมัติ เช่น `67050476` จะถูกผูกกับอาจารย์ของปี `2567`.

ตั้งค่าการส่งอีเมลผ่านตัวแปรระบบต่อไปนี้ (ไม่ต้องใส่รหัสผ่านลงในโค้ด):

```bash
SESSION_SECRET=replace-with-a-long-random-value
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_FROM=smartgrad@example.com
SMTP_USERNAME=smartgrad@example.com
SMTP_PASSWORD=your-smtp-password
SMTP_STARTTLS=true
```

หากยังไม่ได้ตั้งค่า `SMTP_HOST` และ `SMTP_FROM` ระบบจะแจ้งว่าไม่สามารถส่งอีเมลได้ โดยจะไม่บันทึกโน้ตว่า “ส่งสำเร็จ”
