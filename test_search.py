from src.web_tools import WebResearchTool


tool = WebResearchTool()

results = tool.search(
    "Salesforce API authentication official developer documentation",
    official_domain="salesforce.com",
    max_results=5,
)

for index, result in enumerate(results, start=1):
    print(f"\n--- Result {index} ---")
    print("Title:", result.get("title"))
    print("URL:", result.get("url"))
    print("Authority:", result.get("authority_score"))
    print("Content:", result.get("content", "")[:500])