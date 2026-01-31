import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from .models import VisionResult

class GeminiClient:
    def __init__(self, api_key: str, model: str, strict_json_only:bool = True):
        self.model = model
        self.strict_json_only = strict_json_only
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
    
    def _system_instruction(self) -> str:
        return (
            "You are a visual inspection assistant. "
            "Given an image and a user prompt, produce a structured result.\n"
            "Rules:\n"
            "1) Always return JSON that matches the provided schema.\n"
            "2) Provide a short 'summary' answering the prompt.\n"
            "3) If the prompt implies counting or locating specific instances, set 'count' and include one bbox per instance in 'detections'.\n"
            "4) Bounding boxes must tightly enclose the relevant object/person.\n"
            "5) If uncertain, either omit that detection or lower 'score'. Avoid hallucinations.\n"
            "6) Use short snake_case labels (e.g., no_goggles, lid_uncovered).\n"
        )

    
    def analyze_image(self, prompt: str, image_bytes: bytes, mime_type: str) -> VisionResult:
        img_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        
        config = {
            "system_instruction": self._system_instruction(),
            "response_mime_type": "application/json",
            "response_json_schema": VisionResult.model_json_schema(),
        }  
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                img_part,
                f"USER_PROMPT:\n{prompt}\n",
            ],
            config=config,
        )  
        
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned empty response text.")
        try:
            return VisionResult.model_validate_json(text)
        except ValidationError as ve:
            raise RuntimeError(f"Gemini JSON schema mismatch: {ve.errors()} | Raw: {text[:500]}")
        except Exception as e: 
            if self.strict_json_only:
                raise RuntimeError(f"Gemini returned non-conforming JSON. Raw:{text[:400]} ")
            
            try:
                obj = json.loads(text)
                return VisionResult.model_validate(obj)
            
            except Exception as e:
                raise RuntimeError(f"Failed to parse Gemini JSON. Raw: {text[:400]}") from e