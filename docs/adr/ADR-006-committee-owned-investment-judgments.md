# ADR 006: Committee-Owned Investment Judgments

## Decision

Only the Investment Committee can produce investment judgments.

Research, portfolio, watchlist, market data, and intelligence layers provide
facts and context. They do not emit final recommendation actions, final
confidence, committee consensus, today's suggested actions, final risk posture,
or final investment rationale.

## Context

ParakeetNest is built around the principle that the committee remembers before
it reasons. The old daily research path let `InvestmentResearchService` create
recommendation-like outputs before Dongdong, Xixi, and Youyou reviewed the
evidence. That inverted ownership: committee members were explaining a
pre-existing recommendation instead of producing independent committee judgment.

Facts include ticker summaries, portfolio facts, watchlist facts, market
context, intelligence signals, factual risk signals, factual catalyst signals,
findings, evidence notes, and source summaries. Judgments include buy, hold,
watch, reduce, sell, recommendation action, final confidence, committee
consensus, today's suggested actions, final risk posture, and final investment
rationale.

## Alternatives

One option was to keep research-generated recommendations and label them as
preliminary. That preserves compatibility but keeps the architectural confusion.

Another option was to split the report into a factual research service and a
deterministic committee report layer. This is the chosen direction because it
makes ownership explicit and keeps v1 simple.

## Consequences

Research models remain factual. Committee opinion models own stance, reasoning,
evidence considered, concerns, and suggested actions. Committee consensus owns
the final advisory action, confidence, horizon, rationale, final risk posture,
and today's suggested actions.

Reports must not render a separate pre-committee recommendations section.
Reports may render factual ticker context, key risks, catalysts, committee
opinions, and committee consensus.

The boundary remains advisory-only. ParakeetNest does not automate trading,
does not integrate with brokers, and does not place orders. A human investor
always makes the final decision.
