import json
from pathlib import Path

from src.composio_tools import ComposioResearchTool
from src.extraction import ResearchExtractor
from src.web_tools import WebResearchTool


class ResearchAgent:
    """
    End-to-end research pipeline for one application.

    Pipeline:

        App
         ↓
        Tavily web research
         ↓
        Evidence ranking + filtering
         ↓
        Stable evidence IDs
         ↓
        Composio toolkit discovery
         ↓
        Structured evidence bundle
         ↓
        Gemini evidence selection
         ↓
        Pydantic validation
    """

    def __init__(self) -> None:
        self.web = WebResearchTool()
        self.composio = ComposioResearchTool()
        self.extractor = ResearchExtractor()

    def research_app(self, app: dict):
        """
        Research one application and return a validated AppResearch object.
        """

        app_name = app["name"]
        official_domain = self._extract_domain(app["website"])

        print(f"\nResearching: {app_name}")

        # ---------------------------------------------------------
        # 1. Web evidence retrieval
        # ---------------------------------------------------------

        web_evidence = []
        seen_urls = set()

        queries = [
            f"{app_name} API authentication developer documentation",
            f"{app_name} API access requirements developer",
            f"{app_name} REST API documentation",
            f"{app_name} MCP Model Context Protocol",
        ]

        for query in queries:
            print(f"  Web search: {query}")

            results = self.web.search(
                query=query,
                official_domain=official_domain,
                max_results=3,
            )

            for result in results:
                url = result.get("url")

                # Skip malformed results.
                if not url:
                    continue

                # Skip duplicate URLs returned by different queries.
                if url in seen_urls:
                    continue

                seen_urls.add(url)

                web_evidence.append(
                    {
                        "title": result.get("title"),
                        "url": url,
                        "content": result.get("content"),
                        "authority_score": result.get(
                            "authority_score",
                            0,
                        ),
                        "source": "Tavily",
                    }
                )

        # ---------------------------------------------------------
        # 2. Rank and filter web evidence
        # ---------------------------------------------------------

        web_evidence.sort(
            key=lambda item: item.get(
                "authority_score",
                0,
            ),
            reverse=True,
        )

        # Keep the strongest evidence only.
        web_evidence = web_evidence[:8]

        # ---------------------------------------------------------
        # 3. Assign stable evidence IDs
        # ---------------------------------------------------------
        #
        # Gemini will select these IDs instead of generating URLs
        # and source names itself.
        #
        # Example:
        #
        # WEB-001 → Salesforce Developers
        # WEB-002 → Salesforce REST API Guide
        # WEB-003 → Salesforce OAuth documentation
        #
        # Python will later resolve these IDs back to the exact
        # original URL/title.
        # ---------------------------------------------------------

        for index, item in enumerate(
            web_evidence,
            start=1,
        ):
            item["evidence_id"] = f"WEB-{index:03d}"

        # ---------------------------------------------------------
        # 4. Composio discovery
        # ---------------------------------------------------------

        print("  Composio discovery...")

        composio_result = self.composio.find_toolkit(
            app_name
        )

        if composio_result["toolkit_found"]:
            print(
                f"  Composio toolkit found: "
                f"{composio_result['toolkit_slug']}"
            )

            composio_tools = self.composio.get_toolkit_tools(
                toolkit_slug=composio_result["toolkit_slug"],
                limit=10,
            )

            composio_result["sample_tools"] = composio_tools

        else:
            print("  No Composio toolkit found.")

        # ---------------------------------------------------------
        # 5. Build structured evidence bundle
        # ---------------------------------------------------------
        #
        # Web evidence:
        #   Real sources with stable IDs and URLs.
        #
        # Composio:
        #   Integration/toolkit metadata.
        #
        # They remain separate because a Composio toolkit is not
        # automatically proof of an official application MCP.
        # ---------------------------------------------------------

        evidence_bundle = [
            {
                "type": "web_evidence",
                "items": web_evidence,
            },
            {
                "type": "composio_discovery",
                "items": [composio_result],
            },
        ]

        print(
            f"  Web evidence items collected: "
            f"{len(web_evidence)}"
        )

        # ---------------------------------------------------------
        # 6. Gemini extraction + Pydantic validation
        # ---------------------------------------------------------

        print("  Gemini analysis...")

        result = self.extractor.extract(
            app=app,
            evidence=evidence_bundle,
        )

        print(
            f"  Buildability: "
            f"{result.buildability.verdict.value}"
        )

        print(
            f"  Confidence: "
            f"{result.overall_confidence:.2f}"
        )

        return result

    @staticmethod
    def _extract_domain(website: str) -> str:
        """
        Extract a usable domain from an application website.

        Example:
            https://www.salesforce.com/in/
            -> www.salesforce.com
        """

        website = website.strip()

        website = website.replace(
            "https://",
            "",
            1,
        )

        website = website.replace(
            "http://",
            "",
            1,
        )

        website = website.split("/")[0]

        return website


def load_apps() -> list[dict]:
    """Load the 100-app research dataset."""

    path = Path("data/apps.json")

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def main() -> None:
    """
    Run the researcher against one application.

    We intentionally run only the first application while
    validating the research pipeline.
    """

    apps = load_apps()

    if not apps:
        raise ValueError(
            "No applications found in data/apps.json"
        )

    app = apps[0]

    agent = ResearchAgent()

    result = agent.research_app(app)

    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()