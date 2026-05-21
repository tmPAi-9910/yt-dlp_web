from fastapi import FastAPI, Request, HTTPException, Depends, Form, Header
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
import os
import asyncio

from .auth import verify_token
from .downloader import DownloadManager

MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "2"))
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")

app = FastAPI(title="yt-dlp Web Downloader")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

download_manager = DownloadManager(tmp_root=str(Path("/tmp") / "ytdlp_web"), max_concurrent=MAX_CONCURRENT_DOWNLOADS)


@app.on_event("startup")
async def startup_event():
    ttl = int(os.getenv("FILE_TTL_MIN", "60"))
    # start cleanup task in background
    asyncio.create_task(download_manager.cleanup_task(ttl_minutes=ttl))


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"auth_token": AUTH_TOKEN})


@app.post("/download")
async def download_form(url: str = Form(...), format_option: str = Form("original"), token: str = Form(None)):
    if AUTH_TOKEN and token != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    job_id = download_manager.create_job(url, format_option)
    return RedirectResponse(url=f"/status/{job_id}", status_code=303)


@app.post("/api/download")
async def api_download(payload: dict, authorization: str = Header(None), token_ok: bool = Depends(verify_token)):
    url = payload.get("url")
    format_option = payload.get("format", "original")
    if not url:
        raise HTTPException(status_code=400, detail="'url' is required")
    job_id = download_manager.create_job(url, format_option)
    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def status(job_id: str):
    job = download_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/files/{job_id}/{filename}")
async def get_file(job_id: str, filename: str):
    path = download_manager.get_file_path(job_id, filename)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=Path(path).name, media_type='application/octet-stream')
