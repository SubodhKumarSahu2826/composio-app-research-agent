from __future__ import annotations

import json

import pytest

from src.cross_app_analysis import (
    BUILDABILITY_SCORES,
    MCP_SCORES,
    analyze,
    analyze_access,
    analyze_api,
    analyze_authentication,
    analyze_blockers,
    analyze_buildability,
    analyze_categories,
    analyze_confidence,
    analyze_evidence,
    analyze_mcp,
    analyze_verification,
    build_buildability_ranking,
    build_comparison_matrix,
    build_comparison_records,
    build_mcp_ranking,
    calculate_integration_score,
    generate_patterns,
    generate_quality_notes,
    generate_ranking_insights,
    load_results,
    rank_records,
    save_analysis,
)


# ============================================================
# FIXTURES
# ============================================================


@pytest.fixture
def sample_results() -> list[dict]:
    return [
        {
            "app_id": 1,
            "app_name": "Alpha",
            "category": "CRM",
            "authentication": {
                "methods": [
                    "OAuth2",
                    "API Key",
                ],
            },
            "access": {
                "type": "Free",
                "requirements": [],
            },
            "api": {
                "type": "REST",
                "breadth": "Broad",
            },
            "mcp": {
                "status": "Official MCP",
            },
            "buildability": {
                "verdict": "Easy",
                "blocker": None,
            },
            "evidence": [
                {"claim": "Claim 1"},
                {"claim": "Claim 2"},
                {"claim": "Claim 3"},
                {"claim": "Claim 4"},
            ],
            "overall_confidence": 0.90,
            "verification": {
                "passed": True,
                "score": 100,
            },
            "analysis": {
                "quality_score": 90,
            },
        },
        {
            "app_id": 2,
            "app_name": "Beta",
            "category": "Finance",
            "authentication": {
                "methods": [
                    "OAuth2",
                ],
            },
            "access": {
                "type": "Paid Plan Required",
                "requirements": [
                    "Admin Approval Required",
                ],
            },
            "api": {
                "type": "REST",
                "breadth": "Narrow",
            },
            "mcp": {
                "status": "Third-party MCP",
            },
            "buildability": {
                "verdict": "Possible",
                "blocker": "Admin approval",
            },
            "evidence": [
                {"claim": "Claim 1"},
                {"claim": "Claim 2"},
            ],
            "overall_confidence": 0.80,
            "verification": {
                "passed": True,
                "score": 95,
            },
            "analysis": {
                "quality_score": 80,
            },
        },
        {
            "app_id": 3,
            "app_name": "Gamma",
            "category": "CRM",
            "authentication": {
                "methods": [
                    "API Key",
                ],
            },
            "access": {
                "type": "Free",
                "requirements": [],
            },
            "api": {
                "type": "GraphQL",
                "breadth": "Broad",
            },
            "mcp": {
                "status": "Unknown",
            },
            "buildability": {
                "verdict": "Blocked",
                "blocker": "No API access",
            },
            "evidence": [
                {"claim": "Claim 1"},
            ],
            "overall_confidence": 0.70,
            # Intentionally no verification metadata.
            "analysis": {
                "quality_score": 70,
            },
        },
    ]


# ============================================================
# DATA LOADING
# ============================================================


def test_load_results_returns_list():
    results = load_results()

    assert isinstance(
        results,
        list,
    )


# ============================================================
# BASIC HELPERS
# ============================================================


def test_analyze_authentication(sample_results):
    result = analyze_authentication(
        sample_results
    )

    assert result["method_counts"]["OAuth2"] == 2
    assert result["method_counts"]["API Key"] == 2

    assert (
        result["method_percentages"]["OAuth2"]
        == pytest.approx(66.67)
    )


def test_analyze_api(sample_results):
    result = analyze_api(
        sample_results
    )

    assert result["type_counts"]["REST"] == 2
    assert result["type_counts"]["GraphQL"] == 1

    assert result["breadth_counts"]["Broad"] == 2
    assert result["breadth_counts"]["Narrow"] == 1


def test_analyze_mcp(sample_results):
    result = analyze_mcp(
        sample_results
    )

    assert (
        result["status_counts"]["Official MCP"]
        == 1
    )

    assert (
        result["status_counts"]["Third-party MCP"]
        == 1
    )

    assert (
        result["status_counts"]["Unknown"]
        == 1
    )


def test_analyze_buildability(sample_results):
    result = analyze_buildability(
        sample_results
    )

    assert result["verdict_counts"]["Easy"] == 1
    assert result["verdict_counts"]["Possible"] == 1
    assert result["verdict_counts"]["Blocked"] == 1


def test_analyze_access(sample_results):
    result = analyze_access(
        sample_results
    )

    assert (
        result["type_counts"]["Free"]
        == 2
    )

    assert (
        result["type_counts"]["Paid Plan Required"]
        == 1
    )

    assert (
        result["requirement_counts"][
            "Admin Approval Required"
        ]
        == 1
    )


def test_analyze_categories(sample_results):
    result = analyze_categories(
        sample_results
    )

    assert result["category_counts"]["CRM"] == 2
    assert result["category_counts"]["Finance"] == 1


def test_analyze_confidence(sample_results):
    result = analyze_confidence(
        sample_results
    )

    assert result["records_available"] == 3

    assert result["average"] == pytest.approx(
        0.8,
        abs=0.0001,
    )

    assert result["minimum"] == pytest.approx(
        0.7,
        abs=0.0001,
    )

    assert result["maximum"] == pytest.approx(
        0.9,
        abs=0.0001,
    )


def test_analyze_evidence(sample_results):
    result = analyze_evidence(
        sample_results
    )

    assert result["total_evidence_items"] == 7

    assert result["average_evidence_per_app"] == pytest.approx(
        7 / 3,
        abs=0.01,
    )

    assert result["minimum_evidence"] == 1
    assert result["maximum_evidence"] == 4


# ============================================================
# VERIFICATION
# ============================================================


def test_analyze_verification_handles_missing_metadata(
    sample_results,
):
    result = analyze_verification(
        sample_results
    )

    assert result["records_available"] == 2
    assert result["passed"] == 2
    assert result["failed"] == 0

    assert result["pass_rate_percent"] == 100.0

    assert result["average_score"] == pytest.approx(
        97.5
    )


# ============================================================
# BLOCKERS
# ============================================================


def test_analyze_blockers(sample_results):
    result = analyze_blockers(
        sample_results
    )

    assert (
        result["blocker_counts"][
            "Admin approval"
        ]
        == 1
    )

    assert (
        result["blocker_counts"][
            "No API access"
        ]
        == 1
    )


# ============================================================
# PATTERN DETECTION
# ============================================================


def test_generate_patterns(sample_results):
    patterns = generate_patterns(
        sample_results
    )

    titles = [
        pattern["title"]
        for pattern in patterns
    ]

    assert any(
        "OAuth" in title
        for title in titles
    )

    assert any(
        "REST" in title
        for title in titles
    )

    assert any(
        "Easy" in title
        for title in titles
    )

    assert any(
        "Official MCP" in title
        for title in titles
    )


def test_generate_patterns_empty_results():
    assert (
        generate_patterns([])
        == []
    )


# ============================================================
# INTEGRATION SCORE
# ============================================================


def test_buildability_score_constants():
    assert BUILDABILITY_SCORES["Easy"] == 100
    assert BUILDABILITY_SCORES["Possible"] == 70
    assert BUILDABILITY_SCORES["Blocked"] == 20


def test_mcp_score_constants():
    assert MCP_SCORES["Official MCP"] == 100
    assert MCP_SCORES["Third-party MCP"] == 70
    assert MCP_SCORES["Unknown"] == 40
    assert MCP_SCORES["No MCP Found"] == 0


def test_integration_score_is_between_zero_and_hundred(
    sample_results,
):
    for result in sample_results:
        score, components = (
            calculate_integration_score(
                result
            )
        )

        assert 0 <= score <= 100

        assert isinstance(
            components,
            dict,
        )


def test_missing_verification_does_not_become_zero(
    sample_results,
):
    gamma = sample_results[2]

    score, components = (
        calculate_integration_score(
            gamma
        )
    )

    assert score > 0

    assert (
        components[
            "verification"
        ]
        is None
    )

    assert (
        components[
            "verification_available"
        ]
        is False
    )


def test_missing_verification_redistributes_weight(
    sample_results,
):
    gamma = sample_results[2]

    score, components = (
        calculate_integration_score(
            gamma
        )
    )

    weights = components[
        "weights_used"
    ]

    assert "verification" not in weights

    assert sum(
        weights.values()
    ) == pytest.approx(
        1.0,
        abs=0.0001,
    )


def test_complete_record_uses_all_score_components(
    sample_results,
):
    alpha = sample_results[0]

    score, components = (
        calculate_integration_score(
            alpha
        )
    )

    assert 0 <= score <= 100

    assert (
        components[
            "verification_available"
        ]
        is True
    )

    assert (
        components[
            "verification"
        ]
        == 100
    )

    assert set(
        components["weights_used"]
    ) == {
        "buildability",
        "mcp",
        "evidence",
        "verification",
        "confidence",
    }

    assert sum(
        components["weights_used"].values()
    ) == pytest.approx(
        1.0,
        abs=0.0001,
    )


# ============================================================
# COMPARISON RECORDS
# ============================================================


def test_build_comparison_records(sample_results):
    records = build_comparison_records(
        sample_results
    )

    assert len(records) == 3

    assert records[0]["app_name"] == "Alpha"

    assert (
        records[0]["integration_score"]
        > 0
    )

    assert (
        records[0]["evidence_count"]
        == 4
    )

    assert (
        records[2]["verification_passed"]
        is None
    )


# ============================================================
# RANKING
# ============================================================


def test_rank_records_is_deterministic(
    sample_results,
):
    records = build_comparison_records(
        sample_results
    )

    ranking_one = rank_records(
        records
    )

    ranking_two = rank_records(
        records
    )

    assert ranking_one == ranking_two

    assert [
        item["rank"]
        for item in ranking_one
    ] == [1, 2, 3]


def test_rank_records_has_descending_scores(
    sample_results,
):
    records = build_comparison_records(
        sample_results
    )

    ranked = rank_records(
        records
    )

    scores = [
        item["integration_score"]
        for item in ranked
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_buildability_ranking(
    sample_results,
):
    records = build_comparison_records(
        sample_results
    )

    ranking = build_buildability_ranking(
        records
    )

    assert len(ranking) == 3

    assert ranking[0]["buildability"] == "Easy"
    assert ranking[1]["buildability"] == "Possible"
    assert ranking[2]["buildability"] == "Blocked"


def test_mcp_ranking(
    sample_results,
):
    records = build_comparison_records(
        sample_results
    )

    ranking = build_mcp_ranking(
        records
    )

    assert len(ranking) == 3

    assert ranking[0]["mcp_status"] == (
        "Official MCP"
    )

    assert ranking[1]["mcp_status"] == (
        "Third-party MCP"
    )


# ============================================================
# COMPARISON MATRIX
# ============================================================


def test_comparison_matrix_contains_all_apps(
    sample_results,
):
    records = build_comparison_records(
        sample_results
    )

    ranked = rank_records(
        records
    )

    matrix = build_comparison_matrix(
        ranked
    )

    assert len(matrix) == 3

    names = [
        row["app_name"]
        for row in matrix
    ]

    assert set(names) == {
        "Alpha",
        "Beta",
        "Gamma",
    }


def test_comparison_matrix_verification_status(
    sample_results,
):
    records = build_comparison_records(
        sample_results
    )

    ranked = rank_records(
        records
    )

    matrix = build_comparison_matrix(
        ranked
    )

    statuses = {
        row["app_name"]: row[
            "verification"
        ]
        for row in matrix
    }

    assert statuses["Alpha"] == "Passed"
    assert statuses["Beta"] == "Passed"
    assert statuses["Gamma"] == "Unavailable"


# ============================================================
# RANKING INSIGHTS
# ============================================================


def test_generate_ranking_insights(
    sample_results,
):
    records = build_comparison_records(
        sample_results
    )

    ranked = rank_records(
        records
    )

    insights = generate_ranking_insights(
        ranked
    )

    assert insights

    assert any(
        "ranks #1" in insight
        for insight in insights
    )

    assert any(
        "Easy to build" in insight
        for insight in insights
    )


def test_generate_ranking_insights_empty():
    assert (
        generate_ranking_insights([])
        == []
    )


# ============================================================
# QUALITY NOTES
# ============================================================


def test_quality_notes_warn_about_partial_dataset(
    sample_results,
):
    notes = generate_quality_notes(
        sample_results
    )

    assert any(
        "Only 3 completed application" in note
        for note in notes
    )


def test_quality_notes_warn_about_missing_verification(
    sample_results,
):
    notes = generate_quality_notes(
        sample_results
    )

    assert any(
        "verification metadata" in note
        for note in notes
    )


def test_quality_notes_include_scoring_limitation(
    sample_results,
):
    notes = generate_quality_notes(
        sample_results
    )

    assert any(
        "prioritization heuristic" in note
        for note in notes
    )


# ============================================================
# COMPLETE ANALYSIS
# ============================================================


def test_analyze_returns_expected_sections(
    sample_results,
):
    analysis = analyze(
        sample_results
    )

    expected_sections = {
        "metadata",
        "authentication",
        "access",
        "api",
        "mcp",
        "buildability",
        "categories",
        "confidence",
        "evidence",
        "verification",
        "common_blockers",
        "patterns",
        "comparison",
        "quality_notes",
    }

    assert expected_sections.issubset(
        analysis.keys()
    )


def test_analyze_comparison_contains_rankings(
    sample_results,
):
    analysis = analyze(
        sample_results
    )

    comparison = analysis[
        "comparison"
    ]

    assert comparison[
        "overall_ranking"
    ]

    assert comparison[
        "buildability_ranking"
    ]

    assert comparison[
        "mcp_ranking"
    ]

    assert comparison[
        "matrix"
    ]

    assert comparison[
        "insights"
    ]


def test_analyze_metadata(
    sample_results,
):
    analysis = analyze(
        sample_results
    )

    metadata = analysis[
        "metadata"
    ]

    assert (
        metadata[
            "applications_analyzed"
        ]
        == 3
    )

    assert (
        metadata[
            "verification_records_available"
        ]
        == 2
    )

    assert (
        metadata[
            "analysis_records_available"
        ]
        == 3
    )


def test_analyze_empty_results():
    analysis = analyze([])

    assert (
        analysis[
            "metadata"
        ]["applications_analyzed"]
        == 0
    )

    assert (
        analysis[
            "patterns"
        ]
        == []
    )

    assert (
        analysis[
            "comparison"
        ]["overall_ranking"]
        == []
    )

    assert (
        analysis[
            "comparison"
        ]["matrix"]
        == []
    )


# ============================================================
# JSON SERIALIZATION
# ============================================================


def test_analysis_is_json_serializable(
    sample_results,
):
    analysis = analyze(
        sample_results
    )

    serialized = json.dumps(
        analysis
    )

    assert isinstance(
        serialized,
        str,
    )


def test_save_analysis_creates_valid_json(
    sample_results,
    tmp_path,
    monkeypatch,
):
    import src.cross_app_analysis as module

    output_file = (
        tmp_path
        / "cross_app_analysis.json"
    )

    monkeypatch.setattr(
        module,
        "OUTPUT_FILE",
        output_file,
    )

    analysis = analyze(
        sample_results
    )

    save_analysis(
        analysis
    )

    assert output_file.exists()

    with output_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        saved = json.load(file)

    assert saved == analysis