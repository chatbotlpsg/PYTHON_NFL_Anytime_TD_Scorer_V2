# AITA NFL 2026 — Python Pipeline vs. Claude NFL Trading Agent Boundary Specification

**Status:** Architecture lock / coding-agent context  
**Project:** AITA NFL Model 2026  
**Purpose:** Define the non-negotiable separation between the NFL Python pricing/modeling pipeline and the separate Claude NFL Trading Agent.  
**Critical clarification:** This specification is for the **NFL model**. It mirrors the separation previously established in other AITA sports projects, but the downstream agent is a **specific NFL Trading Agent**, not an NCAAF agent.

---

# 1. Executive Architecture Lock

The NFL system is deliberately split into two independent operational layers:

```text
NFL PYTHON PIPELINE
        │
        ├── Source / normalize football data
        ├── Build team states
        ├── Build player / role states
        ├── Build matchup features
        ├── Run game-state simulation
        ├── Run player-opportunity simulation
        ├── Run player-production simulation
        ├── Run Monte Carlo
        ├── Price approved NFL markets
        ├── Ingest CURRENT sportsbook prices
        ├── Calculate fair prices
        ├── Calculate MC / calibrated / blended / conservative probabilities
        ├── Calculate MC / calibrated / blended / conservative EV%
        ├── Calculate uncertainty / confidence
        ├── Calculate cross-market correlations
        ├── Identify best expression of thesis
        ├── Produce all model boards
        ├── Preserve model-reference market snapshot
        │
        ▼
NFL TRADING-AGENT HANDOFF ZIP
        │
        ▼
════════════════════════════════════════════════════
            NFL PYTHON PIPELINE ENDS HERE
════════════════════════════════════════════════════
        │
        ▼
SPECIFIC CLAUDE NFL TRADING AGENT
        │
        ├── Verify current actionable prices
        ├── Search available books / best price
        ├── Decide whether model edge still survives
        ├── Record actual entry
        ├── Monitor meaningful price movement
        ├── Capture closing line
        ├── Capture game / player result
        ├── Grade play
        ├── Calculate CLV
        ├── Produce trading audit
        ├── Build Dataset B — Trading History
        │
        ▼
COMPLETED TRADING-AUDIT / CALIBRATION DATA
        │
        ▼
MAY BE FED BACK INTO A FUTURE PYTHON CALIBRATION CYCLE
```

The boundary is strict.

Python is the **quantitative oddsmaker / pricing engine**.

Claude is the **NFL trader / execution and market-audit layer**.

---

# 2. The Core Rule

The coding agent must understand this sentence literally:

> **Python stops when the immutable NFL Trading-Agent Handoff ZIP is created.**

Nothing after that belongs to the Python pipeline unless a later, separate calibration run explicitly imports completed trading-agent audit data.

Python must **not** continuously monitor the market after handoff.

Python must **not** own the closing line.

Python must **not** own the actual entry.

Python must **not** calculate the final trading CLV from post-handoff market history.

Python must **not** grade executed plays.

Python must **not** replace the Claude NFL Trading Agent.

---

# 3. Dataset A vs. Dataset B

There are two different price/history datasets in the architecture.

They serve different purposes and have different owners.

---

# 4. Dataset A — Python Model Pricing Snapshot

## Owner

```text
NFL PYTHON PIPELINE
```

## Purpose

Dataset A answers:

> **What sportsbook price did the model compare itself against when it calculated its probability, fair price, and EV?**

Python still needs sportsbook prices because EV cannot be calculated without a market price.

Therefore Python must preserve the exact market snapshot it used.

Example:

```text
MODEL RUN:
2026-W01-RUN03

PLAYER:
Example WR

MARKET:
Over 5.5 receptions

BOOK:
DraftKings

MODEL REFERENCE ODDS:
-115

MODEL PRICE TIMESTAMP:
2026-09-XX 11:02 CT

MODEL:
p_raw          = 61.7%
p_calibrated   = 60.5%
p_blended      = 60.0%
p_conservative = 59.4%

CONSERVATIVE FAIR PRICE:
-146

CONSERVATIVE EV AT REFERENCE PRICE:
+10.5%
```

This snapshot belongs in the model run and handoff ZIP.

It exists for:

- reproducibility,
- auditability,
- EV reconstruction,
- model version comparison,
- understanding exactly what the model saw.

---

# 5. Dataset A Is NOT Trading History

This distinction is mandatory.

Dataset A is:

```text
MODEL_REFERENCE_MARKET_SNAPSHOT
```

It is **not**:

```text
actual entry history
closing-line history
CLV history
post-handoff line movement
execution history
trading result history
```

The coding agent must not expand Dataset A into a post-handoff trading database.

---

# 6. Minimum Dataset A Schema

The Python snapshot should contain at least:

```text
run_id
model_version
run_timestamp_utc
aita_event_id
aita_player_id
player_name
team
opponent
market_key
market_display
side
line
book
american_odds
decimal_odds
market_snapshot_timestamp
source
source_response_id_or_hash

p_raw
p_calibrated
p_blended
p_conservative

fair_odds_raw
fair_odds_calibrated
fair_odds_blended
fair_odds_conservative

ev_raw_pct
ev_calibrated_pct
ev_blended_pct
ev_conservative_pct

role_certainty_score
model_agreement_score
edge_type
thesis_id
model_status
```

Optional but recommended:

```text
buy_to_price
hard_stop_price
minimum_required_ev_pct
```

---

# 7. Dataset B — Trading History

## Owner

```text
SPECIFIC CLAUDE NFL TRADING AGENT
```

## Purpose

Dataset B answers:

> **What actually happened to this market after the Python model handed the candidate to the NFL Trading Agent?**

This entire lifecycle exists **outside the Python pipeline**.

---

# 8. Dataset B Lifecycle

For a Python candidate:

```text
Python reference:
O5.5 -115 @ 11:02 CT
```

the Claude NFL Trading Agent may later record:

```text
Current verification:
O5.5 -120 @ 11:27 CT

Best available book:
BetRivers

Actual entry:
O5.5 -118 @ 11:31 CT

Later market:
O5.5 -130

Closing line:
O5.5 -135

Final player result:
7 receptions

Grade:
WIN

CLV:
POSITIVE

Trading audit:
PASS / FAIL against expected pricing discipline
```

That complete record is Dataset B.

---

# 9. Dataset B Fields

The exact Claude-side implementation is outside Python, but conceptually Dataset B should contain:

```text
handoff_run_id
candidate_id
aita_event_id
aita_player_id
market_key
side
line

python_reference_book
python_reference_price
python_reference_timestamp
python_p_conservative
python_fair_price
python_conservative_ev_pct
python_buy_to_price
python_hard_stop_price

trading_agent_verification_timestamp
verified_market_price
verified_book

actual_entry_flag
actual_entry_timestamp
actual_entry_book
actual_entry_line
actual_entry_odds

market_movement_notes
later_market_price_if_captured

close_capture_timestamp
closing_book_or_consensus_source
closing_line
closing_odds
closing_price_provenance

game_result
player_result
bet_grade

clv_price_delta
clv_probability_delta
clv_positive_flag

trading_agent_decision
trading_agent_reason
audit_status
audit_notes
```

Again:

> **Python does not create or maintain this trading-history lifecycle.**

---

# 10. The NFL Trading Agent Owns Everything After Handoff

Once:

```text
NFL_TRADING_AGENT_HANDOFF_2026-W01.zip
```

is generated, the Python process is complete.

The Claude NFL Trading Agent then owns:

```text
CURRENT PRICE VERIFICATION
        ↓
BEST-BOOK SEARCH
        ↓
MARKET MOVEMENT REVIEW
        ↓
ENTRY DECISION
        ↓
ACTUAL ENTRY CAPTURE
        ↓
POST-ENTRY / PRE-CLOSE MARKET OBSERVATION
        ↓
CLOSING-LINE CAPTURE
        ↓
GAME / PLAYER RESULT
        ↓
PLAY GRADING
        ↓
CLV CALCULATION
        ↓
TRADING AUDIT
        ↓
DATASET B
```

---

# 11. The Trading Agent Must Verify the Market Again

A Python reference price is not an execution command.

Example:

```text
Python says:
WR receptions Over 5.5
Reference -115
Fair -146
Conservative EV +10.5%
```

Claude must ask:

> Is the same proposition still available at a price that preserves acceptable EV?

Possible outcomes:

```text
-115 still available
→ likely actionable

-120 available
→ recalculate trade economics against Python fair price

-130 available
→ edge may be compressed

-150 available
→ likely no longer actionable

line moved from 5.5 to 6.5
→ proposition materially changed; do not treat as same bet
```

Claude is the price-sensitive execution layer.

---

# 12. BUY-TO and HARD-STOP Price Fields

Because the trading agent operates after the Python snapshot, Python should provide a price-tolerance framework.

Each candidate should ideally include:

```text
MODEL REFERENCE PRICE
MODEL FAIR PRICE
RECOMMENDED BUY-TO PRICE
HARD-STOP / DO-NOT-PLAY-WORSE-THAN PRICE
```

Example:

```text
Reference:
Over 5.5 -115

Conservative fair:
-146

Recommended buy-to:
-125

Hard stop:
-130
```

These are model-generated execution boundaries.

The exact formulas must eventually be calibrated from:

- model confidence,
- market type,
- EV floor,
- uncertainty,
- historical CLV,
- market liquidity.

---

# 13. Why BUY-TO Is Necessary

Without BUY-TO logic:

```text
Python:
PLAY O5.5 -115
```

becomes useless if Claude receives the ZIP after the price has changed.

With BUY-TO logic:

```text
Python:
Reference -115
Fair -146
Buy to -125
Hard stop -130
```

Claude can immediately determine whether the current quote still satisfies the model's economic requirements.

This preserves the separation between:

```text
MODEL VALUATION
```

and:

```text
TRADE EXECUTION
```

---

# 14. Claude Must Not Rewrite Python Probabilities

This is another non-negotiable boundary.

Suppose Python outputs:

```text
p_conservative = 59.4%
```

Then the market moves:

```text
-115 → -135
```

Claude must **not** change:

```text
59.4% → 63%
```

merely because the market moved.

The correct interpretation is:

```text
same model value
+
worse market price
=
smaller EV
```

The trader reassesses the **price**, not the underlying model probability.

---

# 15. New Football Information Means the Model Is Stale

A different rule applies if the football state itself changes.

Example:

```text
surprise inactive
QB change
weather shock
depth-chart change
starter ruled out
major offensive-line change
```

Then Claude should not invent a new fair probability.

Instead:

```text
MODEL_STATE = STALE
```

and:

```text
ACTION = REQUEST / RUN NEW PYTHON SNAPSHOT
```

The new Python run rebuilds:

- player role states,
- team states,
- game state,
- Monte Carlo,
- fair prices,
- EV.

Then it creates a new handoff snapshot.

---

# 16. Odds API Responsibility Inside Python

The Odds API is used by Python only to obtain sufficient **current market reference prices** to price the slate and generate the handoff.

Approved pattern:

```text
1. Mainline anchor pull
2. Approved opportunity-prop pull
3. Targeted production-prop pull
4. Optional final model-board refresh
5. Build ZIP
6. STOP
```

Python must not use The Odds API for:

```text
continuous repricing after handoff
closing-line polling
Sunday-long monitoring
post-entry market surveillance
result monitoring
CLV collection
trading-history construction
```

Those are trading-agent responsibilities.

---

# 17. Why This Saves Odds API Credits

The separation improves quota efficiency.

Python only spends credits when it needs to answer:

> What price is available right now for purposes of producing the model's EV board?

It does not spend limited Odds API credits trying to recreate a trading terminal throughout the rest of the day.

This is especially important under a constrained free-plan workflow.

The core Python pattern remains:

```text
MODEL FIRST
MARKET SNAPSHOT SECOND
ZIP THIRD
STOP
```

---

# 18. The Handoff ZIP Is the Contract

The ZIP is the formal contract between the quantitative oddsmaker and the trader.

It should contain enough information for Claude to make a price-sensitive final decision without re-running or reverse-engineering Python.

Every actionable candidate should ideally include:

```text
PLAYER
POSITION
TEAM
OPPONENT

MARKET
SIDE
LINE

MODEL REFERENCE BOOK
MODEL REFERENCE PRICE
MODEL PRICE TIMESTAMP

RAW MC PROBABILITY
CALIBRATED PROBABILITY
BLENDED PROBABILITY
CONSERVATIVE PROBABILITY

RAW FAIR PRICE
CALIBRATED FAIR PRICE
BLENDED FAIR PRICE
CONSERVATIVE FAIR PRICE

RAW EV%
CALIBRATED EV%
BLENDED EV%
CONSERVATIVE EV%

RECOMMENDED BUY-TO PRICE
HARD-STOP PRICE

ROLE CERTAINTY
MODEL AGREEMENT
DATA FRESHNESS
UNCERTAINTY TIER

EDGE TYPE
EDGE DECOMPOSITION
THESIS ID

CORRELATED CANDIDATES
BEST EXPRESSION
SECONDARY EXPRESSION
REDUNDANT EXPOSURE

MODEL STATUS
MODEL WARNINGS
```

---

# 19. Example Candidate Handoff

```text
PLAYER:
Example WR

MARKET:
Receptions Over 5.5

MODEL REFERENCE PRICE:
-115

REFERENCE BOOK:
DraftKings

MODEL PRICE TIMESTAMP:
2026-09-XX 11:02 CT

RAW MC:
61.7%

CALIBRATED:
60.5%

BLENDED:
60.0%

CONSERVATIVE:
59.4%

CONSERVATIVE FAIR PRICE:
-146

CONSERVATIVE EV AT REFERENCE PRICE:
+10.5%

RECOMMENDED BUY-TO:
-125

HARD STOP:
-130

EDGE TYPE:
ROLE_EDGE
PASS_VOLUME_EDGE

ROLE CERTAINTY:
91/100

MODEL AGREEMENT:
HIGH

CORRELATED PLAYS:
QB Attempts Over
WR Receiving Yards Over

BEST EXPRESSION:
WR Receptions Over

MODEL STATUS:
ACTIONABLE_AT_REFERENCE_PRICE
```

Claude then answers:

> Is this still actionable at the current price?

That is a trading question.

Python has already answered the valuation question.

---

# 20. Quant / Trader Separation

The architecture deliberately mirrors a professional desk.

## Python = Quantitative Oddsmaker

Python answers:

```text
What should this proposition be worth?
```

It owns:

- football-state estimation,
- role estimation,
- game-state modeling,
- Monte Carlo,
- calibrated probability,
- fair odds,
- EV,
- uncertainty,
- correlations,
- candidate ranking,
- model-reference price.

## Claude NFL Trading Agent = Trader

Claude answers:

```text
Can I still buy this claim cheaply enough right now?
```

It owns:

- price verification,
- best-book search,
- execution decision,
- actual entry,
- price movement,
- closing line,
- grading,
- CLV,
- trading audit.

---

# 21. Trading Agent Can PASS Without Overriding the Model

Claude may reject a Python candidate because:

```text
price moved too far
line changed
liquidity poor
new injury information appeared
market no longer available
correlation exposure too high
better expression exists
execution threshold violated
```

That does **not** mean the Python valuation was wrong.

It means:

```text
TRADE NO LONGER SATISFIES EXECUTION CONDITIONS
```

The trading audit should preserve that distinction.

---

# 22. Three Separate Status Concepts

The system should not collapse these concepts.

## Model status

Example:

```text
ACTIONABLE_AT_REFERENCE_PRICE
LOW_CONFIDENCE
EXTREME_MODEL_MARKET_DISAGREEMENT
STALE_STATE
```

## Trading status

Example:

```text
EXECUTED
PASSED_PRICE
PASSED_CORRELATION
PASSED_NEW_INFORMATION
MARKET_UNAVAILABLE
```

## Result status

Example:

```text
WIN
LOSS
PUSH
VOID
```

These belong to different layers.

---

# 23. Post-Handoff Market Movement

Dataset B may capture:

```text
verified price
actual entry
later price
closing price
```

but there is no requirement that Python continuously observe any of these.

If Claude or another trading-layer process captures them, they belong to Dataset B.

The exact close source should be labeled.

Examples:

```text
OFFICIAL_BOOK_CLOSE
CONSENSUS_CLOSE
CLOSE_PROXY_PUBLIC
CLOSE_PROXY_TRADING_AGENT_CAPTURE
```

Do not label a non-final snapshot as an official close.

---

# 24. CLV Is a Trading-Agent Audit Metric

CLV depends upon:

```text
actual entry
versus
captured closing price
```

Therefore CLV belongs operationally to Dataset B.

Possible representations:

```text
odds CLV
implied-probability CLV
line CLV
```

Example:

```text
Entry:
O5.5 -118

Close:
O5.5 -135

CLV:
positive
```

The final calculation method should be standardized in the trading-agent specification.

---

# 25. Results and Play Grading Belong to Dataset B

The trading agent owns:

```text
final game result
final player stat
bet outcome
win/loss/push/void
units won/lost
actual ROI
```

Python does not need to monitor completed games as part of the original production run.

A later calibration process may import Dataset B after the audit is complete.

---

# 26. The Feedback Loop

Strict separation does **not** mean the two layers never communicate again.

The correct cycle is:

```text
HISTORICAL NFL DATA
        │
        ▼
PYTHON MODEL
        │
        ▼
HANDOFF ZIP
        │
══════════════════════════════
PYTHON PRODUCTION RUN ENDS
══════════════════════════════
        │
        ▼
CLAUDE NFL TRADING AGENT
        │
        ├── ENTRY
        ├── CLOSE
        ├── RESULT
        ├── GRADE
        ├── CLV
        └── AUDIT
        │
        ▼
DATASET B — TRADING HISTORY
        │
        ▼
CALIBRATION DATASET
        │
        ▼
FUTURE PYTHON CALIBRATION / MODEL REVIEW
```

Dataset B can become an input into future model research.

It is not generated by the Python production run.

---

# 27. What Can Feed Back Into Python Later

Completed trading-agent audit data may later be imported for:

```text
EV calibration
EV bucket analysis
CLV analysis
market trust scoring
over/under asymmetry
market-specific thresholds
model version comparison
edge-type validation
role-model validation
best-expression validation
confidence calibration
```

That is a separate **calibration/research workflow**.

It should not blur the production boundary.

---

# 28. Example Calibration Import

A future calibration process may receive:

```text
NFL_TRADING_AUDIT_2026_W01.csv
NFL_TRADING_AUDIT_2026_W02.csv
...
```

and join them against:

```text
run_id
candidate_id
```

from Dataset A.

This gives:

```text
MODEL FORECAST
+
MODEL REFERENCE PRICE
+
ACTUAL ENTRY
+
CLOSE
+
RESULT
```

for research.

This is powerful precisely because Dataset A and Dataset B were kept separate and auditable.

---

# 29. The Join Key Is Critical

Every Python candidate should have an immutable:

```text
candidate_id
```

Example:

```text
NFL-2026-W01-RUN03-EVENT123-PLAYER456-PLAYER_RECEPTIONS-OVER-5.5
```

The Claude trading audit must preserve:

```text
candidate_id
handoff_run_id
```

This allows perfect later reconciliation.

Never rely only on:

```text
player name + market text
```

for joining audit data.

---

# 30. Immutable Handoff

Once Python builds a handoff ZIP:

```text
NFL_TRADING_AGENT_HANDOFF_2026-W01_RUN03.zip
```

its model boards should be immutable.

If football information changes:

```text
RUN04
```

should be created.

Do not silently overwrite RUN03.

Claude must know which run each trading decision came from.

---

# 31. Versioned Handoffs

Recommended naming:

```text
NFL_TRADING_AGENT_HANDOFF_2026-W01_RUN01.zip
NFL_TRADING_AGENT_HANDOFF_2026-W01_RUN02.zip
NFL_TRADING_AGENT_HANDOFF_2026-W01_RUN03.zip
```

Each ZIP should contain:

```text
run_id
model_version
data_timestamp
market_timestamp
config_hash
```

Dataset B must reference the correct run.

---

# 32. Rerun Logic

A new Python run should occur when football-state information materially changes.

Examples:

```text
starting QB changes
major skill-position inactive
major offensive-line inactive
unexpected depth-chart change
weather materially changes
roster transaction changes role
market reveals possible stale model state and new information is confirmed
```

The trading agent can request a rerun.

It cannot manufacture the replacement probability itself.

---

# 33. Market-Only Movement Does Not Require a Rerun

If nothing about football information changed and only the sportsbook price moved:

```text
Python valuation remains the reference valuation.
```

Claude simply recalculates whether the current price is still within:

```text
BUY-TO
HARD STOP
EV FLOOR
```

That is execution logic.

---

# 34. No Continuous Odds Polling Inside Python

The coding agent must not implement:

```text
while game_not_started:
    fetch_odds()
```

or equivalent continuous monitoring.

No cron-like market polling belongs in the production pricing pipeline after ZIP creation.

The Odds API client exists to create the model's reference pricing snapshot.

That is all.

---

# 35. No Closing-Line Module in Python Production

Do not add modules such as:

```text
closing_line_watcher.py
clv_collector.py
post_handoff_monitor.py
entry_tracker.py
trade_grader.py
```

to the core NFL Python production pipeline.

If later research tools need to **import** completed trading audits, place them under a clearly separate calibration/research namespace.

---

# 36. Acceptable Calibration Import Namespace

For example:

```text
src/nfl_model/calibration/import_trading_audit.py
src/nfl_model/calibration/ev_buckets.py
src/nfl_model/calibration/clv_analysis.py
src/nfl_model/calibration/market_trust.py
```

These tools read completed Dataset B.

They do not create Dataset B.

---

# 37. Forbidden Python Responsibilities

The coding agent must explicitly avoid making Python responsible for:

```text
actual bet execution
entry-price capture after handoff
best-book shopping after handoff
continuous odds monitoring
closing-line capture
post-handoff market movement tracking
result monitoring for trading execution
play grading
CLV production
trading audit
Claude-style discretionary trade decisions
```

---

# 38. Required Python Responsibilities

Python must be responsible for:

```text
football-data ingestion
entity resolution
team-state modeling
player-role modeling
matchup modeling
game-state simulation
opportunity simulation
production simulation
Monte Carlo
probability calibration
market anchoring where appropriate
fair odds
current model-reference sportsbook snapshot
EV%
uncertainty
conservative EV%
correlation
edge type
thesis clustering
best-expression analysis
BUY-TO guidance
hard-stop guidance
boards
handoff ZIP
```

---

# 39. Required Claude NFL Trading Agent Responsibilities

Claude must be responsible for:

```text
read handoff ZIP
verify candidate context
verify current price
find best available price
compare current price against BUY-TO / hard stop
decide EXECUTE / PASS
record actual entry
monitor meaningful movement
capture closing line
capture final result
grade wager
calculate CLV
calculate realized ROI
produce trading audit
maintain Dataset B
```

---

# 40. Trading Agent Does Not Become a Second Model

Claude is not supposed to rebuild:

```text
route projections
target projections
carry projections
pass attempts
Monte Carlo
fair probabilities
```

Those remain Python's domain.

Claude interprets the market **against** the model.

This protects model reproducibility.

---

# 41. Example End-to-End Lifecycle

## Python

```text
RUN03

WR Receptions O5.5
Reference: -115
p_cons: 59.4%
Fair: -146
Cons EV: +10.5%
Buy-to: -125
Hard stop: -130

Candidate ID:
NFL-2026-W01-R03-ABC123
```

ZIP produced.

Python stops.

## Claude trading agent

```text
11:27 CT:
DK -122
FD -125
BR -118

Best:
BR -118

Inside buy-to:
YES

Execution:
O5.5 -118

Later:
Market -130

Close:
-135

Result:
7 receptions

Grade:
WIN

CLV:
POSITIVE

Audit:
EXECUTION PASSED
MODEL EDGE CONFIRMED BY CLOSE
```

## Later calibration

Python research process joins:

```text
candidate_id
```

and learns:

```text
forecast
reference
entry
close
result
```

without ever having owned the live trade lifecycle.

---

# 42. Why This Architecture Is Better

It avoids four major failures.

## Failure 1 — Mixing valuation with execution

If Python keeps changing prices and deciding trades after handoff, the model run becomes impossible to audit.

## Failure 2 — Wasting Odds API quota

The production model does not need to spend credits chasing the close.

## Failure 3 — Probability drift

Claude cannot silently change probabilities merely because market sentiment changed.

## Failure 4 — Unclear attribution

If a trade loses, we can determine separately whether the problem was:

```text
model valuation
execution price
market movement
new information
variance
```

That is institutional-grade accountability.

---

# 43. Audit Attribution Framework

Later, every wager can be evaluated across two independent layers.

## Model audit

```text
Was p_conservative calibrated?
Was fair price reasonable?
Was role forecast accurate?
Was opportunity forecast accurate?
Was the candidate correctly ranked?
```

## Trading audit

```text
Was the best available price obtained?
Was the trade taken inside BUY-TO?
Did the trader chase?
Was the closing line captured properly?
Was CLV positive?
Was correlated exposure managed?
```

That is much more useful than one combined “win/loss” metric.

---

# 44. Dataset A / Dataset B Summary

| Property | Dataset A | Dataset B |
|---|---|---|
| Owner | Python | Claude NFL Trading Agent |
| Purpose | Model pricing reference | Actual trading history |
| Market timestamp | Model run | Verification / entry / close |
| Reference price | Yes | Carries forward |
| Actual entry | No | Yes |
| Best-book search | No | Yes |
| Closing line | No | Yes |
| CLV | No | Yes |
| Final result | Not required for production | Yes |
| Grade | No | Yes |
| Used in future calibration | Yes | Yes |
| Created before ZIP | Yes | No |
| Created after ZIP | No | Yes |

---

# 45. Coding-Agent Implementation Rule

The coding agent should treat the ZIP boundary as an architectural interface.

Conceptually:

```python
handoff = build_nfl_trading_agent_handoff(run_state)
write_zip(handoff)

return PipelineComplete
```

There should be no automatic call after this to:

```python
monitor_market()
capture_close()
grade_trade()
calculate_clv()
```

Those functions do not belong to this production package.

---

# 46. Handoff Manifest

The ZIP manifest should explicitly state:

```text
PIPELINE_BOUNDARY:
PYTHON_COMPLETE_AT_ZIP = TRUE

POST_HANDOFF_OWNER:
CLAUDE_NFL_TRADING_AGENT

PYTHON_MODEL_REFERENCE_SNAPSHOT:
INCLUDED

ACTUAL_ENTRY:
NOT_PYTHON_RESPONSIBILITY

CLOSING_LINE_CAPTURE:
NOT_PYTHON_RESPONSIBILITY

CLV:
NOT_PYTHON_RESPONSIBILITY

PLAY_GRADING:
NOT_PYTHON_RESPONSIBILITY

TRADING_AUDIT:
NOT_PYTHON_RESPONSIBILITY
```

This prevents future ambiguity.

---

# 47. README Warning Inside ZIP

The handoff README should contain:

> **This ZIP is a quantitative pricing handoff, not an execution record. The contained sportsbook prices are the reference market snapshots used by the Python model to calculate EV at run time. The separate Claude NFL Trading Agent is responsible for verifying current prices, deciding whether the edge remains actionable, recording actual entry, capturing the close, grading the wager, calculating CLV, and producing the trading audit.**

---

# 48. Final Locked Architecture

```text
NFL DATA
    ↓
NFL PYTHON QUANT / ODDSMAKER
    ↓
MODEL REFERENCE MARKET SNAPSHOT
    ↓
PROBABILITIES
    ↓
FAIR ODDS
    ↓
CONSERVATIVE EV
    ↓
CORRELATION / BEST EXPRESSION
    ↓
BUY-TO / HARD STOP
    ↓
NFL TRADING-AGENT HANDOFF ZIP
    ↓
══════════════════════════════
PYTHON ENDS
══════════════════════════════
    ↓
CLAUDE NFL TRADING AGENT
    ↓
CURRENT MARKET
    ↓
BEST PRICE
    ↓
ENTRY / PASS
    ↓
CLOSE
    ↓
RESULT
    ↓
GRADE
    ↓
CLV
    ↓
TRADING AUDIT
    ↓
DATASET B
    ↓
FUTURE CALIBRATION INPUT
```

---

# 49. Non-Negotiable Final Statement

The AITA NFL model must preserve this division permanently:

> **Python prices the claim. Claude trades the claim.**

More specifically:

> **The NFL Python pipeline owns Dataset A — the immutable model-reference pricing snapshot used to calculate EV. The separate Claude NFL Trading Agent owns Dataset B — actual post-handoff trading history, including price verification, entry, line movement, closing line, result, grading, CLV, and trading audit. Dataset B may later be consumed by Python for calibration, but it must never be generated by the Python production pipeline itself.**

This is the architecture to build.
