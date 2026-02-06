from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MAX_IMAGE_BYTES: int = 1000000
    ALLOW_ORIGINS: str = "*"
    DEMO_TOKEN: str = ""
    STRICT_JSON_ONLY: bool = True

    ALLOW_METHODS: str = "*"
    ALLOW_HEADERS: str = "*"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()


  