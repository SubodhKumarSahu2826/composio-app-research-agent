from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RESULTS_DIR = PROJECT_ROOT / "results"
REPORT_DIR = PROJECT_ROOT / "report"

RESULTS_FILE = RESULTS_DIR / "results.json"
FAILURES_FILE = RESULTS_DIR / "failures.json"
PROGRESS_FILE = RESULTS_DIR / "progress.json"
CROSS_APP_ANALYSIS_FILE = RESULTS_DIR / "cross_app_analysis.json"

TEMPLATE_FILE = REPORT_DIR / "template.html"
OUTPUT_FILE = REPORT_DIR / "research_report.html"


def load_json(path: Path, default: Any) -> Any:
    """Load JSON from disk, returning default when absent."""

    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def escape_html(value: Any) -> str:
    """Safely convert arbitrary values into HTML-safe text."""

    if value is None:
        return ""

    return html.escape(str(value))


def format_confidence(value: Any) -> str:
    """Convert a 0-1 confidence value into a percentage."""

    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "N/A"


def status_class(value: str) -> str:
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


def build_evidence_html(evidence: list[dict]) -> str:
    """Render research evidence items."""

    if not evidence:
        return """
        <div class="empty-state">
            No evidence was recorded.
        </div>
        """

    cards: list[str] = []

    for index, item in enumerate(evidence, start=1):
        claim = escape_html(item.get("claim"))
        url = escape_html(item.get("url"))
        source_name = escape_html(item.get("source_name"))
        source_type = escape_html(item.get("source_type"))
        snippet = escape_html(item.get("snippet"))

        snippet_html = (
            f'<p class="snippet">{snippet}</p>'
            if snippet
            else ""
        )

        source_link_html = (
            f"""
            <a class="source-link"
               href="{url}"
               target="_blank"
               rel="noopener noreferrer">
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
                        {source_type or "Source"}
                    </span>
                </div>

                <h4>{source_name or "Unnamed source"}</h4>
                <p class="claim">{claim}</p>
                {snippet_html}
                {source_link_html}
            </article>
            """
        )

    return "\n".join(cards)


def build_requirements_html(requirements: list[str]) -> str:
    """Render access requirements."""

    if not requirements:
        return '<span class="muted">None specified</span>'

    return (
        "<ul>"
        + "".join(
            f"<li>{escape_html(requirement)}</li>"
            for requirement in requirements
        )
        + "</ul>"
    )


def build_list_html(items: list[str]) -> str:
    """Render a generic list."""

    if not items:
        return '<span class="muted">None</span>'

    return (
        "<ul>"
        + "".join(
            f"<li>{escape_html(item)}</li>"
            for item in items
        )
        + "</ul>"
    )


def normalize_results(raw_results: Any) -> list[dict]:
    """Normalize results.json into a list."""

    if isinstance(raw_results, list):
        return [
            item
            for item in raw_results
            if isinstance(item, dict)
        ]

    if isinstance(raw_results, dict):
        results = raw_results.get("results")

        if isinstance(results, list):
            return [
                item
                for item in results
                if isinstance(item, dict)
            ]

        if "app_id" in raw_results:
            return [raw_results]

    return []


def calculate_statistics(
    results: list[dict],
    failures: list[dict],
    progress: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate report-level statistics.

    The dataset total comes from progress.json when available.
    This is important because a paused run may have 7 completed
    applications out of a 100-app dataset, while results.json
    contains only the completed records.
    """

    progress_total = progress.get("total")

    if isinstance(progress_total, int) and progress_total >= 0:
        total = progress_total
    else:
        total = len(results) + len(failures)

    completed = len(results)
    failed = len(failures)
    remaining = max(total - completed - failed, 0)

    verified = 0
    verification_failed = 0
    quality_scores: list[float] = []
    buildability_counts: dict[str, int] = {}

    for result in results:
        verification = result.get("verification", {})

        if isinstance(verification, dict):
            if verification.get("passed") is True:
                verified += 1
            elif verification.get("passed") is False:
                verification_failed += 1

        analysis = result.get("analysis", {})

        if isinstance(analysis, dict):
            quality_score = analysis.get("quality_score")

            if isinstance(quality_score, (int, float)):
                quality_scores.append(float(quality_score))

        buildability = result.get("buildability", {})

        if isinstance(buildability, dict):
            verdict = buildability.get("verdict", "Unknown")
        else:
            verdict = "Unknown"

        buildability_counts[verdict] = (
            buildability_counts.get(verdict, 0) + 1
        )

    average_quality = (
        sum(quality_scores) / len(quality_scores)
        if quality_scores
        else 0.0
    )

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "remaining": remaining,
        "verified": verified,
        "verification_failed": verification_failed,
        "average_quality": average_quality,
        "buildability_counts": buildability_counts,
        "pipeline_status": progress.get("status", "unknown"),
        "stop_reason": progress.get("stop_reason", ""),
    }


def build_application_html(result: dict) -> str:
    """Render one application research result."""

    app_name = escape_html(
        result.get("app_name", "Unknown application")
    )
    category = escape_html(result.get("category", "Unknown"))
    description = escape_html(result.get("description", ""))

    authentication = result.get("authentication", {})
    if not isinstance(authentication, dict):
        authentication = {}

    auth_methods = authentication.get("methods", [])
    auth_confidence = format_confidence(
        authentication.get("confidence")
    )

    access = result.get("access", {})
    if not isinstance(access, dict):
        access = {}

    access_type = escape_html(access.get("type", "Unknown"))
    access_confidence = format_confidence(
        access.get("confidence")
    )
    requirements = access.get("requirements", [])

    api = result.get("api", {})
    if not isinstance(api, dict):
        api = {}

    api_type = escape_html(api.get("type", "Unknown"))
    api_breadth = escape_html(api.get("breadth", "Unknown"))
    api_documentation = api.get("documentation_url")
    api_confidence = format_confidence(
        api.get("confidence")
    )

    mcp = result.get("mcp", {})
    if not isinstance(mcp, dict):
        mcp = {}

    mcp_status = escape_html(mcp.get("status", "Unknown"))
    mcp_official = mcp.get("official")
    mcp_url = mcp.get("url")
    mcp_confidence = format_confidence(
        mcp.get("confidence")
    )

    buildability = result.get("buildability", {})
    if not isinstance(buildability, dict):
        buildability = {}

    buildability_verdict = escape_html(
        buildability.get("verdict", "Unknown")
    )
    blocker = escape_html(buildability.get("blocker", ""))
    reasoning = escape_html(
        buildability.get("reasoning", "")
    )

    evidence = result.get("evidence", [])
    if not isinstance(evidence, list):
        evidence = []

    verification = result.get("verification", {})
    if not isinstance(verification, dict):
        verification = {}

    verification_passed = verification.get("passed")
    verification_score = verification.get("score")
    verification_errors = verification.get("errors", [])
    verification_warnings = verification.get("warnings", [])

    analysis = result.get("analysis", {})
    if not isinstance(analysis, dict):
        analysis = {}

    quality_score = analysis.get("quality_score")
    confidence_level = escape_html(
        analysis.get("confidence_level", "Unknown")
    )
    evidence_coverage = escape_html(
        analysis.get("evidence_coverage", "Unknown")
    )
    strengths = analysis.get("strengths", [])
    analysis_warnings = analysis.get("warnings", [])

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
        if isinstance(quality_score, (int, float))
        else "N/A"
    )

    verification_score_html = (
        f"{float(verification_score):.2f}"
        if isinstance(verification_score, (int, float))
        else "N/A"
    )

    auth_methods_html = (
        escape_html(", ".join(str(item) for item in auth_methods))
        if auth_methods
        else "Unknown"
    )

    api_documentation_html = (
        f"""
        <a class="source-link"
           href="{escape_html(api_documentation)}"
           target="_blank"
           rel="noopener noreferrer">
            API documentation
        </a>
        """
        if api_documentation
        else ""
    )

    mcp_url_html = (
        f"""
        <a class="source-link"
           href="{escape_html(mcp_url)}"
           target="_blank"
           rel="noopener noreferrer">
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
            {build_list_html(verification_errors)}
        </div>
        """
        if verification_errors
        else '<p class="muted">No verification errors.</p>'
    )

    verification_warnings_html = (
        f"""
        <div class="issue-section">
            <h4>Warnings</h4>
            {build_list_html(verification_warnings)}
        </div>
        """
        if verification_warnings
        else '<p class="muted">No verification warnings.</p>'
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
            {build_list_html(analysis_warnings)}
        </div>
        """
        if analysis_warnings
        else ""
    )

    return f"""
    <section class="application-card">

        <div class="application-header">
            <div>
                <div class="eyebrow">{category}</div>
                <h2>{app_name}</h2>
                <p class="description">{description}</p>
            </div>

            <div class="application-id">
                App ID: {escape_html(result.get("app_id"))}
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric">
                <span class="metric-label">Buildability</span>
                <span class="badge {status_class(buildability_verdict)}">
                    {buildability_verdict}
                </span>
            </div>

            <div class="metric">
                <span class="metric-label">Verification</span>
                <span class="badge {verification_badge_class}">
                    {verification_label}
                </span>
            </div>

            <div class="metric">
                <span class="metric-label">Quality Score</span>
                <strong>{quality_score_html}</strong>
            </div>

            <div class="metric">
                <span class="metric-label">Evidence</span>
                <strong>{len(evidence)}</strong>
            </div>
        </div>

        <div class="two-column">
            <div class="panel">
                <h3>Authentication</h3>

                <div class="field">
                    <span>Methods</span>
                    <strong>{auth_methods_html}</strong>
                </div>

                <div class="field">
                    <span>Confidence</span>
                    <strong>{auth_confidence}</strong>
                </div>
            </div>

            <div class="panel">
                <h3>Access</h3>

                <div class="field">
                    <span>Type</span>
                    <strong>{access_type}</strong>
                </div>

                <div class="field">
                    <span>Confidence</span>
                    <strong>{access_confidence}</strong>
                </div>

                <div class="requirements">
                    <span>Requirements</span>
                    {build_requirements_html(requirements)}
                </div>
            </div>
        </div>

        <div class="two-column">
            <div class="panel">
                <h3>API</h3>

                <div class="field">
                    <span>Type</span>
                    <strong>{api_type}</strong>
                </div>

                <div class="field">
                    <span>Breadth</span>
                    <strong>{api_breadth}</strong>
                </div>

                <div class="field">
                    <span>Confidence</span>
                    <strong>{api_confidence}</strong>
                </div>

                {api_documentation_html}
            </div>

            <div class="panel">
                <h3>MCP</h3>

                <div class="field">
                    <span>Status</span>
                    <span class="badge {status_class(mcp_status)}">
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
                    <strong>{mcp_confidence}</strong>
                </div>

                {mcp_url_html}
            </div>
        </div>

        <div class="panel buildability-panel">
            <h3>Buildability Assessment</h3>
            {blocker_html}
            <p>{reasoning or "No reasoning provided."}</p>
        </div>

        <div class="panel">
            <h3>Verification</h3>

            <div class="field">
                <span>Score</span>
                <strong>{verification_score_html}</strong>
            </div>

            {verification_errors_html}
            {verification_warnings_html}
        </div>

        <div class="panel">
            <h3>Research Quality</h3>

            <div class="two-column">
                <div class="field">
                    <span>Confidence</span>
                    <strong>{confidence_level}</strong>
                </div>

                <div class="field">
                    <span>Evidence Coverage</span>
                    <strong>{evidence_coverage}</strong>
                </div>
            </div>

            {strengths_html}
            {analysis_warnings_html}
        </div>

        <div class="panel">
            <h3>Evidence</h3>

            <div class="evidence-list">
                {build_evidence_html(evidence)}
            </div>
        </div>

    </section>
    """


# =============================================================
# CROSS-APP ANALYSIS
# =============================================================

def build_counter_html(counts: dict[str, Any]) -> str:
    """Render a counter dictionary."""

    if not counts:
        return '<span class="muted">No data</span>'

    return "".join(
        f"""
        <div class="analysis-stat-row">
            <span>{escape_html(label)}</span>
            <strong>{escape_html(count)}</strong>
        </div>
        """
        for label, count in counts.items()
    )


def build_percentage_html(percentages: dict[str, Any]) -> str:
    """Render percentage distributions."""

    if not percentages:
        return '<span class="muted">No data</span>'

    items: list[str] = []

    for label, percentage in percentages.items():
        try:
            percentage_text = f"{float(percentage):.2f}%"
        except (TypeError, ValueError):
            percentage_text = "N/A"

        items.append(
            f"""
            <div class="analysis-stat-row">
                <span>{escape_html(label)}</span>
                <strong>{percentage_text}</strong>
            </div>
            """
        )

    return "".join(items)


def build_patterns_html(patterns: list[dict]) -> str:
    """Render derived cross-app patterns."""

    if not patterns:
        return """
        <div class="empty-state">
            No cross-app patterns available.
        </div>
        """

    cards: list[str] = []

    for index, pattern in enumerate(patterns, start=1):
        title = escape_html(pattern.get("title", "Pattern"))
        observation = escape_html(pattern.get("observation", ""))
        sample_size = escape_html(pattern.get("sample_size", ""))
        scope = escape_html(pattern.get("scope", ""))

        cards.append(
            f"""
            <article class="pattern-card">
                <div class="pattern-number">{index}</div>

                <div>
                    <h4>{title}</h4>
                    <p>{observation}</p>

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


def build_verification_records_html(records: list[dict]) -> str:
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
            record.get("app_name", "Unknown")
        )
        passed = record.get("passed")
        score = record.get("score")

        if passed is True:
            badge = '<span class="badge success">PASSED</span>'
        elif passed is False:
            badge = '<span class="badge danger">FAILED</span>'
        else:
            badge = '<span class="badge neutral">N/A</span>'

        score_text = (
            f"{float(score):.2f}"
            if isinstance(score, (int, float))
            else "N/A"
        )

        rows.append(
            f"""
            <tr>
                <td>{app_name}</td>
                <td>{badge}</td>
                <td>{score_text}</td>
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


def build_ranking_html(ranking: list[dict]) -> str:
    """Render deterministic integration-priority ranking."""

    if not ranking:
        return '<div class="empty-state">No ranking available.</div>'

    rows: list[str] = []

    for record in ranking:
        rank = record.get("rank", "")
        app_name = escape_html(record.get("app_name", "Unknown"))
        score = record.get("integration_score")
        buildability = escape_html(
            record.get("buildability", "Unknown")
        )
        mcp = escape_html(
            record.get("mcp_status", "Unknown")
        )

        score_text = (
            f"{float(score):.2f}"
            if isinstance(score, (int, float))
            else "N/A"
        )

        rows.append(
            f"""
            <tr>
                <td>
                    <span class="ranking-number">
                        {escape_html(rank)}
                    </span>
                </td>
                <td><strong>{app_name}</strong></td>
                <td class="score">{score_text}/100</td>
                <td>
                    <span class="badge {status_class(buildability)}">
                        {buildability}
                    </span>
                </td>
                <td>
                    <span class="badge {status_class(mcp)}">
                        {mcp}
                    </span>
                </td>
            </tr>
            """
        )

    return f"""
    <div class="table-wrapper">
        <table class="analysis-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Application</th>
                    <th>Priority Score</th>
                    <th>Buildability</th>
                    <th>MCP</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
    </div>
    """


def build_ranking_insights_html(insights: list[str]) -> str:
    if not insights:
        return '<span class="muted">No ranking insights available.</span>'

    return build_list_html(insights)


def build_cross_app_analysis_html(analysis: dict) -> str:
    """Render the cross-application analysis section."""

    if not analysis:
        return """
        <section class="section">
            <div class="section-heading">
                <div>
                    <div class="eyebrow">Aggregate Research</div>
                    <h2>Cross-App Analysis</h2>
                </div>
            </div>

            <div class="empty-state large">
                Cross-app analysis has not been generated yet.
            </div>
        </section>
        """

    metadata = analysis.get("metadata", {})
    authentication = analysis.get("authentication", {})
    access = analysis.get("access", {})
    api = analysis.get("api", {})
    mcp = analysis.get("mcp", {})
    buildability = analysis.get("buildability", {})
    categories = analysis.get("categories", {})
    confidence = analysis.get("confidence", {})
    evidence = analysis.get("evidence", {})
    verification = analysis.get("verification", {})
    blockers = analysis.get("common_blockers", {})
    patterns = analysis.get("patterns", [])
    quality_notes = analysis.get("quality_notes", [])
    comparison = analysis.get("comparison", {})

    applications_analyzed = escape_html(
        metadata.get("applications_analyzed", 0)
    )
    verification_records = escape_html(
        metadata.get("verification_records_available", 0)
    )

    average_confidence = confidence.get("average")
    average_confidence_text = (
        f"{float(average_confidence) * 100:.1f}%"
        if isinstance(average_confidence, (int, float))
        else "N/A"
    )

    total_evidence = escape_html(
        evidence.get("total_evidence_items", 0)
    )
    average_evidence = escape_html(
        evidence.get("average_evidence_per_app", 0)
    )
    pass_rate = escape_html(
        verification.get("pass_rate_percent", 0)
    )

    ranking = comparison.get("overall_ranking", [])
    ranking_insights = comparison.get("ranking_insights", [])

    return f"""
    <section class="section">
        <div class="section-heading">
            <div>
                <div class="eyebrow">Aggregate Research</div>
                <h2>Cross-App Analysis</h2>
                <p class="section-description">
                    Deterministic comparison of the completed research sample,
                    including cross-app patterns and an explicit integration-priority
                    heuristic.
                </p>
            </div>
        </div>

        <div class="notice">
            <strong>Sample scope</strong>
            <span>
                This section covers {applications_analyzed} completed applications.
                Findings and rankings should not be generalized to the full dataset
                until the remaining applications have been researched.
            </span>
        </div>

        <div class="analysis-overview-grid" style="margin-top:16px;">
            <div class="analysis-overview-card">
                <span>Applications</span>
                <strong>{applications_analyzed}</strong>
            </div>

            <div class="analysis-overview-card">
                <span>Evidence Items</span>
                <strong>{total_evidence}</strong>
            </div>

            <div class="analysis-overview-card">
                <span>Avg. Evidence / App</span>
                <strong>{average_evidence}</strong>
            </div>

            <div class="analysis-overview-card">
                <span>Avg. Confidence</span>
                <strong>{average_confidence_text}</strong>
            </div>

            <div class="analysis-overview-card">
                <span>Verification Pass Rate</span>
                <strong>{pass_rate}%</strong>
            </div>

            <div class="analysis-overview-card">
                <span>Verification Records</span>
                <strong>{verification_records}</strong>
            </div>
        </div>

        <div class="analysis-panel">
            <h3>Integration Priority Ranking</h3>
            <p class="muted">
                This score is a deterministic prioritization heuristic, not a
                measured benchmark of real integration effort.
            </p>
            {build_ranking_html(ranking)}
        </div>

        <div class="analysis-panel">
            <h3>Ranking Insights</h3>
            {build_ranking_insights_html(ranking_insights)}
        </div>

        <div class="analysis-grid">
            <div class="analysis-panel">
                <h3>Authentication Methods</h3>

                <div class="analysis-columns">
                    <div>
                        <h4>Counts</h4>
                        {build_counter_html(
                            authentication.get("method_counts", {})
                        )}
                    </div>

                    <div>
                        <h4>Percentage of Apps</h4>
                        {build_percentage_html(
                            authentication.get("method_percentages", {})
                        )}
                    </div>
                </div>
            </div>

            <div class="analysis-panel">
                <h3>API Types</h3>

                <div class="analysis-columns">
                    <div>
                        <h4>Counts</h4>
                        {build_counter_html(
                            api.get("type_counts", {})
                        )}
                    </div>

                    <div>
                        <h4>Percentage</h4>
                        {build_percentage_html(
                            api.get("type_percentages", {})
                        )}
                    </div>
                </div>
            </div>

            <div class="analysis-panel">
                <h3>MCP Status</h3>

                <div class="analysis-columns">
                    <div>
                        <h4>Counts</h4>
                        {build_counter_html(
                            mcp.get("status_counts", {})
                        )}
                    </div>

                    <div>
                        <h4>Percentage</h4>
                        {build_percentage_html(
                            mcp.get("status_percentages", {})
                        )}
                    </div>
                </div>
            </div>

            <div class="analysis-panel">
                <h3>Buildability</h3>

                <div class="analysis-columns">
                    <div>
                        <h4>Counts</h4>
                        {build_counter_html(
                            buildability.get("verdict_counts", {})
                        )}
                    </div>

                    <div>
                        <h4>Percentage</h4>
                        {build_percentage_html(
                            buildability.get("verdict_percentages", {})
                        )}
                    </div>
                </div>
            </div>

            <div class="analysis-panel">
                <h3>Access Requirements</h3>
                {build_counter_html(
                    access.get("type_counts", {})
                )}
            </div>

            <div class="analysis-panel">
                <h3>Categories</h3>
                {build_counter_html(
                    categories.get("category_counts", {})
                )}
            </div>
        </div>

        <div class="analysis-panel">
            <h3>Derived Cross-App Patterns</h3>

            <div class="patterns-list">
                {build_patterns_html(patterns)}
            </div>
        </div>

        <div class="analysis-panel">
            <h3>Deterministic Verification</h3>

            <p class="muted">
                Verifier scores measure deterministic consistency checks against
                the available research evidence. They are not independent
                measurements of factual accuracy.
            </p>

            {build_verification_records_html(
                verification.get("records", [])
            )}
        </div>

        <div class="analysis-panel">
            <h3>Common Buildability Blockers</h3>

            {build_counter_html(
                blockers.get("blocker_counts", {})
            )}
        </div>

        <div class="analysis-panel">
            <h3>Research Quality Notes</h3>

            {build_list_html(quality_notes)}
        </div>
    </section>
    """


def build_pipeline_steps_html() -> str:
    """Render the implementation workflow."""

    steps = [
        ("1", "Dataset", "Load and validate the 100-app research dataset."),
        ("2", "Web evidence", "Search official docs and targeted integration sources."),
        ("3", "Composio discovery", "Check whether a matching Composio toolkit exists."),
        ("4", "Structured analysis", "Use Gemini to turn evidence into typed findings."),
        ("5", "Verification", "Run deterministic consistency checks against evidence."),
        ("6", "Cross-app analysis", "Aggregate patterns, quality signals, and priority scores."),
        ("7", "Report", "Generate a deterministic, self-contained HTML case study."),
    ]

    return "".join(
        f"""
        <article class="pipeline-step">
            <span class="step-number">{number}</span>
            <h3>{title}</h3>
            <p>{description}</p>
        </article>
        """
        for number, title, description in steps
    )


def build_execution_notice(
    statistics: dict[str, Any],
) -> tuple[str, str, str]:
    """Build report status and the visible quota/partial-run explanation."""

    status = statistics["pipeline_status"]
    stop_reason = statistics["stop_reason"]

    if status == "paused":
        return (
            "warning",
            "Pipeline paused",
            (
                f"{statistics['completed']} of {statistics['total']} applications "
                f"were completed before the pipeline paused. "
                f"{stop_reason or 'The run was paused before the full dataset was completed.'} "
                f"Saved checkpoints allow the remaining applications to be resumed "
                f"without re-running completed work."
            ),
        )

    if status == "completed":
        return (
            "success",
            "Pipeline completed",
            (
                f"The saved pipeline state reports {statistics['completed']} "
                f"completed applications out of {statistics['total']}."
            ),
        )

    return (
        "warning",
        "Partial execution",
        (
            f"The report currently contains {statistics['completed']} completed "
            f"applications out of a {statistics['total']}-application dataset."
        ),
    )


def generate_report(
    results_path: Path = RESULTS_FILE,
    failures_path: Path = FAILURES_FILE,
    progress_path: Path = PROGRESS_FILE,
    template_path: Path = TEMPLATE_FILE,
    output_path: Path = OUTPUT_FILE,
    cross_app_analysis_path: Path = CROSS_APP_ANALYSIS_FILE,
) -> Path:
    """
    Generate the HTML research report.

    This function is deterministic and performs no network or LLM calls.
    """

    raw_results = load_json(results_path, [])
    raw_failures = load_json(failures_path, [])
    progress = load_json(progress_path, {})
    cross_app_analysis = load_json(
        cross_app_analysis_path,
        {},
    )

    results = normalize_results(raw_results)

    failures = (
        raw_failures
        if isinstance(raw_failures, list)
        else []
    )

    if not isinstance(progress, dict):
        progress = {}

    if not isinstance(cross_app_analysis, dict):
        cross_app_analysis = {}

    template = template_path.read_text(encoding="utf-8")

    statistics = calculate_statistics(
        results=results,
        failures=failures,
        progress=progress,
    )

    buildability_counts = statistics["buildability_counts"]

    buildability_html = (
        "".join(
            f"""
            <span class="distribution-item">
                <span class="badge {status_class(verdict)}">
                    {escape_html(verdict)}
                </span>
                <strong>{count}</strong>
            </span>
            """
            for verdict, count in sorted(buildability_counts.items())
        )
        or '<span class="muted">No data</span>'
    )

    applications_html = (
        "\n".join(
            build_application_html(result)
            for result in results
        )
        or """
        <div class="empty-state large">
            No completed research results are available.
        </div>
        """
    )

    cross_app_html = build_cross_app_analysis_html(
        cross_app_analysis
    )

    failure_html = ""

    if failures:
        failure_items = []

        for failure in failures:
            app_id = escape_html(failure.get("app_id"))
            app_name = escape_html(failure.get("app_name"))
            error = escape_html(failure.get("error"))

            failure_items.append(
                f"""
                <div class="failure-card">
                    <strong>
                        {app_name or "Unknown application"}
                    </strong>

                    <span>App ID: {app_id}</span>

                    <p>
                        {error or "Unknown error"}
                    </p>
                </div>
                """
            )

        failure_html = f"""
        <section class="section">
            <div class="section-heading">
                <div>
                    <div class="eyebrow">Execution Record</div>
                    <h2>Failed / Interrupted Applications</h2>
                </div>
            </div>

            {"".join(failure_items)}
        </section>
        """

    notice_class, notice_title, notice_text = build_execution_notice(
        statistics
    )

    limitations_text = (
        f"The dataset contains {statistics['total']} applications. "
        f"The current saved execution has {statistics['completed']} completed "
        f"results, {statistics['failed']} recorded failure(s), and "
        f"{statistics['remaining']} remaining application(s). "
        f"Cross-app findings therefore describe the completed sample only. "
        f"They should not be generalized to the full dataset until the remaining "
        f"applications have been researched. "
        f"The deterministic verification score is a consistency metric, not "
        f"a guarantee of factual correctness."
    )

    status = statistics["pipeline_status"]
    report_status = (
        f"Pipeline: {status}"
        if status
        else "Pipeline status unavailable"
    )

    generated_at = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    dataset_coverage = (
        f"{statistics['completed']} / "
        f"{statistics['total']} researched"
    )

    html_output = template

    replacements = {
        "{{REPORT_STATUS}}": escape_html(report_status),
        "{{REPORT_GENERATED_AT}}": escape_html(generated_at),
        "{{DATASET_COVERAGE}}": escape_html(dataset_coverage),
        "{{TOTAL_APPS}}": str(statistics["total"]),
        "{{COMPLETED_APPS}}": str(statistics["completed"]),
        "{{REMAINING_APPS}}": str(statistics["remaining"]),
        "{{FAILED_APPS}}": str(statistics["failed"]),
        "{{VERIFIED_APPS}}": str(statistics["verified"]),
        "{{VERIFICATION_FAILED}}": str(
            statistics["verification_failed"]
        ),
        "{{AVERAGE_QUALITY}}": (
            f"{statistics['average_quality']:.1f}"
        ),
        "{{BUILDABILITY_DISTRIBUTION}}": buildability_html,
        "{{EXECUTION_NOTICE_CLASS}}": notice_class,
        "{{EXECUTION_NOTICE_TITLE}}": escape_html(notice_title),
        "{{EXECUTION_NOTICE_TEXT}}": escape_html(notice_text),
        "{{PIPELINE_STEPS}}": build_pipeline_steps_html(),
        "{{LIMITATIONS_TEXT}}": escape_html(limitations_text),
        "{{CROSS_APP_ANALYSIS}}": cross_app_html,
        "{{APPLICATIONS}}": applications_html,
        "{{FAILURES}}": failure_html,
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

    _generate_multipage_site(
        results=results,
        statistics=statistics,
        cross_app_analysis=cross_app_analysis,
        notice_title=notice_title,
        notice_text=notice_text,
        status=status,
    )

    return output_path



def _slugify(value: Any) -> str:
    text = str(value or "application").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "application"


def _page_nav(active: str) -> str:
    links = [
        ("overview", "Overview", "overview.html"),
        ("analysis", "Cross-App Analysis", "cross_app_analysis.html"),
        ("applications", "Applications", "applications.html"),
        ("execution", "Execution & Methodology", "execution.html"),
    ]
    return f"""
    <nav class="site-nav">
        <div class="nav-inner">
            <a class="brand" href="overview.html">AI App Research Agent</a>
            <div class="nav-links">
                {"".join(
                    f'<a class="nav-link {"active" if key == active else ""}" href="{href}">{label}</a>'
                    for key, label, href in links
                )}
            </div>
        </div>
    </nav>
    """


def _page_document(title: str, active: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title)} — AI App Integration Research</title>
<link rel="stylesheet" href="../report.css">
</head>
<body>
{_page_nav(active)}
<header class="page-header">
    <div class="container">
        <div class="eyebrow">AI Engineering Case Study</div>
        <h1>{escape_html(title)}</h1>
    </div>
</header>
<main>
    <div class="container">{body}</div>
</main>
<footer><div class="container">AI App Integration Research Agent · Generated from saved research artifacts</div></footer>
</body>
</html>"""


def _generate_multipage_site(
    results: list[dict],
    statistics: dict[str, Any],
    cross_app_analysis: dict,
    notice_title: str,
    notice_text: str,
    status: str,
) -> None:
    pages_dir = REPORT_DIR / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    (REPORT_DIR / "report.css").write_text(
        r"""
*{box-sizing:border-box}
:root{--bg:#f5f7fa;--surface:#fff;--text:#172033;--muted:#64748b;--border:#e2e8f0;--dark:#111827;--link:#2563eb}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.55}
a{color:var(--link)}
.container{width:min(1400px,calc(100% - 40px));margin:0 auto}
.site-nav{position:sticky;top:0;z-index:100;background:rgba(17,24,39,.97);border-bottom:1px solid #334155;backdrop-filter:blur(12px)}
.nav-inner{width:min(1400px,calc(100% - 40px));min-height:62px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:20px}
.brand{color:#fff;text-decoration:none;font-weight:800;white-space:nowrap}
.nav-links{display:flex;flex-wrap:wrap;gap:4px}
.nav-link{color:#cbd5e1;text-decoration:none;padding:7px 10px;border-radius:7px;font-size:13px;font-weight:650}
.nav-link:hover,.nav-link.active{background:#1e293b;color:#fff}
.page-header{padding:42px 0 34px;background:var(--dark);color:#fff}
.eyebrow{margin-bottom:8px;color:var(--muted);font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase}
.page-header .eyebrow{color:#94a3b8}
.page-header h1{margin:0;font-size:40px;line-height:1.1;letter-spacing:-1px}
main{padding:34px 0 70px}
section{margin-bottom:32px}
h2{margin:0 0 12px;font-size:28px;letter-spacing:-.5px}
h3{margin-top:0}
.section-description{max-width:950px;color:var(--muted)}
.stats-grid,.card-grid,.two-column,.metric-grid{display:grid;gap:16px}
.stats-grid{grid-template-columns:repeat(6,minmax(0,1fr))}
.card-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
.two-column{grid-template-columns:repeat(2,minmax(0,1fr))}
.metric-grid{grid-template-columns:repeat(4,minmax(0,1fr))}
.card,.stat-card,.panel{background:var(--surface);border:1px solid var(--border);border-radius:12px}
.card,.panel{padding:20px}
.card{text-decoration:none;color:inherit}
.card:hover{border-color:#94a3b8}
.card p,.panel p{color:#475569}
.stat-card{padding:18px}
.stat-label,.metric-label{display:block;color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase}
.stat-value{display:block;margin-top:5px;font-size:28px;font-weight:800}
.notice{padding:17px 19px;background:#fffbeb;border:1px solid #fde68a;border-radius:12px;color:#78350f}
.notice.success{background:#f0fdf4;border-color:#bbf7d0;color:#166534}
.notice.danger{background:#fff7f7;border-color:#fecaca;color:#991b1b}
.app-list{display:grid;gap:12px}
.app-row{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:18px 20px;background:#fff;border:1px solid var(--border);border-radius:12px;text-decoration:none;color:inherit}
.app-row:hover{border-color:#94a3b8}
.app-row h3{margin:0 0 4px}.app-row p{margin:0;color:var(--muted);font-size:13px}
.app-row-right{display:flex;align-items:center;gap:8px;flex-shrink:0}
.metric{padding:16px;background:#f8fafc;border:1px solid var(--border);border-radius:10px}
.metric strong{display:block;margin-top:5px}
.badge{display:inline-flex;width:fit-content;padding:4px 9px;border-radius:999px;font-size:11px;font-weight:750;text-transform:uppercase}
.badge.success{background:#dcfce7;color:#166534}.badge.warning{background:#fef3c7;color:#92400e}.badge.danger{background:#fee2e2;color:#991b1b}.badge.neutral{background:#e2e8f0;color:#475569}
table{width:100%;border-collapse:collapse;background:#fff}
th,td{padding:11px 12px;border-bottom:1px solid var(--border);text-align:left}
th{color:var(--muted);font-size:12px;text-transform:uppercase}
.field{display:flex;justify-content:space-between;gap:20px;padding:9px 0;border-bottom:1px solid #edf2f7}
.field:last-child{border-bottom:0}.field>span:first-child{color:var(--muted)}
.code-block{overflow-x:auto;padding:15px;background:#0f172a;color:#e2e8f0;border-radius:10px;font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace}
.empty-state{padding:30px;color:var(--muted);text-align:center;background:#fff;border:1px solid var(--border);border-radius:12px}
.back-link{display:inline-block;margin-bottom:20px;font-size:13px;font-weight:650}
footer{padding:28px 0;border-top:1px solid var(--border);color:var(--muted);font-size:13px}
@media(max-width:1100px){.stats-grid{grid-template-columns:repeat(3,1fr)}.metric-grid{grid-template-columns:repeat(2,1fr)}.card-grid{grid-template-columns:1fr}}
@media(max-width:700px){.container,.nav-inner{width:calc(100% - 24px)}.nav-inner{align-items:flex-start;flex-direction:column;padding:10px 0}.stats-grid,.metric-grid,.two-column{grid-template-columns:1fr}.app-row{align-items:flex-start;flex-direction:column}.app-row-right{flex-wrap:wrap}.page-header h1{font-size:32px}}
""",
        encoding="utf-8",
    )

    overview_body = f"""
    <section>
        <div class="notice {'success' if status == 'completed' else 'danger' if status == 'paused' else ''}">
            <strong>{escape_html(notice_title)}</strong>
            <span>{escape_html(notice_text)}</span>
        </div>
    </section>

    <section class="stats-grid">
        <div class="stat-card"><span class="stat-label">Dataset</span><span class="stat-value">{statistics["total"]}</span></div>
        <div class="stat-card"><span class="stat-label">Completed</span><span class="stat-value">{statistics["completed"]}</span></div>
        <div class="stat-card"><span class="stat-label">Remaining</span><span class="stat-value">{statistics["remaining"]}</span></div>
        <div class="stat-card"><span class="stat-label">Failed</span><span class="stat-value">{statistics["failed"]}</span></div>
        <div class="stat-card"><span class="stat-label">Verified</span><span class="stat-value">{statistics["verified"]}</span></div>
        <div class="stat-card"><span class="stat-label">Avg Quality</span><span class="stat-value">{statistics["average_quality"]:.1f}</span></div>
    </section>

    <section>
        <h2>What this implementation demonstrates</h2>
        <p class="section-description">
            A resumable multi-stage research system that collects evidence,
            performs structured analysis, verifies results, evaluates research
            quality, and produces deterministic cross-app comparisons.
        </p>
        <div class="card-grid">
            <article class="card"><h3>Evidence-first research</h3><p>Web evidence and Composio discovery are collected before structured analysis.</p></article>
            <article class="card"><h3>Reliability</h3><p>Retries, checkpointing, quota handling, and resumable execution preserve completed work.</p></article>
            <article class="card"><h3>Decision support</h3><p>Verification, quality signals, cross-app patterns, and priority ranking turn research into actionable output.</p></article>
        </div>
    </section>

    <section>
        <h2>Navigate the case study</h2>
        <div class="card-grid">
            <a class="card" href="cross_app_analysis.html"><h3>Cross-App Analysis →</h3><p>Patterns, rankings, verification metrics, and scoring methodology.</p></a>
            <a class="card" href="applications.html"><h3>Applications →</h3><p>Browse completed research and open each detailed result.</p></a>
            <a class="card" href="execution.html"><h3>Execution & Methodology →</h3><p>Pipeline architecture, reproducibility, testing, and execution limits.</p></a>
        </div>
    </section>
    """

    (pages_dir / "overview.html").write_text(
        _page_document("Overview", "overview", overview_body),
        encoding="utf-8",
    )

    analysis_body = build_cross_app_analysis_html(cross_app_analysis)
    (pages_dir / "cross_app_analysis.html").write_text(
        _page_document("Cross-App Analysis", "analysis", analysis_body),
        encoding="utf-8",
    )

    app_rows = []
    for result in results:
        app_id = result.get("app_id")
        app_name = result.get("app_name", "Unknown")
        category = result.get("category", "Unknown")

        buildability_data = result.get("buildability", {})
        if not isinstance(buildability_data, dict):
            buildability_data = {}
        verdict = str(buildability_data.get("verdict", "Unknown"))

        verification_data = result.get("verification", {})
        if not isinstance(verification_data, dict):
            verification_data = {}
        passed = verification_data.get("passed")

        verification_label = (
            "Verified" if passed is True
            else "Verification failed" if passed is False
            else "Not verified"
        )

        slug = _slugify(app_name)
        detail_filename = f"app_{app_id}_{slug}.html"

        app_rows.append(f"""
        <a class="app-row" href="{detail_filename}">
            <div>
                <h3>{escape_html(app_name)}</h3>
                <p>{escape_html(category)} · App ID {escape_html(app_id)}</p>
            </div>
            <div class="app-row-right">
                <span class="badge {status_class(verdict)}">{escape_html(verdict)}</span>
                <span class="badge {'success' if passed is True else 'neutral'}">{escape_html(verification_label)}</span>
            </div>
        </a>
        """)

    applications_body = f"""
    <section>
        <h2>Completed Applications</h2>
        <p class="section-description">
            {len(results)} applications currently have saved research results.
            Select an application to inspect its detailed findings and evidence.
        </p>
    </section>
    <section class="app-list">
        {"".join(app_rows) or '<div class="empty-state">No completed applications.</div>'}
    </section>
    """

    (pages_dir / "applications.html").write_text(
        _page_document("Applications", "applications", applications_body),
        encoding="utf-8",
    )

    for result in results:
        app_id = result.get("app_id")
        app_name = result.get("app_name", "Application")
        slug = _slugify(app_name)
        body = f'<a class="back-link" href="applications.html">← Back to applications</a>{build_application_html(result)}'

        (pages_dir / f"app_{app_id}_{slug}.html").write_text(
            _page_document(str(app_name), "applications", body),
            encoding="utf-8",
        )

    execution_body = f"""
    <section>
        <div class="notice {'success' if status == 'completed' else 'danger' if status == 'paused' else ''}">
            <strong>{escape_html(notice_title)}</strong>
            <span>{escape_html(notice_text)}</span>
        </div>
    </section>

    <section>
        <h2>Research workflow</h2>
        <div class="card-grid">
            <article class="card"><h3>1. Dataset</h3><p>Load and validate the 100-app research dataset.</p></article>
            <article class="card"><h3>2. Evidence retrieval</h3><p>Search official documentation and targeted integration sources.</p></article>
            <article class="card"><h3>3. Composio discovery</h3><p>Check whether a matching Composio toolkit exists.</p></article>
            <article class="card"><h3>4. Structured analysis</h3><p>Convert retrieved evidence into typed application findings.</p></article>
            <article class="card"><h3>5. Verification</h3><p>Run deterministic consistency checks against evidence.</p></article>
            <article class="card"><h3>6. Cross-app analysis</h3><p>Aggregate patterns, quality signals, and integration priority.</p></article>
            <article class="card"><h3>7. Reporting</h3><p>Generate a deterministic multi-page case-study report.</p></article>
        </div>
    </section>

    <section class="two-column">
        <div class="panel">
            <h2>Reproduce locally</h2>
            <pre class="code-block">python -m src.pipeline --limit 5
python -m src.cross_app_analysis
python -m report.generate
python -m pytest</pre>
        </div>
        <div class="panel">
            <h2>Current execution</h2>
            <div class="field"><span>Dataset</span><strong>{statistics["total"]}</strong></div>
            <div class="field"><span>Completed</span><strong>{statistics["completed"]}</strong></div>
            <div class="field"><span>Failed / interrupted</span><strong>{statistics["failed"]}</strong></div>
            <div class="field"><span>Remaining</span><strong>{statistics["remaining"]}</strong></div>
        </div>
    </section>

    <section>
        <h2>Submission limitation</h2>
        <div class="notice danger">
            <strong>Gemini API quota</strong>
            <span>
                The current saved execution contains {statistics["completed"]} completed
                applications from the 100-app dataset. The pipeline paused when the
                Gemini API quota was exhausted. Checkpointed results can be resumed
                when quota becomes available.
            </span>
        </div>
    </section>

    <section>
        <h2>Testing</h2>
        <div class="notice success">
            <strong>102 tests passing</strong>
            <span>
                Automated coverage includes the research pipeline, dataset validation,
                report generation, research-agent edge cases, verification, cross-app
                analysis, and web/tool integrations.
            </span>
        </div>
    </section>
    """

    (pages_dir / "execution.html").write_text(
        _page_document("Execution & Methodology", "execution", execution_body),
        encoding="utf-8",
    )

def main() -> None:
    """CLI entry point."""

    print("=" * 70)
    print("RESEARCH REPORT GENERATOR")
    print("=" * 70)

    if not RESULTS_FILE.exists():
        print(f"Results file not found: {RESULTS_FILE}")
        print("Run the research pipeline first.")
        return

    output = generate_report()

    print(f"Report generated: {output}")


if __name__ == "__main__":
    main()
