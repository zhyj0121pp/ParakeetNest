# Epic 001: First Committee

## Goal

Build the first usable ParakeetNest investment committee workflow.

This epic establishes a local, SQLite-backed CLI path where a user can ask an
investment question about a ticker and receive a structured committee result
from the current agents: Dongdong, Xixi, Yoyo, and Chairman.

The goal is not investment automation. The goal is a small, testable research
loop that proves the committee can:

- create a persistent meeting;
- run each committee agent in a fixed order;
- preserve each agent message;
- produce a final structured recommendation object;
- avoid external API calls and hard-coded secrets in v1.

Every final recommendation must include action, confidence, horizon, evidence,
risks, and catalysts.

## Final Architecture

Epic 001 freezes the first committee path around a local application service:

```text
CLI
 |
 v
ParakeetNestApp
 |
 v
MeetingService
 |
 v
CommitteeMeetingRepository ---- SQLite
 |
 v
CommitteeMeetingOrchestrator
 |
 v
AgentRuntime + PromptRenderer + LLMProvider
 |
 v
Xixi -> Dongdong -> Yoyo -> Chairman
 |
 v
Final JSON result
```

The application is wired by `parakeetnest.app.create_app`.

The CLI creates the application container, the meeting service creates a
pending meeting, the orchestrator runs the agents, the repository persists
agent messages, and the final Chairman JSON result is stored on the completed
meeting.

For v1, the default LLM provider is the deterministic mock provider. It does
not call external services.

## Main Components

### CLI

`parakeetnest.cli` exposes the local command-line entry point.

It accepts:

- an investment question;
- a required ticker;
- an optional SQLite database path.

The CLI prints the persistent meeting id, meeting status, and final structured
JSON result.

### Application Container

`parakeetnest.app.ParakeetNestApp` owns runtime wiring:

- configuration;
- SQLite engine and session;
- committee meeting repository;
- prompt renderer;
- LLM provider;
- agent runtime;
- committee orchestrator;
- meeting service.

This keeps CLI code thin and keeps dependency construction in one place.

### Meeting Service

`parakeetnest.services.meeting.MeetingService` is the application-level entry
point for one committee meeting.

It is responsible for:

- creating a pending meeting;
- calling the committee orchestrator;
- marking the meeting completed with final JSON;
- marking the meeting failed if an exception occurs;
- committing or rolling back through the application container.

### Committee Meeting Repository

`parakeetnest.database.repository.CommitteeMeetingRepository` owns persistence
for committee meetings and committee messages.

It stores:

- meeting question;
- ticker;
- meeting status;
- final result JSON;
- error message when failed;
- one message per agent.

SQLite is the v1 persistence layer.

### Committee Meeting Orchestrator

`parakeetnest.committee.orchestrator.CommitteeMeetingOrchestrator` runs the
fixed agent flow for an existing persistent meeting.

For each agent, it builds a `MeetingContext` containing:

- meeting id;
- question;
- ticker;
- previous agent results.

Each agent receives the prior messages so the committee can build toward a
final Chairman decision.

### Agent Runtime

`parakeetnest.committee.runtime.AgentRuntime` provides the shared execution
path for prompt-backed committee agents.

It combines:

- agent metadata;
- rendered prompt files;
- meeting context;
- previous agent messages;
- provider response parsing.

### Prompt Renderer

`parakeetnest.committee.runtime.PromptRenderer` loads committee prompts from
the configured prompt directory.

Current prompt files live under `src/parakeetnest/committee/prompts`.

### LLM Provider

`parakeetnest.llm.provider.LLMProvider` is the provider interface.

`parakeetnest.llm.mock.MockLLMProvider` is the current default provider. It
returns deterministic schema-valid JSON and performs no network calls.

### Committee Agents

Current prompt-backed agents are defined in `parakeetnest.committee.agents`.

They are intentionally small metadata classes. Shared execution lives in the
agent runtime.

## Data Flow

1. User runs `parakeetnest meeting`.
2. CLI normalizes the ticker to uppercase.
3. CLI creates `ParakeetNestApp`.
4. `MeetingService` creates a pending committee meeting in SQLite.
5. `CommitteeMeetingOrchestrator` runs agents in fixed order.
6. For each agent:
   - build `MeetingContext`;
   - render the agent prompt;
   - call the configured `LLMProvider`;
   - parse the provider response;
   - persist the agent message to SQLite.
7. Chairman runs last and returns the final structured result JSON.
8. `MeetingService` marks the meeting completed and stores the final result.
9. CLI prints meeting id, status, and final JSON.

Failure flow:

1. If any step raises an exception, `MeetingService` marks the meeting failed.
2. The application rolls back pending work.
3. The original error is raised to the CLI caller.

## Current Agents

### Dongdong

Role: Chief Opportunity Hunter.

Dongdong focuses on opportunity, market mispricing, catalysts, and upside
possibilities. In the first committee workflow, Dongdong receives the original
meeting question plus prior agent results.

### Xixi

Role: Chief Fundamental Analyst.

Xixi focuses on business quality, fundamentals, durability, and long-term
ownership logic. Xixi is the first agent in the current orchestrator order.

### Yoyo

Role: Chief Risk Officer.

Yoyo focuses on downside scenarios, valuation risk, concentration risk,
uncertainty, and what could go wrong.

### Chairman

Role: Final decision maker.

Chairman runs last and produces the final structured result. The final result
must include:

- action;
- confidence;
- horizon;
- evidence;
- risks;
- catalysts.

## CLI Usage

Install the project in editable mode:

```bash
.venv/bin/python -m pip install -e ".[dev]"
```

Run one local committee meeting:

```bash
.venv/bin/python -m parakeetnest.cli meeting \
  --ticker NVDA \
  "Should we buy more NVDA this quarter?"
```

Run with an explicit SQLite database path:

```bash
.venv/bin/python -m parakeetnest.cli meeting \
  --ticker NVDA \
  --database ./parakeetnest.sqlite3 \
  "Should we buy more NVDA this quarter?"
```

Expected output shape:

```text
meeting_id: 1
status: completed
final_result:
{
  "action": "watch",
  "catalysts": ["..."],
  "confidence": "medium",
  "evidence": [{"summary": "...", "source": "..."}],
  "horizon": "3_months",
  "risks": ["..."]
}
```

## What Is Intentionally Not Included Yet

Epic 001 intentionally does not include:

- automatic trading;
- broker integration;
- portfolio execution;
- hard-coded API keys;
- real OpenAI calls;
- real market data providers;
- real news providers;
- real portfolio account sync;
- background scheduling;
- report generation;
- email delivery;
- web UI;
- multi-meeting memory recall in the CLI path;
- context retrieval from historical theses or research notes in the CLI path.

The first committee is a local research workflow, not an execution system.

## Future Work

### Context Layer

Add a memory-first context layer that loads relevant historical theses,
previous committee discussions, research notes, lessons learned, and data
quality notes before any agent reasons.

The target invariant is:

```text
The committee remembers before it reasons.
```

### Market Data

Add provider-backed market data services behind typed service protocols.

Market data must be normalized, source-attributed, freshness-checked, and
validated before it reaches committee reasoning.

### News

Add news collection and source tracking.

News should enter the system as attributed evidence, not as hidden judgment.
Committee agents may interpret news only after it has been collected and made
available as context.

### Portfolio

Add portfolio snapshot ingestion and portfolio-aware analysis.

The portfolio layer should support research questions such as concentration,
position sizing context, exposure, and risk. It must not place trades or
implement automatic execution.
