from src.extraction import ResearchExtractor


class FakeGeminiClient:
    """Deterministic Gemini replacement for unit tests."""

    def generate_json(self, prompt: str) -> dict:
        return {
            "app_id": 1,
            "app_name": "Salesforce",
            "category": "CRM and Sales",
            "description": (
                "Salesforce provides APIs for application integration."
            ),
            "authentication": {
                "methods": ["OAuth2"],
                "confidence": 0.90,
            },
            "access": {
                "type": "Unknown",
                "requirements": [],
                "confidence": 0.50,
            },
            "api": {
                "type": "REST",
                "breadth": "Broad",
                "documentation_url": (
                    "https://developer.salesforce.com/docs/"
                ),
                "confidence": 0.90,
            },
            "mcp": {
                "status": "Unknown",
                "official": None,
                "url": None,
                "confidence": 0.30,
            },
            "buildability": {
                "verdict": "Possible",
                "blocker": None,
                "reasoning": (
                    "The supplied evidence documents "
                    "OAuth2 authentication and a REST API."
                ),
            },
            "evidence": [
                {
                    "evidence_id": "WEB-001",
                    "claim": (
                        "Salesforce APIs use OAuth 2.0 "
                        "authentication."
                    ),
                    "snippet": (
                        "Salesforce APIs use OAuth 2.0 "
                        "authentication through connected "
                        "applications."
                    ),
                }
            ],
            "overall_confidence": 0.85,
        }


def test_extraction_from_evidence():
    app = {
        "id": 1,
        "name": "Salesforce",
        "category": "CRM and Sales",
        "website": "https://salesforce.com",
    }

    evidence = [
        {
            "type": "web_evidence",
            "items": [
                {
                    "evidence_id": "WEB-001",
                    "title": "Salesforce API Authentication",
                    "url": "https://developer.salesforce.com/docs/",
                    "content": (
                        "Salesforce APIs use OAuth 2.0 authentication "
                        "through connected applications."
                    ),
                    "authority_score": 8,
                }
            ],
        },
        {
            "type": "composio_discovery",
            "items": [
                {
                    "toolkit_found": True,
                    "toolkit_name": "Salesforce",
                    "toolkit_slug": "salesforce",
                }
            ],
        },
    ]

    extractor = ResearchExtractor(
        llm=FakeGeminiClient()
    )

    result = extractor.extract(
        app=app,
        evidence=evidence,
    )

    assert result.app_name == "Salesforce"
    assert result.category == "CRM and Sales"

    assert result.authentication.methods
    assert result.evidence

    evidence_item = result.evidence[0]

    assert str(evidence_item.url) == (
        "https://developer.salesforce.com/docs/"
    )

    assert evidence_item.source_name == (
        "Salesforce API Authentication"
    )

    assert evidence_item.source_type == "official_docs"

    assert evidence_item.claim
    assert evidence_item.snippet