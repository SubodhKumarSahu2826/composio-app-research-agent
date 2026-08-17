import os

from dotenv import load_dotenv


load_dotenv()


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY is not configured")

if not COMPOSIO_API_KEY:
    raise RuntimeError("COMPOSIO_API_KEY is not configured")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured")