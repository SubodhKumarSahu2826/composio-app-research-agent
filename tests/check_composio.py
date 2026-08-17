from dotenv import load_dotenv
from composio import Composio

load_dotenv()

composio = Composio()

session = composio.sessions.create(
    user_id="research-agent",
    mcp=True,
)

print("Composio: OK")
print("Session ID:", session.session_id)
print("MCP URL:", session.mcp.url)