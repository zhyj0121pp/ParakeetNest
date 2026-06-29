# Project ParakeetNest

Three Parakeets. One Committee. Better Investment Decisions.

ParakeetNest is an AI investment research platform where Xixi, Dongdong, and
Yoyo debate, remember, and continuously learn. The committee remembers before
it reasons, and every recommendation must include action, confidence, horizon,
evidence, risks, and catalysts.

## Current Status

This repository contains the initial Python skeleton only. External API calls,
brokerage integrations, market data providers, LLM calls, email delivery, and
automatic trading are not implemented.

## Project Layout

- `src/parakeetnest/committee`: committee roles and meeting orchestration.
- `src/parakeetnest/services`: data collection and validation boundaries.
- `src/parakeetnest/analyzers`: portfolio, stock, market, catalyst, risk,
  opportunity, and thesis analyzers.
- `src/parakeetnest/decision`: recommendation and policy engine skeletons.
- `src/parakeetnest/memory`: investment knowledge base and historical memory.
- `src/parakeetnest/database`: SQLite v1 connection, schema, and repository
  scaffolding.
- `src/parakeetnest/reports`: daily, weekly, and monthly report generators.
- `src/parakeetnest/scheduler`: scheduled research workflow placeholders.
- `tests`: basic pytest coverage for the skeleton.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
```
