import json

from src.gemini_client import GeminiClient
from src.models import AppResearch


class ResearchExtractor:
    """
    Extract structured research findings from evidence.

    Architecture:

        Retrieved Evidence
               ↓
        Gemini selects evidence IDs
               ↓
        Python resolves provenance
               ↓
        Pydantic validation

    Gemini is NOT trusted to generate:
        - URLs
        - source names
        - source types
    """

    def __init__(self) -> None:
        self.llm = GeminiClient()

    def extract(
        self,
        app: dict,
        evidence: list[dict],
    ) -> AppResearch:
        """
        Convert retrieved evidence into a validated AppResearch result.
        """

        prompt = self._build_prompt(
            app=app,
            evidence=evidence,
        )

        raw_result = self.llm.generate_json(prompt)

        # Gemini selects evidence IDs.
        # Python resolves the actual provenance.
        raw_result = self._resolve_evidence(
            result=raw_result,
            evidence=evidence,
        )

        try:
            return AppResearch.model_validate(raw_result)

        except Exception as exc:
            raise ValueError(
                f"Gemini output failed AppResearch validation: {exc}"
            ) from exc

    # =============================================================
    # Evidence provenance
    # =============================================================

    @staticmethod
    def _resolve_evidence(
        result: dict,
        evidence: list[dict],
    ) -> dict:
        """
        Resolve Gemini-selected evidence IDs against the original
        web sources.

        Gemini decides:

            Which source supports this claim?

        Python decides:

            URL
            source name
            source type

        This prevents the LLM from corrupting provenance.
        """

        web_sources: dict[str, dict] = {}

        # ---------------------------------------------------------
        # Build lookup:
        #
        # WEB-001 -> source
        # WEB-002 -> source
        # WEB-003 -> source
        # ---------------------------------------------------------

        for group in evidence:
            if group.get("type") != "web_evidence":
                continue

            for item in group.get("items", []):
                evidence_id = item.get("evidence_id")

                if evidence_id:
                    web_sources[evidence_id] = item

        resolved_evidence = []
        seen_ids = set()

        # ---------------------------------------------------------
        # Resolve Gemini's evidence selections.
        # ---------------------------------------------------------

        for item in result.get("evidence", []):
            evidence_id = item.get("evidence_id")

            # Gemini omitted evidence ID.
            if not evidence_id:
                continue

            # Avoid duplicate evidence.
            if evidence_id in seen_ids:
                continue

            source = web_sources.get(evidence_id)

            # Gemini invented an unknown evidence ID.
            if source is None:
                continue

            seen_ids.add(evidence_id)

            resolved_evidence.append(
                {
                    "claim": item.get(
                        "claim",
                        "",
                    ),
                    "url": source.get(
                        "url",
                        "",
                    ),
                    "source_name": source.get(
                        "title",
                        "",
                    ),
                    "source_type": ResearchExtractor._classify_source(
                        url=source.get(
                            "url",
                            "",
                        ),
                    ),
                    "snippet": item.get(
                        "snippet",
                        "",
                    ),
                }
            )

        result["evidence"] = resolved_evidence

        return result

    # =============================================================
    # Source classification
    # =============================================================

    @staticmethod
    def _classify_source(
        url: str,
        official_domain: str = "",
    ) -> str:
        """
        Classify the source deterministically from its URL.

        Gemini does not control this value.
        """

        normalized_url = url.lower().strip()

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
        # Application-specific official domain
        # ---------------------------------------------------------

        if official_domain:
            normalized_domain = official_domain.lower().strip()

            if normalized_domain in normalized_url:

                if "/blog" in normalized_url:
                    return "official_blog"

                return "official_docs"

        # ---------------------------------------------------------
        # Known official domains
        #
        # This gives us reasonable classification during the
        # single-app development phase.
        #
        # We will make this dynamic when the batch runner is built.
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
        )

        if any(
            domain in normalized_url
            for domain in known_official_domains
        ):
            if "/blog" in normalized_url:
                return "official_blog"

            return "official_docs"

        # ---------------------------------------------------------
        # Third-party
        # ---------------------------------------------------------

        return "third_party"

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

Do not guess.

Do not rely on pretrained knowledge.

Do not invent facts.

============================================================
EVIDENCE SELECTION
============================================================

The supplied web evidence contains stable IDs:

WEB-001
WEB-002
WEB-003
...

When creating an evidence item:

1. Select exactly ONE evidence_id.

2. The evidence_id MUST exactly match one supplied WEB evidence ID.

3. Do NOT invent an evidence ID.

4. Do NOT create a URL.

5. Do NOT create a source name.

6. Do NOT create a source type.

7. Do NOT combine multiple sources into one evidence item.

8. Do NOT create duplicate evidence items for the same evidence ID.

9. The claim must be directly supported by the selected source.

10. The snippet must be based ONLY on the selected source's content.

Gemini selects the evidence.

Python later resolves:

- URL
- source_name
- source_type

============================================================
SOURCE PRIORITY
============================================================

When multiple sources support or contradict a claim, prioritize
evidence in this order:

1. Official developer documentation
2. Official product documentation
3. Official GitHub repositories
4. Official company blogs
5. Reputable third-party technical documentation
6. Other third-party sources
7. Videos/social content

Do not use a lower-authority source to override a higher-authority
source unless the higher-authority source does not address the
specific claim.

For:

- authentication
- access requirements
- API capabilities
- MCP availability

prefer official documentation whenever available.

Do not add an authentication method merely because a third-party
source mentions it if authoritative documentation does not support it.

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
Composio has a toolkit for it.

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

Only include authentication methods directly supported by evidence.

Prefer official documentation over third-party sources.

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

The existence of public API documentation does NOT automatically
mean API access is free or self-serve.

Use direct evidence about:

- pricing
- trials
- developer accounts
- organization requirements
- administrator approval
- sales requirements
- enterprise requirements

If these are unclear, use "Unknown".

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

Narrow:
Limited API surface.

Moderate:
Several meaningful resources/functions.

Broad:
Large API surface covering substantial product functionality.

Unknown:
Insufficient evidence.

============================================================
MCP
============================================================

Use ONLY:

"Official MCP"
"Third-party MCP"
"No MCP Found"
"Unknown"

Official MCP:

Only when supplied evidence explicitly identifies an official
MCP implementation from the application/vendor.

Third-party MCP:

Only when supplied evidence explicitly identifies a third-party
MCP implementation.

No MCP Found:

Only when the evidence explicitly supports that conclusion.

Unknown:

Use when evidence is insufficient.

A Composio toolkit does NOT prove Official MCP.

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
reasonably obtainable, and there is no significant integration
blocker.

Possible:

Technically feasible but requires additional setup, payment,
administrative configuration, or similar effort.

Gated:

Requires sales approval, partnership, enterprise access,
or another significant access gate.

Blocked:

Strong evidence indicates the integration cannot reasonably
be built.

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

Strong evidence supports the conclusion with minor uncertainty.

0.60 - 0.74

Moderate evidence with some missing or indirect information.

0.40 - 0.59

Weak or incomplete evidence.

0.00 - 0.39

Very uncertain.

Use 1.0 only when evidence is exceptionally direct,
authoritative, and unambiguous.

============================================================
REQUIRED JSON
============================================================

Return ONLY valid JSON.

Use EXACTLY this structure:

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
    "documentation_url": null,
    "confidence": 0.0
  }},

  "mcp": {{
    "status": "Unknown",
    "official": null,
    "url": null,
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
      "claim": "Claim directly supported by this source.",
      "snippet": "Short excerpt based only on this source."
    }}
  ],

  "overall_confidence": 0.0
}}

============================================================
EVIDENCE OUTPUT REQUIREMENTS
============================================================

Every evidence item MUST contain:

- evidence_id
- claim
- snippet

Every evidence_id MUST correspond to a supplied WEB evidence ID.

Every evidence_id MUST be unique.

Do NOT return:

- url
- source_name
- source_type

Python will populate those fields after Gemini responds.

============================================================
FINAL INTERNAL CHECK
============================================================

Before returning JSON:

1. Every evidence_id exists in supplied web evidence.

2. Every evidence_id is unique.

3. Every claim is supported by its selected source.

4. Every snippet comes only from its selected source.

5. Official sources are preferred when available.

6. MCP classification is supported by evidence.

7. Access requirements are supported by evidence.

8. Authentication methods are supported by evidence.

9. Do not automatically use confidence 1.0.

10. Return JSON only.

============================================================
SUPPLIED EVIDENCE
============================================================

{evidence_text}
"""