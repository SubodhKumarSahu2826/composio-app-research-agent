from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
REPORT_DIR = PROJECT_ROOT / "report"

RESULTS_FILE = RESULTS_DIR / "results.json"
FAILURES_FILE = RESULTS_DIR / "failures.json"
PROGRESS_FILE = RESULTS_DIR / "progress.json"

TEMPLATE_FILE = REPORT_DIR / "template.html"
OUTPUT_FILE = REPORT_DIR / "research_report.html"


def load_json(path: Path, default: Any) -> Any:
    """Load JSON from disk, returning default when the file is absent."""

    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def escape_html(value: Any) -> str:
    """Safely convert arbitrary values into HTML-safe text."""

    import html

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

                <h4>{source_name or "Unnamed source"}</h4>

                <p class="claim">
                    {claim}
                </p>

                {
                    f'''
                    <p class="snippet">
                        {snippet}
                    </p>
                    '''
                    if snippet
                    else ""
                }

                {
                    f'''
                    <a
                        class="source-link"
                        href="{url}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Open source
                    </a>
                    '''
                    if url
                    else ""
                }
            </article>
            """
        )

    return "\n".join(cards)


def build_requirements_html(requirements: list[str]) -> str:
    """Render access requirements."""

    if not requirements:
        return "<span class=\"muted\">None specified</span>"

    items = []

    for requirement in requirements:
        items.append(
            f"<li>{escape_html(requirement)}</li>"
        )

    return f"<ul>{''.join(items)}</ul>"


def build_list_html(items: list[str]) -> str:
    """Render a generic list."""

    if not items:
        return "<span class=\"muted\">None</span>"

    return (
        "<ul>"
        + "".join(
            f"<li>{escape_html(item)}</li>"
            for item in items
        )
        + "</ul>"
    )


def normalize_results(raw_results: Any) -> list[dict]:
    """
    Normalize results.json into a list.

    The pipeline currently writes a JSON list, but this also
    supports a future wrapper object containing a `results` key.
    """

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

        # Support a single AppResearch object.
        if "app_id" in raw_results:
            return [raw_results]

    return []


def calculate_statistics(
    results: list[dict],
    failures: list[dict],
) -> dict[str, Any]:
    """Calculate report-level statistics."""

    total = len(results) + len(failures)

    verified = 0
    verification_failed = 0

    quality_scores: list[float] = []

    buildability_counts: dict[str, int] = {}

    for result in results:
        verification = result.get("verification", {})

        if isinstance(verification, dict):
            if verification.get("passed") is True:
                verified += 1
            else:
                verification_failed += 1

        analysis = result.get("analysis", {})

        if isinstance(analysis, dict):
            quality_score = analysis.get("quality_score")

            if isinstance(
                quality_score,
                (int, float),
            ):
                quality_scores.append(
                    float(quality_score)
                )

        buildability = result.get(
            "buildability",
            {},
        )

        if isinstance(buildability, dict):
            verdict = buildability.get(
                "verdict",
                "Unknown",
            )
        else:
            verdict = "Unknown"

        buildability_counts[verdict] = (
            buildability_counts.get(
                verdict,
                0,
            )
            + 1
        )

    average_quality = (
        sum(quality_scores) / len(quality_scores)
        if quality_scores
        else 0.0
    )

    return {
        "total": total,
        "completed": len(results),
        "failed": len(failures),
        "verified": verified,
        "verification_failed": verification_failed,
        "average_quality": average_quality,
        "buildability_counts": buildability_counts,
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
                {escape_html(result.get("app_id"))}
            </div>
        </div>

        <div class="metrics-grid">

            <div class="metric">
                <span class="metric-label">
                    Buildability
                </span>

                <span class="badge {status_class(buildability_verdict)}">
                    {buildability_verdict}
                </span>
            </div>

            <div class="metric">
                <span class="metric-label">
                    Verification
                </span>

                <span class="badge {
                    "success"
                    if verification_passed is True
                    else "danger"
                    if verification_passed is False
                    else "neutral"
                }">
                    {
                        "PASSED"
                        if verification_passed is True
                        else "FAILED"
                        if verification_passed is False
                        else "N/A"
                    }
                </span>
            </div>

            <div class="metric">
                <span class="metric-label">
                    Quality Score
                </span>

                <strong>
                    {
                        f"{float(quality_score):.1f}/100"
                        if isinstance(
                            quality_score,
                            (int, float),
                        )
                        else "N/A"
                    }
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
                <h3>Authentication</h3>

                <div class="field">
                    <span>Methods</span>
                    <strong>
                        {
                            escape_html(
                                ", ".join(
                                    str(item)
                                    for item in auth_methods
                                )
                            )
                            if auth_methods
                            else "Unknown"
                        }
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
                <h3>Access</h3>

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

                {
                    f'''
                    <a
                        class="source-link"
                        href="{escape_html(api_documentation)}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        API documentation
                    </a>
                    '''
                    if api_documentation
                    else ""
                }

            </div>

            <div class="panel">
                <h3>MCP</h3>

                <div class="field">
                    <span>Status</span>
                    <span class="badge {
                        status_class(mcp_status)
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

                {
                    f'''
                    <a
                        class="source-link"
                        href="{escape_html(mcp_url)}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        MCP documentation
                    </a>
                    '''
                    if mcp_url
                    else ""
                }

            </div>

        </div>

        <div class="panel buildability-panel">

            <h3>Buildability Assessment</h3>

            {
                f'''
                <div class="field">
                    <span>Blocker</span>
                    <strong>{blocker}</strong>
                </div>
                '''
                if blocker
                else ""
            }

            <p>
                {reasoning or "No reasoning provided."}
            </p>

        </div>

        <div class="panel">

            <h3>Verification</h3>

            <div class="field">
                <span>Score</span>
                <strong>
                    {
                        f"{float(verification_score):.2f}"
                        if isinstance(
                            verification_score,
                            (int, float),
                        )
                        else "N/A"
                    }
                </strong>
            </div>

            {
                f'''
                <div class="issue-section">
                    <h4>Errors</h4>
                    {build_list_html(verification_errors)}
                </div>
                '''
                if verification_errors
                else
                '<p class="muted">No verification errors.</p>'
            }

            {
                f'''
                <div class="issue-section">
                    <h4>Warnings</h4>
                    {build_list_html(verification_warnings)}
                </div>
                '''
                if verification_warnings
                else
                '<p class="muted">No verification warnings.</p>'
            }

        </div>

        <div class="panel">

            <h3>Research Quality</h3>

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

            {
                f'''
                <div class="issue-section">
                    <h4>Strengths</h4>
                    {build_list_html(strengths)}
                </div>
                '''
                if strengths
                else ""
            }

            {
                f'''
                <div class="issue-section">
                    <h4>Warnings</h4>
                    {build_list_html(analysis_warnings)}
                </div>
                '''
                if analysis_warnings
                else ""
            }

        </div>

        <div class="panel">

            <h3>Evidence</h3>

            <div class="evidence-list">
                {build_evidence_html(evidence)}
            </div>

        </div>

    </section>
    """


def generate_report(
    results_path: Path = RESULTS_FILE,
    failures_path: Path = FAILURES_FILE,
    template_path: Path = TEMPLATE_FILE,
    output_path: Path = OUTPUT_FILE,
) -> Path:
    """
    Generate the HTML research report.

    This function is deterministic and performs no network or
    LLM calls.
    """

    raw_results = load_json(
        results_path,
        [],
    )

    raw_failures = load_json(
        failures_path,
        [],
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
                <strong>{count}</strong>
            </span>
            """
            for verdict, count
            in sorted(
                buildability_counts.items()
            )
        )
        or '<span class="muted">No data</span>'
    )

    applications_html = (
        "\n".join(
            build_application_html(
                result
            )
            for result in results
        )
        or """
        <div class="empty-state large">
            No completed research results are available.
        </div>
        """
    )

    failure_html = ""

    if failures:
        failure_items = []

        for failure in failures:
            app_id = escape_html(
                failure.get("app_id")
            )

            app_name = escape_html(
                failure.get("app_name")
            )

            error = escape_html(
                failure.get("error")
            )

            failure_items.append(
                f"""
                <div class="failure-card">
                    <strong>
                        {app_name or "Unknown application"}
                    </strong>

                    <span>
                        App ID: {app_id}
                    </span>

                    <p>
                        {error or "Unknown error"}
                    </p>
                </div>
                """
            )

        failure_html = f"""
        <section class="failures-section">

            <h2>Failed Applications</h2>

            {"".join(failure_items)}

        </section>
        """

    html = template

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
            statistics["verification_failed"]
        ),
        "{{AVERAGE_QUALITY}}": (
            f"{statistics['average_quality']:.1f}"
        ),
        "{{BUILDABILITY_DISTRIBUTION}}": (
            buildability_html
        ),
        "{{APPLICATIONS}}": applications_html,
        "{{FAILURES}}": failure_html,
    }

    for placeholder, value in replacements.items():
        html = html.replace(
            placeholder,
            value,
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        html,
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