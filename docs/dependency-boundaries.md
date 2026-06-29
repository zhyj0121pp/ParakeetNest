# Dependency Boundaries

This document defines which ParakeetNest packages may import each other after
Milestone 6.5. The goal is to keep data collection, persistence, memory,
committee reasoning, and reporting independently testable.

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
- `decision`;
- `reports`;
- `scheduler`.

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

Allowed imports:

- `parakeetnest.domain`;
- `parakeetnest.exceptions`;
- `parakeetnest.services` internals;
- shared service protocols and data quality models.

Must not import:

- `parakeetnest.database.models`;
- SQLAlchemy;
- `parakeetnest.committee`;
- `parakeetnest.memory`;
- `parakeetnest.decision`;
- `parakeetnest.reports`;
- OpenAI clients;
- email clients;
- brokerage/trading execution clients.

Notes:

- `services.orchestrator` may depend on the `SnapshotPersistence` protocol from
  `services.base`.
- Concrete persistence belongs in `database`.

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
- OpenAI clients;
- email clients;
- scheduler jobs.

Notes:

- `database.snapshot_repository` is the concrete adapter from validated domain
  snapshots to SQLite ORM records.
- Database code persists facts and records; it does not collect, reason, or
  decide.

### Memory

Packages:

- `parakeetnest.memory`

Allowed imports:

- `parakeetnest.memory` internals;
- `parakeetnest.models` for committee memo shapes.

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

### Committee

Packages:

- `parakeetnest.committee`

Allowed imports:

- `parakeetnest.models`;
- `parakeetnest.committee` internals;
- `parakeetnest.memory.knowledge_base`;
- future LLM provider interfaces, once introduced.

Must not import:

- `parakeetnest.database.models`;
- SQLAlchemy;
- concrete market data providers;
- `parakeetnest.services.orchestrator`;
- external API clients directly;
- email clients;
- trading clients.

Notes:

- The committee receives current facts and data quality notes after services
  validate them.
- The committee must load memory through the Investment Secretary before member
  review.

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

- Decision logic should transform validated committee outputs into final
  recommendation objects.
- Recommendations must include action, confidence, horizon, evidence, risks,
  and catalysts.

### Analyzers

Packages:

- `parakeetnest.analyzers`

Allowed imports:

- `parakeetnest.domain`;
- `parakeetnest.models`;
- future typed analysis models;
- memory read interfaces where needed.

Must not import:

- concrete provider clients;
- OpenAI clients directly;
- SQLAlchemy ORM models directly;
- email clients;
- trading clients.

Notes:

- Analyzers consume validated facts and memory context.
- Analyzers should not fetch data directly.

### Reports

Packages:

- `parakeetnest.reports`

Allowed imports:

- `parakeetnest.models`;
- committee and decision output models;
- memory read interfaces;
- report persistence interfaces when introduced.

Must not import:

- concrete provider clients;
- OpenAI clients directly;
- trading clients;
- scheduler internals.

Notes:

- Reports present evidence and conclusions.
- Reports do not create new investment facts or execute trades.

### Scheduler

Packages:

- `parakeetnest.scheduler`

Allowed imports:

- top-level workflow functions;
- configuration and logging;
- service orchestrators through application workflow composition;
- report generation workflows.

Must not import:

- SQLAlchemy ORM models directly;
- OpenAI clients directly;
- provider-specific payload mappers;
- trading clients.

Notes:

- Scheduler code triggers workflows.
- Scheduler code should not contain investment analysis, recommendation policy,
  or prompt logic.

## Forbidden Dependencies

These dependencies are forbidden unless a future RFC explicitly changes the
boundary:

- `services` importing `database.models` or SQLAlchemy.
- `services` calling OpenAI or any LLM provider.
- `committee` calling market data, brokerage, news, macro, or calendar APIs
  directly.
- `committee` importing SQLAlchemy ORM models.
- `database` calling external providers or LLMs.
- `memory` fetching external data directly.
- `decision` executing trades.
- `reports` executing trades.
- Any package hard-coding API keys.
- Any package implementing automatic trading.

## Correct Import Examples

Service protocol using normalized snapshots:

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

Committee recalling investment memory:

```python
from parakeetnest.memory.knowledge_base import KnowledgeBase
from parakeetnest.committee.models import InvestmentContext
```

Decision logic using shared recommendation models:

```python
from parakeetnest.models import Recommendation, RecommendationAction
```

## Incorrect Import Examples

Service importing ORM models:

```python
from parakeetnest.database.models import MarketData
```

Service importing SQLAlchemy:

```python
from sqlalchemy.orm import Session
```

Committee fetching data directly:

```python
from parakeetnest.services.market_data import YahooMarketDataService
```

Committee importing persistence models:

```python
from parakeetnest.database.models import Recommendation
```

Database calling a model provider:

```python
from openai import OpenAI
```

Decision logic executing trades:

```python
from parakeetnest.services.brokerage import RobinhoodOrderService
```

Report generation fetching provider payloads directly:

```python
from parakeetnest.services.news import YahooFinanceNewsClient
```

## Current Enforcement

The test suite currently includes a boundary test that verifies
`services.orchestrator` does not import SQLAlchemy or `parakeetnest.database`
ORM models.

Future milestones should add broader import-boundary tests when new provider,
LLM, report, and scheduler modules are introduced.
