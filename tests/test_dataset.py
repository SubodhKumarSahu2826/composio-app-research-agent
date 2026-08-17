from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APPS_FILE = PROJECT_ROOT / "data" / "apps.json"


def load_apps() -> list[dict]:
    with APPS_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_apps_file_exists():
    assert APPS_FILE.exists()


def test_dataset_contains_100_apps():
    apps = load_apps()

    assert isinstance(
        apps,
        list,
    )

    assert len(apps) == 100


def test_app_ids_are_unique():
    apps = load_apps()

    ids = [
        app["id"]
        for app in apps
    ]

    assert len(ids) == len(
        set(ids)
    )


def test_app_ids_are_sequential():
    apps = load_apps()

    ids = [
        app["id"]
        for app in apps
    ]

    assert ids == list(
        range(1, 101)
    )


def test_required_app_fields_exist():
    apps = load_apps()

    required_fields = {
        "id",
        "name",
        "category",
        "website",
    }

    for app in apps:
        missing = (
            required_fields
            - app.keys()
        )

        assert not missing, (
            f"App {app.get('id')} "
            f"is missing fields: "
            f"{sorted(missing)}"
        )


def test_app_names_are_unique():
    apps = load_apps()

    names = [
        app["name"].strip().lower()
        for app in apps
    ]

    assert len(names) == len(
        set(names)
    )


def test_websites_are_valid_or_explicitly_unresolved():
    """
    Validate website metadata without requiring every dataset
    record to have a verified public URL.

    Normal records must contain an HTTP/HTTPS URL.

    Records with unresolved website metadata must provide a
    non-empty hint so the research pipeline can identify the
    application without pretending the value is an official URL.
    """

    apps = load_apps()

    for app in apps:
        website = app["website"]

        assert isinstance(
            website,
            str,
        )

        website = website.strip()

        assert website, (
            f"App {app['id']} has an empty "
            "website field."
        )

        if website.startswith(
            (
                "http://",
                "https://",
            )
        ):
            continue

        # Non-URL website values are allowed only when the
        # dataset provides a hint identifying the application.
        hint = app.get("hint")

        assert isinstance(
            hint,
            str,
        ), (
            f"App {app['id']} has a non-URL "
            "website but no valid hint."
        )

        assert hint.strip(), (
            f"App {app['id']} has a non-URL "
            "website and an empty hint."
        )


def test_categories_are_present():
    apps = load_apps()

    for app in apps:
        assert isinstance(
            app["category"],
            str,
        )

        assert app["category"].strip()


def test_dataset_has_reasonable_category_distribution():
    apps = load_apps()

    categories = {
        app["category"]
        for app in apps
    }

    # Prevent accidentally shipping a dataset where every
    # application belongs to one category.
    assert len(categories) >= 5