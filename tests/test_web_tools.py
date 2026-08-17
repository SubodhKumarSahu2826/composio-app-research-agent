from src.web_tools import WebResearchTool


def test_web_search():
    """Verify that Tavily returns usable search results."""

    tool = WebResearchTool()

    results = tool.search(
        "Salesforce API authentication official developer documentation",
        official_domain="salesforce.com",
        max_results=5,
    )

    assert results
    assert len(results) <= 5

    for result in results:
        assert result.get("url")
        assert result.get("title")
        assert "authority_score" in result


def test_authority_scoring():
    """Verify that official documentation receives higher scores."""

    tool = WebResearchTool()

    official_score = tool._authority_score(
        "https://developer.salesforce.com/docs/",
        "salesforce.com",
    )

    third_party_score = tool._authority_score(
        "https://example-blog.com/salesforce-api",
        "salesforce.com",
    )

    youtube_score = tool._authority_score(
        "https://www.youtube.com/watch?v=example",
        "salesforce.com",
    )

    assert official_score > third_party_score
    assert third_party_score > youtube_score


def test_official_domain_matching():
    """Verify that the official domain and its subdomains are recognized."""

    tool = WebResearchTool()

    root_domain_score = tool._authority_score(
        "https://salesforce.com",
        "salesforce.com",
    )

    developer_domain_score = tool._authority_score(
        "https://developer.salesforce.com/docs",
        "salesforce.com",
    )

    unrelated_domain_score = tool._authority_score(
        "https://example.com",
        "salesforce.com",
    )

    assert root_domain_score > unrelated_domain_score
    assert developer_domain_score > unrelated_domain_score