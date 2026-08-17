from src.composio_tools import ComposioResearchTool


def test_composio_toolkit_discovery():
    tool = ComposioResearchTool()

    result = tool.find_toolkit("Salesforce")

    assert result["app_name"] == "Salesforce"
    assert result["toolkit_found"] is True
    assert result["toolkit_slug"] == "salesforce"
    assert result["toolkit_name"] == "Salesforce"
    assert result["tool_count"] > 0
    assert result["source"] == "Composio"


def test_composio_tool_discovery():
    tool = ComposioResearchTool()

    result = tool.find_toolkit("Salesforce")

    assert result["toolkit_found"] is True

    tools = tool.get_toolkit_tools(
        toolkit_slug=result["toolkit_slug"],
        limit=5,
    )

    assert tools
    assert len(tools) <= 5

    for item in tools:
        assert item["slug"]