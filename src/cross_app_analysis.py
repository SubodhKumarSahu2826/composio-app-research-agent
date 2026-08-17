from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RESULTS_FILE = PROJECT_ROOT / "results" / "results.json"
OUTPUT_FILE = (
    PROJECT_ROOT
    / "results"
    / "cross_app_analysis.json"
)


class CrossAppAnalyzer:
    """
    Deterministic cross-application analysis.

    Reads completed research results from results.json and
    produces aggregate patterns for the completed sample.

    This class does not:
        - call Gemini
        - call Tavily
        - perform web requests
        - invent missing research data
        - treat verifier scores as factual accuracy

    The analysis is designed to work with a partial dataset.
    This is important because the 100-app pipeline may not have
    completed all applications yet.
    """

    def __init__(
        self,
        results_file: Path = RESULTS_FILE,
    ) -> None:
        self.results_file = Path(results_file)

    # =========================================================
    # LOAD RESULTS
    # =========================================================

    def load_results(self) -> list[dict[str, Any]]:
        """Load completed research results."""

        if not self.results_file.exists():
            raise FileNotFoundError(
                f"Results file not found: {self.results_file}"
            )

        with self.results_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            results = json.load(file)

        if not isinstance(results, list):
            raise ValueError(
                "results.json must contain a JSON list."
            )

        return results

    # =========================================================
    # MAIN ANALYSIS
    # =========================================================

    def analyze(
        self,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate deterministic cross-app analysis."""

        if not results:
            return self._empty_analysis()

        return {
            "metadata": self._build_metadata(results),
            "authentication": self._analyze_authentication(
                results
            ),
            "access": self._analyze_access(
                results
            ),
            "api": self._analyze_api(
                results
            ),
            "mcp": self._analyze_mcp(
                results
            ),
            "buildability": self._analyze_buildability(
                results
            ),
            "categories": self._analyze_categories(
                results
            ),
            "confidence": self._analyze_confidence(
                results
            ),
            "evidence": self._analyze_evidence(
                results
            ),
            "verification": self._analyze_verification(
                results
            ),
            "common_blockers": self._analyze_blockers(
                results
            ),
            "patterns": self._derive_patterns(
                results
            ),
            "quality_notes": self._quality_notes(
                results
            ),
        }

    # =========================================================
    # METADATA
    # =========================================================

    @staticmethod
    def _build_metadata(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build high-level dataset metadata."""

        total = len(results)

        verification_count = sum(
            1
            for result in results
            if isinstance(
                result.get("verification"),
                dict,
            )
        )

        analysis_count = sum(
            1
            for result in results
            if isinstance(
                result.get("analysis"),
                dict,
            )
        )

        return {
            "applications_analyzed": total,
            "dataset_scope": (
                "Completed research results only"
            ),
            "verification_records_available": (
                verification_count
            ),
            "analysis_records_available": (
                analysis_count
            ),
            "verification_coverage_percent": round(
                (
                    verification_count
                    / total
                    * 100
                    if total
                    else 0
                ),
                2,
            ),
            "analysis_coverage_percent": round(
                (
                    analysis_count
                    / total
                    * 100
                    if total
                    else 0
                ),
                2,
            ),
        }

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    @staticmethod
    def _analyze_authentication(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Analyze authentication methods.

        One application can contain multiple methods.
        Therefore method counts can exceed the number of apps.
        """

        counter: Counter[str] = Counter()

        apps_with_data = 0

        for result in results:
            authentication = result.get(
                "authentication",
                {},
            )

            if not isinstance(
                authentication,
                dict,
            ):
                continue

            methods = authentication.get(
                "methods",
                [],
            )

            if not isinstance(
                methods,
                list,
            ):
                continue

            if methods:
                apps_with_data += 1

            for method in methods:
                if isinstance(
                    method,
                    str,
                ) and method.strip():
                    counter[
                        method.strip()
                    ] += 1

        return {
            "applications_with_authentication_data": (
                apps_with_data
            ),
            "method_counts": dict(
                counter.most_common()
            ),
            "method_percentages": (
                CrossAppAnalyzer._percentages(
                    counter,
                    len(results),
                )
            ),
        }

    # =========================================================
    # ACCESS
    # =========================================================

    @staticmethod
    def _analyze_access(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze application access classifications."""

        counter: Counter[str] = Counter()

        for result in results:
            access = result.get(
                "access",
                {},
            )

            if not isinstance(
                access,
                dict,
            ):
                continue

            access_type = access.get(
                "type"
            )

            if isinstance(
                access_type,
                str,
            ) and access_type.strip():
                counter[
                    access_type.strip()
                ] += 1

        return {
            "type_counts": dict(
                counter.most_common()
            ),
            "type_percentages": (
                CrossAppAnalyzer._percentages(
                    counter,
                    len(results),
                )
            ),
        }

    # =========================================================
    # API
    # =========================================================

    @staticmethod
    def _analyze_api(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze API type, breadth and documentation."""

        type_counter: Counter[str] = Counter()
        breadth_counter: Counter[str] = Counter()

        documentation_count = 0

        for result in results:
            api = result.get(
                "api",
                {},
            )

            if not isinstance(
                api,
                dict,
            ):
                continue

            api_type = api.get(
                "type"
            )

            if isinstance(
                api_type,
                str,
            ) and api_type.strip():
                type_counter[
                    api_type.strip()
                ] += 1

            breadth = api.get(
                "breadth"
            )

            if isinstance(
                breadth,
                str,
            ) and breadth.strip():
                breadth_counter[
                    breadth.strip()
                ] += 1

            documentation_url = api.get(
                "documentation_url"
            )

            if (
                isinstance(
                    documentation_url,
                    str,
                )
                and documentation_url.strip()
            ):
                documentation_count += 1

        return {
            "type_counts": dict(
                type_counter.most_common()
            ),
            "type_percentages": (
                CrossAppAnalyzer._percentages(
                    type_counter,
                    len(results),
                )
            ),
            "breadth_counts": dict(
                breadth_counter.most_common()
            ),
            "documentation_url_coverage_percent": round(
                (
                    documentation_count
                    / len(results)
                    * 100
                    if results
                    else 0
                ),
                2,
            ),
        }

    # =========================================================
    # MCP
    # =========================================================

    @staticmethod
    def _analyze_mcp(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze MCP classifications."""

        status_counter: Counter[str] = Counter()

        official_count = 0

        for result in results:
            mcp = result.get(
                "mcp",
                {},
            )

            if not isinstance(
                mcp,
                dict,
            ):
                continue

            status = mcp.get(
                "status"
            )

            if isinstance(
                status,
                str,
            ) and status.strip():
                status_counter[
                    status.strip()
                ] += 1

            if mcp.get(
                "official"
            ) is True:
                official_count += 1

        return {
            "status_counts": dict(
                status_counter.most_common()
            ),
            "status_percentages": (
                CrossAppAnalyzer._percentages(
                    status_counter,
                    len(results),
                )
            ),
            "official_flag_count": official_count,
            "official_flag_percentage": round(
                (
                    official_count
                    / len(results)
                    * 100
                    if results
                    else 0
                ),
                2,
            ),
        }

    # =========================================================
    # BUILDABILITY
    # =========================================================

    @staticmethod
    def _analyze_buildability(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze buildability verdicts."""

        counter: Counter[str] = Counter()

        for result in results:
            buildability = result.get(
                "buildability",
                {},
            )

            if not isinstance(
                buildability,
                dict,
            ):
                continue

            verdict = buildability.get(
                "verdict"
            )

            if isinstance(
                verdict,
                str,
            ) and verdict.strip():
                counter[
                    verdict.strip()
                ] += 1

        return {
            "verdict_counts": dict(
                counter.most_common()
            ),
            "verdict_percentages": (
                CrossAppAnalyzer._percentages(
                    counter,
                    len(results),
                )
            ),
        }

    # =========================================================
    # CATEGORIES
    # =========================================================

    @staticmethod
    def _analyze_categories(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze category distribution."""

        counter: Counter[str] = Counter()

        for result in results:
            category = result.get(
                "category"
            )

            if isinstance(
                category,
                str,
            ) and category.strip():
                counter[
                    category.strip()
                ] += 1

        return {
            "category_counts": dict(
                counter.most_common()
            ),
            "category_percentages": (
                CrossAppAnalyzer._percentages(
                    counter,
                    len(results),
                )
            ),
        }

    # =========================================================
    # CONFIDENCE
    # =========================================================

    @staticmethod
    def _analyze_confidence(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze overall confidence."""

        values: list[float] = []

        for result in results:
            confidence = result.get(
                "overall_confidence"
            )

            if isinstance(
                confidence,
                (int, float),
            ):
                values.append(
                    float(confidence)
                )

        if not values:
            return {
                "count": 0,
                "average": None,
                "minimum": None,
                "maximum": None,
            }

        return {
            "count": len(values),
            "average": round(
                mean(values),
                4,
            ),
            "minimum": round(
                min(values),
                4,
            ),
            "maximum": round(
                max(values),
                4,
            ),
        }

    # =========================================================
    # EVIDENCE
    # =========================================================

    @staticmethod
    def _analyze_evidence(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze evidence quantity and source types."""

        source_type_counter: Counter[str] = Counter()

        evidence_counts: list[int] = []

        total_evidence = 0

        for result in results:
            evidence = result.get(
                "evidence",
                [],
            )

            if not isinstance(
                evidence,
                list,
            ):
                continue

            evidence_counts.append(
                len(evidence)
            )

            total_evidence += len(evidence)

            for item in evidence:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                source_type = item.get(
                    "source_type"
                )

                if isinstance(
                    source_type,
                    str,
                ) and source_type.strip():
                    source_type_counter[
                        source_type.strip()
                    ] += 1

        return {
            "total_evidence_items": total_evidence,
            "average_evidence_per_app": round(
                (
                    total_evidence
                    / len(results)
                    if results
                    else 0
                ),
                2,
            ),
            "minimum_evidence_per_app": (
                min(evidence_counts)
                if evidence_counts
                else 0
            ),
            "maximum_evidence_per_app": (
                max(evidence_counts)
                if evidence_counts
                else 0
            ),
            "source_type_counts": dict(
                source_type_counter.most_common()
            ),
        }

    # =========================================================
    # VERIFICATION
    # =========================================================

    @staticmethod
    def _analyze_verification(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Analyze deterministic verification.

        IMPORTANT:
        Verifier score is a consistency metric.
        It is NOT factual accuracy.
        """

        records: list[dict[str, Any]] = []

        passed_count = 0
        failed_count = 0

        scores: list[float] = []

        for result in results:
            verification = result.get(
                "verification"
            )

            if not isinstance(
                verification,
                dict,
            ):
                continue

            passed = verification.get(
                "passed"
            )

            score = verification.get(
                "score"
            )

            if passed is True:
                passed_count += 1

            elif passed is False:
                failed_count += 1

            if isinstance(
                score,
                (int, float),
            ):
                scores.append(
                    float(score)
                )

            records.append(
                {
                    "app_id": result.get(
                        "app_id"
                    ),
                    "app_name": result.get(
                        "app_name"
                    ),
                    "passed": passed,
                    "score": score,
                    "errors": verification.get(
                        "errors",
                        [],
                    ),
                    "warnings": verification.get(
                        "warnings",
                        [],
                    ),
                }
            )

        return {
            "records_available": len(records),
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate_percent": round(
                (
                    passed_count
                    / len(records)
                    * 100
                    if records
                    else 0
                ),
                2,
            ),
            "average_verifier_score": round(
                (
                    mean(scores)
                    if scores
                    else 0
                ),
                4,
            ),
            "records": records,
            "interpretation": (
                "Verifier scores measure deterministic "
                "consistency checks and must not be "
                "reported as independently verified "
                "factual accuracy."
            ),
        }

    # =========================================================
    # BLOCKERS
    # =========================================================

    @staticmethod
    def _analyze_blockers(
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Extract recurring explicit buildability blockers."""

        counter: Counter[str] = Counter()

        for result in results:
            buildability = result.get(
                "buildability",
                {},
            )

            if not isinstance(
                buildability,
                dict,
            ):
                continue

            blocker = buildability.get(
                "blocker"
            )

            if isinstance(
                blocker,
                str,
            ) and blocker.strip():
                counter[
                    blocker.strip()
                ] += 1

        return {
            "blocker_counts": dict(
                counter.most_common()
            ),
        }

    # =========================================================
    # PATTERNS
    # =========================================================

    @staticmethod
    def _derive_patterns(
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Generate conservative observations from the completed
        sample.

        These observations must not be presented as conclusions
        about the complete 100-app dataset.
        """

        total = len(results)

        if total == 0:
            return []

        patterns: list[dict[str, Any]] = []

        # -----------------------------------------------------
        # OAuth2
        # -----------------------------------------------------

        oauth_count = 0

        for result in results:
            authentication = result.get(
                "authentication",
                {},
            )

            if not isinstance(
                authentication,
                dict,
            ):
                continue

            methods = authentication.get(
                "methods",
                [],
            )

            if not isinstance(
                methods,
                list,
            ):
                continue

            if any(
                isinstance(
                    method,
                    str,
                )
                and "oauth" in method.lower()
                for method in methods
            ):
                oauth_count += 1

        if oauth_count:
            patterns.append(
                {
                    "title": (
                        "OAuth-based authentication "
                        "is common in the completed sample"
                    ),
                    "observation": (
                        f"{oauth_count} of {total} "
                        "completed applications list "
                        "an OAuth-based authentication "
                        "method."
                    ),
                    "sample_size": total,
                    "scope": "Completed sample only",
                }
            )

        # -----------------------------------------------------
        # REST
        # -----------------------------------------------------

        rest_count = 0

        for result in results:
            api = result.get(
                "api",
                {},
            )

            if not isinstance(
                api,
                dict,
            ):
                continue

            api_type = api.get(
                "type"
            )

            if (
                isinstance(
                    api_type,
                    str,
                )
                and "rest" in api_type.lower()
            ):
                rest_count += 1

        if rest_count:
            patterns.append(
                {
                    "title": (
                        "REST APIs dominate "
                        "the completed sample"
                    ),
                    "observation": (
                        f"{rest_count} of {total} "
                        "completed applications expose "
                        "a REST API classification."
                    ),
                    "sample_size": total,
                    "scope": "Completed sample only",
                }
            )

        # -----------------------------------------------------
        # EASY BUILDABILITY
        # -----------------------------------------------------

        easy_count = 0

        for result in results:
            buildability = result.get(
                "buildability",
                {},
            )

            if not isinstance(
                buildability,
                dict,
            ):
                continue

            verdict = buildability.get(
                "verdict"
            )

            if (
                isinstance(
                    verdict,
                    str,
                )
                and verdict.lower() == "easy"
            ):
                easy_count += 1

        if easy_count:
            patterns.append(
                {
                    "title": (
                        "Most completed applications "
                        "are classified as Easy to build"
                    ),
                    "observation": (
                        f"{easy_count} of {total} "
                        "completed applications received "
                        "an Easy buildability verdict."
                    ),
                    "sample_size": total,
                    "scope": "Completed sample only",
                }
            )

        # -----------------------------------------------------
        # OFFICIAL MCP
        # -----------------------------------------------------

        official_mcp_count = 0

        for result in results:
            mcp = result.get(
                "mcp",
                {},
            )

            if not isinstance(
                mcp,
                dict,
            ):
                continue

            status = mcp.get(
                "status"
            )

            if status == "Official MCP":
                official_mcp_count += 1

        if official_mcp_count:
            patterns.append(
                {
                    "title": (
                        "Official MCP support appears "
                        "in a subset of the sample"
                    ),
                    "observation": (
                        f"{official_mcp_count} of {total} "
                        "completed applications are "
                        "classified as having Official "
                        "MCP support."
                    ),
                    "sample_size": total,
                    "scope": "Completed sample only",
                }
            )

        return patterns

    # =========================================================
    # QUALITY NOTES
    # =========================================================

    @staticmethod
    def _quality_notes(
        results: list[dict[str, Any]],
    ) -> list[str]:
        """Generate caveats for the final report."""

        notes: list[str] = []

        total = len(results)

        verification_count = sum(
            1
            for result in results
            if isinstance(
                result.get("verification"),
                dict,
            )
        )

        analysis_count = sum(
            1
            for result in results
            if isinstance(
                result.get("analysis"),
                dict,
            )
        )

        if total < 100:
            notes.append(
                f"Only {total} completed application "
                "results are currently available. "
                "Cross-app patterns describe the completed "
                "sample and should not be generalized to "
                "the full 100-app dataset."
            )

        if verification_count < total:
            notes.append(
                f"Verification metadata is available "
                f"for {verification_count} of {total} "
                "applications. Older results may predate "
                "the deterministic verification layer."
            )

        if analysis_count < total:
            notes.append(
                f"Research analysis metadata is available "
                f"for {analysis_count} of {total} "
                "applications."
            )

        notes.append(
            "Deterministic verifier scores are consistency "
            "metrics, not independently measured factual "
            "accuracy."
        )

        return notes

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _percentages(
        counter: Counter[str],
        denominator: int,
    ) -> dict[str, float]:
        """Convert counts to percentages."""

        if denominator <= 0:
            return {}

        return {
            key: round(
                value / denominator * 100,
                2,
            )
            for key, value in counter.items()
        }

    @staticmethod
    def _empty_analysis() -> dict[str, Any]:
        """Return an empty but valid analysis structure."""

        return {
            "metadata": {
                "applications_analyzed": 0,
                "dataset_scope": (
                    "No completed results"
                ),
                "verification_records_available": 0,
                "analysis_records_available": 0,
                "verification_coverage_percent": 0,
                "analysis_coverage_percent": 0,
            },
            "authentication": {},
            "access": {},
            "api": {},
            "mcp": {},
            "buildability": {},
            "categories": {},
            "confidence": {},
            "evidence": {},
            "verification": {},
            "common_blockers": {},
            "patterns": [],
            "quality_notes": [
                "No completed application "
                "results are available."
            ],
        }

    # =========================================================
    # SAVE
    # =========================================================

    def save_analysis(
        self,
        analysis: dict[str, Any],
        output_file: Path = OUTPUT_FILE,
    ) -> None:
        """Save analysis to JSON."""

        output_file = Path(
            output_file
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                analysis,
                file,
                indent=2,
                ensure_ascii=False,
            )

    # =========================================================
    # RUN
    # =========================================================

    def run(
        self,
        output_file: Path = OUTPUT_FILE,
    ) -> dict[str, Any]:
        """Load, analyze and persist results."""

        results = self.load_results()

        analysis = self.analyze(
            results
        )

        self.save_analysis(
            analysis,
            output_file,
        )

        return analysis


def print_summary(
    analysis: dict[str, Any],
) -> None:
    """Print a concise terminal summary."""

    metadata = analysis.get(
        "metadata",
        {},
    )

    verification = analysis.get(
        "verification",
        {},
    )

    patterns = analysis.get(
        "patterns",
        [],
    )

    print(
        "=" * 70
    )
    print(
        "CROSS-APP RESEARCH ANALYSIS"
    )
    print(
        "=" * 70
    )

    print(
        "Applications analyzed: "
        f"{metadata.get('applications_analyzed', 0)}"
    )

    print(
        "Verification records: "
        f"{verification.get('records_available', 0)}"
    )

    print(
        "Verifier pass rate: "
        f"{verification.get('pass_rate_percent', 0)}%"
    )

    print()

    print(
        "PATTERNS"
    )

    print(
        "-" * 70
    )

    if not patterns:
        print(
            "No patterns available."
        )

    for index, pattern in enumerate(
        patterns,
        start=1,
    ):
        print(
            f"{index}. "
            f"{pattern.get('title', '')}"
        )

        print(
            f"   {pattern.get('observation', '')}"
        )

    print()

    print(
        "QUALITY NOTES"
    )

    print(
        "-" * 70
    )

    for note in analysis.get(
        "quality_notes",
        [],
    ):
        print(
            f"- {note}"
        )

    print()

    print(
        "=" * 70
    )


def main() -> None:
    """CLI entry point."""

    analyzer = CrossAppAnalyzer()

    analysis = analyzer.run()

    print_summary(
        analysis
    )

    print(
        "\nAnalysis saved to: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()