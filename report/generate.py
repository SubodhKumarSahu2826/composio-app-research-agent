from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = PROJECT_ROOT / "results"
REPORT_DIR = PROJECT_ROOT / "report"

RESULTS_FILE = RESULTS_DIR / "results.json"
FAILURES_FILE = RESULTS_DIR / "failures.json"
PROGRESS_FILE = RESULTS_DIR / "progress.json"
CROSS_APP_ANALYSIS_FILE = (
    RESULTS_DIR / "cross_app_analysis.json"
)

TEMPLATE_FILE = REPORT_DIR / "template.html"
OUTPUT_FILE = REPORT_DIR / "research_report.html"


def load_json(
    path: Path,
    default: Any,
) -> Any:
    """Load JSON from disk, returning default when absent."""

    if not path.exists():
        return default

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def escape_html(value: Any) -> str:
    """Safely convert arbitrary values into HTML-safe text."""

    if value is None:
        return ""

    return html.escape(
        str(value)
    )


def format_confidence(
    value: Any,
) -> str:
    """Convert a 0-1 confidence value into a percentage."""

    try:
        return f"{float(value) * 100:.0f}%"
    except (
        TypeError,
        ValueError,
    ):
        return "N/A"


def status_class(
    value: str,
) -> str:
    """Return a CSS class for a status/value."""

    normalized = value.lower().strip()

    if normalized in {
        "passed",
        "easy",
        "official mcp",
        "high",
    }:
        return "success"

    if normalized in {
        "possible",
        "moderate",
        "medium",
        "unknown",
        "third-party mcp",
    }:
        return "warning"

    if normalized in {
        "failed",
        "blocked",
        "gated",
        "low",
        "no mcp found",
    }:
        return "danger"

    return "neutral"


def build_evidence_html(
    evidence: list[dict],
) -> str:
    """Render research evidence items."""

    if not evidence:
        return """
        <div class="empty-state">
            No evidence was recorded.
        </div>
        """

    cards: list[str] = []

    for index, item in enumerate(
        evidence,
        start=1,
    ):
        claim = escape_html(
            item.get("claim")
        )

        url = escape_html(
            item.get("url")
        )

        source_name = escape_html(
            item.get("source_name")
        )

        source_type = escape_html(
            item.get("source_type")
        )

        snippet = escape_html(
            item.get("snippet")
        )

        snippet_html = (
            f"""
            <p class="snippet">
                {snippet}
            </p>
            """
            if snippet
            else ""
        )

        source_link_html = (
            f"""
            <a
                class="source-link"
                href="{url}"
                target="_blank"
                rel="noopener noreferrer"
            >
                Open source
            </a>
            """
            if url
            else ""
        )

        cards.append(
            f"""
            <article class="evidence-card">

                <div class="evidence-header">

                    <span class="evidence-number">
                        Evidence {index}
                    </span>

                    <span class="badge neutral">
                        {source_type}
                    </span>

                </div>

                <h4>
                    {source_name or "Unnamed source"}
                </h4>

                <p class="claim">
                    {claim}
                </p>

                {snippet_html}

                {source_link_html}

            </article>
            """
        )

    return "\n".join(cards)


def build_requirements_html(
    requirements: list[str],
) -> str:
    """Render access requirements."""

    if not requirements:
        return (
            '<span class="muted">'
            "None specified"
            "</span>"
        )

    items = []

    for requirement in requirements:
        items.append(
            f"<li>{escape_html(requirement)}</li>"
        )

    return (
        "<ul>"
        + "".join(items)
        + "</ul>"
    )


def build_list_html(
    items: list[str],
) -> str:
    """Render a generic list."""

    if not items:
        return (
            '<span class="muted">'
            "None"
            "</span>"
        )

    return (
        "<ul>"
        + "".join(
            f"<li>{escape_html(item)}</li>"
            for item in items
        )
        + "</ul>"
    )


def normalize_results(
    raw_results: Any,
) -> list[dict]:
    """
    Normalize results.json into a list.

    Supports:
        - JSON list
        - {"results": [...]}
        - single AppResearch object
    """

    if isinstance(
        raw_results,
        list,
    ):
        return [
            item
            for item in raw_results
            if isinstance(
                item,
                dict,
            )
        ]

    if isinstance(
        raw_results,
        dict,
    ):
        results = raw_results.get(
            "results"
        )

        if isinstance(
            results,
            list,
        ):
            return [
                item
                for item in results
                if isinstance(
                    item,
                    dict,
                )
            ]

        if "app_id" in raw_results:
            return [raw_results]

    return []


def calculate_statistics(
    results: list[dict],
    failures: list[dict],
) -> dict[str, Any]:
    """Calculate report-level statistics."""

    total = (
        len(results)
        + len(failures)
    )

    verified = 0
    verification_failed = 0

    quality_scores: list[float] = []

    buildability_counts: dict[
        str,
        int,
    ] = {}

    for result in results:

        verification = result.get(
            "verification",
            {},
        )

        if isinstance(
            verification,
            dict,
        ):
            if verification.get(
                "passed"
            ) is True:
                verified += 1
            elif verification.get(
                "passed"
            ) is False:
                verification_failed += 1

        analysis = result.get(
            "analysis",
            {},
        )

        if isinstance(
            analysis,
            dict,
        ):
            quality_score = analysis.get(
                "quality_score"
            )

            if isinstance(
                quality_score,
                (int, float),
            ):
                quality_scores.append(
                    float(
                        quality_score
                    )
                )

        buildability = result.get(
            "buildability",
            {},
        )

        if isinstance(
            buildability,
            dict,
        ):
            verdict = buildability.get(
                "verdict",
                "Unknown",
            )
        else:
            verdict = "Unknown"

        buildability_counts[
            verdict
        ] = (
            buildability_counts.get(
                verdict,
                0,
            )
            + 1
        )

    average_quality = (
        sum(quality_scores)
        / len(quality_scores)
        if quality_scores
        else 0.0
    )

    return {
        "total": total,
        "completed": len(results),
        "failed": len(failures),
        "verified": verified,
        "verification_failed": (
            verification_failed
        ),
        "average_quality": (
            average_quality
        ),
        "buildability_counts": (
            buildability_counts
        ),
    }


def build_application_html(
    result: dict,
) -> str:
    """Render one application research result."""

    app_name = escape_html(
        result.get(
            "app_name",
            "Unknown application",
        )
    )

    category = escape_html(
        result.get(
            "category",
            "Unknown",
        )
    )

    description = escape_html(
        result.get(
            "description",
            "",
        )
    )

    authentication = result.get(
        "authentication",
        {},
    )

    if not isinstance(
        authentication,
        dict,
    ):
        authentication = {}

    auth_methods = authentication.get(
        "methods",
        [],
    )

    auth_confidence = format_confidence(
        authentication.get(
            "confidence"
        )
    )

    access = result.get(
        "access",
        {},
    )

    if not isinstance(
        access,
        dict,
    ):
        access = {}

    access_type = escape_html(
        access.get(
            "type",
            "Unknown",
        )
    )

    access_confidence = format_confidence(
        access.get(
            "confidence"
        )
    )

    requirements = access.get(
        "requirements",
        [],
    )

    api = result.get(
        "api",
        {},
    )

    if not isinstance(
        api,
        dict,
    ):
        api = {}

    api_type = escape_html(
        api.get(
            "type",
            "Unknown",
        )
    )

    api_breadth = escape_html(
        api.get(
            "breadth",
            "Unknown",
        )
    )

    api_documentation = api.get(
        "documentation_url"
    )

    api_confidence = format_confidence(
        api.get(
            "confidence"
        )
    )

    mcp = result.get(
        "mcp",
        {},
    )

    if not isinstance(
        mcp,
        dict,
    ):
        mcp = {}

    mcp_status = escape_html(
        mcp.get(
            "status",
            "Unknown",
        )
    )

    mcp_official = mcp.get(
        "official"
    )

    mcp_url = mcp.get(
        "url"
    )

    mcp_confidence = format_confidence(
        mcp.get(
            "confidence"
        )
    )

    buildability = result.get(
        "buildability",
        {},
    )

    if not isinstance(
        buildability,
        dict,
    ):
        buildability = {}

    buildability_verdict = escape_html(
        buildability.get(
            "verdict",
            "Unknown",
        )
    )

    blocker = escape_html(
        buildability.get(
            "blocker",
            "",
        )
    )

    reasoning = escape_html(
        buildability.get(
            "reasoning",
            "",
        )
    )

    evidence = result.get(
        "evidence",
        [],
    )

    if not isinstance(
        evidence,
        list,
    ):
        evidence = []

    verification = result.get(
        "verification",
        {},
    )

    if not isinstance(
        verification,
        dict,
    ):
        verification = {}

    verification_passed = verification.get(
        "passed"
    )

    verification_score = verification.get(
        "score"
    )

    verification_errors = verification.get(
        "errors",
        [],
    )

    verification_warnings = verification.get(
        "warnings",
        [],
    )

    analysis = result.get(
        "analysis",
        {},
    )

    if not isinstance(
        analysis,
        dict,
    ):
        analysis = {}

    quality_score = analysis.get(
        "quality_score"
    )

    confidence_level = escape_html(
        analysis.get(
            "confidence_level",
            "Unknown",
        )
    )

    evidence_coverage = escape_html(
        analysis.get(
            "evidence_coverage",
            "Unknown",
        )
    )

    strengths = analysis.get(
        "strengths",
        [],
    )

    analysis_warnings = analysis.get(
        "warnings",
        [],
    )

    verification_badge_class = (
        "success"
        if verification_passed is True
        else "danger"
        if verification_passed is False
        else "neutral"
    )

    verification_label = (
        "PASSED"
        if verification_passed is True
        else "FAILED"
        if verification_passed is False
        else "N/A"
    )

    quality_score_html = (
        f"{float(quality_score):.1f}/100"
        if isinstance(
            quality_score,
            (int, float),
        )
        else "N/A"
    )

    verification_score_html = (
        f"{float(verification_score):.2f}"
        if isinstance(
            verification_score,
            (int, float),
        )
        else "N/A"
    )

    auth_methods_html = (
        escape_html(
            ", ".join(
                str(item)
                for item in auth_methods
            )
        )
        if auth_methods
        else "Unknown"
    )

    api_documentation_html = (
        f"""
        <a
            class="source-link"
            href="{escape_html(api_documentation)}"
            target="_blank"
            rel="noopener noreferrer"
        >
            API documentation
        </a>
        """
        if api_documentation
        else ""
    )

    mcp_url_html = (
        f"""
        <a
            class="source-link"
            href="{escape_html(mcp_url)}"
            target="_blank"
            rel="noopener noreferrer"
        >
            MCP documentation
        </a>
        """
        if mcp_url
        else ""
    )

    blocker_html = (
        f"""
        <div class="field">
            <span>Blocker</span>
            <strong>{blocker}</strong>
        </div>
        """
        if blocker
        else ""
    )

    verification_errors_html = (
        f"""
        <div class="issue-section">
            <h4>Errors</h4>
            {build_list_html(
                verification_errors
            )}
        </div>
        """
        if verification_errors
        else """
        <p class="muted">
            No verification errors.
        </p>
        """
    )

    verification_warnings_html = (
        f"""
        <div class="issue-section">
            <h4>Warnings</h4>
            {build_list_html(
                verification_warnings
            )}
        </div>
        """
        if verification_warnings
        else """
        <p class="muted">
            No verification warnings.
        </p>
        """
    )

    strengths_html = (
        f"""
        <div class="issue-section">
            <h4>Strengths</h4>
            {build_list_html(strengths)}
        </div>
        """
        if strengths
        else ""
    )

    analysis_warnings_html = (
        f"""
        <div class="issue-section">
            <h4>Warnings</h4>
            {build_list_html(
                analysis_warnings
            )}
        </div>
        """
        if analysis_warnings
        else ""
    )

    return f"""
    <section class="application-card">

        <div class="application-header">

            <div>

                <div class="eyebrow">
                    {category}
                </div>

                <h2>
                    {app_name}
                </h2>

                <p class="description">
                    {description}
                </p>

            </div>

            <div class="application-id">
                App ID:
                {escape_html(
                    result.get("app_id")
                )}
            </div>

        </div>

        <div class="metrics-grid">

            <div class="metric">

                <span class="metric-label">
                    Buildability
                </span>

                <span class="badge {
                    status_class(
                        buildability_verdict
                    )
                }">
                    {buildability_verdict}
                </span>

            </div>

            <div class="metric">

                <span class="metric-label">
                    Verification
                </span>

                <span class="badge {
                    verification_badge_class
                }">
                    {verification_label}
                </span>

            </div>

            <div class="metric">

                <span class="metric-label">
                    Quality Score
                </span>

                <strong>
                    {quality_score_html}
                </strong>

            </div>

            <div class="metric">

                <span class="metric-label">
                    Evidence
                </span>

                <strong>
                    {len(evidence)}
                </strong>

            </div>

        </div>

        <div class="two-column">

            <div class="panel">

                <h3>
                    Authentication
                </h3>

                <div class="field">
                    <span>Methods</span>
                    <strong>
                        {auth_methods_html}
                    </strong>
                </div>

                <div class="field">
                    <span>Confidence</span>
                    <strong>
                        {auth_confidence}
                    </strong>
                </div>

            </div>

            <div class="panel">

                <h3>
                    Access
                </h3>

                <div class="field">
                    <span>Type</span>
                    <strong>
                        {access_type}
                    </strong>
                </div>

                <div class="field">
                    <span>Confidence</span>
                    <strong>
                        {access_confidence}
                    </strong>
                </div>

                <div class="requirements">
                    <span>
                        Requirements
                    </span>

                    {
                        build_requirements_html(
                            requirements
                        )
                    }

                </div>

            </div>

        </div>

        <div class="two-column">

            <div class="panel">

                <h3>
                    API
                </h3>

                <div class="field">
                    <span>Type</span>
                    <strong>
                        {api_type}
                    </strong>
                </div>

                <div class="field">
                    <span>Breadth</span>
                    <strong>
                        {api_breadth}
                    </strong>
                </div>

                <div class="field">
                    <span>Confidence</span>
                    <strong>
                        {api_confidence}
                    </strong>
                </div>

                {api_documentation_html}

            </div>

            <div class="panel">

                <h3>
                    MCP
                </h3>

                <div class="field">
                    <span>Status</span>

                    <span class="badge {
                        status_class(
                            mcp_status
                        )
                    }">
                        {mcp_status}
                    </span>

                </div>

                <div class="field">
                    <span>Official</span>

                    <strong>
                        {
                            "Yes"
                            if mcp_official is True
                            else "No"
                            if mcp_official is False
                            else "Unknown"
                        }
                    </strong>

                </div>

                <div class="field">
                    <span>Confidence</span>

                    <strong>
                        {mcp_confidence}
                    </strong>

                </div>

                {mcp_url_html}

            </div>

        </div>

        <div class="panel buildability-panel">

            <h3>
                Buildability Assessment
            </h3>

            {blocker_html}

            <p>
                {
                    reasoning
                    or
                    "No reasoning provided."
                }
            </p>

        </div>

        <div class="panel">

            <h3>
                Verification
            </h3>

            <div class="field">
                <span>Score</span>

                <strong>
                    {verification_score_html}
                </strong>
            </div>

            {verification_errors_html}

            {verification_warnings_html}

        </div>

        <div class="panel">

            <h3>
                Research Quality
            </h3>

            <div class="two-column compact">

                <div class="field">
                    <span>Confidence</span>

                    <strong>
                        {confidence_level}
                    </strong>
                </div>

                <div class="field">
                    <span>Evidence Coverage</span>

                    <strong>
                        {evidence_coverage}
                    </strong>
                </div>

            </div>

            {strengths_html}

            {analysis_warnings_html}

        </div>

        <div class="panel">

            <h3>
                Evidence
            </h3>

            <div class="evidence-list">
                {
                    build_evidence_html(
                        evidence
                    )
                }
            </div>

        </div>

    </section>
    """


# =============================================================
# CROSS-APP ANALYSIS
# =============================================================


def build_counter_html(
    counts: dict[str, Any],
) -> str:
    """Render a counter dictionary."""

    if not counts:
        return (
            '<span class="muted">'
            "No data"
            "</span>"
        )

    items: list[str] = []

    for label, count in counts.items():

        safe_label = escape_html(
            label
        )

        safe_count = escape_html(
            count
        )

        items.append(
            f"""
            <div class="analysis-stat-row">

                <span>
                    {safe_label}
                </span>

                <strong>
                    {safe_count}
                </strong>

            </div>
            """
        )

    return "".join(items)


def build_percentage_html(
    percentages: dict[str, Any],
) -> str:
    """Render percentage distributions."""

    if not percentages:
        return (
            '<span class="muted">'
            "No data"
            "</span>"
        )

    items: list[str] = []

    for label, percentage in percentages.items():

        safe_label = escape_html(
            label
        )

        try:
            percentage_text = (
                f"{float(percentage):.2f}%"
            )
        except (
            TypeError,
            ValueError,
        ):
            percentage_text = "N/A"

        items.append(
            f"""
            <div class="analysis-stat-row">

                <span>
                    {safe_label}
                </span>

                <strong>
                    {percentage_text}
                </strong>

            </div>
            """
        )

    return "".join(items)


def build_patterns_html(
    patterns: list[dict],
) -> str:
    """Render derived cross-app patterns."""

    if not patterns:
        return """
        <div class="empty-state">
            No cross-app patterns available.
        </div>
        """

    cards: list[str] = []

    for index, pattern in enumerate(
        patterns,
        start=1,
    ):
        title = escape_html(
            pattern.get(
                "title",
                "Pattern",
            )
        )

        observation = escape_html(
            pattern.get(
                "observation",
                "",
            )
        )

        sample_size = escape_html(
            pattern.get(
                "sample_size",
                "",
            )
        )

        scope = escape_html(
            pattern.get(
                "scope",
                "",
            )
        )

        cards.append(
            f"""
            <article class="pattern-card">

                <div class="pattern-number">
                    {index}
                </div>

                <div>

                    <h4>
                        {title}
                    </h4>

                    <p>
                        {observation}
                    </p>

                    <span class="pattern-scope">
                        {scope}
                        {
                            f" · Sample size: {sample_size}"
                            if sample_size
                            else ""
                        }
                    </span>

                </div>

            </article>
            """
        )

    return "".join(cards)


def build_verification_records_html(
    records: list[dict],
) -> str:
    """Render cross-app verification records."""

    if not records:
        return """
        <div class="empty-state">
            No verification records available.
        </div>
        """

    rows: list[str] = []

    for record in records:

        app_name = escape_html(
            record.get(
                "app_name",
                "Unknown",
            )
        )

        passed = record.get(
            "passed"
        )

        score = record.get(
            "score"
        )

        if passed is True:
            badge = (
                '<span class="badge success">'
                "PASSED"
                "</span>"
            )
        elif passed is False:
            badge = (
                '<span class="badge danger">'
                "FAILED"
                "</span>"
            )
        else:
            badge = (
                '<span class="badge neutral">'
                "N/A"
                "</span>"
            )

        score_text = (
            f"{float(score):.2f}"
            if isinstance(
                score,
                (int, float),
            )
            else "N/A"
        )

        rows.append(
            f"""
            <tr>

                <td>
                    {app_name}
                </td>

                <td>
                    {badge}
                </td>

                <td>
                    {score_text}
                </td>

            </tr>
            """
        )

    return f"""
    <div class="table-wrapper">

        <table class="analysis-table">

            <thead>

                <tr>
                    <th>Application</th>
                    <th>Status</th>
                    <th>Score</th>
                </tr>

            </thead>

            <tbody>
                {"".join(rows)}
            </tbody>

        </table>

    </div>
    """


def build_cross_app_analysis_html(
    analysis: dict,
) -> str:
    """Render the cross-application analysis section."""

    if not analysis:
        return """
        <section class="cross-app-section">

            <div class="section-heading">
                <div>
                    <div class="eyebrow">
                        Aggregate Research
                    </div>

                    <h2>
                        Cross-App Analysis
                    </h2>
                </div>
            </div>

            <div class="empty-state large">
                Cross-app analysis has not been generated yet.
            </div>

        </section>
        """

    metadata = analysis.get(
        "metadata",
        {},
    )

    authentication = analysis.get(
        "authentication",
        {},
    )

    access = analysis.get(
        "access",
        {},
    )

    api = analysis.get(
        "api",
        {},
    )

    mcp = analysis.get(
        "mcp",
        {},
    )

    buildability = analysis.get(
        "buildability",
        {},
    )

    categories = analysis.get(
        "categories",
        {},
    )

    confidence = analysis.get(
        "confidence",
        {},
    )

    evidence = analysis.get(
        "evidence",
        {},
    )

    verification = analysis.get(
        "verification",
        {},
    )

    blockers = analysis.get(
        "common_blockers",
        {},
    )

    patterns = analysis.get(
        "patterns",
        [],
    )

    quality_notes = analysis.get(
        "quality_notes",
        [],
    )

    applications_analyzed = escape_html(
        metadata.get(
            "applications_analyzed",
            0,
        )
    )

    verification_records = escape_html(
        metadata.get(
            "verification_records_available",
            0,
        )
    )

    average_confidence = confidence.get(
        "average"
    )

    average_confidence_text = (
        f"{float(average_confidence) * 100:.1f}%"
        if isinstance(
            average_confidence,
            (int, float),
        )
        else "N/A"
    )

    total_evidence = escape_html(
        evidence.get(
            "total_evidence_items",
            0,
        )
    )

    average_evidence = escape_html(
        evidence.get(
            "average_evidence_per_app",
            0,
        )
    )

    pass_rate = escape_html(
        verification.get(
            "pass_rate_percent",
            0,
        )
    )

    return f"""
    <section class="cross-app-section">

        <div class="section-heading">

            <div>

                <div class="eyebrow">
                    Aggregate Research
                </div>

                <h2>
                    Cross-App Analysis
                </h2>

                <p class="section-description">
                    Deterministic aggregate analysis of the
                    completed application research sample.
                </p>

            </div>

        </div>

        <div class="analysis-notice">

            <strong>
                Sample scope
            </strong>

            <span>
                This analysis covers
                {applications_analyzed}
                completed applications.
                It should not be generalized to the
                full 100-app dataset until the remaining
                applications have been researched.
            </span>

        </div>

        <div class="analysis-overview-grid">

            <div class="analysis-overview-card">

                <span>
                    Applications
                </span>

                <strong>
                    {applications_analyzed}
                </strong>

            </div>

            <div class="analysis-overview-card">

                <span>
                    Evidence Items
                </span>

                <strong>
                    {total_evidence}
                </strong>

            </div>

            <div class="analysis-overview-card">

                <span>
                    Avg. Evidence / App
                </span>

                <strong>
                    {average_evidence}
                </strong>

            </div>

            <div class="analysis-overview-card">

                <span>
                    Avg. Confidence
                </span>

                <strong>
                    {average_confidence_text}
                </strong>

            </div>

            <div class="analysis-overview-card">

                <span>
                    Verification Pass Rate
                </span>

                <strong>
                    {pass_rate}%
                </strong>

            </div>

            <div class="analysis-overview-card">

                <span>
                    Verification Records
                </span>

                <strong>
                    {verification_records}
                </strong>

            </div>

        </div>

        <div class="analysis-grid">

            <div class="analysis-panel">

                <h3>
                    Authentication Methods
                </h3>

                <div class="analysis-columns">

                    <div>

                        <h4>
                            Counts
                        </h4>

                        {
                            build_counter_html(
                                authentication.get(
                                    "method_counts",
                                    {},
                                )
                            )
                        }

                    </div>

                    <div>

                        <h4>
                            Percentage of Apps
                        </h4>

                        {
                            build_percentage_html(
                                authentication.get(
                                    "method_percentages",
                                    {},
                                )
                            )
                        }

                    </div>

                </div>

            </div>

            <div class="analysis-panel">

                <h3>
                    API Types
                </h3>

                <div class="analysis-columns">

                    <div>

                        <h4>
                            Counts
                        </h4>

                        {
                            build_counter_html(
                                api.get(
                                    "type_counts",
                                    {},
                                )
                            )
                        }

                    </div>

                    <div>

                        <h4>
                            Percentage
                        </h4>

                        {
                            build_percentage_html(
                                api.get(
                                    "type_percentages",
                                    {},
                                )
                            )
                        }

                    </div>

                </div>

            </div>

            <div class="analysis-panel">

                <h3>
                    MCP Status
                </h3>

                <div class="analysis-columns">

                    <div>

                        <h4>
                            Counts
                        </h4>

                        {
                            build_counter_html(
                                mcp.get(
                                    "status_counts",
                                    {},
                                )
                            )
                        }

                    </div>

                    <div>

                        <h4>
                            Percentage
                        </h4>

                        {
                            build_percentage_html(
                                mcp.get(
                                    "status_percentages",
                                    {},
                                )
                            )
                        }

                    </div>

                </div>

            </div>

            <div class="analysis-panel">

                <h3>
                    Buildability
                </h3>

                <div class="analysis-columns">

                    <div>

                        <h4>
                            Counts
                        </h4>

                        {
                            build_counter_html(
                                buildability.get(
                                    "verdict_counts",
                                    {},
                                )
                            )
                        }

                    </div>

                    <div>

                        <h4>
                            Percentage
                        </h4>

                        {
                            build_percentage_html(
                                buildability.get(
                                    "verdict_percentages",
                                    {},
                                )
                            )
                        }

                    </div>

                </div>

            </div>

            <div class="analysis-panel">

                <h3>
                    Access Requirements
                </h3>

                {
                    build_counter_html(
                        access.get(
                            "type_counts",
                            {},
                        )
                    )
                }

            </div>

            <div class="analysis-panel">

                <h3>
                    Categories
                </h3>

                {
                    build_counter_html(
                        categories.get(
                            "category_counts",
                            {},
                        )
                    )
                }

            </div>

        </div>

        <div class="analysis-panel">

            <h3>
                Derived Cross-App Patterns
            </h3>

            <div class="patterns-list">

                {
                    build_patterns_html(
                        patterns
                    )
                }

            </div>

        </div>

        <div class="analysis-panel">

            <h3>
                Deterministic Verification
            </h3>

            <p class="muted">
                Verifier scores measure deterministic
                consistency checks. They are not independent
                measurements of factual accuracy.
            </p>

            {
                build_verification_records_html(
                    verification.get(
                        "records",
                        [],
                    )
                )
            }

        </div>

        <div class="analysis-panel">

            <h3>
                Common Buildability Blockers
            </h3>

            {
                build_counter_html(
                    blockers.get(
                        "blocker_counts",
                        {},
                    )
                )
            }

        </div>

        <div class="analysis-panel">

            <h3>
                Research Quality Notes
            </h3>

            {
                build_list_html(
                    quality_notes
                )
            }

        </div>

    </section>
    """


def generate_report(
    results_path: Path = RESULTS_FILE,
    failures_path: Path = FAILURES_FILE,
    template_path: Path = TEMPLATE_FILE,
    output_path: Path = OUTPUT_FILE,
    cross_app_analysis_path: Path = (
        CROSS_APP_ANALYSIS_FILE
    ),
) -> Path:
    """
    Generate the HTML research report.

    This function is deterministic and performs no network
    or LLM calls.
    """

    raw_results = load_json(
        results_path,
        [],
    )

    raw_failures = load_json(
        failures_path,
        [],
    )

    cross_app_analysis = load_json(
        cross_app_analysis_path,
        {},
    )

    results = normalize_results(
        raw_results
    )

    failures = (
        raw_failures
        if isinstance(
            raw_failures,
            list,
        )
        else []
    )

    if not isinstance(
        cross_app_analysis,
        dict,
    ):
        cross_app_analysis = {}

    template = template_path.read_text(
        encoding="utf-8"
    )

    statistics = calculate_statistics(
        results=results,
        failures=failures,
    )

    buildability_counts = statistics[
        "buildability_counts"
    ]

    buildability_html = (
        "".join(
            f"""
            <span class="distribution-item">

                <span class="badge {
                    status_class(verdict)
                }">
                    {escape_html(verdict)}
                </span>

                <strong>
                    {count}
                </strong>

            </span>
            """
            for verdict, count
            in sorted(
                buildability_counts.items()
            )
        )
        or
        '<span class="muted">No data</span>'
    )

    applications_html = (
        "\n".join(
            build_application_html(
                result
            )
            for result in results
        )
        or
        """
        <div class="empty-state large">
            No completed research results are available.
        </div>
        """
    )

    cross_app_html = (
        build_cross_app_analysis_html(
            cross_app_analysis
        )
    )

    failure_html = ""

    if failures:

        failure_items = []

        for failure in failures:

            app_id = escape_html(
                failure.get(
                    "app_id"
                )
            )

            app_name = escape_html(
                failure.get(
                    "app_name"
                )
            )

            error = escape_html(
                failure.get(
                    "error"
                )
            )

            failure_items.append(
                f"""
                <div class="failure-card">

                    <strong>
                        {
                            app_name
                            or
                            "Unknown application"
                        }
                    </strong>

                    <span>
                        App ID: {app_id}
                    </span>

                    <p>
                        {
                            error
                            or
                            "Unknown error"
                        }
                    </p>

                </div>
                """
            )

        failure_html = f"""
        <section class="failures-section">

            <h2>
                Failed Applications
            </h2>

            {"".join(failure_items)}

        </section>
        """

    html_output = template

    replacements = {
        "{{TOTAL_APPS}}": str(
            statistics["total"]
        ),
        "{{COMPLETED_APPS}}": str(
            statistics["completed"]
        ),
        "{{FAILED_APPS}}": str(
            statistics["failed"]
        ),
        "{{VERIFIED_APPS}}": str(
            statistics["verified"]
        ),
        "{{VERIFICATION_FAILED}}": str(
            statistics[
                "verification_failed"
            ]
        ),
        "{{AVERAGE_QUALITY}}": (
            f"{statistics['average_quality']:.1f}"
        ),
        "{{BUILDABILITY_DISTRIBUTION}}": (
            buildability_html
        ),
        "{{CROSS_APP_ANALYSIS}}": (
            cross_app_html
        ),
        "{{APPLICATIONS}}": (
            applications_html
        ),
        "{{FAILURES}}": (
            failure_html
        ),
    }

    for placeholder, value in replacements.items():
        html_output = html_output.replace(
            placeholder,
            value,
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        html_output,
        encoding="utf-8",
    )

    return output_path


def main() -> None:
    """CLI entry point."""

    print("=" * 70)
    print("RESEARCH REPORT GENERATOR")
    print("=" * 70)

    if not RESULTS_FILE.exists():
        print(
            f"Results file not found: "
            f"{RESULTS_FILE}"
        )

        print(
            "Run the research pipeline first."
        )

        return

    output = generate_report()

    print(
        f"Report generated: {output}"
    )


if __name__ == "__main__":
    main()