import json
import time
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.gemini_client import GeminiQuotaError
from src.research_agent import ResearchAgent


class ResearchPipeline:
    """
    Batch execution pipeline for the application research system.

    Responsibilities:

    - Load applications
    - Process applications sequentially
    - Retry temporary application failures
    - Stop safely on exhausted global API quota
    - Save successful results immediately
    - Save failed applications separately
    - Resume previously completed work
    - Persist progress checkpoints
    - Persist Phase 2 verification metadata
    - Persist Phase 2 analysis metadata
    """

    def __init__(
        self,
        apps_path: str = "data/apps.json",
        results_dir: str = "results",
        max_retries: int = 3,
        retry_delay: int = 5,
    ) -> None:
        self.apps_path = Path(apps_path)
        self.results_dir = Path(results_dir)

        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.results_file = (
            self.results_dir / "results.json"
        )

        self.progress_file = (
            self.results_dir / "progress.json"
        )

        self.failures_file = (
            self.results_dir / "failures.json"
        )

        self.results_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.agent = ResearchAgent()

    # =========================================================
    # DATA LOADING
    # =========================================================

    def load_apps(self) -> list[dict]:
        """Load the application dataset."""

        with self.apps_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            apps = json.load(file)

        if not isinstance(apps, list):
            raise ValueError(
                "apps.json must contain a JSON list."
            )

        return apps

    def load_results(self) -> list[dict]:
        """Load previously completed results."""

        if not self.results_file.exists():
            return []

        try:
            with self.results_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except (
            json.JSONDecodeError,
            OSError,
        ):
            return []

        return (
            data
            if isinstance(data, list)
            else []
        )

    def load_failures(self) -> list[dict]:
        """Load previously recorded failures."""

        if not self.failures_file.exists():
            return []

        try:
            with self.failures_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except (
            json.JSONDecodeError,
            OSError,
        ):
            return []

        return (
            data
            if isinstance(data, list)
            else []
        )

    # =========================================================
    # PERSISTENCE
    # =========================================================

    def save_results(
        self,
        results: list[dict],
    ) -> None:
        """Persist successful results atomically."""

        temporary_file = (
            self.results_dir
            / "results.tmp.json"
        )

        with temporary_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                results,
                file,
                indent=2,
                ensure_ascii=False,
            )

        temporary_file.replace(
            self.results_file
        )

    def save_failures(
        self,
        failures: list[dict],
    ) -> None:
        """Persist failures atomically."""

        temporary_file = (
            self.results_dir
            / "failures.tmp.json"
        )

        with temporary_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                failures,
                file,
                indent=2,
                ensure_ascii=False,
            )

        temporary_file.replace(
            self.failures_file
        )

    def save_progress(
        self,
        total: int,
        completed: int,
        failed: int,
        status: str = "running",
        stop_reason: str | None = None,
    ) -> None:
        """Persist pipeline progress."""

        progress = {
            "total": total,
            "completed": completed,
            "failed": failed,
            "remaining": max(
                total - completed - failed,
                0,
            ),
            "status": status,
            "stop_reason": stop_reason,
        }

        temporary_file = (
            self.results_dir
            / "progress.tmp.json"
        )

        with temporary_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                progress,
                file,
                indent=2,
            )

        temporary_file.replace(
            self.progress_file
        )

    # =========================================================
    # JSON SERIALIZATION
    # =========================================================

    @staticmethod
    def _make_json_serializable(
        value: Any,
    ) -> Any:
        """
        Convert Phase 2 objects into JSON-compatible data.

        Handles:

        - Pydantic models
        - dataclasses
        - enums
        - dictionaries
        - lists / tuples / sets
        - primitive values
        """

        if value is None:
            return None

        if isinstance(value, Enum):
            return value.value

        if hasattr(
            value,
            "model_dump",
        ):
            try:
                dumped = value.model_dump(
                    mode="json"
                )
            except TypeError:
                dumped = value.model_dump()

            return ResearchPipeline._make_json_serializable(
                dumped
            )

        if is_dataclass(value):
            return ResearchPipeline._make_json_serializable(
                asdict(value)
            )

        if isinstance(value, dict):
            return {
                str(key): ResearchPipeline._make_json_serializable(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):
            return [
                ResearchPipeline._make_json_serializable(
                    item
                )
                for item in value
            ]

        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        # Last-resort conversion for unexpected objects.
        return str(value)

    # =========================================================
    # PHASE 2 METADATA
    # =========================================================

    @staticmethod
    def _serialize_phase2_metadata(
        result: Any,
    ) -> dict:
        """
        Serialize deterministic Phase 2 metadata.

        ResearchAgent attaches:

            result._verification
            result._analysis

        These runtime attributes are not included in
        AppResearch.model_dump().
        """

        metadata: dict = {}

        verification = getattr(
            result,
            "_verification",
            None,
        )

        if verification is not None:
            metadata["verification"] = (
                ResearchPipeline._make_json_serializable(
                    verification
                )
            )

        analysis = getattr(
            result,
            "_analysis",
            None,
        )

        if analysis is not None:
            metadata["analysis"] = (
                ResearchPipeline._make_json_serializable(
                    analysis
                )
            )

        return metadata

    # =========================================================
    # RETRY HANDLING
    # =========================================================

    def _research_with_retry(
        self,
        app: dict,
    ) -> Any:
        """
        Research one application with bounded retries.

        Gemini quota exhaustion is propagated immediately.

        Other application-level errors are retried.
        """

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.max_retries + 1,
        ):
            try:
                return self.agent.research_app(
                    app
                )

            except GeminiQuotaError:
                raise

            except Exception as exc:
                last_error = exc

                print(
                    f"  Attempt {attempt}/"
                    f"{self.max_retries} failed: "
                    f"{type(exc).__name__}: {exc}"
                )

                if attempt >= self.max_retries:
                    break

                print(
                    f"  Retrying in "
                    f"{self.retry_delay}s..."
                )

                time.sleep(
                    self.retry_delay
                )

        raise RuntimeError(
            f"Research failed after "
            f"{self.max_retries} attempts."
        ) from last_error

    # =========================================================
    # MAIN PIPELINE
    # =========================================================

    def run(
        self,
        limit: int | None = None,
    ) -> None:
        """
        Execute the research pipeline.

        Args:
            limit:
                Optional number of applications to process.
        """

        apps = self.load_apps()

        if limit is not None:
            apps = apps[:limit]

        total = len(apps)

        results = self.load_results()
        failures = self.load_failures()

        completed_ids = {
            item.get("app_id")
            for item in results
            if item.get("app_id") is not None
        }

        failed_ids = {
            item.get("app_id")
            for item in failures
            if item.get("app_id") is not None
        }

        print()
        print("=" * 70)
        print("RESEARCH PIPELINE")
        print("=" * 70)

        print(
            f"Applications in run: {total}"
        )

        print(
            f"Previously completed: "
            f"{len(completed_ids)}"
        )

        print(
            f"Previously failed: "
            f"{len(failed_ids)}"
        )

        print("=" * 70)

        stopped_early = False
        stop_reason = None

        for index, app in enumerate(
            apps,
            start=1,
        ):
            app_id = app["id"]
            app_name = app["name"]

            # -------------------------------------------------
            # Already completed
            # -------------------------------------------------

            if app_id in completed_ids:
                print(
                    f"\n[{index}/{total}] "
                    f"Skipping {app_name} "
                    f"(already completed)"
                )
                continue

            # -------------------------------------------------
            # Previously failed
            # -------------------------------------------------

            if app_id in failed_ids:
                print(
                    f"\n[{index}/{total}] "
                    f"Retrying previous failure: "
                    f"{app_name}"
                )
            else:
                print(
                    f"\n[{index}/{total}] "
                    f"Processing: {app_name}"
                )

            try:
                result = self._research_with_retry(
                    app
                )

                # -------------------------------------------------
                # Build complete result BEFORE modifying state.
                # -------------------------------------------------

                result_dict = result.model_dump(
                    mode="json"
                )

                phase2_metadata = (
                    self._serialize_phase2_metadata(
                        result
                    )
                )

                result_dict.update(
                    phase2_metadata
                )

                # -------------------------------------------------
                # Validate JSON serializability BEFORE modifying
                # completed_ids.
                # -------------------------------------------------

                json.dumps(
                    result_dict,
                    ensure_ascii=False,
                )

                # -------------------------------------------------
                # Remove previous failure after successful research.
                # -------------------------------------------------

                new_failures = [
                    failure
                    for failure in failures
                    if failure.get("app_id")
                    != app_id
                ]

                # -------------------------------------------------
                # Replace existing result.
                # -------------------------------------------------

                new_results = [
                    existing
                    for existing in results
                    if existing.get("app_id")
                    != app_id
                ]

                new_results.append(
                    result_dict
                )

                # -------------------------------------------------
                # Persist everything BEFORE marking app completed.
                # -------------------------------------------------

                self.save_results(
                    new_results
                )

                self.save_failures(
                    new_failures
                )

                # -------------------------------------------------
                # Only now update in-memory state.
                # -------------------------------------------------

                results = new_results
                failures = new_failures

                failed_ids.discard(
                    app_id
                )

                completed_ids.add(
                    app_id
                )

                self.save_progress(
                    total=total,
                    completed=len(
                        completed_ids
                    ),
                    failed=len(
                        failed_ids
                    ),
                )

                print(
                    f"  ✓ Completed: "
                    f"{app_name}"
                )

            # =====================================================
            # GLOBAL GEMINI QUOTA FAILURE
            # =====================================================

            except GeminiQuotaError as exc:

                failure = {
                    "app_id": app_id,
                    "app_name": app_name,
                    "error_type": type(
                        exc
                    ).__name__,
                    "error": str(exc),
                    "scope": "global",
                }

                failures = [
                    existing
                    for existing in failures
                    if existing.get("app_id")
                    != app_id
                ]

                failures.append(
                    failure
                )

                failed_ids.add(
                    app_id
                )

                self.save_failures(
                    failures
                )

                self.save_progress(
                    total=total,
                    completed=len(
                        completed_ids
                    ),
                    failed=len(
                        failed_ids
                    ),
                    status="paused",
                    stop_reason=(
                        "Gemini API quota exhausted"
                    ),
                )

                print()
                print(
                    "!" * 70
                )
                print(
                    "PIPELINE PAUSED"
                )
                print(
                    "!" * 70
                )
                print(
                    "Gemini API quota is exhausted."
                )
                print(
                    "Successful results have been saved."
                )
                print(
                    "Resume the pipeline after the quota "
                    "becomes available."
                )
                print(
                    "!" * 70
                )

                stopped_early = True
                stop_reason = str(
                    exc
                )

                break

            # =====================================================
            # APPLICATION FAILURE
            # =====================================================

            except Exception as exc:

                failure = {
                    "app_id": app_id,
                    "app_name": app_name,
                    "error_type": type(
                        exc
                    ).__name__,
                    "error": str(exc),
                    "scope": "application",
                }

                failures = [
                    existing
                    for existing in failures
                    if existing.get("app_id")
                    != app_id
                ]

                failures.append(
                    failure
                )

                failed_ids.add(
                    app_id
                )

                self.save_failures(
                    failures
                )

                self.save_progress(
                    total=total,
                    completed=len(
                        completed_ids
                    ),
                    failed=len(
                        failed_ids
                    ),
                )

                print(
                    f"  ✗ Failed: "
                    f"{app_name}"
                )

                print(
                    f"    Error: {exc}"
                )

                continue

        # =========================================================
        # FINAL SUMMARY
        # =========================================================

        status = (
            "paused"
            if stopped_early
            else "completed"
        )

        remaining = max(
            total
            - len(completed_ids)
            - len(failed_ids),
            0,
        )

        self.save_progress(
            total=total,
            completed=len(
                completed_ids
            ),
            failed=len(
                failed_ids
            ),
            status=status,
            stop_reason=stop_reason,
        )

        print()
        print("=" * 70)
        print("PIPELINE COMPLETE")
        print("=" * 70)

        print(
            f"Total:       {total}"
        )

        print(
            f"Completed:   "
            f"{len(completed_ids)}"
        )

        print(
            f"Failed:      "
            f"{len(failed_ids)}"
        )

        print(
            f"Remaining:   {remaining}"
        )

        print(
            f"Status:      {status}"
        )

        print()

        print(
            f"Results:     "
            f"{self.results_file}"
        )

        print(
            f"Failures:    "
            f"{self.failures_file}"
        )

        print(
            f"Progress:    "
            f"{self.progress_file}"
        )

        print("=" * 70)


def main() -> None:
    """Phase 2 development entry point."""

    pipeline = ResearchPipeline()

    pipeline.run(
        limit=3
    )


if __name__ == "__main__":
    main()