import json
import re
from typing import Any, Dict, Optional
import httpx

from app.services.ai.base_provider import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        self._api_key = api_key.strip() if api_key else ""
        self._model_name = (model_name or "gemini-3.8-flash").strip()
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    @staticmethod
    def _clean_json_text(raw_text: str) -> str:
        """Strip markdown code fence blocks if returned by the LLM."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    async def generate_understanding(
        self, prompt: str, system_instruction: str, timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Generate structured JSON dataset understanding from prompt.
        """
        return await self.generate_json(prompt, system_instruction, timeout_seconds)

    async def generate_json(
        self, prompt: str, system_instruction: str, timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """
        Call Gemini REST API using structured JSON mode via x-goog-api-key header.
        """
        if not self._api_key:
            raise ValueError("Gemini API key is not configured.")

        url = f"{self._base_url}/models/{self._model_name}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_instruction}],
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        async with httpx.AsyncClient(timeout=float(timeout_seconds)) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException:
                raise TimeoutError(f"Gemini request timed out after {timeout_seconds} seconds.")
            except httpx.RequestError as e:
                # Do not expose internal connection details that might leak tokens
                raise ConnectionError("Failed to establish secure connection to Gemini API.")

        if response.status_code == 429:
            raise RuntimeError("Gemini API rate limit exceeded (HTTP 429). Please retry shortly.")
        elif response.status_code in (401, 403):
            raise PermissionError("Gemini API authentication failed. Please verify your GEMINI_API_KEY.")
        elif response.status_code >= 400:
            error_msg = f"Gemini API returned error (HTTP {response.status_code})."
            try:
                err_data = response.json()
                if "error" in err_data and "message" in err_data["error"]:
                    clean_msg = err_data["error"]["message"]
                    # Mask any potential key if present in message
                    clean_msg = re.sub(r"key=[a-zA-Z0-9_\-]+", "key=[REDACTED]", clean_msg)
                    error_msg += f" Details: {clean_msg}"
            except Exception:
                pass
            raise RuntimeError(error_msg)

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned empty response with zero candidates.")

        content_parts = candidates[0].get("content", {}).get("parts", [])
        if not content_parts or "text" not in content_parts[0]:
            raise RuntimeError("Gemini candidate contains no text response.")

        raw_text = content_parts[0]["text"]
        clean_text = self._clean_json_text(raw_text)

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as jde:
            raise ValueError(f"Gemini returned invalid JSON: {str(jde)}")

