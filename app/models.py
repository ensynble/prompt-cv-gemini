from pydantic import BaseModel, Field
from typing import Optional, List

class BBox(BaseModel):
    # normalized coordinate(0...1) to be resolution independent
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)
    
class Detection(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    score: float = Field(ge=0.0, le=1.0)
    bbox: BBox
    reason: Optional[str] = Field(default=None, max_length=200)
    
class VisionResult(BaseModel):
    """`
    Universal structured response for ANY prompt:
    - summary: always present
    - count: 0 if not applicable / unknown
    - detections: bboxes when localization make sense, else []"""
    summary: str = Field(min_length=1, max_length=500)
    count: int = Field(ge=0)
    detections: List[Detection] = Field(default_factory=list)
    
class AnalyzeImageResponse(BaseModel):
    request_id: str
    result: VisionResult
    model: str
    latency_ms: int
    
    