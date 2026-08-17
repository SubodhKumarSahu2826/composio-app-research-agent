# AI App Integration Research Agent

An evidence-first, resumable research pipeline for evaluating whether third-party applications are good candidates for AI-agent integrations and Composio toolkits.

Built for the Composio AI Product Ops Intern take-home assignment.

## What the assignment asks

For each of 100 applications, research:

- What the app does and its category
- Authentication methods
- Self-serve vs gated credential access
- Public REST/GraphQL API surface and breadth
- Existing MCP support
- Buildability and the main blocker
- Evidence URLs supporting each finding

The assignment also emphasizes cross-app patterns, an agent-driven workflow rather than manual research, and verification against real documentation.

## What this project implements

```text
100-app dataset
      │
      ▼
Research Pipeline
      │
      ├── Web evidence retrieval
      ├── Composio toolkit discovery
      │
      ▼
Structured LLM extraction
      │
      ▼
Pydantic schema validation
      │
      ▼
Deterministic verification
      │
      ▼
Research-quality analysis
      │
      ▼
Cross-app analysis
      │
      ├── Patterns
      ├── Common blockers
      ├── Buildability distribution
      └── Integration-priority ranking
      │
      ▼
HTML Case Study
```

The LLM is not treated as the source of truth. Evidence is collected first, structured output is validated, and verification is performed against the available evidence.

## Key features

### Evidence-first research

The agent performs targeted searches for:

```text
<App> API authentication developer documentation
<App> API access requirements developer
<App> REST API documentation
<App> MCP Model Context Protocol
```

Official documentation is preferred where available.

### Composio discovery

The pipeline uses the Composio SDK to determine whether a matching toolkit exists and records that information alongside the research.

### Structured extraction

Gemini converts collected evidence into a typed `AppResearch` model containing:

```text
application
authentication
access
api
mcp
buildability
evidence
confidence
```

Pydantic validation rejects malformed model output instead of silently accepting it.

### Verification

Generated findings are checked against the collected evidence.

Verification metadata is preserved in the result artifacts so the report can distinguish:

- verified findings
- failed verification
- unavailable verification metadata

### Resumable pipeline

Progress is checkpointed in:

```text
results/results.json
results/failures.json
results/progress.json
```

Already-completed applications are skipped on subsequent runs.

This means a quota/network interruption does not require restarting the entire research run.

### Cross-app analysis

`src/cross_app_analysis.py` converts individual research results into aggregate decision support:

- authentication patterns
- API patterns
- MCP patterns
- access requirements
- buildability distribution
- categories
- evidence coverage
- verification coverage
- common blockers
- deterministic integration-priority ranking

The priority score is explicitly a heuristic for prioritization, not a measured benchmark of engineering effort.

## Current execution status

The current saved execution contains:

```text
Dataset:       100 applications
Completed:       7
Remaining:      92
Status:       Paused
```

Completed:

```text
1. Salesforce
2. HubSpot
3. Pipedrive
4. Attio
5. Twenty
6. Podio
7. Zoho CRM
```

The pipeline paused when the Gemini API quota was exhausted while processing Close.

This is intentionally documented rather than presenting the 7-app sample as a completed 100-app study.

The architecture is already resumable. Once quota becomes available:

```bash
python -m src.pipeline
```

will continue from the saved checkpoint.

## Current cross-app findings

The completed sample currently shows:

- OAuth2 is present across the completed sample.
- REST APIs dominate the completed sample.
- Most completed applications are classified as Easy to build.
- Official MCP support appears in a subset of the sample.
- Pipedrive currently ranks highest in the deterministic integration-priority heuristic.

These findings are explicitly limited to the completed 7-app sample and should not be generalized to all 100 applications.

## Verification status

The current saved execution contains verification metadata for 5 of the 7 completed applications.

The verifier measures consistency between structured findings and supplied evidence. It is **not** presented as an independent factual-accuracy benchmark.

The final assignment also calls for human spot-checking against real documentation. That should be recorded separately as:

```text
Application
Claim
Agent result
Source-of-truth result
Correct / Incorrect
Correction
```

No unsupported 100-app accuracy percentage is claimed.

## Project structure

```text
composio-app-research-agent/
│
├── data/
│   └── apps.json
│
├── src/
│   ├── research_agent.py
│   ├── pipeline.py
│   ├── web_tools.py
│   ├── composio_tools.py
│   ├── extraction.py
│   ├── models.py
│   ├── verifier.py
│   ├── analysis.py
│   ├── cross_app_analysis.py
│   └── gemini_client.py
│
├── report/
│   ├── generate.py
│   ├── template.html
│   ├── research_report.html
│   └── pages/
│
├── results/
│   ├── results.json
│   ├── failures.json
│   ├── progress.json
│   └── cross_app_analysis.json
│
├── tests/
│   ├── test_analysis.py
│   ├── test_apps.py
│   ├── test_composio_tools.py
│   ├── test_cross_app_analysis.py
│   ├── test_dataset.py
│   ├── test_extraction.py
│   ├── test_models.py
│   ├── test_pipeline.py
│   ├── test_report.py
│   ├── test_research_agent.py
│   ├── test_verifier.py
│   └── test_web_tools.py
│
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

Requires Python 3.12.

```bash
git clone https://github.com/SubodhKumarSahu2826/composio-app-research-agent.git
cd composio-app-research-agent

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Create `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
COMPOSIO_API_KEY=your_composio_api_key
```

Never commit `.env`.

## Run the research agent

Single-app development run:

```bash
python -m src.research_agent
```

Batch run:

```bash
python -m src.pipeline --limit 5
```

Full/resume run:

```bash
python -m src.pipeline
```

The pipeline uses the saved progress files and skips completed applications.

## Generate cross-app analysis

```bash
python -m src.cross_app_analysis
```

Output:

```text
results/cross_app_analysis.json
```

## Generate the case study

```bash
python -m report.generate
```

Primary report:

```text
report/research_report.html
```

Navigable presentation:

```text
report/pages/overview.html
report/pages/cross_app_analysis.html
report/pages/applications.html
report/pages/execution.html
```

Open locally:

```bash
open report/pages/overview.html
```

The report contains the findings, patterns, agent workflow, execution boundary, verification information, and reproduction instructions.

## Run tests

```bash
python -m pytest
```

Current test status:

```text
102 passed
```

Coverage includes:

- dataset validation
- web research
- Composio integration
- structured extraction
- research pipeline
- retry/checkpoint behavior
- verification
- research-quality analysis
- cross-app analysis
- report generation
- research-agent edge cases

Useful focused suites:

```bash
python -m pytest tests/test_pipeline.py -v
python -m pytest tests/test_cross_app_analysis.py -v
python -m pytest tests/test_report.py -v
python -m pytest tests/test_research_agent.py -v
```

## Reproducibility

From a clean environment:

```bash
git clone https://github.com/SubodhKumarSahu2826/composio-app-research-agent.git
cd composio-app-research-agent

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure .env

python -m pytest
python -m src.pipeline --limit 5
python -m src.cross_app_analysis
python -m report.generate
```

## Human vs automated work

### Automated

- Dataset validation
- Web evidence retrieval
- Composio toolkit discovery
- Evidence aggregation
- LLM extraction
- Pydantic validation
- Retry handling
- Quota handling
- Checkpointing
- Deterministic verification
- Research-quality analysis
- Cross-app pattern analysis
- Integration-priority ranking
- HTML generation
- Regression testing

### Human

- Review ambiguous evidence
- Spot-check claims against official documentation
- Review incorrect model outputs
- Decide whether evidence genuinely supports a claim
- Interpret business/product implications
- Perform final submission review

## Known limitation

The assignment's target is 100 researched applications. The current execution has 7 completed applications because the Gemini API quota was exhausted.

This is an execution/data-volume limitation, not a missing pipeline capability.

The completed results remain saved and the pipeline can resume when quota is available.

## Submission artifacts

The repository contains:

1. Source code
2. 100-app research dataset
3. Research results
4. Verification artifacts
5. Cross-app analysis
6. Automated tests
7. HTML case study
8. Reproduction instructions

Add the deployed case-study URL before submission:

```text
CASE_STUDY_URL=<YOUR_DEPLOYED_HTML_URL>
```

Repository:

https://github.com/SubodhKumarSahu2826/composio-app-research-agent

## Design principle

The core workflow is:

```text
Search
  ↓
Collect evidence
  ↓
Discover Composio support
  ↓
Structure findings
  ↓
Validate schema
  ↓
Verify against evidence
  ↓
Analyze research quality
  ↓
Find cross-app patterns
  ↓
Prioritize integrations
  ↓
Generate case study
```

The goal is not simply to produce LLM-generated rows. The goal is to build a repeatable research system with evidence, validation, verification, failure handling, resumability, and decision-oriented output.
