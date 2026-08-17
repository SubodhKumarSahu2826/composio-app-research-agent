import json
from pathlib import Path


def test_research_dataset():
    path = Path("data/apps.json")

    with path.open("r", encoding="utf-8") as file:
        apps = json.load(file)

    assert len(apps) == 100

    ids = [app["id"] for app in apps]

    assert ids == list(range(1, 101))

    for app in apps:
        assert app["name"]
        assert app["category"]
        assert app["website"]