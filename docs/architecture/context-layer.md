# Context Layer Architecture

The Context Layer assembles all non-LLM research inputs before the committee
reasons. Its job is to make "remember before reasoning" concrete: providers
load facts and memory into one deterministic `MeetingContext`, then the prompt
renderer turns that context into committee-readable markdown.

## Pipeline

```text
ContextRequest
  -> ContextProviderRegistry
  -> provider config enable/disable
  -> ContextService
  -> MeetingContext
  -> MeetingContextPromptRenderer
  -> MeetingService / Committee prompt
```

1. `MeetingService.run()` creates a `ContextRequest` from the meeting question
   and ticker symbols.
2. `ContextProviderRegistry` registers providers under stable provider IDs in a
   deterministic order.
3. App config applies provider enable/disable rules before `ContextService`
   receives providers.
4. `ContextService.build_context()` asks enabled providers whether they support
   the request, executes supported providers in order, and merges their partial
   contexts.
5. The result is a single `MeetingContext` containing request metadata, data
   quality notes, warnings, and populated context sections.
6. `MeetingContextPromptRenderer` renders `MeetingContext` into markdown.
7. `PromptRenderer` inserts that markdown into each agent prompt, and the
   committee uses it during `MeetingService` execution.

## Provider Responsibilities

Context providers adapt one data source into the shared context model. Future
providers such as Yahoo Finance, SEC filings, news, portfolio, and macro should
follow the same contract:

- Implement `supports(request)` and return whether the provider can contribute.
- Implement `build_context(request)` and return `ContextProviderResult`.
- Return a partial `MeetingContext`; populate only sections the provider owns.
- Include source, fetch time, data quality notes, warnings, and provider
  metadata when available.
- Do not call an LLM.
- Do not mutate persistence.
- Keep output deterministic for the same request and fixture/input state.

Providers may return non-fatal problems through `ContextProviderResult.errors`
or `warnings`. They should reserve exceptions for programmer errors or cases
where the application cannot safely continue.

## Merge Rules

`ContextService` owns merging so every provider follows one predictable policy:

- Providers run in the deterministic order resolved from the registry.
- Providers whose `supports(request)` returns `False` are skipped.
- Context sections use first-provider-wins semantics.
- If a later provider returns a section that is already populated, that duplicate
  section is skipped and a warning is added.
- Provider result warnings are appended to context warnings.
- Provider result errors are converted to context warnings in the form
  `<provider_name> error: <error>`.
- Partial context metadata sources, warnings, and data quality notes are
  appended in provider order.
- Provider result metadata is converted to deterministic data quality notes as
  `<provider_name>.<key>=<value>`, sorted by metadata key.
- `generated_at` starts from `ContextRequest.as_of`; if absent, the first
  provider metadata timestamp can fill it.

Current sections are `market`, `news`, `filings`, `portfolio`, `macro`, and
`knowledge_base`.

## Provider IDs

The app currently registers these mock Context Layer provider IDs:

- `mock_market`
- `mock_news`
- `mock_portfolio`
- `mock_macro`
- `mock_knowledge_base`

Provider IDs are stable configuration names. They do not need to match a
provider class name, but they should be clear, unique, and documented here when
added.

## Config Behavior

`AppConfig` controls which registered providers reach `ContextService`:

- `enabled_context_provider_ids` is an allow-list.
- `disabled_context_provider_ids` is a block-list.
- If both are configured for the same provider, disabled wins.
- If `enabled_context_provider_ids` is `None`, all registered providers are
  enabled by default.
- Unknown provider IDs raise during app creation instead of being ignored.

## How to Add a New Provider

1. Add a provider class under `src/parakeetnest/context/providers/` that
   implements the `ContextProvider` protocol.
2. Give it a stable `provider_name` and return that name in
   `ContextProviderResult.provider_name`.
3. Implement `supports(request)` around request shape and feature flags such as
   `include_portfolio`, `include_macro`, or `include_knowledge_base`.
4. Implement `build_context(request)` by adapting the source into a partial
   `MeetingContext`; do not call LLMs or write to SQLite.
5. Register it in `_create_context_provider_registry()` with a documented
   provider ID.
6. Add focused tests for support behavior, partial context contents, merge
   behavior, and config enable/disable behavior.
