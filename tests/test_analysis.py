from src.analysis import ResearchAnalyzer
from src.models import (
    Access,
    AccessType,
    ApiBreadth,
    ApiSurface,
    ApiType,
    AppResearch,
    Authentication,
    AuthMethod,
    Buildability,
    BuildabilityResult,
    Evidence,
    McpInfo,
    McpStatus,
)


def create_research(
    evidence=None,
    confidence=0.90,
):
    """Create deterministic research data for testing."""

    if evidence is None:
        evidence = [
            Evidence(
                claim="Salesforce uses OAuth2.",
                url="https://developer.salesforce.com/docs/",
                source_name="Salesforce Developers",
                source_type="official_docs",
                snippet="Salesforce uses OAuth2.",
            ),
            Evidence(
                claim="Salesforce provides a REST API.",
                url="https://developer.salesforce.com/",
                source_name="Salesforce API Documentation",
                source_type="official_docs",
                snippet="Salesforce REST API.",
            ),
            Evidence(
                claim="Salesforce supports MCP.",
                url="https://developer.salesforce.com/mcp",
                source_name="Salesforce MCP",
                source_type="official_docs",
                snippet="Official MCP support.",
            ),
            Evidence(
                claim="Third-party API overview.",
                url="https://example.com/article",
                source_name="Example Article",
                source_type="third_party",
                snippet="API overview.",
            ),
            Evidence(
                claim="Another official source.",
                url="https://developer.salesforce.com/guide",
                source_name="Salesforce Guide",
                source_type="official_docs",
                snippet="Official guide.",
            ),
        ]

    return AppResearch(
        app_id=1,
        app_name="Salesforce",
        category="CRM and Sales",
        description="CRM platform.",
        authentication=Authentication(
            methods=[AuthMethod.OAUTH2],
            confidence=0.95,
        ),
        access=Access(
            type=AccessType.SELF_SERVE_FREE,
            requirements=[],
            confidence=0.90,
        ),
        api=ApiSurface(
            type=ApiType.REST,
            breadth=ApiBreadth.BROAD,
            documentation_url=(
                "https://developer.salesforce.com/"
            ),
            confidence=0.95,
        ),
        mcp=McpInfo(
            status=McpStatus.OFFICIAL,
            official=True,
            url=(
                "https://developer.salesforce.com/mcp"
            ),
            confidence=0.95,
        ),
        buildability=BuildabilityResult(
            verdict=Buildability.EASY,
            blocker=None,
            reasoning="Public API and documentation are available.",
        ),
        evidence=evidence,
        overall_confidence=confidence,
    )


def test_analysis_counts_evidence():
    analyzer = ResearchAnalyzer()

    research = create_research()

    result = analyzer.analyze(
        research
    )

    assert result.evidence_count == 5
    assert result.official_evidence_count == 4
    assert result.third_party_evidence_count == 1


def test_analysis_detects_high_quality_research():
    analyzer = ResearchAnalyzer()

    research = create_research(
        confidence=0.94
    )

    result = analyzer.analyze(
        research
    )

    assert result.evidence_coverage == "High"
    assert result.confidence_level == "High"
    assert result.quality_score >= 80


def test_analysis_flags_missing_evidence():
    analyzer = ResearchAnalyzer()

    research = create_research(
        evidence=[],
        confidence=0.30,
    )

    result = analyzer.analyze(
        research
    )

    assert result.evidence_count == 0
    assert result.evidence_coverage == "None"
    assert result.confidence_level == "Very Low"

    assert any(
        "No evidence" in warning
        for warning in result.warnings
    )


def test_analysis_flags_missing_official_sources():
    analyzer = ResearchAnalyzer()

    evidence = [
        Evidence(
            claim="Third-party API information.",
            url="https://example.com/api",
            source_name="Example",
            source_type="third_party",
            snippet="Third-party source.",
        )
    ]

    research = create_research(
        evidence=evidence,
        confidence=0.60,
    )

    result = analyzer.analyze(
        research
    )

    assert result.official_evidence_count == 0

    assert any(
        "No official sources" in warning
        for warning in result.warnings
    )


def test_analysis_identifies_strengths():
    analyzer = ResearchAnalyzer()

    research = create_research()

    result = analyzer.analyze(
        research
    )

    assert result.strengths

    assert any(
        "official" in strength.lower()
        for strength in result.strengths
    )

    assert any(
        "authentication" in strength.lower()
        for strength in result.strengths
    )