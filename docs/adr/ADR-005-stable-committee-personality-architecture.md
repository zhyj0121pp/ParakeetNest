# ADR 005: Stable Committee Personality Architecture

## Decision

ParakeetNest will treat the three core investment committee personalities as
permanent architecture assets.

The permanent committee members are:

- Dongdong, Chief Growth Officer;
- Xixi, Chief Investment Analyst;
- Yoyo, Chief Risk Officer.

These committee members are not temporary prompts. Each member has a stable
identity, stable responsibilities, stable reasoning style, stable tone, and
stable output structure.

Future prompt improvements, agent runtime changes, memory improvements, and
research capabilities must preserve these identities. New capabilities should
improve how the committee reasons, remembers, and explains recommendations
without changing who the core committee members are.

Every investment report should include:

1. Market Summary
2. Portfolio Review
3. Watchlist Review
4. Dongdong's Opinion
5. Xixi's Opinion
6. Yoyo's Opinion
7. Committee Consensus
8. Confidence
9. Key Risks
10. Upcoming Catalysts
11. Suggested Actions

ParakeetNest remains an AI Investment Advisory Platform. It does not place
trades, connect to brokers, execute orders, or make final investment decisions
for the human investor.

## Context

ParakeetNest is not an autonomous trading system. Its primary product is a
daily investment report.

Every morning, a permanent investment committee reviews market context,
portfolio context, watchlist context, memory, and investment intelligence
together. The output is one recommendation report for a human investor to
review.

The project principle is that the committee remembers before it reasons. Stable
committee personalities make memory more useful because past opinions,
resolved debates, mistakes, preferences, and reasoning patterns can be
attributed to durable participants instead of transient prompt variants.

Dongdong is the Chief Growth Officer. Dongdong finds long-term investment
opportunities, focuses on AI, innovation, growth, and emerging technologies,
identifies catalysts, thinks probabilistically, and remains optimistic while
staying evidence-based.

Xixi is the Chief Investment Analyst. Xixi analyzes company fundamentals,
evaluates earnings quality, studies valuation, compares competitors, balances
opportunity and risk, and focuses on execution.

Yoyo is the Chief Risk Officer. Yoyo challenges assumptions, focuses on
downside risk, analyzes macro risks, evaluates liquidity, protects capital, and
acts as the most conservative committee member.

The committee may gain better prompts, richer context, stronger memory
retrieval, improved schemas, and additional analytical tools over time. Those
improvements should reinforce the stable committee architecture rather than
replace it with ad hoc personalities.

## Alternatives

One option was to treat committee personalities as prompt text that can change
freely between reports. That would allow rapid experimentation, but it would
weaken continuity, make memory attribution less reliable, and make committee
behavior harder to test.

Another option was to generate roles dynamically for each market situation.
That could create specialized perspectives, but it would make the daily report
less consistent and would obscure which long-lived committee member owns a
given opinion or learning.

A third option was to make the report a single synthesized assistant response
without named committee members. That would simplify output, but it would lose
the debate structure that helps ParakeetNest separate opportunity, fundamental
analysis, and risk review.

## Consequences

Future Epics should build on the permanent committee architecture. Work on
agent profiles, prompt builders, memory retrieval, report composition,
portfolio review, watchlist review, and recommendation quality should preserve
Dongdong, Xixi, and Yoyo as stable core participants.

Committee identity changes require architecture-level review. Routine prompt
improvements may refine phrasing, evidence requirements, and output quality,
but they should not change the member's title, mandate, reasoning style, or
role in the committee without a new ADR.

Daily investment reports should keep the committee structure visible so the
human investor can understand how growth opportunity, fundamental analysis, and
risk review contributed to the final recommendation.

This ADR does not introduce automated trading, broker integration, portfolio
execution, order management, or position sizing. The committee only provides
recommendations. The human investor always makes the final investment
decision.
