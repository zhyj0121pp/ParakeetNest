# ADR 004: Agent-First Committee Architecture

## Decision

ParakeetNest will evolve the AI Investment Committee through an agent-first
architecture.

Specialist committee members will be defined as agent profiles, registered by
stable IDs, rendered through a shared prompt builder, executed through a shared
agent runtime, and orchestrated by committee flows that inject memory and
research context before reasoning begins.

Future Phase V work must follow this architecture:

- Epic 21: Specialized Investment Agents;
- Epic 22: Committee Memory;
- Epic 23: Portfolio Committee;
- Epic 24: Watchlist Intelligence;
- Epic 25: CIO Decision Engine.

This ADR is architecture-only. It does not require production code changes,
runtime behavior changes, or refactoring of the existing committee
implementation before the migration path is started.

## Background

ParakeetNest v2.0 completes the first full investment committee. The system now
has normalized data sources, investment intelligence context, prompt-backed
committee agents, meeting orchestration, memory repositories, and a Chairman
summary that produces structured investment research.

The current committee proves the end-to-end product shape. Xixi, Dongdong,
Yoyo, and the Chairman can review rendered context and produce recommendations
that include action, confidence, horizon, evidence, risks, and catalysts.

Phase V changes the scaling problem. The platform must support more specialized
agents, richer memory, portfolio-aware meetings, watchlist intelligence, and a
CIO-style decision engine without turning every new role into a bespoke class,
prompt path, orchestration branch, or persistence exception.

The committee remembers before it reasons. Agent-first architecture keeps that
principle explicit by making agent identity, instructions, context needs,
memory needs, and output contracts first-class architectural concepts.

## Problem With Current Committee Architecture

The current committee architecture is intentionally small and fixed. That was
correct for the first complete committee, but it creates pressure points for
Phase V.

Agent identity is partly encoded in concrete classes and prompt filenames.
Adding many specialists would require repetitive class definitions even when
the role differs only by profile metadata, prompt instructions, context needs,
or output schema.

Committee composition is fixed at construction time. The orchestrator can run a
tuple of agents, but there is no architectural concept of selecting agents by
meeting type, portfolio scope, watchlist trigger, mandate, or specialist
capability.

Prompt rendering is shared, but it is not yet driven by explicit agent profile
requirements. As specialist agents grow, prompts need consistent handling for
role instructions, available tools, required evidence, output schemas,
guardrails, memory, prior agent results, and context sections.

Memory exists, but committee memory is not yet agent-aware. Future agents need
to retrieve role-relevant memories, prior theses, unresolved debates, portfolio
decisions, watchlist events, and past mistakes before they reason.

Context injection is meeting-level rather than profile-aware. Some agents need
fundamentals, some need risk and portfolio exposure, some need catalysts, and
some need watchlist history. The architecture needs a controlled way to declare
and inject those needs without letting agents fetch raw providers or source
services directly.

The Chairman currently summarizes after a fixed debate. Phase V needs a CIO
decision engine that can synthesize specialist outputs, enforce recommendation
contracts, preserve research-only boundaries, and decide when more committee
work is required.

## Agent-First Architecture Principles

Agents are configured before they are coded. A new specialist should begin as
an agent profile that declares identity, mandate, prompt source, context needs,
memory needs, output contract, and research guardrails.

Agents consume rendered context, not providers. Specialist agents must not
import external provider SDKs, concrete provider services, or raw source
payloads. Data and derived intelligence must still flow through provider,
service, intelligence, context provider, and rendering boundaries.

Memory is injected before reasoning. Agent runtime receives memory artifacts as
part of the prompt-ready context. Agents do not query persistence directly
during a reasoning turn.

Committee composition is explicit. A committee meeting should declare which
agent profiles participate, why they participate, what order or topology they
use, and which output contracts govern the result.

The runtime is shared. Prompt rendering, LLM calls, schema parsing, metadata,
and error handling should live in shared runtime services instead of being
reimplemented by each agent.

The Chairman and future CIO remain research-only decision makers. They may
produce recommendations and portfolio research decisions, but they must not
place trades, trigger automatic trading, or require hard-coded API keys.

Every recommendation remains structured. Final recommendations must include
action, confidence, horizon, evidence, risks, and catalysts.

## Agent Profile Model

An agent profile is the durable definition of a committee role. It should be a
small provider-neutral model that can be registered, inspected, tested, and
passed to the prompt builder.

An agent profile should include:

- stable `agent_id`;
- display `name`;
- committee `role`;
- investment `mandate`;
- prompt template or instruction source;
- required context sections;
- optional context sections;
- memory query policy;
- output schema;
- participation constraints;
- research guardrails;
- version metadata.

The profile is not the runtime. It should not own LLM calls, database access,
provider access, or orchestration behavior. It tells the platform what kind of
agent is being run; shared services decide how to prepare and execute the turn.

Initial profiles should cover Xixi, Dongdong, Yoyo, the Chairman, and the
specialists introduced by Epic 21. Later profiles can add portfolio, watchlist,
macro, valuation, catalyst, forensic accounting, quality, sentiment, liquidity,
or tax-aware research roles without changing the core runtime shape.

## Agent Registry

The agent registry owns discovery and selection of agent profiles.

The registry should provide stable lookup by `agent_id`, list available
profiles, and support committee composition by meeting type. Unknown agent IDs
should fail early as configuration errors.

The registry should not instantiate provider clients, fetch research data, read
memory records directly, or call the LLM. It is the equivalent of the provider
registry pattern for committee roles: centralize selection while keeping
runtime behavior behind explicit boundaries.

Committee flows should depend on the registry abstraction, not on concrete
specialist classes. Tests should be able to register deterministic profiles
without LLM calls or network access.

## Agent Prompt Builder

The agent prompt builder owns prompt assembly for one agent turn.

It should combine:

1. system instructions;
2. agent profile instructions;
3. original user request;
4. meeting metadata;
5. rendered research context;
6. rendered investment intelligence context;
7. role-relevant memory context;
8. prior agent results;
9. required output schema instructions;
10. research guardrails.

Prompt construction should be deterministic and testable. Agent prompt files
may remain Markdown, but the builder should be driven by profile metadata
rather than hard-coded role branches.

The prompt builder may format context, but it must not fetch external data,
derive investment intelligence, query persistence, or decide the final
recommendation. Those responsibilities remain outside prompt rendering.

## Agent Runtime

The agent runtime executes one prepared agent turn.

It should render the prompt through the agent prompt builder, call the
configured LLM provider, parse the response against the profile output schema,
attach execution metadata, and return a persistable agent result.

The runtime should remain provider-neutral and deterministic in tests. Mock LLM
providers must remain first-class. Runtime code must not hard-code API keys,
call trading APIs, or import source-specific provider SDKs.

Runtime failures should preserve enough metadata for the meeting orchestrator
to record failed turns, retry safely where appropriate, or ask the CIO flow to
defer a decision.

## Agent Context Injection

Agent context injection prepares the prompt-ready evidence each profile is
allowed to see.

Context injection should start from assembled meeting context and investment
intelligence context. It may filter, prioritize, summarize, or label context
sections according to the agent profile, but it must not bypass existing data
source, intelligence, or context provider boundaries.

For example:

- a fundamental analyst may receive financial statements, valuation, filings,
  and business-quality notes;
- a risk officer may receive risk, sentiment, health, drawdown, and portfolio
  exposure context;
- an opportunity hunter may receive catalysts, momentum, sentiment, sector
  rotation, and watchlist changes;
- a portfolio committee agent may receive holdings, constraints, concentration,
  liquidity, and tax or mandate notes;
- a CIO agent may receive all final agent outputs plus decision policy context.

The output of context injection should be rendered context or a prompt-ready
context bundle, not concrete provider models.

## Agent Memory Integration

Committee memory must become profile-aware without letting agents query
persistence directly.

A memory integration service should retrieve and render memory before the agent
runtime begins. It should use the meeting request, ticker, portfolio scope,
watchlist scope, agent profile, and meeting type to select relevant memory.

Memory artifacts may include:

- previous theses;
- prior committee decisions;
- unresolved disagreements;
- thesis drift;
- known risks and catalysts;
- portfolio constraints;
- watchlist events;
- agent-specific lessons;
- postmortems and decision quality notes.

The Investment Secretary remains the memory keeper. Future implementations may
split retrieval, ranking, summarization, and persistence into smaller modules,
but committee orchestration should still inject memory before reasoning and
record the debate after reasoning.

## Committee Orchestration Flow

The agent-first committee flow should follow this sequence:

```text
Request
  -> Meeting policy selects committee type
  -> Agent registry resolves profiles
  -> Context services assemble research and intelligence context
  -> Memory integration retrieves and renders relevant memory
  -> Context injection prepares agent-specific context
  -> Agent runtime executes specialist turns
  -> Orchestrator persists each agent result
  -> Chairman or CIO synthesizes the debate
  -> Decision policy validates required recommendation fields
  -> Investment Secretary records memory
  -> Research-only result is returned
```

The default flow may remain sequential for now. Future flows may support
parallel specialist reviews, challenge rounds, CIO follow-up questions,
portfolio committee escalation, or watchlist-triggered lightweight reviews.
Those extensions should use the same profile, registry, prompt builder,
runtime, context injection, and memory integration boundaries.

## Extension Mechanism For Future Specialist Agents

Future specialist agents should be added by:

1. defining an agent profile;
2. adding or reusing a prompt template;
3. declaring required and optional context sections;
4. declaring memory policy;
5. selecting an output schema;
6. registering the profile by stable ID;
7. adding focused tests for prompt assembly, registry lookup, and orchestration;
8. adding integration tests with mock context and mock LLM providers.

New agents should not require new runtime classes unless they introduce a
genuinely new execution mode. A new role is usually profile data plus prompt
content, not a new orchestration subsystem.

This extension mechanism is the governing architecture for Epics 21-25.
Specialist investment agents, committee memory, portfolio committee workflows,
watchlist intelligence, and the CIO decision engine must build on this model.

## Migration Path From Current Committee Implementation

Migration should be incremental and test-preserving.

1. Document the current fixed agents as initial agent profiles.
2. Introduce an agent registry that can return those profiles by stable ID.
3. Adapt the existing prompt renderer into an agent prompt builder that accepts
   profiles while preserving current prompt output where possible.
4. Extend meeting context preparation with profile-aware context injection.
5. Add memory integration as a pre-runtime step controlled by meeting type and
   agent profile.
6. Move committee composition from hard-coded construction toward registry and
   meeting policy selection.
7. Introduce new specialist agents from Epic 21 through profiles rather than
   bespoke runtime code.
8. Evolve the Chairman into, or alongside, a CIO decision engine that validates
   final recommendation contracts.
9. Retire duplicate legacy paths only after the profile-based flow has
   equivalent coverage and behavior.

The migration should not weaken existing architecture boundaries. Committee
agents should continue to consume prompt-ready context, not source services.
Memory should be retrieved before reasoning. Tests should remain deterministic
and network-free by default.

## Consequences

Agent identity becomes inspectable and testable. The platform can explain which
agents participated, what mandate they had, what context they received, and
which schema governed their output.

Adding specialists becomes lower risk. Most new roles can be introduced through
profiles, prompts, context declarations, memory policy, and tests instead of
custom runtime code.

Committee memory becomes a first-class input to reasoning. This strengthens
the project principle that the committee remembers before it reasons.

Committee orchestration becomes more flexible. Portfolio, watchlist, and CIO
flows can select different agent sets while reusing the same execution
boundaries.

There is more up-front modeling work. Profiles, registries, prompt builders,
memory policies, and context injection introduce structure before the feature
surface fully needs it. The tradeoff is intentional: Phase V values durable
committee evolution over one-off role additions.

The architecture creates new testing obligations. Future epics should test
profile registration, prompt construction, memory injection, context filtering,
schema parsing, and orchestration behavior with mocks.

## Alternatives Considered

One option was to keep adding concrete agent classes for every specialist. That
would be simple at first, but it would duplicate metadata, prompt rendering,
schema selection, memory rules, and orchestration wiring across roles.

Another option was to make each agent responsible for fetching its own context
and memory. That would give agents autonomy, but it would break provider
boundaries, make prompts harder to reproduce, and weaken the memory-before-
reasoning principle.

A third option was to encode specialist behavior only in a large prompt. That
would avoid new architecture, but it would make committee composition,
evidence access, memory selection, and output contracts hard to test.

A fourth option was to build the CIO decision engine first and let it call
specialists ad hoc. That would centralize decisions too early and make future
specialists implementation details of the CIO rather than reusable committee
members.

The accepted approach treats agents as first-class architecture objects while
keeping execution, memory, context, and orchestration behind explicit,
testable boundaries.
