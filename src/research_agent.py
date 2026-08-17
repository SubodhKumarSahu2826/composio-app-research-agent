import json
from pathlib import Path

from src.analysis import ResearchAnalyzer
from src.composio_tools import ComposioResearchTool
from src.extraction import ResearchExtractor
from src.verifier import ResearchVerifier
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
        Gemini extraction
         ↓
        Pydantic validation
         ↓
        Deterministic verification
         ↓
        Deterministic analysis
         ↓
        Final research result
    """

    def __init__(self) -> None:
        self.web = WebResearchTool()
        self.composio = ComposioResearchTool()
        self.extractor = ResearchExtractor()

        # Phase 2 deterministic quality layers.
        self.verifier = ResearchVerifier()
        self.analyzer = ResearchAnalyzer()

    def research_app(self, app: dict):
        """
        Research one application and return a validated AppResearch object.

        The research process is split into:

        1. Evidence retrieval
        2. Evidence ranking and normalization
        3. Composio discovery
        4. Gemini extraction
        5. Deterministic verification
        6. Deterministic analysis
        """

        app_name = app["name"]
        official_domain = self._extract_domain(
            app["website"]
        )

        print(f"\nResearching: {app_name}")

        # =========================================================
        # 1. WEB EVIDENCE RETRIEVAL
        # =========================================================

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

                # Ignore malformed search results.
                if not url:
                    continue

                # Avoid duplicate sources.
                if url in seen_urls:
                    continue

                seen_urls.add(url)

                web_evidence.append(
                    {
                        "title": result.get(
                            "title",
                            "",
                        ),
                        "url": url,
                        "content": result.get(
                            "content",
                            "",
                        ),
                        "authority_score": result.get(
                            "authority_score",
                            0,
                        ),
                        "source": "Tavily",
                    }
                )

        # =========================================================
        # 2. RANK AND FILTER WEB EVIDENCE
        # =========================================================

        web_evidence.sort(
            key=lambda item: item.get(
                "authority_score",
                0,
            ),
            reverse=True,
        )

        # Keep only the strongest sources.
        web_evidence = web_evidence[:8]

        # =========================================================
        # 3. ASSIGN STABLE EVIDENCE IDs
        # =========================================================

        for index, item in enumerate(
            web_evidence,
            start=1,
        ):
            item["evidence_id"] = (
                f"WEB-{index:03d}"
            )

        # =========================================================
        # 4. COMPOSIO DISCOVERY
        # =========================================================

        print("  Composio discovery...")

        composio_result = self.composio.find_toolkit(
            app_name
        )

        if composio_result["toolkit_found"]:
            print(
                "  Composio toolkit found: "
                f"{composio_result['toolkit_slug']}"
            )

            composio_tools = (
                self.composio.get_toolkit_tools(
                    toolkit_slug=(
                        composio_result[
                            "toolkit_slug"
                        ]
                    ),
                    limit=10,
                )
            )

            composio_result[
                "sample_tools"
            ] = composio_tools

        else:
            print(
                "  No Composio toolkit found."
            )

        # =========================================================
        # 5. BUILD STRUCTURED EVIDENCE BUNDLE
        # =========================================================
        #
        # Web evidence contains real source URLs.
        #
        # Composio discovery contains integration metadata.
        #
        # These remain separate because a Composio toolkit does not
        # prove that an application has an official MCP server.
        # =========================================================

        evidence_bundle = [
            {
                "type": "web_evidence",
                "items": web_evidence,
            },
            {
                "type": "composio_discovery",
                "items": [
                    composio_result
                ],
            },
        ]

        print(
            "  Web evidence items collected: "
            f"{len(web_evidence)}"
        )

        # =========================================================
        # 6. GEMINI EXTRACTION
        # =========================================================

        print("  Gemini analysis...")

        result = self.extractor.extract(
            app=app,
            evidence=evidence_bundle,
        )

        print(
            "  Buildability: "
            f"{result.buildability.verdict.value}"
        )

        print(
            "  Confidence: "
            f"{result.overall_confidence:.2f}"
        )

        # =========================================================
        # 7. DETERMINISTIC VERIFICATION
        # =========================================================
        #
        # Important:
        #
        # ResearchVerifier.verify() expects:
        #
        #     result=AppResearch
        #     evidence=list[dict]
        #
        # It does not accept research=...
        # =========================================================

        print("  Verifying research...")

        verification = self.verifier.verify(
            result=result,
            evidence=evidence_bundle,
        )

        if verification.passed:
            print(
                "  Verification: PASSED"
            )
        else:
            print(
                "  Verification: FAILED"
            )

        if verification.errors:
            print(
                "  Verification errors: "
                f"{len(verification.errors)}"
            )

        if verification.warnings:
            print(
                "  Verification warnings: "
                f"{len(verification.warnings)}"
            )

        # =========================================================
        # 8. DETERMINISTIC ANALYSIS
        # =========================================================
        #
        # ResearchAnalyzer.analyze() currently accepts only:
        #
        #     research=AppResearch
        #
        # Verification is therefore not passed into the analyzer.
        # =========================================================

        print(
            "  Analyzing research quality..."
        )

        analysis = self.analyzer.analyze(
            research=result,
        )

        print(
            "  Analysis complete."
        )

        # =========================================================
        # 9. ATTACH PHASE 2 METADATA
        # =========================================================
        #
        # AppResearch remains the canonical Pydantic model.
        #
        # Verification and analysis are attached as runtime
        # attributes for the current Phase 2 integration.
        # =========================================================

        result._verification = verification
        result._analysis = analysis

        return result

    @staticmethod
    def _extract_domain(
        website: str,
    ) -> str:
        """
        Extract a usable domain from an application website.

        Example:

            https://www.salesforce.com/in/
            -> www.salesforce.com
        """

        website = website.strip()

        if website.startswith(
            "https://"
        ):
            website = website[
                len("https://") :
            ]

        elif website.startswith(
            "http://"
        ):
            website = website[
                len("http://") :
            ]

        website = website.split(
            "/",
            1,
        )[0]

        return website


def load_apps() -> list[dict]:
    """
    Load the application research dataset.
    """

    path = Path(
        "data/apps.json"
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Application dataset not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        apps = json.load(file)

    if not isinstance(
        apps,
        list,
    ):
        raise ValueError(
            "data/apps.json must contain a JSON list."
        )

    return apps


def main() -> None:
    """
    Run the researcher against one application.

    During development we intentionally process only the first
    application.
    """

    apps = load_apps()

    if not apps:
        raise ValueError(
            "No applications found in data/apps.json"
        )

    app = apps[0]

    agent = ResearchAgent()

    result = agent.research_app(
        app
    )

    # =============================================================
    # FINAL RESEARCH RESULT
    # =============================================================

    print(
        "\n"
        + "=" * 70
    )

    print(
        "FINAL RESULT"
    )

    print(
        "=" * 70
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )

    # =============================================================
    # VERIFICATION SUMMARY
    # =============================================================

    verification = getattr(
        result,
        "_verification",
        None,
    )

    if verification is not None:
        print(
            "\n"
            + "=" * 70
        )

        print(
            "VERIFICATION"
        )

        print(
            "=" * 70
        )

        if hasattr(
            verification,
            "model_dump_json",
        ):
            print(
                verification.model_dump_json(
                    indent=2
                )
            )

        else:
            print(
                verification
            )

    # =============================================================
    # ANALYSIS SUMMARY
    # =============================================================

    analysis = getattr(
        result,
        "_analysis",
        None,
    )

    if analysis is not None:
        print(
            "\n"
            + "=" * 70
        )

        print(
            "ANALYSIS"
        )

        print(
            "=" * 70
        )

        if hasattr(
            analysis,
            "model_dump_json",
        ):
            print(
                analysis.model_dump_json(
                    indent=2
                )
            )

        else:
            print(
                analysis
            )


if __name__ == "__main__":
    main()