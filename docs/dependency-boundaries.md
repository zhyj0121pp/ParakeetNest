# Dependency Boundaries

This document defines which ParakeetNest packages may import each other at the
v1.0 architecture freeze. The goal is to keep facts, context assembly,
committee reasoning, investment judgment, and local reporting independently
testable.

The governing product flow is:

```text
Facts -> Context -> LLM Committee -> Investment Judgment -> Human Decision
```

ParakeetNest is committee-driven. It is not a research-pipeline-first system
and it is not an autonomous trading system.

## Import Layers

### Foundation

Packages:

- `parakeetnest.config`
- `parakeetnest.logging`
- `parakeetnest.exceptions`
- `parakeetnest.runtime`

Allowed imports:

- standard library;
- third-party infrastructure libraries where appropriate;
- `runtime` may import `config` and `logging`.

Must not import:

- `services`;
- `database`;
- `committee`;
- `memory`;
- provider packages;
- report workflows.

### Stable Models

Packages:

- `parakeetnest.domain`
- `parakeetnest.models`

Allowed imports:

- standard library only.

Must not import:

- service implementations;
- database models;
- committee members;
- memory services;
- LLM providers;
- external API clients.

### Services

Packages:

- `parakeetnest.services`

Current ownership:

- `services.meeting` is an application service for committee meeting
  orchestration.
- `services.base`, `services.orchestrator`, `services.data_quality`, and the
  `Mock*Service` modules are retained legacy data collection compatibility
  infrastructure.

Allowed imports:

- `parakeetnest.domain`;
- `parakeetnest.exceptions`;
- `parakeetnest.services` internals;
- shared service protocols and data quality models.
- `services.meeting` may import committee, context, database repository, LLM
  context rendering, and shared model contracts needed to run a meeting.

Must not import:

- `parakeetnest.database.models`;
- SQLAlchemy;
- concrete provider SDKs;
- report delivery implementations;
- OpenAI clients directly;
- email clients;
- brokerage/trading execution clients.

Notes:

- `services.orchestrator` may depend on the `SnapshotPersistence` protocol from
  `services.base`.
- Concrete persistence belongs in `database`.
- New source or intelligence work should use domain packages plus context
  providers instead of expanding the legacy collection path.

### Database

Packages:

- `parakeetnest.database`

Allowed imports:

- `parakeetnest.domain`;
- `parakeetnest.models` when mapping recommendation-like records;
- `parakeetnest.services.data_quality` for persisted quality metadata;
- SQLAlchemy.

Must not import:

- `parakeetnest.committee` role implementations;
- `parakeetnest.services.orchestrator`;
- real provider clients;
- LLM clients;
- email clients.

Notes:

- `database.snapshot_repository` is the concrete adapter from validated domain
  snapshots to SQLite ORM records.
- Database code persists facts and records; it does not collect, reason, or
  decide.

### Memory

Packages:

- `parakeetnest.memory`
- `parakeetnest.committee.memory`

Allowed imports:

- `parakeetnest.memory` internals;
- `parakeetnest.committee.memory` internals;
- shared model contracts;
- repository interfaces.

Must not import:

- `parakeetnest.services` provider implementations;
- `parakeetnest.committee` role implementations;
- OpenAI clients;
- real market data clients;
- email clients;
- trading clients.

Notes:

- Memory owns investment knowledge, not raw provider payloads.
- Future repository-backed memory may import database repositories through a
  narrow adapter, but role logic should still remain outside memory.

### Source and Intelligence Packages

Packages:

- `parakeetnest.market_data`
- `parakeetnest.news`
- `parakeetnest.sec`
- `parakeetnest.financials`
- `parakeetnest.macro`
- `parakeetnest.valuation`
- `parakeetnest.portfolio`
- `parakeetnest.watchlist`
- `parakeetnest.regime`
- `parakeetnest.intelligence`

Allowed imports:

- package-local models, providers, registries, services, and calculators;
- shared model types;
- context provider contracts when adapting facts into `MeetingContext`.

Must not import:

- committee agent implementations;
- `services.orchestrator`;
- SQLAlchemy ORM models directly;
- LLM clients directly;
- email clients;
- trading clients.

Notes:

- These packages prepare facts and derived context. They do not produce final
  investment judgment.
- Provider-specific SDKs stay inside concrete provider adapter modules.

### Context

Packages:

- `parakeetnest.context`

Allowed imports:

- context models and provider contracts;
- source and intelligence service models through dedicated context providers;
- shared model contracts.

Must not import:

- concrete provider SDKs;
- SQLAlchemy ORM models directly;
- LLM clients directly;
- email clients;
- trading clients.

Notes:

- `ContextService` owns merge policy.
- Context providers adapt facts into `MeetingContext`; they do not run
  committee reasoning.

### Committee

Packages:

- `parakeetnest.committee`

Allowed imports:

- `parakeetnest.models`;
- `parakeetnest.committee` internals;
- `parakeetnest.memory.knowledge_base`;
- `parakeetnest.committee.memory`;
- LLM provider interfaces.

Must not import:

- `parakeetnest.database.models`;
- SQLAlchemy;
- concrete market data providers;
- `parakeetnest.services.orchestrator`;
- external API clients directly;
- email clients;
- trading clients.

Notes:

- The committee receives prepared context and recalled memory.
- Committee agents must not fetch source data directly.
- The committee produces advisory judgment only; human decision remains final.

### LLM

Packages:

- `parakeetnest.llm`

Allowed imports:

- shared model contracts;
- provider-neutral request/response schemas;
- standard library and configured client libraries inside concrete adapters.

Must not import:

- concrete source providers;
- SQLAlchemy ORM models directly;
- email clients;
- trading clients.

Notes:

- LLM code provides execution boundaries. It does not fetch facts or execute
  investment actions.

### Decision

Packages:

- `parakeetnest.decision`

Allowed imports:

- `parakeetnest.models`;
- future typed committee output models;
- future policy helpers.

Must not import:

- concrete external data providers;
- OpenAI clients directly;
- SQLAlchemy ORM models directly;
- email clients;
- trading clients.

Notes:

- Decision currently provides shared recommendation model exports.
- Investment judgment is committee-led and human-reviewed.
- Recommendations must include action, confidence, horizon, evidence, risks,
  and catalysts.

### Research and Reports

Packages:

- `parakeetnest.research`
- `parakeetnest.reports`

Allowed imports:

- `parakeetnest.models`;
- committee and decision output models;
- memory read interfaces;
- report persistence interfaces when introduced.

Must not import:

- concrete provider clients;
- OpenAI clients directly;
- trading clients.

Notes:

- Reports present committee judgment, evidence, risks, and catalysts.
- Reports do not create new investment facts, make autonomous decisions, or
  execute trades.

## Forbidden Dependencies

These dependencies are forbidden unless a future RFC explicitly changes the
boundary:

- `services` importing `database.models` or SQLAlchemy.
- legacy collection services calling OpenAI or any LLM provider.
- `committee` calling market data, brokerage, news, macro, or calendar APIs
  directly.
- `committee` importing SQLAlchemy ORM models.
- `database` calling external providers or LLMs.
- `memory` fetching external data directly.
- `decision` executing trades.
- `reports` executing trades.
- `research` or `reports` making autonomous trading decisions.
- Any package hard-coding API keys.
- Any package implementing automatic trading.

## Correct Import Examples

Legacy collection protocol using normalized snapshots:

```python
from parakeetnest.domain import MarketSnapshot
from parakeetnest.services.base import ServiceResult
```

Collection orchestration depending on a persistence protocol:

```python
from parakeetnest.services.base import SnapshotPersistence
```

Database adapter mapping domain snapshots to ORM rows:

```python
from parakeetnest.database.models import MarketData
from parakeetnest.domain import MarketSnapshot
from parakeetnest.services.data_quality import DataQuality
```

Committee memory through the memory service boundary:

```python
from parakeetnest.committee.memory import CommitteeMemoryService
```

Decision logic using shared recommendation models:

```python
from parakeetnest.models import Recommendation, RecommendationAction
```

## Incorrect Import Examples

Legacy collection service importing ORM models:

```python
from parakeetnest.database.models import MarketData
```

Legacy collection service importing SQLAlchemy:

```python
from sqlalchemy.orm import Session
```

Committee fetching data directly:

```python
from parakeetnest.market_data.yahoo import YahooFinanceMarketDataProvider
```

Committee importing persistence models:

```python
from parakeetnest.database.models import Recommendation
```

Database calling an LLM provider:

```python
from openai import OpenAI
```

Decision logic executing trades:

```python
from parakeetnest.services.brokerage import RobinhoodOrderService
```

Report generation fetching provider payloads directly:

```python
from parakeetnest.news.yahoo import YahooNewsProvider
```

## Current Enforcement

The test suite currently includes a boundary test that verifies
`services.orchestrator` does not import SQLAlchemy or `parakeetnest.database`
ORM models.

Future milestones should add broader import-boundary tests as provider, LLM,
and report workflows expand.
