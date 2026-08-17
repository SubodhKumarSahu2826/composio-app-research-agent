from src.research_agent import ResearchAgent


def test_extract_domain_from_valid_https_url():
    assert (
        ResearchAgent._extract_domain(
            "https://www.salesforce.com/in/"
        )
        == "www.salesforce.com"
    )


def test_extract_domain_from_valid_http_url():
    assert (
        ResearchAgent._extract_domain(
            "http://example.com/docs"
        )
        == "example.com"
    )


def test_extract_domain_from_domain_without_scheme():
    assert (
        ResearchAgent._extract_domain(
            "example.com/docs"
        )
        == "example.com"
    )


def test_extract_domain_rejects_unresolved_website_text():
    assert (
        ResearchAgent._extract_domain(
            "Paygent (NMI-powered)"
        )
        is None
    )


def test_extract_domain_rejects_empty_value():
    assert (
        ResearchAgent._extract_domain("")
        is None
    )


def test_extract_domain_rejects_whitespace():
    assert (
        ResearchAgent._extract_domain(
            "   "
        )
        is None
    )


def test_extract_domain_rejects_plain_text():
    assert (
        ResearchAgent._extract_domain(
            "Some Application Name"
        )
        is None
    )