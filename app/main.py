import time, asyncio
from typing import Optional

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .gemini_client import GeminiClient
from .job_queue import JobManager, JobStatus

SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp"}
JOBS = JobManager(max_queue=100)
GEMINI_SEMAPHORE = asyncio.Semaphore(2)
WORKER_COUNT = 1
GEMINI_TIMEOUT_S = 30  # move this near your constants

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY in .env")
    
    tasks = [asyncio.create_task(_worker_loop(i)) for i in range(WORKER_COUNT)]
    yield
    ## graceful shutdown
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

app = FastAPI(title="Local CV prompt Detection(backend)", version="0.6.0", lifespan=lifespan)

allow_origins = [o.strip() for o in settings.ALLOW_ORIGINS.split(",") if o.strip()]
wildcard = (not allow_origins) or (allow_origins == ["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if wildcard else allow_origins,
    allow_credentials=False if wildcard else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini = GeminiClient(
    api_key=settings.GEMINI_API_KEY,
    model=settings.GEMINI_MODEL)

async def _worker_loop(worker_id: int):
    while True:
        job = await JOBS.queue.get()
        try:
            rec = JOBS.records.get(job.job_id)
            if not rec: continue

            rec.status = JobStatus.RUNNING
            rec.started_at = time.monotonic()
            rec.model = settings.GEMINI_MODEL

            async with GEMINI_SEMAPHORE:
                result = await asyncio.wait_for(
                    gemini.analyze_image(
                        prompt=job.prompt,
                        image_bytes=job.image_bytes,
                        mime_type=job.mime_type,
                    ),
                    timeout=GEMINI_TIMEOUT_S,
                )

            rec.result = result
            rec.status = JobStatus.SUCCEEDED

        except asyncio.TimeoutError:
            if rec is not None:
                rec.error = f"Gemini timeout after {GEMINI_TIMEOUT_S}s"
                rec.status = JobStatus.FAILED

        except Exception as e:
            if rec is not None:
                rec.error = str(e)
                rec.status = JobStatus.FAILED
        finally:
            if rec is not None:
                rec.finished_at = time.monotonic()
                rec.done_event.set()
            JOBS.queue.task_done()

        
def _require_demo_token(x_demo_token: Optional[str]) -> None:
    if settings.DEMO_TOKEN:
        if not x_demo_token or x_demo_token != settings.DEMO_TOKEN:
            raise HTTPException(status_code=401, detail="Missing or invalid X-DEMO-TOKEN")

async def _read_upload_limited(upload: UploadFile, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = await upload.read(1024*1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail=f"Image too large. Limit is {max_bytes}") 
        chunks.append(chunk)
    
    return b"".join(chunks)

def _job_payload(job_id: str, rec) -> dict:
    out = {
        "job_id": job_id,
        "status": rec.status.value,
        "model": rec.model,
        "error": rec.error,
    }
    
    if rec.started_at is not None:
        out["queued_ms"] = int((rec.started_at - rec.created_at) * 1000)
    if rec.finished_at is not None:
        start = rec.started_at or rec.created_at
        out["latency_ms"] = int((rec.finished_at - start) * 1000)
    if rec.status == JobStatus.SUCCEEDED and rec.result is not None:
        out["result"] = rec.result.model_dump()
    
    return out

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "prompt-cv-backend",
        "queue_size": JOBS.queue.qsize(),
        "workers": WORKER_COUNT,
        "gemini_concurrency": GEMINI_SEMAPHORE._value,  # or store separately
    }

# synchronous API
@app.post("/jobs")
async def submit_job(
    prompt: str = Form(..., min_length=1, max_length=2000),
    image: UploadFile = File(...),
    x_demo_token: Optional[str] = Header(default=None, alias="X-DEMO-TOKEN"),
  
    wait_ms: int = Query(default=0, ge=0, le=30000),      
):
    _require_demo_token(x_demo_token)
    
    if image.content_type not in SUPPORTED_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image content type {image.content_type}. Supported: {sorted(SUPPORTED_MIME)} ",
        )
    
    image_bytes = await _read_upload_limited(image, settings.MAX_IMAGE_BYTES)
    await image.close()
    
    try:
        job_id = JOBS.submit(prompt=prompt, image_bytes=image_bytes, mime_type=image.content_type)
    except asyncio.QueueFull:
        raise HTTPException(status_code=429, detail="Server busy (queue full). Try again.")
    
    rec = JOBS.get(job_id)
    if rec is None:
        raise HTTPException(status_code=500, detail="Internal error: job record missing")
    
    # if caller wants one-call behavior, wait for completion(up to wait_ms)
    if wait_ms > 0:
        try:
            await asyncio.wait_for(rec.done_event.wait(), timeout=wait_ms/1000.0)
        except asyncio.TimeoutError:
            pass
        
        rec = JOBS.get(job_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="job expired")
        return _job_payload(job_id, rec)
    
    return {"job_id": job_id, "status": "queued"}


@app.get("/job/{job_id}")
async def get_job(
    job_id: str,
    wait_ms: int = Query(default=0, le=30000),
):
    """
    Event-based long polling:
    - if job is done -> returns immediately
    - if job is not done and wait_ms > 0 -> wait until done_event OR timeout
    This does not sacrifice latency (no periodic polling loop)
    """
    rec = JOBS.get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="job not found")
    
    if wait_ms > 0 and rec.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        try:
            await asyncio.wait_for(rec.done_event.wait(), timeout=wait_ms/1000.0)
        except asyncio.TimeoutError:
            pass
    
    rec = JOBS.get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="job expired")
    
    return _job_payload(job_id, rec)       
        
    
    
    
        
