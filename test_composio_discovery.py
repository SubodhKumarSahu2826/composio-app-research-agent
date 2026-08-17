from src.composio_tools import ComposioResearchTool


tool = ComposioResearchTool()

apps = [
    "Salesforce",
    "Slack",
    "GitHub",
    "Shopify",
    "Stripe",
]

for app in apps:
    result = tool.find_toolkit(app)

    print("\n==============================")
    print("Application:", result["app_name"])
    print("Toolkit found:", result["toolkit_found"])
    print("Toolkit name:", result["toolkit_name"])
    print("Toolkit slug:", result["toolkit_slug"])
    print("Tool count:", result["tool_count"])
    print("Trigger count:", result["trigger_count"])
    print("Auth:", result["auth_schemes"])
    print("App URL:", result["app_url"])
    print("==============================")

    if result["toolkit_found"]:
        tools = tool.get_toolkit_tools(
            result["toolkit_slug"],
            limit=3,
        )

        print("Sample tools:")

        for item in tools:
            print(
                f"  - {item['slug']}: "
                f"{item['name']}"
            )