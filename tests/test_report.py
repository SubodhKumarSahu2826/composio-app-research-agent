from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "report"
RESULTS_DIR = PROJECT_ROOT / "results"

RESULTS_FILE = RESULTS_DIR / "results.json"
FAILURES_FILE = RESULTS_DIR / "failures.json"
PROGRESS_FILE = RESULTS_DIR / "progress.json"
REPORT_FILE = REPORT_DIR / "research_report.html"


def run_report_generator() -> subprocess.CompletedProcess:
    """
    Run the report generator exactly the way a user would run it.

    Using a subprocess makes this a true integration test of the
    report generation entry point.
    """

    return subprocess.run(
        [
            sys.executable,
            "-m",
            "report.generate",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


def test_report_generator_module_imports():
    """
    The report generator module must be importable.
    """

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import report.generate",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_results_file_exists():
    """
    Phase 3 depends on the research pipeline producing results.json.
    """

    assert RESULTS_FILE.exists(), (
        f"Missing research results file: {RESULTS_FILE}"
    )

    data = json.loads(
        RESULTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    assert isinstance(data, list)


def test_results_have_required_application_fields():
    """
    Every research result should contain the core fields required
    by the report.
    """

    data = json.loads(
        RESULTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    for result in data:
        assert "app_id" in result
        assert "app_name" in result
        assert "category" in result
        assert "description" in result
        assert "authentication" in result
        assert "access" in result
        assert "api" in result
        assert "mcp" in result
        assert "buildability" in result
        assert "evidence" in result


def test_report_generator_runs_successfully():
    """
    The complete report generation command must finish successfully.
    """

    result = run_report_generator()

    assert result.returncode == 0, (
        "Report generator failed.\n\n"
        f"STDOUT:\n{result.stdout}\n\n"
        f"STDERR:\n{result.stderr}"
    )


def test_report_file_is_created():
    """
    Running the generator must create the final HTML report.
    """

    result = run_report_generator()

    assert result.returncode == 0, (
        f"Generator failed:\n{result.stderr}"
    )

    assert REPORT_FILE.exists(), (
        f"Expected report was not created: {REPORT_FILE}"
    )


def test_report_file_is_not_empty():
    """
    The generated report must contain actual HTML.
    """

    run_report_generator()

    assert REPORT_FILE.exists()

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    assert content.strip() != ""
    assert len(content) > 500


def test_report_contains_html_structure():
    """
    Basic structural validation of the generated HTML document.
    """

    run_report_generator()

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    lowered = content.lower()

    assert "<html" in lowered
    assert "<head" in lowered
    assert "<body" in lowered
    assert "</html>" in lowered


def test_report_contains_application_names():
    """
    Every application in results.json should appear in the generated
    report.
    """

    run_report_generator()

    results = json.loads(
        RESULTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    for result in results:
        app_name = result["app_name"]

        assert app_name in content, (
            f"Application '{app_name}' was not found "
            "in the generated report."
        )


def test_report_contains_research_sections():
    """
    The report should expose the major research dimensions.
    """

    run_report_generator()

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    lowered = content.lower()

    expected_terms = [
        "authentication",
        "access",
        "api",
        "mcp",
        "buildability",
        "evidence",
    ]

    for term in expected_terms:
        assert term in lowered, (
            f"Expected report section/content '{term}' "
            "was not found."
        )


def test_report_contains_evidence_links():
    """
    Evidence URLs should be rendered as clickable links.
    """

    run_report_generator()

    results = json.loads(
        RESULTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    evidence_urls = []

    for result in results:
        for evidence in result.get(
            "evidence",
            [],
        ):
            url = evidence.get("url")

            if url:
                evidence_urls.append(url)

    # The current dataset should contain evidence.
    assert evidence_urls, (
        "No evidence URLs were found in results.json."
    )

    for url in evidence_urls:
        assert url in content, (
            f"Evidence URL was not rendered in report: {url}"
        )


def test_report_contains_verification_when_available():
    """
    Phase 2 verification information should appear in the report
    for results that contain it.

    Older results may legitimately lack the field.
    """

    run_report_generator()

    results = json.loads(
        RESULTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    results_with_verification = [
        result
        for result in results
        if "verification" in result
    ]

    if not results_with_verification:
        return

    assert "verification" in content.lower()


def test_report_contains_analysis_when_available():
    """
    Phase 2 analysis information should appear in the report
    for results that contain it.

    Older results may legitimately lack the field.
    """

    run_report_generator()

    results = json.loads(
        RESULTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    results_with_analysis = [
        result
        for result in results
        if "analysis" in result
    ]

    if not results_with_analysis:
        return

    assert "analysis" in content.lower()


def test_progress_file_exists():
    """
    The pipeline should have produced progress metadata.
    """

    assert PROGRESS_FILE.exists()

    progress = json.loads(
        PROGRESS_FILE.read_text(
            encoding="utf-8"
        )
    )

    assert isinstance(progress, dict)
    assert "total" in progress
    assert "completed" in progress
    assert "failed" in progress


def test_failures_file_exists():
    """
    The pipeline should maintain a failures.json file even when
    there are currently no failures.
    """

    assert FAILURES_FILE.exists()

    failures = json.loads(
        FAILURES_FILE.read_text(
            encoding="utf-8"
        )
    )

    assert isinstance(failures, list)


def test_report_generation_is_repeatable():
    """
    Running the generator twice should succeed both times.

    This catches accidental dependence on temporary state.
    """

    first = run_report_generator()

    assert first.returncode == 0, (
        f"First generation failed:\n{first.stderr}"
    )

    assert REPORT_FILE.exists()

    first_content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    second = run_report_generator()

    assert second.returncode == 0, (
        f"Second generation failed:\n{second.stderr}"
    )

    assert REPORT_FILE.exists()

    second_content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    assert second_content.strip() != ""
    assert len(second_content) > 500


def test_report_has_no_python_traceback():
    """
    A generated HTML report should never contain a Python traceback.
    """

    run_report_generator()

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    assert "Traceback (most recent call last)" not in content


def test_report_has_no_json_serialization_error():
    """
    Catch the exact class of Phase 3 serialization issue encountered
    earlier in the pipeline.
    """

    run_report_generator()

    content = REPORT_FILE.read_text(
        encoding="utf-8"
    )

    assert "not JSON serializable" not in content