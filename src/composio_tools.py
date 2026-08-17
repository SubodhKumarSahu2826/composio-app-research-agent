from typing import Any

from composio import Composio

from src.config import COMPOSIO_API_KEY


class ComposioResearchTool:
    """
    Discover Composio integrations for an application.

    This component only performs discovery. It does not execute
    application actions or connect user accounts.
    """

    def __init__(self) -> None:
        self.composio = Composio(api_key=COMPOSIO_API_KEY)

    def find_toolkit(self, app_name: str) -> dict[str, Any]:
        """
        Find a Composio toolkit for an application.

        We first inspect Composio's toolkit catalog and match the
        application by name. Once the matching slug is found, we
        retrieve the complete toolkit metadata.
        """

        try:
            toolkit_slug = self._find_toolkit_slug(app_name)

            if not toolkit_slug:
                return self._not_found_result(app_name)

            toolkit = self.composio.toolkits.get(
                slug=toolkit_slug
            )

            return {
                "app_name": app_name,
                "toolkit_found": True,
                "toolkit_slug": toolkit.slug,
                "toolkit_name": toolkit.name,
                "description": toolkit.meta.description,
                "tool_count": int(toolkit.meta.tools_count),
                "trigger_count": int(toolkit.meta.triggers_count),
                "type": toolkit.type,
                "auth_schemes": toolkit.meta.auth_schemes
                if hasattr(toolkit.meta, "auth_schemes")
                else [],
                "app_url": toolkit.meta.app_url,
                "source": "Composio",
            }

        except Exception as exc:
            return {
                "app_name": app_name,
                "toolkit_found": False,
                "toolkit_slug": None,
                "toolkit_name": None,
                "description": None,
                "tool_count": 0,
                "trigger_count": 0,
                "type": None,
                "auth_schemes": [],
                "app_url": None,
                "source": "Composio",
                "error": str(exc),
            }

    def get_toolkit_tools(
        self,
        toolkit_slug: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Retrieve a sample of tools exposed by a Composio toolkit.

        This is used for capability discovery, not execution.
        """

        try:
            tools = self.composio.tools.get_raw_composio_tools(
                toolkits=[toolkit_slug],
                limit=limit,
            )

            return [
                {
                    "slug": getattr(tool, "slug", None),
                    "name": getattr(tool, "name", None),
                    "description": getattr(
                        tool,
                        "description",
                        None,
                    ),
                }
                for tool in tools
            ]

        except Exception:
            return []

    def _find_toolkit_slug(
        self,
        app_name: str,
    ) -> str | None:
        """
        Find the best matching toolkit slug from Composio's catalog.
        """

        response = self.composio.toolkits.list()

        toolkits = response.items

        normalized_app = self._normalize(app_name)

        # First: exact name match.
        for toolkit in toolkits:
            if self._normalize(toolkit.name) == normalized_app:
                return toolkit.slug

        # Second: exact slug match.
        for toolkit in toolkits:
            if self._normalize(toolkit.slug) == normalized_app:
                return toolkit.slug

        # Third: controlled partial matching.
        for toolkit in toolkits:
            toolkit_name = self._normalize(toolkit.name)
            toolkit_slug = self._normalize(toolkit.slug)

            if (
                normalized_app in toolkit_name
                or normalized_app in toolkit_slug
            ):
                return toolkit.slug

        return None

    @staticmethod
    def _normalize(value: str) -> str:
        """
        Normalize application names for matching.

        Examples:

        "Salesforce"       -> "salesforce"
        "Zoho CRM"         -> "zohocrm"
        "Monday.com"       -> "mondaycom"
        """
        return "".join(
            character.lower()
            for character in value
            if character.isalnum()
        )

    @staticmethod
    def _not_found_result(
        app_name: str,
    ) -> dict[str, Any]:
        return {
            "app_name": app_name,
            "toolkit_found": False,
            "toolkit_slug": None,
            "toolkit_name": None,
            "description": None,
            "tool_count": 0,
            "trigger_count": 0,
            "type": None,
            "auth_schemes": [],
            "app_url": None,
            "source": "Composio",
        }