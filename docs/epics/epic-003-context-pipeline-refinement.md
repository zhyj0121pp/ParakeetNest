# Epic 003: Context Pipeline Refinement

## Overview

Epic 003 refined the Context Layer created in Epic 002.

Epic 002 established the main boundary: the committee receives prepared context
before it reasons, and providers adapt external or remembered information into a
shared `MeetingContext`. Epic 003 made that boundary easier to configure,
extend, test, and render predictably.

This epic does not redefine the full Context Layer architecture. The detailed
pipeline contract remains in
[`docs/architecture/context-layer.md`](../architecture/context-layer.md).

## Why This Epic Existed

After Epic 002, ParakeetNest had a working context boundary, but the pipeline
still needed clearer operational rules before real providers could be added.

The immediate problem was not lack of provider types. It was that provider
registration, enablement, merge behavior, error handling, and prompt rendering
needed to become deterministic application behavior rather than informal
conventions.

Epic 003 existed to turn the Context Layer from a useful architecture into a
stable provider pipeline.

## Problem Solved After Epic 002

Epic 002 answered where context belongs. Epic 003 answered how context providers
are selected, ordered, merged, and rendered.

Without this refinement, future providers such as market data, SEC filings,
news, portfolio, and macro sources would risk introducing hidden coupling:

- app configuration could leak into `ContextService`;
- providers could run in accidental order;
- duplicate context sections could merge unpredictably;
- provider failures could break whole meetings unnecessarily;
- rendered prompt context could drift across runs;
- adding real data providers could require changes to committee execution.

Epic 003 solved those risks by making provider wiring explicit and keeping the
core context assembly path small, deterministic, and testable.

## Completed Milestones

### 3.1 Context Provider Registry

Added a simple registry for provider registration by stable provider ID.

The registry owns provider identity and order. It gives application wiring one
place to register mock providers today and real providers later.

### 3.2 Provider Configuration

Added provider enable/disable configuration at application construction time.

Provider selection happens before `ContextService` is created, so
`ContextService` receives only the enabled providers it should execute.

### 3.3 ContextService Pipeline Cleanup

Cleaned up the pipeline so `ContextService` focuses on provider support checks,
execution, section merging, sources, warnings, and data quality notes.

It does not know about the registry or app configuration.

### 3.4 Context Renderer Enhancement

Improved context rendering into deterministic prompt-ready Markdown.

The renderer is responsible for presentation. `MeetingContext` remains a domain
model, and committee agents receive context through the normal prompt path.

### 3.5 Context Layer Documentation

Documented the Context Layer pipeline, provider responsibilities, merge rules,
provider IDs, configuration behavior, and the steps for adding future
providers.

## Key Design Decisions

### Simple Registry Instead of a DI Framework

Provider registration uses a small project-owned registry instead of adding a
dependency injection framework.

The current pipeline needs stable IDs, deterministic order, and lookup
validation. A lightweight registry is enough for v1 and keeps the provider
boundary easy to inspect.

### ContextService Remains Registry/Config Agnostic

`ContextService` receives a list of providers and builds one
`MeetingContext`.

It does not read application configuration, inspect registry state, or decide
which configured providers are enabled. This keeps context assembly independent
from app wiring.

### Provider Enable/Disable Happens Before ContextService Creation

Application setup resolves enabled and disabled provider IDs before constructing
`ContextService`.

This makes provider selection an application wiring concern and keeps runtime
context assembly deterministic.

### Deterministic Provider Order

Providers execute in registry order after configuration filtering.

This matters because merge behavior, warnings, sources, and rendered output must
be reproducible for the same request and fixture state.

### First-Provider-Wins Section Merge

When multiple providers return the same context section, the first populated
section wins.

Later duplicate sections are skipped and reported as warnings. This avoids
implicit blending of provider payloads and gives future provider composition a
clear rule.

### Provider Errors Become Context Warnings

Non-fatal provider errors are converted into context warnings.

The committee can still reason over available context while seeing that part of
the pipeline failed or returned incomplete information.

### Renderer Output Is Deterministic Prompt-Ready Markdown

`MeetingContextPromptRenderer` turns the domain model into stable Markdown
sections for prompts.

The renderer avoids direct dataclass dumps and keeps prompt formatting explicit,
repeatable, and suitable for committee agents.

## Future Work

Epic 003 prepares the project for Epic 4: Market Data Layer.

Expected provider work includes:

- Yahoo Finance provider;
- SEC filings provider;
- News provider;
- Portfolio provider;
- Macro provider.

These providers should follow the documented Context Layer contract: adapt data
into partial `MeetingContext` objects, avoid LLM calls, avoid persistence
mutation, include source and quality metadata, and keep output deterministic for
the same input state.

## Completion Checklist

- Context provider registry exists with stable provider IDs.
- Provider configuration can enable and disable providers.
- `ContextService` is independent of registry and app configuration.
- Providers run in deterministic order.
- Duplicate sections use first-provider-wins merge behavior.
- Provider warnings and errors are preserved as context warnings.
- Context rendering produces deterministic prompt-ready Markdown.
- Context Layer architecture documentation is available.
- No automatic trading was introduced.
- No API keys were hard-coded.
