from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RESULTS_FILE = (
    PROJECT_ROOT
    / "results"
    / "results.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "results"
    / "cross_app_analysis.json"
)


# ============================================================
# CONSTANTS
# ============================================================

BUILDABILITY_SCORES = {
    "Easy": 100,
    "Possible": 70,
    "Blocked": 20,
}

MCP_SCORES = {
    "Official MCP": 100,
    "Third-party MCP": 70,
    "Unknown": 40,
    "No MCP Found": 0,
}


# ============================================================
# DATA LOADING
# ============================================================


def load_results() -> list[dict]:
    """Load completed application research results."""

    if not RESULTS_FILE.exists():
        return []

    with RESULTS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        return []

    return [
        item
        for item in data
        if isinstance(item, dict)
    ]


# ============================================================
# GENERIC HELPERS
# ============================================================


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Safely convert a value to float."""

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def percentage(
    count: int,
    total: int,
) -> float:
    """Calculate percentage safely."""

    if total <= 0:
        return 0.0

    return round(
        (count / total) * 100,
        2,
    )


def increment(
    counter: dict[str, int],
    key: str,
) -> None:
    """Increment a dictionary counter."""

    counter[key] = (
        counter.get(key, 0)
        + 1
    )


def get_nested_dict(
    value: Any,
) -> dict:
    """Return value if it is a dictionary."""

    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


# ============================================================
# EXISTING CROSS-APP PATTERNS
# ============================================================


def analyze_authentication(
    results: list[dict],
) -> dict:
    """Analyze authentication methods."""

    method_counts: dict[str, int] = {}

    for result in results:

        authentication = get_nested_dict(
            result.get(
                "authentication"
            )
        )

        methods = authentication.get(
            "methods",
            [],
        )

        if not isinstance(
            methods,
            list,
        ):
            continue

        unique_methods = {
            str(method)
            for method in methods
        }

        for method in unique_methods:
            increment(
                method_counts,
                method,
            )

    total = len(results)

    method_percentages = {
        method: percentage(
            count,
            total,
        )
        for method, count
        in method_counts.items()
    }

    return {
        "method_counts": dict(
            sorted(
                method_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),
        "method_percentages": (
            dict(
                sorted(
                    method_percentages.items(),
                    key=lambda item: (
                        -item[1],
                        item[0],
                    ),
                )
            )
        ),
    }


def analyze_api(
    results: list[dict],
) -> dict:
    """Analyze API classifications."""

    type_counts: dict[str, int] = {}
    breadth_counts: dict[str, int] = {}

    for result in results:

        api = get_nested_dict(
            result.get("api")
        )

        api_type = str(
            api.get(
                "type",
                "Unknown",
            )
        )

        breadth = str(
            api.get(
                "breadth",
                "Unknown",
            )
        )

        increment(
            type_counts,
            api_type,
        )

        increment(
            breadth_counts,
            breadth,
        )

    total = len(results)

    return {
        "type_counts": dict(
            sorted(
                type_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),
        "type_percentages": {
            key: percentage(
                value,
                total,
            )
            for key, value
            in type_counts.items()
        },
        "breadth_counts": dict(
            sorted(
                breadth_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),
    }


def analyze_mcp(
    results: list[dict],
) -> dict:
    """Analyze MCP support."""

    status_counts: dict[str, int] = {}

    for result in results:

        mcp = get_nested_dict(
            result.get("mcp")
        )

        status = str(
            mcp.get(
                "status",
                "Unknown",
            )
        )

        increment(
            status_counts,
            status,
        )

    total = len(results)

    return {
        "status_counts": dict(
            sorted(
                status_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),
        "status_percentages": {
            key: percentage(
                value,
                total,
            )
            for key, value
            in status_counts.items()
        },
    }


def analyze_buildability(
    results: list[dict],
) -> dict:
    """Analyze buildability verdicts."""

    verdict_counts: dict[str, int] = {}

    for result in results:

        buildability = get_nested_dict(
            result.get(
                "buildability"
            )
        )

        verdict = str(
            buildability.get(
                "verdict",
                "Unknown",
            )
        )

        increment(
            verdict_counts,
            verdict,
        )

    total = len(results)

    return {
        "verdict_counts": dict(
            sorted(
                verdict_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),
        "verdict_percentages": {
            key: percentage(
                value,
                total,
            )
            for key, value
            in verdict_counts.items()
        },
    }


def analyze_access(
    results: list[dict],
) -> dict:
    """Analyze access requirements."""

    type_counts: dict[str, int] = {}

    requirement_counts: dict[str, int] = {}

    for result in results:

        access = get_nested_dict(
            result.get("access")
        )

        access_type = str(
            access.get(
                "type",
                "Unknown",
            )
        )

        increment(
            type_counts,
            access_type,
        )

        requirements = access.get(
            "requirements",
            [],
        )

        if isinstance(
            requirements,
            list,
        ):
            for requirement in {
                str(item)
                for item in requirements
            }:
                increment(
                    requirement_counts,
                    requirement,
                )

    return {
        "type_counts": dict(
            sorted(
                type_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),
        "requirement_counts": dict(
            sorted(
                requirement_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        ),
    }


# ============================================================
# CONFIDENCE / EVIDENCE / VERIFICATION
# ============================================================


def analyze_confidence(
    results: list[dict],
) -> dict:
    """Analyze research confidence."""

    values: list[float] = []

    for result in results:

        confidence = safe_float(
            result.get(
                "overall_confidence"
            ),
            default=-1,
        )

        if confidence >= 0:
            values.append(
                confidence
            )

    if not values:
        return {
            "average": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
            "records_available": 0,
        }

    return {
        "average": round(
            sum(values)
            / len(values),
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
        "records_available": len(values),
    }


def analyze_evidence(
    results: list[dict],
) -> dict:
    """Analyze evidence coverage."""

    counts: list[int] = []

    for result in results:

        evidence = result.get(
            "evidence",
            [],
        )

        if isinstance(
            evidence,
            list,
        ):
            counts.append(
                len(evidence)
            )

    total = sum(counts)

    average = (
        total / len(counts)
        if counts
        else 0.0
    )

    return {
        "total_evidence_items": total,
        "average_evidence_per_app": round(
            average,
            2,
        ),
        "minimum_evidence": (
            min(counts)
            if counts
            else 0
        ),
        "maximum_evidence": (
            max(counts)
            if counts
            else 0
        ),
    }


def analyze_verification(
    results: list[dict],
) -> dict:
    """Analyze deterministic verification metadata."""

    records: list[dict] = []

    passed = 0

    scores: list[float] = []

    for result in results:

        verification = get_nested_dict(
            result.get(
                "verification"
            )
        )

        if not verification:
            continue

        app_name = str(
            result.get(
                "app_name",
                "Unknown",
            )
        )

        passed_value = verification.get(
            "passed"
        )

        score = verification.get(
            "score"
        )

        if passed_value is True:
            passed += 1

        if isinstance(
            score,
            (int, float),
        ):
            scores.append(
                float(score)
            )

        records.append(
            {
                "app_name": app_name,
                "passed": passed_value,
                "score": score,
            }
        )

    record_count = len(records)

    return {
        "records_available": record_count,
        "passed": passed,
        "failed": (
            record_count - passed
        ),
        "pass_rate_percent": percentage(
            passed,
            record_count,
        ),
        "average_score": round(
            (
                sum(scores)
                / len(scores)
                if scores
                else 0.0
            ),
            3,
        ),
        "records": records,
    }


# ============================================================
# CATEGORY ANALYSIS
# ============================================================


def analyze_categories(
    results: list[dict],
) -> dict:
    """Analyze application categories."""

    category_counts: dict[str, int] = {}

    for result in results:

        category = str(
            result.get(
                "category",
                "Unknown",
            )
        )

        increment(
            category_counts,
            category,
        )

    return {
        "category_counts": dict(
            sorted(
                category_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        )
    }


# ============================================================
# COMMON BLOCKERS
# ============================================================


def analyze_blockers(
    results: list[dict],
) -> dict:
    """Extract common buildability blockers."""

    blocker_counts: dict[str, int] = {}

    for result in results:

        buildability = get_nested_dict(
            result.get(
                "buildability"
            )
        )

        blocker = buildability.get(
            "blocker"
        )

        if blocker:
            increment(
                blocker_counts,
                str(blocker),
            )

    return {
        "blocker_counts": dict(
            sorted(
                blocker_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )
        )
    }


# ============================================================
# CROSS-APP PATTERN DETECTION
# ============================================================


def generate_patterns(
    results: list[dict],
) -> list[dict]:
    """Generate deterministic cross-app patterns."""

    total = len(results)

    if total == 0:
        return []

    patterns: list[dict] = []

    # --------------------------------------------------------
    # OAuth pattern
    # --------------------------------------------------------

    oauth_count = 0

    for result in results:

        authentication = get_nested_dict(
            result.get(
                "authentication"
            )
        )

        methods = authentication.get(
            "methods",
            [],
        )

        if not isinstance(
            methods,
            list,
        ):
            continue

        normalized = {
            str(method).lower()
            for method in methods
        }

        if any(
            "oauth" in method
            for method in normalized
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
                    "an OAuth-based authentication method."
                ),
                "sample_size": total,
                "scope": "Authentication",
            }
        )

    # --------------------------------------------------------
    # REST pattern
    # --------------------------------------------------------

    rest_count = 0

    for result in results:

        api = get_nested_dict(
            result.get("api")
        )

        api_type = str(
            api.get(
                "type",
                "",
            )
        ).lower()

        if "rest" in api_type:
            rest_count += 1

    if rest_count:
        patterns.append(
            {
                "title": (
                    "REST APIs dominate the completed sample"
                ),
                "observation": (
                    f"{rest_count} of {total} "
                    "completed applications expose "
                    "a REST API classification."
                ),
                "sample_size": total,
                "scope": "API",
            }
        )

    # --------------------------------------------------------
    # Easy buildability
    # --------------------------------------------------------

    easy_count = 0

    for result in results:

        buildability = get_nested_dict(
            result.get(
                "buildability"
            )
        )

        verdict = str(
            buildability.get(
                "verdict",
                "",
            )
        )

        if verdict == "Easy":
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
                "scope": "Buildability",
            }
        )

    # --------------------------------------------------------
    # Official MCP
    # --------------------------------------------------------

    official_mcp_count = 0

    for result in results:

        mcp = get_nested_dict(
            result.get("mcp")
        )

        if (
            mcp.get("status")
            == "Official MCP"
        ):
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
                    "completed applications are classified "
                    "as having Official MCP support."
                ),
                "sample_size": total,
                "scope": "MCP",
            }
        )

    return patterns


# ============================================================
# COMPARISON / RANKING
# ============================================================


def calculate_integration_score(
    result: dict,
) -> tuple[float, dict]:
    """
    Calculate a deterministic integration-priority score.

    Nominal weights:

        Buildability       35%
        MCP support        20%
        Evidence           15%
        Verification       15%
        Confidence         15%

    When a component is genuinely unavailable, its weight is
    redistributed proportionally across the available
    components instead of treating missing data as zero.

    This is a prioritization heuristic, not a factual
    measurement of real-world integration difficulty.
    """

    # --------------------------------------------------------
    # Buildability
    # --------------------------------------------------------

    buildability = get_nested_dict(
        result.get(
            "buildability"
        )
    )

    buildability_verdict = str(
        buildability.get(
            "verdict",
            "Unknown",
        )
    )

    buildability_score = BUILDABILITY_SCORES.get(
        buildability_verdict,
        50,
    )

    # Buildability is always represented in the schema.
    buildability_available = (
        "verdict" in buildability
    )

    # --------------------------------------------------------
    # MCP
    # --------------------------------------------------------

    mcp = get_nested_dict(
        result.get("mcp")
    )

    mcp_status = str(
        mcp.get(
            "status",
            "Unknown",
        )
    )

    mcp_score = MCP_SCORES.get(
        mcp_status,
        40,
    )

    mcp_available = (
        "status" in mcp
    )

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    evidence = result.get(
        "evidence",
        [],
    )

    evidence_available = isinstance(
        evidence,
        list,
    )

    evidence_count = (
        len(evidence)
        if evidence_available
        else 0
    )

    # Cap evidence contribution at 8 sources.
    evidence_score = (
        min(
            evidence_count / 8,
            1.0,
        )
        * 100
    )

    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    verification = get_nested_dict(
        result.get(
            "verification"
        )
    )

    verification_value = verification.get(
        "score"
    )

    verification_available = (
        bool(verification)
        and isinstance(
            verification_value,
            (int, float),
        )
    )

    verification_score = None

    if verification_available:

        verification_score = float(
            verification_value
        )

        # Verifier scores are normally represented
        # on a 0-1 scale.
        if verification_score <= 1:
            verification_score *= 100

        verification_score = max(
            0.0,
            min(
                verification_score,
                100.0,
            ),
        )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence_value = result.get(
        "overall_confidence"
    )

    confidence_available = (
        isinstance(
            confidence_value,
            (int, float),
        )
        and confidence_value >= 0
    )

    confidence_score = (
        float(confidence_value) * 100
        if confidence_available
        else None
    )

    # --------------------------------------------------------
    # Nominal weights
    # --------------------------------------------------------

    weights = {
        "buildability": 0.35,
        "mcp": 0.20,
        "evidence": 0.15,
        "verification": 0.15,
        "confidence": 0.15,
    }

    scores = {
        "buildability": (
            float(buildability_score)
            if buildability_available
            else None
        ),
        "mcp": (
            float(mcp_score)
            if mcp_available
            else None
        ),
        "evidence": (
            float(evidence_score)
            if evidence_available
            else None
        ),
        "verification": verification_score,
        "confidence": confidence_score,
    }

    # --------------------------------------------------------
    # Find available components.
    #
    # Missing verification is NOT a failure.
    # It simply isn't included in the weighted calculation.
    # --------------------------------------------------------

    available_components = [
        name
        for name, score in scores.items()
        if score is not None
    ]

    available_weight = sum(
        weights[name]
        for name in available_components
    )

    if available_weight <= 0:
        return (
            0.0,
            {
                "buildability": None,
                "mcp": None,
                "evidence": None,
                "verification": None,
                "confidence": None,
                "verification_available": False,
                "weights_used": {},
            },
        )

    # --------------------------------------------------------
    # Redistribute missing-component weight.
    #
    # Example:
    #
    # Original:
    #   Buildability = 35%
    #   MCP          = 20%
    #   Evidence     = 15%
    #   Verification = 15%
    #   Confidence   = 15%
    #
    # If verification is missing:
    #
    #   Available weight = 85%
    #
    # The available components are normalized so that
    # their effective weights sum to 100%.
    # --------------------------------------------------------

    normalized_weights = {
        name: weights[name] / available_weight
        for name in available_components
    }

    total_score = sum(
        scores[name]
        * normalized_weights[name]
        for name in available_components
    )

    components = {
        "buildability": round(
            buildability_score,
            2,
        ),
        "mcp": round(
            mcp_score,
            2,
        ),
        "evidence": round(
            evidence_score,
            2,
        ),
        "verification": (
            round(
                verification_score,
                2,
            )
            if verification_score is not None
            else None
        ),
        "confidence": (
            round(
                confidence_score,
                2,
            )
            if confidence_score is not None
            else None
        ),
        "verification_available": (
            verification_available
        ),
        "weights_used": {
            name: round(
                normalized_weights[name],
                4,
            )
            for name in available_components
        },
    }

    return (
        round(
            total_score,
            2,
        ),
        components,
    )


def build_comparison_records(
    results: list[dict],
) -> list[dict]:
    """Build normalized comparison records."""

    records: list[dict] = []

    for result in results:

        app_id = result.get(
            "app_id"
        )

        app_name = str(
            result.get(
                "app_name",
                "Unknown",
            )
        )

        category = str(
            result.get(
                "category",
                "Unknown",
            )
        )

        buildability = get_nested_dict(
            result.get(
                "buildability"
            )
        )

        api = get_nested_dict(
            result.get("api")
        )

        mcp = get_nested_dict(
            result.get("mcp")
        )

        authentication = get_nested_dict(
            result.get(
                "authentication"
            )
        )

        access = get_nested_dict(
            result.get("access")
        )

        evidence = result.get(
            "evidence",
            [],
        )

        evidence_count = (
            len(evidence)
            if isinstance(
                evidence,
                list,
            )
            else 0
        )

        verification = get_nested_dict(
            result.get(
                "verification"
            )
        )

        quality_analysis = get_nested_dict(
            result.get(
                "analysis"
            )
        )

        overall_score, components = (
            calculate_integration_score(
                result
            )
        )

        methods = authentication.get(
            "methods",
            [],
        )

        if not isinstance(
            methods,
            list,
        ):
            methods = []

        records.append(
            {
                "app_id": app_id,
                "app_name": app_name,
                "category": category,
                "integration_score": overall_score,
                "score_components": components,
                "buildability": buildability.get(
                    "verdict",
                    "Unknown",
                ),
                "mcp_status": mcp.get(
                    "status",
                    "Unknown",
                ),
                "api_type": api.get(
                    "type",
                    "Unknown",
                ),
                "api_breadth": api.get(
                    "breadth",
                    "Unknown",
                ),
                "authentication_methods": [
                    str(method)
                    for method in methods
                ],
                "access_type": access.get(
                    "type",
                    "Unknown",
                ),
                "evidence_count": evidence_count,
                "verification_passed": (
                    verification.get(
                        "passed"
                    )
                ),
                "verification_score": (
                    verification.get(
                        "score"
                    )
                ),
                "overall_confidence": (
                    result.get(
                        "overall_confidence"
                    )
                ),
                "quality_score": (
                    quality_analysis.get(
                        "quality_score"
                    )
                ),
            }
        )

    return records


def rank_records(
    records: list[dict],
) -> list[dict]:
    """Rank comparison records by integration score."""

    ranked = sorted(
        records,
        key=lambda item: (
            -safe_float(
                item.get(
                    "integration_score"
                )
            ),
            str(
                item.get(
                    "app_name",
                    "",
                )
            ),
        ),
    )

    output: list[dict] = []

    for rank, record in enumerate(
        ranked,
        start=1,
    ):
        item = dict(record)
        item["rank"] = rank
        output.append(item)

    return output


def build_buildability_ranking(
    records: list[dict],
) -> list[dict]:
    """Rank applications by buildability."""

    ranked = sorted(
        records,
        key=lambda item: (
            -BUILDABILITY_SCORES.get(
                str(
                    item.get(
                        "buildability",
                        "Unknown",
                    )
                ),
                50,
            ),
            -safe_float(
                item.get(
                    "overall_confidence"
                )
            ),
            str(
                item.get(
                    "app_name",
                    "",
                )
            ),
        ),
    )

    output: list[dict] = []

    for rank, record in enumerate(
        ranked,
        start=1,
    ):
        output.append(
            {
                "rank": rank,
                "app_id": record.get(
                    "app_id"
                ),
                "app_name": record.get(
                    "app_name"
                ),
                "buildability": record.get(
                    "buildability"
                ),
                "confidence": record.get(
                    "overall_confidence"
                ),
            }
        )

    return output


def build_mcp_ranking(
    records: list[dict],
) -> list[dict]:
    """Rank applications by MCP support."""

    ranked = sorted(
        records,
        key=lambda item: (
            -MCP_SCORES.get(
                str(
                    item.get(
                        "mcp_status",
                        "Unknown",
                    )
                ),
                40,
            ),
            str(
                item.get(
                    "app_name",
                    "",
                )
            ),
        ),
    )

    output: list[dict] = []

    for rank, record in enumerate(
        ranked,
        start=1,
    ):
        output.append(
            {
                "rank": rank,
                "app_id": record.get(
                    "app_id"
                ),
                "app_name": record.get(
                    "app_name"
                ),
                "mcp_status": record.get(
                    "mcp_status"
                ),
            }
        )

    return output


# ============================================================
# COMPARISON MATRIX
# ============================================================


def build_comparison_matrix(
    records: list[dict],
) -> list[dict]:
    """
    Create a compact application comparison matrix.

    This is intended to be consumed by the HTML report,
    CSV export, or future API layer.
    """

    matrix: list[dict] = []

    for record in records:

        matrix.append(
            {
                "rank": record.get(
                    "rank"
                ),
                "app_name": record.get(
                    "app_name"
                ),
                "category": record.get(
                    "category"
                ),
                "integration_score": record.get(
                    "integration_score"
                ),
                "buildability": record.get(
                    "buildability"
                ),
                "api_type": record.get(
                    "api_type"
                ),
                "api_breadth": record.get(
                    "api_breadth"
                ),
                "mcp_status": record.get(
                    "mcp_status"
                ),
                "authentication": ", ".join(
                    record.get(
                        "authentication_methods",
                        [],
                    )
                ),
                "access_type": record.get(
                    "access_type"
                ),
                "evidence_count": record.get(
                    "evidence_count"
                ),
                "verification": (
                    "Passed"
                    if record.get(
                        "verification_passed"
                    )
                    is True
                    else
                    "Failed"
                    if record.get(
                        "verification_passed"
                    )
                    is False
                    else
                    "Unavailable"
                ),
            }
        )

    return matrix


# ============================================================
# RANKING INSIGHTS
# ============================================================


def generate_ranking_insights(
    ranked_records: list[dict],
) -> list[str]:
    """Generate deterministic ranking observations."""

    if not ranked_records:
        return []

    insights: list[str] = []

    best = ranked_records[0]

    insights.append(
        (
            f"{best['app_name']} ranks #1 in the "
            "deterministic integration-priority ranking "
            f"with a score of "
            f"{best['integration_score']:.2f}/100."
        )
    )

    easy_apps = [
        record
        for record in ranked_records
        if record.get(
            "buildability"
        ) == "Easy"
    ]

    if easy_apps:
        insights.append(
            (
                f"{len(easy_apps)} of "
                f"{len(ranked_records)} applications "
                "are classified as Easy to build."
            )
        )

    official_mcp_apps = [
        record
        for record in ranked_records
        if record.get(
            "mcp_status"
        ) == "Official MCP"
    ]

    if official_mcp_apps:
        insights.append(
            (
                f"{len(official_mcp_apps)} applications "
                "have Official MCP support in the "
                "current sample."
            )
        )

    highest_evidence = max(
        ranked_records,
        key=lambda record: (
            safe_float(
                record.get(
                    "evidence_count"
                )
            ),
            safe_float(
                record.get(
                    "overall_confidence"
                )
            ),
        ),
    )

    insights.append(
        (
            f"{highest_evidence['app_name']} has the "
            "largest evidence set in the current "
            f"sample with "
            f"{highest_evidence['evidence_count']} "
            "evidence items."
        )
    )

    return insights


# ============================================================
# QUALITY NOTES
# ============================================================


def generate_quality_notes(
    results: list[dict],
) -> list[str]:
    """Generate methodological limitations."""

    total = len(results)

    notes: list[str] = []

    if total < 100:
        notes.append(
            (
                f"Only {total} completed application "
                "results are currently available. "
                "Cross-app rankings describe the completed "
                "sample and should not be generalized to "
                "the full 100-app dataset."
            )
        )

    verification_count = sum(
        1
        for result in results
        if isinstance(
            result.get(
                "verification"
            ),
            dict,
        )
        and result.get(
            "verification"
        )
    )

    if verification_count < total:
        notes.append(
            (
                "Not every completed application contains "
                "verification metadata. Missing verification "
                "data is excluded from the integration score "
                "and its nominal weight is redistributed "
                "across available scoring components."
            )
        )

    analysis_count = sum(
        1
        for result in results
        if isinstance(
            result.get(
                "analysis"
            ),
            dict,
        )
        and result.get(
            "analysis"
        )
    )

    if analysis_count < total:
        notes.append(
            (
                "Research-quality analysis metadata is not "
                "available for every completed application."
            )
        )

    notes.append(
        (
            "The integration score is a deterministic "
            "prioritization heuristic combining "
            "buildability, MCP support, evidence coverage, "
            "verification, and confidence. It is not a "
            "measured benchmark of real integration effort."
        )
    )

    notes.append(
        (
            "Verification scores measure consistency against "
            "the supplied evidence and should not be "
            "interpreted as independent factual accuracy."
        )
    )

    return notes


# ============================================================
# COMPLETE ANALYSIS
# ============================================================


def analyze(
    results: list[dict],
) -> dict:
    """Generate the complete cross-app analysis."""

    total = len(results)

    authentication = (
        analyze_authentication(
            results
        )
    )

    access = analyze_access(
        results
    )

    api = analyze_api(
        results
    )

    mcp = analyze_mcp(
        results
    )

    buildability = (
        analyze_buildability(
            results
        )
    )

    categories = analyze_categories(
        results
    )

    confidence = analyze_confidence(
        results
    )

    evidence = analyze_evidence(
        results
    )

    verification = (
        analyze_verification(
            results
        )
    )

    blockers = analyze_blockers(
        results
    )

    patterns = generate_patterns(
        results
    )

    comparison_records = (
        build_comparison_records(
            results
        )
    )

    ranked_records = rank_records(
        comparison_records
    )

    buildability_ranking = (
        build_buildability_ranking(
            comparison_records
        )
    )

    mcp_ranking = build_mcp_ranking(
        comparison_records
    )

    comparison_matrix = (
        build_comparison_matrix(
            ranked_records
        )
    )

    ranking_insights = (
        generate_ranking_insights(
            ranked_records
        )
    )

    quality_notes = (
        generate_quality_notes(
            results
        )
    )

    return {
        "metadata": {
            "applications_analyzed": total,
            "verification_records_available": (
                verification[
                    "records_available"
                ]
            ),
            "analysis_records_available": sum(
                1
                for result in results
                if isinstance(
                    result.get(
                        "analysis"
                    ),
                    dict,
                )
                and result.get(
                    "analysis"
                )
            ),
            "ranking_method": (
                "Deterministic weighted integration "
                "priority heuristic"
            ),
        },
        "authentication": authentication,
        "access": access,
        "api": api,
        "mcp": mcp,
        "buildability": buildability,
        "categories": categories,
        "confidence": confidence,
        "evidence": evidence,
        "verification": verification,
        "common_blockers": blockers,
        "patterns": patterns,
        "comparison": {
            "overall_ranking": ranked_records,
            "buildability_ranking": (
                buildability_ranking
            ),
            "mcp_ranking": mcp_ranking,
            "matrix": comparison_matrix,
            "insights": ranking_insights,
        },
        "quality_notes": quality_notes,
    }


# ============================================================
# OUTPUT
# ============================================================


def save_analysis(
    analysis: dict,
) -> None:
    """Save analysis JSON."""

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            analysis,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# CLI
# ============================================================


def main() -> None:
    """CLI entry point."""

    print("=" * 70)
    print("CROSS-APP RESEARCH ANALYSIS")
    print("=" * 70)

    results = load_results()

    print(
        f"Applications analyzed: "
        f"{len(results)}"
    )

    if not results:
        print(
            "No research results available."
        )

        return

    analysis = analyze(
        results
    )

    verification = analysis[
        "verification"
    ]

    print(
        f"Verification records: "
        f"{verification['records_available']}"
    )

    print(
        f"Verifier pass rate: "
        f"{verification['pass_rate_percent']:.1f}%"
    )

    print()
    print("PATTERNS")
    print("-" * 70)

    for index, pattern in enumerate(
        analysis["patterns"],
        start=1,
    ):
        print(
            f"{index}. "
            f"{pattern['title']}"
        )

        print(
            f"   {pattern['observation']}"
        )

    print()
    print("INTEGRATION PRIORITY RANKING")
    print("-" * 70)

    for record in analysis[
        "comparison"
    ]["overall_ranking"]:

        print(
            f"{record['rank']:>2}. "
            f"{record['app_name']:<20} "
            f"{record['integration_score']:>6.2f}/100 "
            f"| Buildability: "
            f"{record['buildability']:<9} "
            f"| MCP: "
            f"{record['mcp_status']}"
        )

    print()
    print("RANKING INSIGHTS")
    print("-" * 70)

    for insight in analysis[
        "comparison"
    ]["insights"]:

        print(
            f"- {insight}"
        )

    print()
    print("QUALITY NOTES")
    print("-" * 70)

    for note in analysis[
        "quality_notes"
    ]:

        print(
            f"- {note}"
        )

    save_analysis(
        analysis
    )

    print()
    print("=" * 70)
    print()
    print(
        f"Analysis saved to: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()