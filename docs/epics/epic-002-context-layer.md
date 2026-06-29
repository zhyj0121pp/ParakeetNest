# Epic 002: Context Layer

## Overview

Build the ParakeetNest Context Layer so the committee remembers before it
reasons.

Epic 002 establishes a domain boundary for research context. Meeting execution
now prepares market, news, portfolio, macro, and knowledge base context before
any committee agent runs. The committee receives that context through normal
prompt rendering, not by fetching data itself.

The goal is not to add live external APIs yet. The goal is a small, testable
context pipeline where all external information flows through `ContextService`
and `ContextProviders`.

## Goals

Epic 002 makes context preparation a first-class part of the meeting workflow:

- define context domain models;
- define a provider abstraction for external and remembered information;
- coordinate providers through `ContextService`;
- control enabled providers through `ContextProviderRegistry`;
- provide deterministic mock providers for local development and tests;
- build one `MeetingContext` before committee execution;
- render that context into prompt-ready markdown;
- keep committee agents from calling providers directly.

Committee recommendations still must include action, confidence, horizon,
evidence, risks, and catalysts.

## Motivation

ParakeetNest is an investment research committee, not a stateless chatbot.

If each agent fetched its own inputs, the meeting would become hard to test,
hard to reproduce, and hard to reason about. Agents could see different data,
duplicate provider calls, or mix data retrieval with investment judgment.

The Context Layer keeps those responsibilities separate:

- `MeetingService` prepares the meeting inputs;
- `ContextService` assembles the domain context;
- providers adapt data sources into partial context;
- committee agents reason over prepared context only.

This preserves the project rule: the committee remembers before it reasons.

## Architecture

Epic 002 extends the meeting path with a context preparation stage:

```text
User Request
 |
 v
MeetingService
 |
 v
ContextRequest
 |
 v
ContextProviderRegistry
 |
 v
ContextService
 |
 v
ContextProviders
 |
 v
MeetingContext
 |
 v
MeetingContextPromptRenderer
 |
 v
CommitteeMeetingOrchestrator
 |
 v
PromptRenderer + AgentRuntime
 |
 v
Xixi -> Dongdong -> Yoyo -> Chairman
 |
 v
Final JSON result
```

The important boundary is that committee agents must never fetch external data
directly. Providers know nothing about the committee, and the committee knows
nothing about provider execution.

## Components

### Context Request

`ContextRequest` describes the context needed for a meeting.

It contains:

- the user question;
- requested symbols;
- optional as-of time;
- flags for portfolio, macro, and knowledge base inclusion.

### Meeting Context

`MeetingContext` is a domain model. It is the complete prepared context for a
meeting, including request metadata and optional sections such as market, news,
filings, portfolio, macro, and knowledge base.

It is not serialized directly into prompts.

### Context Providers

`ContextProvider` is the abstraction for data sources.

A provider answers whether it supports a request and returns a
`ContextProviderResult` containing a partial `MeetingContext`. Providers may
populate only the sections they own.

Providers know nothing about `CommitteeMeetingOrchestrator`, committee agents,
prompt files, or LLM execution.

### Context Provider Registry

`ContextProviderRegistry` owns the configured provider set.

It keeps provider IDs stable, preserves deterministic provider order, and
controls which providers are enabled for the application. This lets the app
wire mock providers today and real providers later without changing committee
execution.

### Context Service

`ContextService` coordinates providers and merges partial context.

It:

- asks providers whether they support the request;
- calls supported providers in deterministic order;
- merges partial `MeetingContext` sections;
- aggregates sources, warnings, and data quality notes;
- returns one complete `MeetingContext`.

### Mock Providers

Current providers are deterministic local mocks:

- market;
- news;
- portfolio;
- macro;
- knowledge base.

They provide stable fixture data for tests, CLI use, and local development. No
external APIs are called by these providers.

### Meeting Context Prompt Renderer

`MeetingContextPromptRenderer` converts the context domain model into
prompt-ready markdown.

Current sections are intentionally simple:

- `## Market`
- `## News`
- `## Portfolio`
- `## Macro`
- `## Knowledge Base`

This keeps prompt formatting reusable while avoiding direct dataclass
serialization.

### Meeting Service

`MeetingService` is responsible for preparing context before committee
execution.

It creates the persistent meeting, constructs a `ContextRequest`, asks
`ContextService` to build a `MeetingContext`, and passes that prepared context
into the committee execution path.

### Committee

The committee receives prepared context only through normal prompt rendering.

Agents do not call providers, do not know the registry, and do not fetch market,
news, portfolio, macro, or memory data directly.

## Request Flow

1. User runs a meeting through the CLI or application service.
2. `MeetingService` creates a pending meeting.
3. `MeetingService` constructs a `ContextRequest` from the question and ticker.
4. `ContextProviderRegistry` supplies the enabled providers in stable order.
5. `ContextService` calls each supported provider.
6. Providers return partial `MeetingContext` objects.
7. `ContextService` merges partial context into one `MeetingContext`.
8. `MeetingService` passes the prepared context into committee execution.
9. `MeetingContextPromptRenderer` converts the domain context into markdown.
10. `PromptRenderer` inserts rendered context into each agent prompt.
11. Agents reason over the rendered context and previous agent messages.
12. Chairman returns the final structured recommendation.
13. `MeetingService` stores the completed result or marks the meeting failed.

## Design Decisions

### Committee Agents Do Not Fetch Data

Agents are reasoning participants. They are not data adapters.

All external information must enter through `ContextService` and registered
`ContextProviders`. This keeps provider behavior testable and prevents hidden
network or persistence work inside committee roles.

### Providers Are Committee-Agnostic

Providers adapt sources into context sections. They do not know about Xixi,
Dongdong, Yoyo, Chairman, prompts, or LLMs.

This allows new providers to be added without changing committee agent code.

### Meeting Service Owns Preparation

`MeetingService` is the boundary between user request and committee execution.
It prepares context before calling the orchestrator so every agent sees the same
meeting inputs.

### Context Service Owns Merge Policy

Provider merging is centralized in `ContextService`.

This keeps duplicate section handling, warnings, sources, and data quality
notes deterministic across all provider types.

### Meeting Context Is a Domain Model

`MeetingContext` represents prepared research context, not a prompt string and
not provider-specific payloads.

Prompt formatting belongs to `MeetingContextPromptRenderer`.

### Prompt Rendering Is the Only Committee Path

The committee receives context through rendered markdown in the normal prompt
rendering path. This preserves a single LLM execution flow and avoids a second
hidden data channel.

## Future Providers

Future providers can be added behind the same provider abstraction:

- market data provider;
- real-time or delayed quote provider;
- company fundamentals provider;
- SEC filings provider;
- earnings transcript provider;
- news provider;
- portfolio/account snapshot provider;
- macro data provider;
- internal research note provider;
- thesis history provider;
- prior discussion retrieval provider;
- lessons learned provider.

Each provider should return deterministic, source-labeled context for the same
input state and should avoid hard-coded API keys.

## Future Improvements

Future work can improve the Context Layer without changing committee
boundaries:

- richer provider configuration;
- provider freshness and staleness policies;
- data quality scoring;
- better conflict handling across duplicate sections;
- partial provider failure reporting in final recommendations;
- persisted context snapshots for meeting auditability;
- retrieval over historical theses and discussions;
- source citations in rendered context;
- provider-level caching;
- async provider execution where safe;
- richer prompt rendering templates;
- context size budgeting and summarization.

These improvements should preserve the core rule: the committee reasons over
prepared context and never fetches external data directly.
