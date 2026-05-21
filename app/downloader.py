import os
import uuid
import time
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List

import yt_dlp


class DownloadManager:
    def __init__(self, tmp_root: str = "/tmp/ytdlp_web", max_concurrent: int = 2):
        self.tmp_root = tmp_root
        os.makedirs(self.tmp_root, exist_ok=True)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.jobs = {}  # job_id -> job dict
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

    def create_job(self, url: str, format_option: str = "original") -> str:
        job_id = uuid.uuid4().hex
        self.jobs[job_id] = {
            "id": job_id,
            "url": url,
            "format": format_option,
            "status": "queued",
            "files": [],
            "error": None,
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "dir": None,
        }
        asyncio.create_task(self._run_job(job_id, url, format_option))
        return job_id

    async def _run_job(self, job_id: str, url: str, format_option: str):
        job = self.jobs[job_id]
        job["status"] = "running"
        job["started_at"] = time.time()

        await self.semaphore.acquire()
        dest_dir = os.path.join(self.tmp_root, job_id)
        os.makedirs(dest_dir, exist_ok=True)
        job["dir"] = dest_dir

        loop = asyncio.get_running_loop()

        try:
            def blocking_download():
                ydl_opts = {"outtmpl": os.path.join(dest_dir, "%(title)s.%(ext)s")}

                if format_option == "audio":
                    ydl_opts["format"] = "bestaudio/best"
                    ydl_opts["postprocessors"] = [
                        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
                    ]
                elif format_option == "mp4":
                    # tell yt-dlp to get best audio+video and merge to mp4
                    ydl_opts["format"] = "bestvideo+bestaudio/best"
                    ydl_opts["merge_output_format"] = "mp4"
                else:
                    ydl_opts["format"] = "best"

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)

                files = []
                for root, _, filenames in os.walk(dest_dir):
                    for fn in filenames:
                        files.append(os.path.join(root, fn))
                return files

            files = await loop.run_in_executor(self.executor, blocking_download)
            job["files"] = files
            job["status"] = "finished"
        except Exception as e:
            job["status"] = "error"
            job["error"] = str(e)
        finally:
            job["finished_at"] = time.time()
            try:
                self.semaphore.release()
            except Exception:
                pass

    def get_job(self, job_id: str) -> Optional[dict]:
        return self.jobs.get(job_id)

    def get_file_path(self, job_id: str, filename: str) -> Optional[str]:
        job = self.jobs.get(job_id)
        if not job or not job.get("dir"):
            return None
        # direct path
        candidate = os.path.join(job["dir"], filename)
        if os.path.exists(candidate):
            return candidate
        # try to match by basename
        for f in job.get("files", []):
            if os.path.basename(f) == filename:
                return f
        return None

    async def cleanup_task(self, ttl_minutes: int = 60):
        """Periodically remove job directories older than ttl_minutes."""
        while True:
            now = time.time()
            try:
                for name in os.listdir(self.tmp_root):
                    path = os.path.join(self.tmp_root, name)
                    try:
                        mtime = os.path.getmtime(path)
                    except Exception:
                        continue
                    age_min = (now - mtime) / 60.0
                    if age_min > ttl_minutes:
                        try:
                            shutil.rmtree(path)
                        except Exception:
                            pass
                        if name in self.jobs:
                            del self.jobs[name]
            except Exception:
                pass
            await asyncio.sleep(60)
