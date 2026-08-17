import json
from pathlib import Path

from src.gemini_client import GeminiQuotaError
from src.pipeline import ResearchPipeline


class FakeResult:
    """Small replacement for AppResearch in pipeline tests."""

    def __init__(
        self,
        app_id: int,
        app_name: str,
    ):
        self.app_id = app_id
        self.app_name = app_name

    def model_dump(self, mode="json"):
        return {
            "app_id": self.app_id,
            "app_name": self.app_name,
            "category": "Test",
        }


class FakeAgent:
    """Deterministic research agent for tests."""

    def __init__(self):
        self.calls = []

    def research_app(self, app):
        self.calls.append(app["id"])

        return FakeResult(
            app_id=app["id"],
            app_name=app["name"],
        )


def create_apps_file(
    tmp_path: Path,
):
    """Create a small deterministic application dataset."""

    apps = [
        {
            "id": 1,
            "name": "App One",
            "category": "Test",
            "website": "https://example.com",
        },
        {
            "id": 2,
            "name": "App Two",
            "category": "Test",
            "website": "https://example.com",
        },
        {
            "id": 3,
            "name": "App Three",
            "category": "Test",
            "website": "https://example.com",
        },
    ]

    path = tmp_path / "apps.json"

    path.write_text(
        json.dumps(apps),
        encoding="utf-8",
    )

    return path


def test_pipeline_processes_apps(
    tmp_path,
):
    """Pipeline should process all applications successfully."""

    apps_path = create_apps_file(
        tmp_path
    )

    pipeline = ResearchPipeline(
        apps_path=str(apps_path),
        results_dir=str(
            tmp_path / "results"
        ),
    )

    fake_agent = FakeAgent()
    pipeline.agent = fake_agent

    pipeline.run()

    assert fake_agent.calls == [
        1,
        2,
        3,
    ]

    results = json.loads(
        (
            tmp_path
            / "results"
            / "results.json"
        ).read_text(
            encoding="utf-8",
        )
    )

    assert len(results) == 3


def test_pipeline_resumes_completed_apps(
    tmp_path,
):
    """Pipeline should skip applications already present in results."""

    apps_path = create_apps_file(
        tmp_path
    )

    results_dir = (
        tmp_path / "results"
    )

    results_dir.mkdir()

    existing_results = [
        {
            "app_id": 1,
            "app_name": "App One",
        }
    ]

    (
        results_dir / "results.json"
    ).write_text(
        json.dumps(existing_results),
        encoding="utf-8",
    )

    pipeline = ResearchPipeline(
        apps_path=str(apps_path),
        results_dir=str(results_dir),
    )

    fake_agent = FakeAgent()
    pipeline.agent = fake_agent

    pipeline.run()

    assert fake_agent.calls == [
        2,
        3,
    ]


def test_pipeline_stops_on_quota_error(
    tmp_path,
):
    """
    Pipeline should pause immediately when Gemini quota is exhausted.

    This is important for the real 100-app run because continuing after
    a quota error would waste retries and API calls.
    """

    apps_path = create_apps_file(
        tmp_path
    )

    pipeline = ResearchPipeline(
        apps_path=str(apps_path),
        results_dir=str(
            tmp_path / "results"
        ),
    )

    class QuotaAgent:
        def __init__(self):
            self.calls = []

        def research_app(self, app):
            self.calls.append(
                app["id"]
            )

            raise GeminiQuotaError(
                "Gemini API quota exhausted."
            )

    fake_agent = QuotaAgent()

    pipeline.agent = fake_agent

    pipeline.run()

    # Only the first application should be attempted.
    # The pipeline must stop rather than continuing through the dataset.
    assert fake_agent.calls == [1]

    progress = json.loads(
        (
            tmp_path
            / "results"
            / "progress.json"
        ).read_text(
            encoding="utf-8",
        )
    )

    assert progress["status"] == "paused"

    # Keep the expected value identical to the actual exception message.
    assert (
        progress["stop_reason"]
        == "Gemini API quota exhausted."
    )


def test_pipeline_persists_failures(
    tmp_path,
):
    """Pipeline should persist failed applications."""

    apps_path = create_apps_file(
        tmp_path
    )

    pipeline = ResearchPipeline(
        apps_path=str(apps_path),
        results_dir=str(
            tmp_path / "results"
        ),
    )

    class FailingAgent:
        def research_app(self, app):
            raise ValueError(
                "Application research failed."
            )

    pipeline.agent = FailingAgent()

    # Make the test fast.
    pipeline.max_retries = 1

    pipeline.run()

    failures = json.loads(
        (
            tmp_path
            / "results"
            / "failures.json"
        ).read_text(
            encoding="utf-8",
        )
    )

    assert len(failures) == 3

    assert failures[0]["app_id"] == 1
    assert failures[0]["scope"] == "application"