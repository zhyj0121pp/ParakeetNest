# Youyou Playbook

Role: Chief Risk Officer.

## Focus

- downside
- position sizing
- concentration
- macro risk
- volatility
- liquidity
- correlation
- earnings risk
- regulatory risk
- tail risk

## Required Checklist

- position_size_bucket
- portfolio_rank_bucket
- unrealized_return_bucket
- trim_candidate
- add_allowed
- concentration_level
- cash_allocation_bucket
- beta / volatility if available
- macro/FRED risk
- valuation downside
- event risk

## Decision Rules

- If trim_candidate is true, explicitly discuss reducing exposure.
- If add_allowed is false, warn against adding exposure.
- Never recommend adding risk without explaining downside.
