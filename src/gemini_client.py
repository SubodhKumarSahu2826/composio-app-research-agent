import json

from google import genai

from src.config import GEMINI_API_KEY


class GeminiClient:
    """Small wrapper around the Gemini API."""

    def __init__(self) -> None:
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = "gemini-2.5-flash"

    def generate_json(self, prompt: str) -> dict:
        """
        Send a prompt to Gemini and parse the response as JSON.

        The model is explicitly instructed to return JSON so that
        the result can be validated by our Pydantic models.
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )

        text = response.text

        if not text:
            raise ValueError("Gemini returned an empty response")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Gemini returned invalid JSON: {text[:500]}"
            ) from exc