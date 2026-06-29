# ADR 002: Unified Data Source Architecture

## Decision

ParakeetNest will use the same provider, registry, service, and context provider
architecture for every external data source.

Each data family will own its provider-neutral models, provider protocol,
provider registry, service boundary, context adapter, deterministic mock
provider, optional live providers, and focused tests.

The committee, memory, decision, report, and context assembly layers must not
depend on concrete provider SDKs, raw provider payloads, provider-specific
exceptions, or provider-specific configuration details.

## Context

The Market Data Layer established a working provider pattern with mock and Yahoo
Finance providers. The News Layer then reused the same architectural shape with
source-attributed news articles, `NewsProvider`, `NewsProviderRegistry`,
`NewsService`, and `NewsContextProvider`.

Future Epics will add SEC filings, macro data, portfolio data, and calendar
events. Without one shared architecture, each source could introduce its own
configuration style, error behavior, context integration, and test strategy.
That would make committee reasoning harder to trust and would weaken the core
project principle: the committee remembers before it reasons.

ParakeetNest must also remain research-only. A unified data source architecture
keeps external read integrations separate from any trading behavior, which
remains out of scope.

## Alternatives

One option was to let each Epic design its own integration style. That would
optimize locally, but it would produce inconsistent services, provider IDs,
tests, and dependency boundaries.

Another option was to make the Context Layer fetch all external data directly.
That would simplify initial wiring but would turn context assembly into a
source-specific integration layer and make it harder to test or replace
providers independently.

A third option was to expose concrete provider clients directly to meeting or
committee workflows. That would leak vendor behavior into reasoning, prompts,
and tests.

## Consequences

Every new external data family has a predictable extension model:

1. define provider-neutral models and requests;
2. define a small provider protocol;
3. implement a deterministic mock provider;
4. implement optional live providers behind configuration;
5. register providers by stable IDs;
6. expose a service that depends on the provider protocol;
7. adapt the service into `MeetingContext` through a context provider;
8. keep tests deterministic and network-free by default.

Benefits:

- provider SDKs stay isolated at the edge;
- mock providers remain first-class and safe for tests;
- configuration fails early for unknown provider IDs;
- committee prompts receive normalized facts instead of vendor payloads;
- source replacement does not require committee, memory, or decision changes;
- future cross-provider behavior has a clear home in service layers;
- architecture boundary tests can be reused across data families.

Tradeoffs:

- every data family has a small amount of repeated structure;
- simple integrations require more up-front modeling than direct SDK calls;
- provider-specific capabilities must be translated into provider-neutral
  models, which can hide details unless metadata is designed carefully.

The accepted tradeoff is intentional. ParakeetNest values reliable memory,
source attribution, testability, and safe dependency boundaries over direct
access to provider SDK features.
