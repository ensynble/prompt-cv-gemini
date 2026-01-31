from pydantic import BaseModel
import os

class Settings(BaseModel):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    DEMO_TOKEN: str = os.getenv("DEMO_TOKEN",  "")
    
    ALLOW_ORIGINS: str = os.getenv("ALLOW_ORIGINS", "*")
    
    MAX_IMAGE_BYTES: int = int(os.getenv("MAX_IMAGE_BYTES", "4000000"))  # 4MB default
    
    STRICT_JSON_ONLY: bool = os.getenv("STRICT_JSON_ONLY", "true").lower() == "true" # 20 seconds default

settings = Settings()
    