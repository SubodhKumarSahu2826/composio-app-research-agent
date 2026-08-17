from dataclasses import dataclass

from src.models import AppResearch


@dataclass
class ResearchAnalysis:
    """
    Deterministic quality analysis of an AppResearch result.

    This layer does not call an LLM or any external API.
    """

    app_id: int
    app_name: str

    evidence_count: int
    official_evidence_count: int
    third_party_evidence_count: int

    evidence_coverage: str
    confidence_level: str
    quality_score: float

    warnings: list[str]
    strengths: list[str]


class ResearchAnalyzer:
    """Analyze the quality and consistency of research results."""

    def analyze(
        self,
        research: AppResearch,
    ) -> ResearchAnalysis:
        evidence = research.evidence

        evidence_count = len(evidence)

        official_evidence_count = sum(
            1
            for item in evidence
            if item.source_type
            in {
                "official_docs",
                "official_blog",
                "official_github",
            }
        )

        third_party_evidence_count = sum(
            1
            for item in evidence
            if item.source_type == "third_party"
        )

        warnings: list[str] = []
        strengths: list[str] = []

        # ---------------------------------------------------------
        # Evidence coverage
        # ---------------------------------------------------------

        if evidence_count == 0:
            evidence_coverage = "None"
            warnings.append(
                "No evidence items were provided."
            )

        elif evidence_count < 3:
            evidence_coverage = "Low"
            warnings.append(
                "Research has fewer than 3 evidence sources."
            )

        elif evidence_count < 5:
            evidence_coverage = "Moderate"
            warnings.append(
                "Research has moderate evidence coverage."
            )

        else:
            evidence_coverage = "High"
            strengths.append(
                "Research contains multiple evidence sources."
            )

        # ---------------------------------------------------------
        # Official source coverage
        # ---------------------------------------------------------

        if official_evidence_count == 0:
            warnings.append(
                "No official sources support the research."
            )

        elif official_evidence_count >= 3:
            strengths.append(
                "Multiple official sources support the research."
            )

        else:
            warnings.append(
                "Limited official-source coverage."
            )

        # ---------------------------------------------------------
        # Confidence
        # ---------------------------------------------------------

        confidence = research.overall_confidence

        if confidence >= 0.90:
            confidence_level = "High"

        elif confidence >= 0.75:
            confidence_level = "Good"

        elif confidence >= 0.60:
            confidence_level = "Moderate"

        elif confidence >= 0.40:
            confidence_level = "Low"

        else:
            confidence_level = "Very Low"

        # ---------------------------------------------------------
        # Authentication
        # ---------------------------------------------------------

        if research.authentication.methods:
            strengths.append(
                "Authentication method is identified."
            )
        else:
            warnings.append(
                "Authentication method is unknown."
            )

        # ---------------------------------------------------------
        # API
        # ---------------------------------------------------------

        if research.api.type.value == "Unknown":
            warnings.append(
                "API type could not be determined."
            )

        elif research.api.type.value == "No Public API Found":
            warnings.append(
                "No public API was found."
            )

        else:
            strengths.append(
                "A public API surface was identified."
            )

        # ---------------------------------------------------------
        # MCP
        # ---------------------------------------------------------

        if research.mcp.status.value == "Official MCP":
            if research.mcp.official is True:
                strengths.append(
                    "Official MCP support is explicitly identified."
                )

        elif research.mcp.status.value == "Unknown":
            warnings.append(
                "MCP availability could not be determined."
            )

        # ---------------------------------------------------------
        # Buildability consistency
        # ---------------------------------------------------------

        if research.buildability.verdict.value == "Easy":
            if (
                research.api.type.value
                in {
                    "Unknown",
                    "No Public API Found",
                }
            ):
                warnings.append(
                    "Buildability is marked Easy despite "
                    "limited API evidence."
                )

        if research.buildability.verdict.value == "Blocked":
            strengths.append(
                "Research identifies an integration blocker."
            )

        # ---------------------------------------------------------
        # Quality score
        # ---------------------------------------------------------

        score = self._calculate_quality_score(
            research=research,
            evidence_count=evidence_count,
            official_evidence_count=official_evidence_count,
        )

        return ResearchAnalysis(
            app_id=research.app_id,
            app_name=research.app_name,
            evidence_count=evidence_count,
            official_evidence_count=official_evidence_count,
            third_party_evidence_count=third_party_evidence_count,
            evidence_coverage=evidence_coverage,
            confidence_level=confidence_level,
            quality_score=score,
            warnings=warnings,
            strengths=strengths,
        )

    @staticmethod
    def _calculate_quality_score(
        research: AppResearch,
        evidence_count: int,
        official_evidence_count: int,
    ) -> float:
        """
        Calculate a deterministic research-quality score.

        The score is intentionally independent of another LLM call.
        """

        score = 0.0

        # Overall confidence contributes up to 40 points.
        score += research.overall_confidence * 40

        # Evidence quantity contributes up to 25 points.
        evidence_score = min(
            evidence_count / 5,
            1.0,
        )
        score += evidence_score * 25

        # Official evidence contributes up to 25 points.
        official_score = min(
            official_evidence_count / 3,
            1.0,
        )
        score += official_score * 25

        # Structured API/authentication information contributes
        # another 10 points.
        if research.authentication.methods:
            score += 5

        if research.api.type.value not in {
            "Unknown",
            "No Public API Found",
        }:
            score += 5

        return round(
            min(score, 100.0),
            2,
        )