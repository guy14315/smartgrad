import json
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.templating import Jinja2Templates

from dashboard import compute_dashboard
from parser import parse_transcript

app = FastAPI()
templates = Jinja2Templates(directory="templates")

CURRICULUM = json.loads((Path(__file__).parent / "curriculum.json").read_text(encoding="utf-8"))


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/")
async def upload_transcript(request: Request, file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return templates.TemplateResponse(
            request, "index.html", {"error": "กรุณาอัปโหลดไฟล์ .pdf เท่านั้น"}
        )

    courses = parse_transcript(file.file)
    dashboard = compute_dashboard(courses, CURRICULUM)

    return templates.TemplateResponse(request, "index.html", {"dashboard": dashboard})
