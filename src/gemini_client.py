import json
import time
from typing import Any

from google import genai

from src.config import GEMINI_API_KEY


class GeminiQuotaError(RuntimeError):
    """Raised when the Gemini API quota has been exhausted."""


class GeminiTemporaryError(RuntimeError):
    """Raised when Gemini has a temporary service/rate-limit problem."""


class GeminiClient:
    """
    Small wrapper around the Gemini API.

    Responsibilities:

    - Call Gemini
    - Request structured JSON
    - Parse JSON responses
    - Distinguish quota failures from temporary failures
    - Retry only when retrying makes sense
    """

    def __init__(
        self,
        model: str = "gemini-3.6-flash",
        max_retries: int = 2,
        retry_delay: int = 5,
    ) -> None:
        self.client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def generate_json(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        """
        Send a prompt to Gemini and parse the response as JSON.

        Quota exhaustion is raised immediately.

        Temporary failures are retried a bounded number of times.

        Non-retryable configuration/model errors are raised
        immediately.
        """

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.max_retries + 1,
        ):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                    },
                )

                text = response.text

                if not text:
                    raise ValueError(
                        "Gemini returned an empty response"
                    )

                try:
                    return json.loads(text)

                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "Gemini returned invalid JSON: "
                        f"{text[:500]}"
                    ) from exc

            except Exception as exc:
                last_error = exc

                error_text = str(exc).lower()

                # -------------------------------------------------
                # Quota exhaustion
                # -------------------------------------------------
                #
                # Example:
                #
                # 429 RESOURCE_EXHAUSTED
                # generate_content_free_tier_requests
                #
                # Retrying is pointless when the project/model
                # quota itself has been exhausted.
                # -------------------------------------------------

                if (
                    "resource_exhausted" in error_text
                    or "quota exceeded" in error_text
                    or "free_tier" in error_text
                ):
                    raise GeminiQuotaError(
                        "Gemini API quota exhausted. "
                        "The current API project/model quota "
                        "does not allow additional requests."
                    ) from exc

                # -------------------------------------------------
                # Model/configuration errors
                # -------------------------------------------------
                #
                # Example:
                #
                # 404 NOT_FOUND
                # model is not available
                #
                # Retrying will not fix an invalid/unavailable
                # model.
                # -------------------------------------------------

                if (
                    "404" in error_text
                    or "not_found" in error_text
                    or "model is not available" in error_text
                    or "no longer available" in error_text
                ):
                    raise RuntimeError(
                        f"Gemini model '{self.model}' is unavailable "
                        "for the current API project. "
                        "Check the configured model name and "
                        "project access."
                    ) from exc

                # -------------------------------------------------
                # Temporary service errors
                # -------------------------------------------------

                if (
                    "503" in error_text
                    or "service unavailable" in error_text
                    or "temporarily unavailable" in error_text
                ):
                    if attempt < self.max_retries:
                        print(
                            f"  Gemini temporary error "
                            f"(attempt {attempt}/"
                            f"{self.max_retries}). "
                            f"Retrying in "
                            f"{self.retry_delay}s..."
                        )

                        time.sleep(
                            self.retry_delay
                        )

                        continue

                    raise GeminiTemporaryError(
                        "Gemini service remained unavailable "
                        f"after {self.max_retries} attempts."
                    ) from exc

                # -------------------------------------------------
                # Other 429 errors
                # -------------------------------------------------
                #
                # Some 429 responses may represent transient
                # rate limiting rather than exhausted daily quota.
                # Retry these rather than immediately stopping.
                # -------------------------------------------------

                if "429" in error_text:
                    if attempt < self.max_retries:
                        print(
                            f"  Gemini rate limit "
                            f"(attempt {attempt}/"
                            f"{self.max_retries}). "
                            f"Retrying in "
                            f"{self.retry_delay}s..."
                        )

                        time.sleep(
                            self.retry_delay
                        )

                        continue

                    raise GeminiTemporaryError(
                        "Gemini rate limit persisted "
                        f"after {self.max_retries} attempts."
                    ) from exc

                # -------------------------------------------------
                # Non-retryable errors
                # -------------------------------------------------

                raise

        raise RuntimeError(
            "Gemini request failed."
        ) from last_error