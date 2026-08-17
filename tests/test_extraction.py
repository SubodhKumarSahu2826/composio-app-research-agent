from src.extraction import ResearchExtractor


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

    extractor = ResearchExtractor()

    result = extractor.extract(
        app=app,
        evidence=evidence,
    )

    # Basic application validation.
    assert result.app_name == "Salesforce"
    assert result.category == "CRM and Sales"

    # Authentication should have been extracted.
    assert result.authentication.methods

    # Evidence should have been resolved from WEB-001.
    assert result.evidence

    evidence_item = result.evidence[0]

    # Pydantic stores HttpUrl, so compare its string representation.
    assert str(evidence_item.url) == (
        "https://developer.salesforce.com/docs/"
    )

    # These values must come from the original retrieved source,
    # not from Gemini-generated metadata.
    assert evidence_item.source_name == (
        "Salesforce API Authentication"
    )

    assert evidence_item.source_type == "official_docs"

    # The claim and snippet should also be populated.
    assert evidence_item.claim
    assert evidence_item.snippet