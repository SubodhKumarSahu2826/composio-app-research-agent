from urllib.parse import urlparse

from tavily import TavilyClient

from src.config import TAVILY_API_KEY


class WebResearchTool:
    """Search the web and prioritize authoritative sources."""

    def __init__(self) -> None:
        self.client = TavilyClient(api_key=TAVILY_API_KEY)

    def search(
        self,
        query: str,
        official_domain: str | None = None,
        max_results: int = 5,
    ) -> list[dict]:
        """
        Search the web and rank results by source authority.

        Args:
            query: Search query.
            official_domain: Official domain of the application,
                e.g. "salesforce.com".
            max_results: Maximum number of results to return.

        Returns:
            List of search results sorted by authority score.
        """

        response = self.client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=False,
        )

        results = response.get("results", [])

        for result in results:
            url = result.get("url", "")

            result["authority_score"] = self._authority_score(
                url=url,
                official_domain=official_domain,
            )

        # Highest-authority sources first.
        results.sort(
            key=lambda result: result.get("authority_score", 0),
            reverse=True,
        )

        return results

    @staticmethod
    def _authority_score(
        url: str,
        official_domain: str | None = None,
    ) -> int:
        """
        Calculate a simple deterministic authority score.

        Higher score = more likely to be authoritative.

        Scoring:
        - Official application domain: +5
        - developer.* subdomain: +3
        - docs.* subdomain: +3
        - api.* subdomain: +3
        - GitHub: +2
        - YouTube: -2
        """

        if not url:
            return 0

        parsed_url = urlparse(url)
        hostname = parsed_url.netloc.lower()

        # Remove a possible "www." prefix.
        hostname = hostname.removeprefix("www.")

        score = 0

        # ---------------------------------------------------------
        # 1. Official application domain
        # ---------------------------------------------------------
        if official_domain:
            official = official_domain.lower()
            official = official.removeprefix("https://")
            official = official.removeprefix("http://")
            official = official.removeprefix("www.")
            official = official.rstrip("/")

            if hostname == official or hostname.endswith(
                "." + official
            ):
                score += 5

        # ---------------------------------------------------------
        # 2. Developer documentation
        # ---------------------------------------------------------
        if hostname.startswith("developer."):
            score += 3

        # ---------------------------------------------------------
        # 3. Documentation subdomain
        # ---------------------------------------------------------
        if hostname.startswith("docs."):
            score += 3

        # ---------------------------------------------------------
        # 4. API subdomain
        # ---------------------------------------------------------
        if hostname.startswith("api."):
            score += 3

        # ---------------------------------------------------------
        # 5. GitHub
        # ---------------------------------------------------------
        if hostname == "github.com" or hostname.endswith(".github.com"):
            score += 2

        # ---------------------------------------------------------
        # 6. YouTube is useful for discovery but weak evidence
        # ---------------------------------------------------------
        if hostname == "youtube.com" or hostname.endswith(".youtube.com"):
            score -= 2

        return score