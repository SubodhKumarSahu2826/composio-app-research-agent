import json
from typing import Any
from urllib.parse import urlparse

from src.gemini_client import GeminiClient
from src.models import AppResearch


class ResearchExtractor:
    """
    Extract structured research findings from retrieved evidence.

    Architecture:

        Retrieved Evidence
               ↓
        Stable WEB-* evidence IDs
               ↓
        Gemini selects evidence IDs
               ↓
        Python normalizes LLM output
               ↓
        Python resolves provenance
               ↓
        Pydantic validation

    Gemini is NOT trusted to generate:

        - URLs
        - source names
        - source types
        - evidence snippets

    Gemini only decides:

        - what the claim is
        - which evidence ID supports it
        - which evidence ID supports API documentation
        - which evidence ID supports MCP

    Python resolves all provenance-sensitive fields.
    """

    def __init__(
        self,
        llm: Any | None = None,
    ) -> None:
        """
        Initialize the extractor.

        Args:
            llm:
                Optional injectable LLM client.

                Production:
                    ResearchExtractor()

                Tests:
                    ResearchExtractor(llm=FakeGeminiClient())
        """

        self.llm = llm or GeminiClient()

    # =============================================================
    # Public API
    # =============================================================

    def extract(
        self,
        app: dict,
        evidence: list[dict],
    ) -> AppResearch:
        """
        Convert retrieved evidence into a validated AppResearch.

        The LLM produces analytical decisions, while Python resolves
        all source provenance deterministically.
        """

        prompt = self._build_prompt(
            app=app,
            evidence=evidence,
        )

        raw_result = self.llm.generate_json(prompt)

        if not isinstance(raw_result, dict):
            raise ValueError(
                "Gemini output must be a JSON object."
            )

        # ---------------------------------------------------------
        # Normalize harmless LLM variations before Pydantic.
        #
        # Gemini may return:
        #
        #   "Official"
        #
        # while our canonical model expects:
        #
        #   "Official MCP"
        #
        # This layer normalizes schema labels. It does NOT invent
        # research facts.
        # ---------------------------------------------------------

        raw_result = self._normalize_llm_output(
            raw_result
        )

        # ---------------------------------------------------------
        # Resolve every provenance-sensitive field before
        # Pydantic validation.
        # ---------------------------------------------------------

        raw_result = self._resolve_provenance(
            result=raw_result,
            evidence=evidence,
            official_domain=self._extract_domain(
                app.get("website", "")
            ),
        )

        try:
            return AppResearch.model_validate(
                raw_result
            )

        except Exception as exc:
            raise ValueError(
                "Gemini output failed AppResearch validation: "
                f"{exc}"
            ) from exc

    # =============================================================
    # LLM output normalization
    # =============================================================

    @staticmethod
    def _normalize_llm_output(
        result: dict,
    ) -> dict:
        """
        Normalize harmless variations in Gemini's structured output.

        The LLM is responsible for making research decisions.

        Python is responsible for enforcing the application's
        canonical schema.

        This method does NOT create evidence or research facts.
        It only converts equivalent labels into the exact enum
        values expected by src.models.
        """

        if not isinstance(result, dict):
            return result

        # ---------------------------------------------------------
        # MCP status
        # ---------------------------------------------------------

        mcp = result.get("mcp")

        if isinstance(mcp, dict):
            status = mcp.get("status")

            mcp_status_map = {
                "Official": "Official MCP",
                "official": "Official MCP",
                "Official MCP": "Official MCP",

                "Third Party": "Third-party MCP",
                "Third-Party": "Third-party MCP",
                "third-party": "Third-party MCP",
                "Third-party": "Third-party MCP",
                "Third-party MCP": "Third-party MCP",

                "None": "No MCP Found",
                "No MCP": "No MCP Found",
                "No MCP Found": "No MCP Found",

                "Unknown": "Unknown",
                "unknown": "Unknown",
            }

            if status in mcp_status_map:
                mcp["status"] = (
                    mcp_status_map[status]
                )

            # Keep the boolean flag consistent with the
            # canonical MCP status.

            if mcp.get("status") == "Official MCP":
                mcp["official"] = True

            elif mcp.get("status") == "Third-party MCP":
                mcp["official"] = False

            elif mcp.get("status") == "No MCP Found":
                mcp["official"] = False

            elif mcp.get("status") == "Unknown":
                mcp["official"] = None

            result["mcp"] = mcp

        # ---------------------------------------------------------
        # Authentication methods
        # ---------------------------------------------------------

        authentication = result.get(
            "authentication"
        )

        if isinstance(authentication, dict):
            methods = authentication.get(
                "methods"
            )

            if isinstance(methods, list):
                auth_map = {
                    "OAuth": "OAuth2",
                    "OAuth 2": "OAuth2",
                    "OAuth 2.0": "OAuth2",
                    "OAuth2": "OAuth2",

                    "API key": "API Key",
                    "API Key": "API Key",
                    "API-Key": "API Key",

                    "Bearer": "Bearer Token",
                    "Bearer token": "Bearer Token",
                    "Bearer Token": "Bearer Token",

                    "JWT": "JWT",

                    "Basic Auth": "Basic",
                    "Basic Authentication": "Basic",
                    "Basic": "Basic",

                    "Unknown": "Unknown",
                    "unknown": "Unknown",
                }

                normalized_methods = []

                for method in methods:
                    normalized = auth_map.get(
                        method,
                        method,
                    )

                    if normalized not in normalized_methods:
                        normalized_methods.append(
                            normalized
                        )

                authentication["methods"] = (
                    normalized_methods
                )

            result["authentication"] = (
                authentication
            )

        # ---------------------------------------------------------
        # Access type
        # ---------------------------------------------------------

        access = result.get(
            "access"
        )

        if isinstance(access, dict):
            access_type = access.get(
                "type"
            )

            access_map = {
                "Free": "Self-serve / Free",
                "Self-serve Free":
                    "Self-serve / Free",
                "Self-serve / Free":
                    "Self-serve / Free",

                "Trial": "Self-serve / Trial",
                "Self-serve Trial":
                    "Self-serve / Trial",
                "Self-serve / Trial":
                    "Self-serve / Trial",

                "Paid":
                    "Paid Plan Required",
                "Paid Plan":
                    "Paid Plan Required",
                "Paid Plan Required":
                    "Paid Plan Required",

                "Admin Approval":
                    "Admin Approval Required",
                "Admin Approval Required":
                    "Admin Approval Required",

                "Partnership":
                    "Partnership Required",
                "Partnership Required":
                    "Partnership Required",

                "Sales":
                    "Contact Sales",
                "Contact Sales":
                    "Contact Sales",

                "Unknown": "Unknown",
                "unknown": "Unknown",
            }

            if access_type in access_map:
                access["type"] = access_map[
                    access_type
                ]

            result["access"] = access

        # ---------------------------------------------------------
        # API type
        # ---------------------------------------------------------

        api = result.get(
            "api"
        )

        if isinstance(api, dict):
            api_type = api.get(
                "type"
            )

            api_type_map = {
                "REST API": "REST",
                "REST": "REST",

                "GraphQL API": "GraphQL",
                "GraphQL": "GraphQL",

                "REST and GraphQL":
                    "REST + GraphQL",
                "REST & GraphQL":
                    "REST + GraphQL",
                "REST + GraphQL":
                    "REST + GraphQL",

                "No API":
                    "No Public API Found",
                "No Public API":
                    "No Public API Found",
                "No Public API Found":
                    "No Public API Found",

                "Unknown": "Unknown",
                "unknown": "Unknown",
            }

            if api_type in api_type_map:
                api["type"] = api_type_map[
                    api_type
                ]

            # -----------------------------------------------------
            # API breadth
            # -----------------------------------------------------

            breadth = api.get(
                "breadth"
            )

            breadth_map = {
                "narrow": "Narrow",
                "Narrow": "Narrow",

                "moderate": "Moderate",
                "Moderate": "Moderate",

                "broad": "Broad",
                "Broad": "Broad",

                "unknown": "Unknown",
                "Unknown": "Unknown",
            }

            if breadth in breadth_map:
                api["breadth"] = breadth_map[
                    breadth
                ]

            result["api"] = api

        # ---------------------------------------------------------
        # Buildability verdict
        # ---------------------------------------------------------

        buildability = result.get(
            "buildability"
        )

        if isinstance(buildability, dict):
            verdict = buildability.get(
                "verdict"
            )

            verdict_map = {
                "easy": "Easy",
                "Easy": "Easy",

                "possible": "Possible",
                "Possible": "Possible",

                "gated": "Gated",
                "Gated": "Gated",

                "blocked": "Blocked",
                "Blocked": "Blocked",

                "unknown": "Unknown",
                "Unknown": "Unknown",
            }

            if verdict in verdict_map:
                buildability["verdict"] = (
                    verdict_map[verdict]
                )

            result["buildability"] = (
                buildability
            )

        return result

    # =============================================================
    # Provenance resolution
    # =============================================================

    @staticmethod
    def _resolve_provenance(
        result: dict,
        evidence: list[dict],
        official_domain: str = "",
    ) -> dict:
        """
        Resolve every Gemini-selected evidence ID against the
        original web evidence.

        Gemini provides IDs.

        Python provides:

            URL
            source name
            source type
            snippet
            API documentation URL
            MCP URL

        This guarantees that provenance cannot be hallucinated.
        """

        web_sources: dict[str, dict] = {}

        for group in evidence:
            if not isinstance(group, dict):
                continue

            if group.get("type") != "web_evidence":
                continue

            for item in group.get(
                "items",
                [],
            ):
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                evidence_id = item.get(
                    "evidence_id"
                )

                if evidence_id:
                    web_sources[
                        evidence_id
                    ] = item

        # ---------------------------------------------------------
        # Resolve evidence[]
        # ---------------------------------------------------------

        resolved_evidence: list[dict] = []
        seen_ids: set[str] = set()

        for item in result.get(
            "evidence",
            [],
        ):
            if not isinstance(
                item,
                dict,
            ):
                continue

            evidence_id = item.get(
                "evidence_id"
            )

            if not evidence_id:
                continue

            if evidence_id in seen_ids:
                continue

            source = web_sources.get(
                evidence_id
            )

            if source is None:
                continue

            seen_ids.add(
                evidence_id
            )

            source_url = source.get(
                "url",
                "",
            )

            source_title = source.get(
                "title",
                "",
            )

            source_content = source.get(
                "content",
                "",
            )

            # The snippet comes directly from the original source.
            # Gemini cannot rewrite provenance.
            snippet = ResearchExtractor._build_snippet(
                source_content
            )

            resolved_evidence.append(
                {
                    "claim": item.get(
                        "claim",
                        "",
                    ),
                    "url": source_url,
                    "source_name": source_title,
                    "source_type": (
                        ResearchExtractor._classify_source(
                            url=source_url,
                            official_domain=official_domain,
                        )
                    ),
                    "snippet": snippet,
                }
            )

        result["evidence"] = (
            resolved_evidence
        )

        # ---------------------------------------------------------
        # Resolve API documentation URL
        # ---------------------------------------------------------

        api = result.get(
            "api"
        )

        if not isinstance(
            api,
            dict,
        ):
            api = {}

        api_documentation_id = api.pop(
            "documentation_evidence_id",
            None,
        )

        if api_documentation_id:
            source = web_sources.get(
                api_documentation_id
            )

            if source:
                api["documentation_url"] = (
                    source.get(
                        "url"
                    )
                )
            else:
                api["documentation_url"] = None

        else:
            # Never trust a Gemini-generated URL.
            api["documentation_url"] = None

        result["api"] = api

        # ---------------------------------------------------------
        # Resolve MCP URL
        # ---------------------------------------------------------

        mcp = result.get(
            "mcp"
        )

        if not isinstance(
            mcp,
            dict,
        ):
            mcp = {}

        mcp_evidence_id = mcp.pop(
            "evidence_id",
            None,
        )

        if mcp_evidence_id:
            source = web_sources.get(
                mcp_evidence_id
            )

            if source:
                mcp["url"] = source.get(
                    "url"
                )

                source_type = (
                    ResearchExtractor._classify_source(
                        url=source.get(
                            "url",
                            "",
                        ),
                        official_domain=official_domain,
                    )
                )

                # If Gemini claims Official MCP, make sure
                # the selected source is actually official.
                if (
                    mcp.get("status")
                    == "Official MCP"
                    and source_type
                    not in {
                        "official_docs",
                        "official_blog",
                        "official_github",
                    }
                ):
                    mcp["status"] = "Unknown"
                    mcp["official"] = None
                    mcp["url"] = None

            else:
                mcp["url"] = None

        else:
            # Never trust a Gemini-generated URL.
            mcp["url"] = None

        result["mcp"] = mcp

        return result

    # =============================================================
    # Backwards-compatible evidence resolver
    # =============================================================

    @staticmethod
    def _resolve_evidence(
        result: dict,
        evidence: list[dict],
    ) -> dict:
        """
        Backwards-compatible wrapper used by older tests/code.

        Resolves evidence using the original evidence structure.
        """

        return ResearchExtractor._resolve_provenance(
            result=result,
            evidence=evidence,
        )

    # =============================================================
    # Snippet handling
    # =============================================================

    @staticmethod
    def _build_snippet(
        content: Any,
        max_length: int = 500,
    ) -> str:
        """
        Build a deterministic snippet from the original source.

        The returned text is always an exact substring of the
        original retrieved content.

        This is important because the verifier checks that snippets
        actually originate from the supplied source.
        """

        if not isinstance(
            content,
            str,
        ):
            return ""

        content = content.strip()

        if not content:
            return ""

        if len(content) <= max_length:
            return content

        return content[
            :max_length
        ].rstrip()

    # =============================================================
    # Source classification
    # =============================================================

    @staticmethod
    def _classify_source(
        url: str,
        official_domain: str = "",
    ) -> str:
        """
        Classify a source deterministically from its URL.

        Gemini does not control source_type.
        """

        normalized_url = (
            str(url)
            .lower()
            .strip()
        )

        if not normalized_url:
            return "other"

        # ---------------------------------------------------------
        # Video
        # ---------------------------------------------------------

        if (
            "youtube.com" in normalized_url
            or "youtu.be" in normalized_url
        ):
            return "video"

        # ---------------------------------------------------------
        # GitHub
        # ---------------------------------------------------------

        if "github.com" in normalized_url:
            return "official_github"

        # ---------------------------------------------------------
        # Official application domain
        # ---------------------------------------------------------

        normalized_domain = (
            official_domain
            .lower()
            .strip()
        )

        hostname = ""

        try:
            hostname = (
                urlparse(
                    normalized_url
                ).hostname
                or ""
            )
        except Exception:
            hostname = ""

        hostname = hostname.lower()

        if normalized_domain:
            domain = normalized_domain

            if domain.startswith(
                "www."
            ):
                domain = domain[4:]

            normalized_hostname = hostname

            if normalized_hostname.startswith(
                "www."
            ):
                normalized_hostname = (
                    normalized_hostname[4:]
                )

            if (
                normalized_hostname == domain
                or normalized_hostname.endswith(
                    "." + domain
                )
            ):
                if (
                    "/blog" in normalized_url
                    or "/blogs" in normalized_url
                ):
                    return "official_blog"

                return "official_docs"

        # ---------------------------------------------------------
        # Known official domains
        # ---------------------------------------------------------

        known_official_domains = (
            "salesforce.com",
            "slack.com",
            "github.com",
            "shopify.com",
            "stripe.com",
            "hubspot.com",
            "microsoft.com",
            "google.com",
            "atlassian.com",
            "notion.so",
            "linear.app",
            "discord.com",
            "twilio.com",
            "zoom.us",
            "dropbox.com",
            "pipedrive.com",
            "intercom.com",
            "asana.com",
            "zendesk.com",
        )

        for domain in known_official_domains:
            normalized_domain_name = (
                domain.lower()
            )

            if (
                hostname == normalized_domain_name
                or hostname.endswith(
                    "." + normalized_domain_name
                )
            ):
                if (
                    "/blog" in normalized_url
                    or "/blogs" in normalized_url
                ):
                    return "official_blog"

                return "official_docs"

        return "third_party"

    # =============================================================
    # Domain extraction
    # =============================================================

    @staticmethod
    def _extract_domain(
        website: str,
    ) -> str:
        """
        Extract hostname/domain from an application website.

        Example:

            https://www.salesforce.com/in/
            -> www.salesforce.com
        """

        if not website:
            return ""

        website = str(
            website
        ).strip()

        if "://" not in website:
            website = (
                "https://"
                + website
            )

        try:
            hostname = (
                urlparse(
                    website
                ).hostname
                or ""
            )

            return hostname

        except Exception:
            return ""

    # =============================================================
    # Gemini prompt
    # =============================================================

    @staticmethod
    def _build_prompt(
        app: dict,
        evidence: list[dict],
    ) -> str:
        """
        Build the evidence-first Gemini prompt.

        Gemini selects evidence IDs only.

        Python resolves all provenance-sensitive values.
        """

        evidence_text = json.dumps(
            evidence,
            indent=2,
            ensure_ascii=False,
        )

        return f"""
You are an evidence-first research analyst.

Your task is to research the application below using ONLY the
supplied evidence.

Do not use outside knowledge.

Do not use pretrained knowledge.

Do not guess.

Do not invent facts.

============================================================
APPLICATION
============================================================

ID:
{app["id"]}

Name:
{app["name"]}

Category:
{app["category"]}

Website:
{app["website"]}

============================================================
CORE RESEARCH RULE
============================================================

Every conclusion must be supported by the supplied evidence.

If evidence is insufficient, use:

"Unknown"

============================================================
EVIDENCE IDs
============================================================

The supplied web evidence contains stable IDs:

WEB-001
WEB-002
WEB-003
...

Gemini MUST select these IDs.

Gemini MUST NOT generate:

- URLs
- source names
- source types
- evidence snippets

Python will resolve those values from the original evidence.

============================================================
EVIDENCE ITEM RULES
============================================================

For every evidence item:

1. Select exactly ONE evidence_id.

2. The evidence_id MUST exactly match one supplied WEB evidence ID.

3. Never invent an evidence_id.

4. Never use Composio metadata as an evidence ID.

5. Every evidence_id must be unique.

6. The claim must be directly supported by that source.

7. Do not combine multiple sources into one evidence item.

8. Do not create evidence for unsupported claims.

9. The evidence item must contain ONLY:

   evidence_id
   claim

Do NOT return:

   url
   source_name
   source_type
   snippet

Python will resolve all of those.

============================================================
API DOCUMENTATION EVIDENCE
============================================================

The API object contains:

"documentation_evidence_id"

This MUST be:

- one supplied WEB evidence ID, if API documentation is directly
  supported by a supplied source
- null if no suitable source exists

Never generate a URL yourself.

The resulting URL will be resolved by Python.

============================================================
MCP EVIDENCE
============================================================

The MCP object contains:

"evidence_id"

This MUST be:

- one supplied WEB evidence ID supporting the MCP classification
- null when evidence is insufficient

Rules:

Official MCP:

Only when supplied evidence explicitly identifies an official
MCP implementation from the application/vendor.

Third-party MCP:

Only when supplied evidence explicitly identifies a third-party
MCP implementation.

No MCP Found:

Only when supplied evidence explicitly supports that conclusion.

Unknown:

When evidence is insufficient.

A Composio toolkit does NOT prove Official MCP.

Never generate an MCP URL.

Python will resolve the URL from evidence_id.

============================================================
SOURCE PRIORITY
============================================================

When multiple sources support a claim, prefer:

1. Official developer documentation
2. Official product documentation
3. Official GitHub repositories
4. Official company blogs
5. Reputable third-party technical documentation
6. Other third-party sources
7. Videos/social content

For:

- authentication
- access requirements
- API capabilities
- MCP availability

prefer official documentation whenever available.

============================================================
COMPOSIO
============================================================

Composio discovery is supplied separately.

A Composio toolkit proves that Composio has an integration for
the application.

It does NOT automatically prove:

- official MCP support
- official application MCP servers
- official application documentation

Never classify an application as Official MCP solely because
Composio has a toolkit.

============================================================
AUTHENTICATION
============================================================

Use ONLY:

"OAuth2"
"API Key"
"Basic"
"Bearer Token"
"JWT"
"Other"
"Unknown"

Only include authentication methods directly supported by
the supplied evidence.

============================================================
ACCESS
============================================================

Use ONLY:

"Self-serve / Free"
"Self-serve / Trial"
"Paid Plan Required"
"Admin Approval Required"
"Partnership Required"
"Contact Sales"
"Unknown"

Do not infer access requirements solely from API documentation.

Use direct evidence about:

- pricing
- trials
- developer accounts
- organization requirements
- administrator approval
- sales requirements
- enterprise requirements

If unclear:

"Unknown"

============================================================
API TYPE
============================================================

Use ONLY:

"REST"
"GraphQL"
"REST + GraphQL"
"Other"
"No Public API Found"
"Unknown"

============================================================
API BREADTH
============================================================

Use ONLY:

"Narrow"
"Moderate"
"Broad"
"Unknown"

============================================================
BUILDABILITY
============================================================

Use ONLY:

"Easy"
"Possible"
"Gated"
"Blocked"
"Unknown"

Easy:

Public API exists, authentication is documented, access is
reasonably obtainable, and there is no significant blocker.

Possible:

Technically feasible but requires additional setup, payment,
administrative configuration, or similar effort.

Gated:

Requires sales approval, partnership, enterprise access,
or another significant access gate.

Blocked:

Strong evidence indicates integration cannot reasonably be built.

Unknown:

Evidence is insufficient.

============================================================
CONFIDENCE
============================================================

Do NOT automatically use 1.0.

Use approximately:

0.90 - 1.00
Multiple direct authoritative sources explicitly support the
conclusion with little ambiguity.

0.75 - 0.89
Strong evidence with minor uncertainty.

0.60 - 0.74
Moderate evidence with some missing information.

0.40 - 0.59
Weak or incomplete evidence.

0.00 - 0.39
Very uncertain.

============================================================
REQUIRED JSON
============================================================

Return ONLY valid JSON.

Use exactly this structure:

{{
  "app_id": {app["id"]},
  "app_name": "{app["name"]}",
  "category": "{app["category"]}",
  "description": "Short evidence-supported description.",

  "authentication": {{
    "methods": [],
    "confidence": 0.0
  }},

  "access": {{
    "type": "Unknown",
    "requirements": [],
    "confidence": 0.0
  }},

  "api": {{
    "type": "Unknown",
    "breadth": "Unknown",
    "documentation_evidence_id": null,
    "confidence": 0.0
  }},

  "mcp": {{
    "status": "Unknown",
    "official": null,
    "evidence_id": null,
    "confidence": 0.0
  }},

  "buildability": {{
    "verdict": "Unknown",
    "blocker": null,
    "reasoning": "Insufficient evidence."
  }},

  "evidence": [
    {{
      "evidence_id": "WEB-001",
      "claim": "Claim directly supported by this source."
    }}
  ],

  "overall_confidence": 0.0
}}

============================================================
FINAL CHECK
============================================================

Before returning JSON:

1. Every evidence_id exists in supplied web evidence.

2. Every evidence_id is unique.

3. Every claim is supported by its selected source.

4. documentation_evidence_id is either a valid WEB ID or null.

5. MCP evidence_id is either a valid WEB ID or null.

6. Authentication is supported by evidence.

7. Access classification is supported by evidence.

8. MCP classification is supported by evidence.

9. Never invent a URL.

10. Never invent a source name.

11. Never invent a snippet.

12. Never use Composio metadata as web evidence.

13. Do not automatically use confidence 1.0.

14. Return JSON only.

============================================================
SUPPLIED EVIDENCE
============================================================

{evidence_text}
"""