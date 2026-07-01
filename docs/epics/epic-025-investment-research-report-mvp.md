# Epic 25 - Investment Research Report MVP

## Goal

Create the first end-to-end investment research report model and generator for
the daily email report outcome. The MVP focuses on portfolio/watchlist research
and recommendations, not a generic platform surface.

## Scope

- Add provider-neutral report models under `src/parakeetnest/research/`.
- Add `InvestmentResearchService` to assemble reports for requested tickers.
- Reuse existing portfolio, watchlist, and investment intelligence abstractions
  when they are provided.
- Avoid external APIs, schedulers, email delivery, web UI, REST APIs, auth,
  dashboards, and new database tables.

## Output Model

- `InvestmentResearchReport`
- `ResearchTickerReport`
- `ResearchFinding`
- `ResearchRisk`
- `ResearchCatalyst`
- `ResearchRecommendation`
- `RecommendationType`
- `ConfidenceLevel`

Every ticker report includes summary, bull case, bear case, risks, catalysts,
recommendation, confidence, source summaries, and evidence notes. Every
recommendation carries action, confidence, horizon, evidence, risks, and
catalysts so it can be rendered into email later without recovering missing
decision context.

## Architecture Decisions

- The research package is provider-neutral and dataclass-based, matching the
  existing domain model style.
- The service depends on small protocols instead of provider classes. It can use
  `PortfolioService`, `WatchlistIntelligenceService`, and
  `InvestmentIntelligenceService`, but it does not know about Yahoo, SEC, news,
  financial statement, scheduler, email, or persistence adapters.
- Missing dependencies are represented as evidence notes and low-confidence
  watch recommendations rather than hidden failures.
- Watchlist-only tickers produce `WATCH`; existing holdings default to `HOLD`
  unless aggregate intelligence risk is high enough to suggest `REDUCE`.

## Acceptance Criteria

- Generate a research report for a list of tickers.
- Include ticker, summary, bull case, bear case, risks, catalysts,
  recommendation, and confidence.
- Add tests for report models and service behavior.
- Keep the implementation small and ready for an email renderer.
