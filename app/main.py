import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import AnalyzeImageResponse
from .gemini_client import GeminiClient
from pydantic import ValidationError
import logging

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Prompt-CV backend", version="0.5.0")

allow_origins = [o.strip() for o in settings.ALLOW_ORIGINS.split(",")] if settings.ALLOW_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins if allow_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp"}

gemini = GeminiClient(
    api_key=settings.GEMINI_API_KEY,
    model=settings.GEMINI_MODEL,
    strict_json_only=settings.STRICT_JSON_ONLY,)

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

@app.get("/health")
def health():
    return {"ok": True, "service": "prompt-cv-backend"}

# synchronous API
@app.post("/v1/analyze-image", response_model=AnalyzeImageResponse)
async def analyze_image(
    prompt: str = Form(..., min_length=1, max_length=2000),
    image: UploadFile = File(...),
    x_demo_token: Optional[str] = Header(default=None, convert_underscore=False),        
):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not set. Put it in backend/.env for local dev.",
        )

    t0 = time.time()
    _require_demo_token(x_demo_token)
    
    if image.content_type not in SUPPORTED_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image content type {image.content_type}. Supported: {sorted(SUPPORTED_MIME)} ",
        )
    
    image_bytes = await _read_upload_limited(image, settings.MAX_IMAGE_BYTES)
    
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured: GEMINI_API_KEY is missing")
    
    request_id = str(uuid.uuid4())
    
    try:
        result = gemini.analyze_image(prompt, image_bytes=image_bytes, mime_type=image.content_type)
    except Exception as e:
        logger.exception("Gemini inference failed")
        raise HTTPException(status_code=502, detail=f"Gemini inference failed: {str(e)}")
    
    if result is None:
        raise HTTPException(status_code=502, detail="Gemini returned null result unexpectedly.")
    latency_ms = int((time.time() - t0) * 1000)
    
    try:
        return AnalyzeImageResponse(
            request_id=request_id,
            result=result,
            model=settings.GEMINI_MODEL,
            latency_ms=latency_ms,
        )
    except ValidationError as ve:
        logger.exception("Response validation failed")
        raise HTTPException(status_code=502, detail={"error": "Response validation failed", "details": ve.errors()})
        
    
    
    
        
