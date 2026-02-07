from google import genai
from google.genai import types

from .models import QAResult

class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        if not api_key:
            raise ValueError("Missing api_key")
        self.model = model
        self.client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})

    def _system_instruction(self) -> str:
        return (
            "Analyze the image and answer the user's checklist.\n"
            "Return JSON matching the schema.\n"
            "Preserve original question wording for 'question', no rephase or change\n"
            "Values for 'answer': 'yes', 'no', 'unknown'.\n"
        )

    def _thinking_config_for_model(self) -> types.ThinkingConfig | None:
        """
        Adapt thinking config by model:
          - gemini-3-flash-preview -> thinking_level=MINIMAL
          - gemini-2.5-flash      -> thinking_budget=0
          - gemini-2.5-flash-lite -> None (do not set)
        """
        m = (self.model or "").lower()

        if m == "gemini-3-flash-preview":
            return types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)

        if m == "gemini-2.5-flash":
            return types.ThinkingConfig(thinking_budget=0)
        if m == "gemini-2.5-flash-lite":
            return None
        # default: don't force anything for unknown models
        return None


    async def analyze_image(self, prompt: str, image_bytes: bytes, mime_type: str) -> QAResult:
        img_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type,media_resolution={"level": "MEDIA_RESOLUTION_LOW"})

        thinking_cfg = self._thinking_config_for_model()

        config_kwargs = dict(
            system_instruction=self._system_instruction(),
            response_mime_type="application/json",
            response_schema=QAResult,
            temperature=0.0,
            max_output_tokens=1000,
        )
        if thinking_cfg is not None:
            config_kwargs["thinking_config"] = thinking_cfg

        config = types.GenerateContentConfig(**config_kwargs)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[img_part, f"Checklist Items:\n{prompt}"],
            config=config,
        )

        if getattr(response, "parsed", None):
            return response.parsed

        raw = getattr(response, "text", None) or getattr(response, "output_text", None) or str(response)
        raise RuntimeError(f"Gemini failed to return parsed JSON. Raw: {raw}")
