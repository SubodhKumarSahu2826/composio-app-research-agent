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
    McpInfo,
    McpStatus,
)


def test_app_research_schema():
    result = AppResearch(
        app_id=1,
        app_name="Salesforce",
        category="CRM and Sales",
        description="Customer relationship management platform.",
        authentication=Authentication(
            methods=[AuthMethod.OAUTH2],
            confidence=0.95,
        ),
        access=Access(
            type=AccessType.SELF_SERVE_FREE,
            confidence=0.90,
        ),
        api=ApiSurface(
            type=ApiType.REST,
            breadth=ApiBreadth.BROAD,
            confidence=0.95,
        ),
        mcp=McpInfo(
            status=McpStatus.UNKNOWN,
            confidence=0.50,
        ),
        buildability=BuildabilityResult(
            verdict=Buildability.EASY,
            reasoning="Public API with documented authentication.",
        ),
        overall_confidence=0.90,
    )

    assert result.app_name == "Salesforce"
    assert result.authentication.methods == [AuthMethod.OAUTH2]
    assert result.buildability.verdict == Buildability.EASY