from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, urlsplit, urlunsplit

from src.models import AppResearch


VALID_SOURCE_TYPES = {
    "official_docs",
    "official_blog",
    "official_github",
    "third_party",
    "video",
    "other",
}

VALID_MCP_STATUSES = {
    "Official MCP",
    "Third-party MCP",
    "No MCP Found",
    "Unknown",
}


@dataclass
class VerificationResult:
    """
    Result of deterministic verification of an AppResearch result.

    The verifier does not change the research result. It reports
    inconsistencies, warnings, and an overall verification score.
    """

    passed: bool
    score: float
    checked_evidence: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def model_dump(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return {
            "passed": self.passed,
            "score": self.score,
            "checked_evidence": self.checked_evidence,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class ResearchVerifier:
    """
    Deterministically verify Gemini's structured research output.

    The verifier checks:

    - evidence URL consistency
    - evidence source-name consistency
    - source type validity
    - URL validity
    - MCP consistency
    - API documentation consistency
    - confidence ranges
    - suspicious evidence metadata

    It deliberately does not perform web requests and does not call
    an LLM. This keeps verification deterministic and inexpensive.
    """

    def verify(
        self,
        result: AppResearch,
        evidence: list[dict] | None = None,
    ) -> VerificationResult:
        """
        Verify an AppResearch result against the original evidence.

        Parameters
        ----------
        result:
            Validated AppResearch object produced by the extractor.

        evidence:
            Original structured evidence bundle supplied to Gemini.

        Returns
        -------
        VerificationResult
        """

        errors: list[str] = []
        warnings: list[str] = []

        web_sources = self._extract_web_sources(
            evidence or []
        )

        self._verify_evidence(
            result=result,
            web_sources=web_sources,
            errors=errors,
            warnings=warnings,
        )

        self._verify_mcp(
            result=result,
            web_sources=web_sources,
            errors=errors,
            warnings=warnings,
        )

        self._verify_api(
            result=result,
            web_sources=web_sources,
            errors=errors,
            warnings=warnings,
        )

        self._verify_confidence(
            result=result,
            errors=errors,
            warnings=warnings,
        )

        self._verify_buildability(
            result=result,
            errors=errors,
            warnings=warnings,
        )

        score = self._calculate_score(
            result=result,
            errors=errors,
            warnings=warnings,
        )

        return VerificationResult(
            passed=not errors,
            score=score,
            checked_evidence=len(result.evidence),
            errors=errors,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # URL normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_url(
        url: str | None,
    ) -> str:
        """
        Normalize URLs for deterministic comparison.

        Trailing slash differences are ignored.

        Query strings and fragments are preserved.
        """

        if not url:
            return ""

        value = str(url).strip()

        if not value:
            return ""

        try:
            parsed = urlsplit(value)

            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()

            path = parsed.path or "/"

            if path != "/":
                path = path.rstrip("/")

            return urlunsplit(
                (
                    scheme,
                    netloc,
                    path,
                    parsed.query,
                    parsed.fragment,
                )
            )

        except Exception:
            return value.rstrip("/").lower()

    # ------------------------------------------------------------------
    # Evidence extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_web_sources(
        evidence: list[dict],
    ) -> list[dict]:
        """
        Extract only real web evidence items.

        Composio discovery metadata is intentionally ignored.
        """

        sources: list[dict] = []

        for section in evidence:
            if not isinstance(section, dict):
                continue

            if section.get("type") != "web_evidence":
                continue

            items = section.get("items", [])

            if not isinstance(items, list):
                continue

            for item in items:
                if isinstance(item, dict):
                    sources.append(item)

        return sources

    # ------------------------------------------------------------------
    # Evidence verification
    # ------------------------------------------------------------------

    def _verify_evidence(
        self,
        result: AppResearch,
        web_sources: list[dict],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """
        Verify every extracted evidence item against the original
        web evidence.
        """

        if not result.evidence:
            errors.append(
                "Research result contains no evidence items."
            )
            return

        source_by_url = {
            self._normalize_url(
                item.get("url")
            ): item
            for item in web_sources
            if item.get("url")
        }

        source_by_title = {
            str(item.get("title")): item
            for item in web_sources
            if item.get("title")
        }

        for index, item in enumerate(
            result.evidence,
            start=1,
        ):
            url = str(item.url)
            normalized_url = self._normalize_url(url)

            source_name = item.source_name
            source_type = item.source_type

            source = source_by_url.get(
                normalized_url
            )

            if source is None:
                errors.append(
                    f"Evidence {index}: URL was not present in "
                    f"the supplied web evidence: {url}"
                )
                continue

            original_title = source.get("title")

            if source_name != original_title:
                errors.append(
                    f"Evidence {index}: source_name does not match "
                    f"the original source title."
                )

            if source_type not in VALID_SOURCE_TYPES:
                errors.append(
                    f"Evidence {index}: invalid source_type "
                    f"'{source_type}'."
                )

            if not self._valid_http_url(url):
                errors.append(
                    f"Evidence {index}: invalid HTTP(S) URL: {url}"
                )

            snippet = item.snippet

            if snippet:
                content = str(
                    source.get("content") or ""
                )

                normalized_snippet = self._normalize_text(
                    snippet
                )

                normalized_content = self._normalize_text(
                    content
                )

                if (
                    normalized_snippet
                    and normalized_snippet not in normalized_content
                ):
                    warnings.append(
                        f"Evidence {index}: snippet is not an "
                        f"exact substring of the supplied source "
                        f"content."
                    )
            else:
                warnings.append(
                    f"Evidence {index}: snippet is empty."
                )

            suspicious_labels = {
                "composio evidence",
                "web evidence",
                "tavily evidence",
                "official documentation",
            }

            if source_name.strip().lower() in suspicious_labels:
                errors.append(
                    f"Evidence {index}: suspicious source_name "
                    f"'{source_name}'."
                )

        urls = [
            self._normalize_url(
                str(item.url)
            )
            for item in result.evidence
        ]

        if len(urls) != len(set(urls)):
            warnings.append(
                "Research result contains duplicate evidence URLs."
            )

        _ = source_by_title

    # ------------------------------------------------------------------
    # MCP verification
    # ------------------------------------------------------------------

    def _verify_mcp(
        self,
        result: AppResearch,
        web_sources: list[dict],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """
        Verify MCP classification against extracted evidence.

        A Composio toolkit alone cannot establish official MCP.
        """

        status = result.mcp.status.value

        if status not in VALID_MCP_STATUSES:
            errors.append(
                f"Invalid MCP status: {status}"
            )
            return

        official_mcp_evidence = self._find_mcp_evidence(
            result=result,
            web_sources=web_sources,
            require_official=True,
        )

        third_party_mcp_evidence = self._find_mcp_evidence(
            result=result,
            web_sources=web_sources,
            require_official=False,
            third_party_only=True,
        )

        if status == "Official MCP":
            if result.mcp.official is not True:
                errors.append(
                    "MCP is classified as Official MCP but "
                    "official is not true."
                )

            if not result.mcp.url:
                errors.append(
                    "MCP is classified as Official MCP but "
                    "no MCP URL was provided."
                )

            if not official_mcp_evidence:
                errors.append(
                    "MCP is classified as Official MCP but no "
                    "supporting official evidence was found."
                )

            if (
                result.mcp.url
                and official_mcp_evidence
            ):
                mcp_url = self._normalize_url(
                    str(result.mcp.url)
                )

                official_urls = {
                    self._normalize_url(
                        item.get("url")
                    )
                    for item in official_mcp_evidence
                    if item.get("url")
                }

                if (
                    mcp_url
                    and mcp_url not in official_urls
                ):
                    warnings.append(
                        "Official MCP URL does not exactly "
                        "match an official MCP evidence URL."
                    )

        elif status == "Third-party MCP":
            if result.mcp.official is True:
                errors.append(
                    "MCP is classified as Third-party MCP but "
                    "official is true."
                )

            if not third_party_mcp_evidence:
                warnings.append(
                    "Third-party MCP classification has no "
                    "clearly identifiable third-party MCP evidence."
                )

        elif status == "No MCP Found":
            if official_mcp_evidence:
                errors.append(
                    "MCP is classified as No MCP Found despite "
                    "official MCP evidence being present."
                )

        elif status == "Unknown":
            if official_mcp_evidence:
                warnings.append(
                    "MCP is marked Unknown even though official "
                    "MCP evidence appears to be present."
                )

    # ------------------------------------------------------------------
    # API verification
    # ------------------------------------------------------------------

    def _verify_api(
        self,
        result: AppResearch,
        web_sources: list[dict],
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Verify API documentation claims."""

        documentation_url = result.api.documentation_url

        if documentation_url is None:
            if result.api.type.value not in {
                "Unknown",
                "No Public API Found",
            }:
                warnings.append(
                    "API type is specified but no documentation "
                    "URL was provided."
                )

            return

        documentation_url_string = str(
            documentation_url
        )

        source_urls = {
            self._normalize_url(
                item.get("url")
            )
            for item in web_sources
            if item.get("url")
        }

        normalized_documentation_url = (
            self._normalize_url(
                documentation_url_string
            )
        )

        if (
            normalized_documentation_url
            not in source_urls
        ):
            errors.append(
                "API documentation_url was not present in "
                "the supplied web evidence."
            )

    # ------------------------------------------------------------------
    # Confidence verification
    # ------------------------------------------------------------------

    def _verify_confidence(
        self,
        result: AppResearch,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """Check confidence values and flag suspicious certainty."""

        confidence_values = {
            "authentication": result.authentication.confidence,
            "access": result.access.confidence,
            "api": result.api.confidence,
            "mcp": result.mcp.confidence,
            "overall": result.overall_confidence,
        }

        for name, value in confidence_values.items():
            if not 0.0 <= value <= 1.0:
                errors.append(
                    f"{name} confidence is outside [0, 1]: "
                    f"{value}"
                )

        if result.overall_confidence == 1.0:
            warnings.append(
                "Overall confidence is 1.0. "
                "This should only be used for exceptionally "
                "direct and unambiguous evidence."
            )

        if result.mcp.confidence == 1.0:
            warnings.append(
                "MCP confidence is 1.0. "
                "Verify that the evidence is exceptionally direct."
            )

    # ------------------------------------------------------------------
    # Buildability verification
    # ------------------------------------------------------------------

    def _verify_buildability(
        self,
        result: AppResearch,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        """
        Check obvious contradictions between buildability and
        access/API/MCP information.
        """

        verdict = result.buildability.verdict.value
        access_type = result.access.type.value
        api_type = result.api.type.value

        if verdict == "Easy":
            if api_type in {
                "No Public API Found",
                "Unknown",
            }:
                warnings.append(
                    "Buildability is Easy although no confirmed "
                    "public API was identified."
                )

            if access_type in {
                "Gated",
                "Contact Sales",
                "Partnership Required",
                "Admin Approval Required",
            }:
                warnings.append(
                    "Buildability is Easy despite a significant "
                    "access gate."
                )

        if verdict == "Blocked":
            if api_type not in {
                "No Public API Found",
                "Unknown",
            }:
                warnings.append(
                    "Buildability is Blocked even though an API "
                    "surface was identified."
                )

        if verdict == "Gated":
            if access_type in {
                "Self-serve / Free",
                "Self-serve / Trial",
            }:
                warnings.append(
                    "Buildability is Gated while access is "
                    "classified as self-serve."
                )

    # ------------------------------------------------------------------
    # MCP evidence helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_mcp_evidence(
        result: AppResearch,
        web_sources: list[dict],
        require_official: bool = False,
        third_party_only: bool = False,
    ) -> list[dict]:
        """
        Find source evidence supporting MCP claims.

        IMPORTANT:

        Raw Tavily evidence does not necessarily contain the
        canonical ``source_type`` field.

        The extractor assigns source_type when Gemini selects
        evidence and Python resolves the provenance.

        Therefore the verifier must use:

            result.evidence[].source_type

        rather than:

            web_sources[].source_type

        Otherwise legitimate official MCP evidence will be
        incorrectly rejected.
        """

        # --------------------------------------------------------------
        # Build a lookup of raw web sources by normalized URL.
        # --------------------------------------------------------------

        source_by_url = {
            ResearchVerifier._normalize_url(
                str(source.get("url") or "")
            ): source
            for source in web_sources
            if source.get("url")
        }

        matches: list[dict] = []

        # --------------------------------------------------------------
        # Inspect only evidence that Gemini actually selected.
        # --------------------------------------------------------------

        for selected_evidence in result.evidence:
            selected_url = (
                ResearchVerifier._normalize_url(
                    str(selected_evidence.url)
                )
            )

            source = source_by_url.get(
                selected_url
            )

            if source is None:
                continue

            # ----------------------------------------------------------
            # Determine whether this source actually discusses MCP.
            # ----------------------------------------------------------

            title = str(
                source.get("title") or ""
            ).lower()

            content = str(
                source.get("content") or ""
            ).lower()

            combined = f"{title} {content}"

            if "mcp" not in combined:
                continue

            # ----------------------------------------------------------
            # CRITICAL FIX:
            #
            # Use the canonical source type assigned by the
            # extraction/provenance layer.
            # ----------------------------------------------------------

            source_type = (
                selected_evidence.source_type
            )

            if require_official:
                if source_type in {
                    "official_docs",
                    "official_blog",
                    "official_github",
                }:
                    matches.append(source)

            elif third_party_only:
                if source_type == "third_party":
                    matches.append(source)

            else:
                matches.append(source)

        return matches

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_score(
        result: AppResearch,
        errors: list[str],
        warnings: list[str],
    ) -> float:
        """
        Calculate a deterministic verification score.

        The score starts at 1.0 and is reduced for detected issues.
        """

        score = 1.0

        score -= min(
            len(errors) * 0.20,
            0.80,
        )

        score -= min(
            len(warnings) * 0.05,
            0.20,
        )

        if not result.evidence:
            score = min(
                score,
                0.20,
            )

        return round(
            max(
                0.0,
                min(
                    1.0,
                    score,
                ),
            ),
            2,
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _valid_http_url(
        url: str,
    ) -> bool:
        """Return True for an absolute HTTP(S) URL."""

        try:
            parsed = urlparse(url)

            return (
                parsed.scheme in {
                    "http",
                    "https",
                }
                and bool(parsed.netloc)
            )

        except Exception:
            return False

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        """
        Normalize whitespace for substring comparison.

        This intentionally does not perform semantic matching.
        """

        return " ".join(
            value.split()
        ).strip()