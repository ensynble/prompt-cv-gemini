from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class CheckResult(BaseModel):
    id: str = Field(min_length=1, max_length=16) 
    question: str = Field(min_length=1, max_length=300)
    answer: Literal["yes", "no", "unknown"]
    # confidence: float = Field(ge=0.0, le=1.0)
    # evidence: Optional[str] = Field(default=None, max_length=180)

class QAResult(BaseModel):
    results: List[CheckResult] = Field(default_factory=list)    
    