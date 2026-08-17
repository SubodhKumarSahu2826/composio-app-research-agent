from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class AuthMethod(str, Enum):
    OAUTH2 = "OAuth2"
    API_KEY = "API Key"
    BASIC = "Basic"
    BEARER_TOKEN = "Bearer Token"
    JWT = "JWT"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class AccessType(str, Enum):
    SELF_SERVE_FREE = "Self-serve / Free"
    SELF_SERVE_TRIAL = "Self-serve / Trial"
    PAID_PLAN = "Paid Plan Required"
    ADMIN_APPROVAL = "Admin Approval Required"
    PARTNER_REQUIRED = "Partnership Required"
    CONTACT_SALES = "Contact Sales"
    UNKNOWN = "Unknown"


class ApiType(str, Enum):
    REST = "REST"
    GRAPHQL = "GraphQL"
    REST_GRAPHQL = "REST + GraphQL"
    OTHER = "Other"
    NONE_FOUND = "No Public API Found"
    UNKNOWN = "Unknown"


class ApiBreadth(str, Enum):
    NARROW = "Narrow"
    MODERATE = "Moderate"
    BROAD = "Broad"
    UNKNOWN = "Unknown"


class McpStatus(str, Enum):
    OFFICIAL = "Official MCP"
    THIRD_PARTY = "Third-party MCP"
    NONE_FOUND = "No MCP Found"
    UNKNOWN = "Unknown"


class Buildability(str, Enum):
    EASY = "Easy"
    POSSIBLE = "Possible"
    GATED = "Gated"
    BLOCKED = "Blocked"
    UNKNOWN = "Unknown"


class Evidence(BaseModel):
    claim: str
    url: HttpUrl
    source_name: str
    source_type: str
    snippet: Optional[str] = None


class Authentication(BaseModel):
    methods: list[AuthMethod] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class Access(BaseModel):
    type: AccessType
    requirements: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class ApiSurface(BaseModel):
    type: ApiType
    breadth: ApiBreadth
    documentation_url: Optional[HttpUrl] = None
    confidence: float = Field(ge=0.0, le=1.0)


class McpInfo(BaseModel):
    status: McpStatus
    official: Optional[bool] = None
    url: Optional[HttpUrl] = None
    confidence: float = Field(ge=0.0, le=1.0)


class BuildabilityResult(BaseModel):
    verdict: Buildability
    blocker: Optional[str] = None
    reasoning: str


class AppResearch(BaseModel):
    app_id: int
    app_name: str
    category: str
    description: str

    authentication: Authentication
    access: Access
    api: ApiSurface
    mcp: McpInfo

    buildability: BuildabilityResult

    evidence: list[Evidence] = Field(default_factory=list)

    overall_confidence: float = Field(ge=0.0, le=1.0)