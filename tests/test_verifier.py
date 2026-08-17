from __future__ import annotations

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
from src.verifier import ResearchVerifier


def create_result(
    *,
    evidence=None,
    mcp_status=McpStatus.UNKNOWN,
    mcp_official=None,
    mcp_url=None,
    api_type=ApiType.REST,
    api_documentation_url=None,
    buildability=Buildability.POSSIBLE,
    access_type=AccessType.UNKNOWN,
):
    """Create a minimal valid AppResearch object for tests."""

    return AppResearch(
        app_id=1,
        app_name="Salesforce",
        category="CRM and Sales",
        description="Salesforce research result.",
        authentication=Authentication(
            methods=[AuthMethod.OAUTH2],
            confidence=0.9,
        ),
        access=Access(
            type=access_type,
            requirements=[],
            confidence=0.8,
        ),
        api=ApiSurface(
            type=api_type,
            breadth=ApiBreadth.BROAD,
            documentation_url=api_documentation_url,
            confidence=0.9,
        ),
        mcp=McpInfo(
            status=mcp_status,
            official=mcp_official,
            url=mcp_url,
            confidence=0.9,
        ),
        buildability=BuildabilityResult(
            verdict=buildability,
            blocker=None,
            reasoning="Research indicates technical feasibility.",
        ),
        evidence=evidence or [],
        overall_confidence=0.9,
    )


def create_web_evidence(
    *,
    title="Salesforce API Authentication",
    url="https://developer.salesforce.com/docs/",
    content=(
        "Salesforce APIs use OAuth 2.0 authentication "
        "through connected applications."
    ),
    authority_score=8,
    source_type="official_docs",
):
    """Create a single web evidence source."""

    return {
        "evidence_id": "WEB-001",
        "title": title,
        "url": url,
        "content": content,
        "authority_score": authority_score,
        "source_type": source_type,
    }


def create_bundle(
    web_items,
    composio_items=None,
):
    """Create the structured evidence bundle."""

    return [
        {
            "type": "web_evidence",
            "items": web_items,
        },
        {
            "type": "composio_discovery",
            "items": composio_items or [],
        },
    ]


def create_evidence(
    *,
    claim="Salesforce APIs use OAuth 2.0.",
    url="https://developer.salesforce.com/docs/",
    source_name="Salesforce API Authentication",
    source_type="official_docs",
    snippet=(
        "Salesforce APIs use OAuth 2.0 authentication "
        "through connected applications."
    ),
    title=None,
    content=None,
):
    """
    Create an extracted Evidence model.

    `title` and `content` are accepted because some tests
    intentionally construct evidence using the same shape as
    the original web-research evidence.

    Mapping:

        title   -> source_name
        content -> snippet

    Explicit `source_name` and `snippet` remain the defaults
    unless the corresponding compatibility argument is supplied.
    """

    if title is not None:
        source_name = title

    if content is not None:
        snippet = content

    return Evidence(
        claim=claim,
        url=url,
        source_name=source_name,
        source_type=source_type,
        snippet=snippet,
    )


def test_valid_research_passes_verification():
    evidence = [
        create_evidence()
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence,
        api_documentation_url=(
            "https://developer.salesforce.com/docs/"
        ),
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is True
    assert verification.errors == []
    assert verification.checked_evidence == 1
    assert verification.score > 0.8


def test_unknown_evidence_url_fails_verification():
    evidence = [
        create_evidence(
            url="https://example.com/fake-source"
        )
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is False

    assert any(
        "was not present" in error
        for error in verification.errors
    )


def test_mismatched_source_name_fails_verification():
    evidence = [
        create_evidence(
            source_name="Fake Source Name"
        )
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is False

    assert any(
        "source_name does not match" in error
        for error in verification.errors
    )


def test_invalid_source_type_fails_verification():
    evidence = [
        create_evidence(
            source_type="fake_source_type"
        )
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is False

    assert any(
        "invalid source_type" in error
        for error in verification.errors
    )


def test_official_mcp_requires_official_evidence():
    evidence = [
        create_evidence(
            title="Third Party MCP Article",
            url="https://example.com/mcp",
            content=(
                "This article describes an MCP server "
                "for Salesforce."
            ),
            source_type="third_party",
        )
    ]

    sources = [
        create_web_evidence(
            title="Third Party MCP Article",
            url="https://example.com/mcp",
            content=(
                "This article describes an MCP server "
                "for Salesforce."
            ),
            source_type="third_party",
        )
    ]

    result = create_result(
        evidence=evidence,
        mcp_status=McpStatus.OFFICIAL,
        mcp_official=True,
        mcp_url="https://example.com/mcp",
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is False

    assert any(
        "official evidence" in error
        for error in verification.errors
    )


def test_official_mcp_with_official_evidence_passes():
    evidence = [
        create_evidence(
            title="Salesforce Hosted MCP Servers",
            url=(
                "https://developer.salesforce.com/"
                "docs/platform/hosted-mcp-servers/"
            ),
            content=(
                "Salesforce Hosted MCP Servers use "
                "the Model Context Protocol."
            ),
            source_type="official_docs",
        )
    ]

    sources = [
        create_web_evidence(
            title="Salesforce Hosted MCP Servers",
            url=(
                "https://developer.salesforce.com/"
                "docs/platform/hosted-mcp-servers/"
            ),
            content=(
                "Salesforce Hosted MCP Servers use "
                "the Model Context Protocol."
            ),
            source_type="official_docs",
        )
    ]

    result = create_result(
        evidence=evidence,
        mcp_status=McpStatus.OFFICIAL,
        mcp_official=True,
        mcp_url=(
            "https://developer.salesforce.com/"
            "docs/platform/hosted-mcp-servers/"
        ),
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is True


def test_api_documentation_must_exist_in_evidence():
    evidence = [
        create_evidence()
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence,
        api_documentation_url=(
            "https://developer.salesforce.com/not-in-evidence/"
        ),
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is False

    assert any(
        "documentation_url" in error
        for error in verification.errors
    )


def test_empty_evidence_fails_verification():
    result = create_result(
        evidence=[]
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=[],
    )

    assert verification.passed is False
    assert verification.checked_evidence == 0

    assert any(
        "no evidence" in error.lower()
        for error in verification.errors
    )


def test_composio_metadata_is_not_treated_as_web_evidence():
    evidence = [
        create_evidence()
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    bundle = create_bundle(
        sources,
        composio_items=[
            {
                "toolkit_found": True,
                "toolkit_name": "Salesforce",
                "toolkit_slug": "salesforce",
            }
        ],
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=bundle,
    )

    assert verification.passed is True
    assert verification.checked_evidence == 1


def test_duplicate_evidence_urls_generate_warning():
    evidence = [
        create_evidence(),
        create_evidence(
            claim="Another claim from the same source."
        ),
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is True

    assert any(
        "duplicate evidence URLs" in warning
        for warning in verification.warnings
    )


def test_missing_snippet_generates_warning():
    evidence = [
        create_evidence(
            snippet=None
        )
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is True

    assert any(
        "snippet is empty" in warning
        for warning in verification.warnings
    )


def test_non_matching_snippet_generates_warning():
    evidence = [
        create_evidence(
            snippet="This statement does not appear in the source."
        )
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is True

    assert any(
        "not an exact substring" in warning
        for warning in verification.warnings
    )


def test_confidence_one_generates_warning():
    evidence = [
        create_evidence()
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    result.overall_confidence = 1.0

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is True

    assert any(
        "confidence is 1.0" in warning
        for warning in verification.warnings
    )


def test_easy_buildability_with_admin_gate_generates_warning():
    evidence = [
        create_evidence()
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence,
        buildability=Buildability.EASY,
        access_type=AccessType.ADMIN_APPROVAL,
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    assert verification.passed is True

    assert any(
        "significant access gate" in warning
        for warning in verification.warnings
    )


def test_verification_result_can_be_serialized():
    evidence = [
        create_evidence()
    ]

    sources = [
        create_web_evidence()
    ]

    result = create_result(
        evidence=evidence
    )

    verification = ResearchVerifier().verify(
        result=result,
        evidence=create_bundle(sources),
    )

    dumped = verification.model_dump()

    assert dumped["passed"] is True
    assert dumped["checked_evidence"] == 1
    assert isinstance(dumped["errors"], list)
    assert isinstance(dumped["warnings"], list)
    assert isinstance(dumped["score"], float)