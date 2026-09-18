# AITA NFL ANYTIME TD SCORER
## Formal Postgame Audit, Closing-Line Validation & Python Pipeline Calibration Specification

**Model Version:** `v0.2.0a1`  
**Slate:** `2026-09-14 MNF`  
**Matchup:** Denver Broncos at Kansas City Chiefs  
**Frozen Run:** `NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W01_NFL-SCORER-2026-W01-20260914T230509Z-MNF_0914.zip`  
**Final:** Kansas City 31, Denver 10  
**Audit Status:** `CALIBRATION REQUIRED BEFORE MODEL PROMOTION`

---

# 1. PURPOSE

This document converts the 2026-09-14 MNF postgame review into a formal calibration specification for the AITA NFL Anytime TD Scorer Python pipeline.

The purpose is **not** to overfit the model to one game or to reward predictions simply because they happened to win.

The purpose is to determine whether the model behaved like a professional sportsbook/quant pricing system:

> **Did high-ranked model edge consistently beat the closing market, price the player correctly, and outperform lower-ranked edge?**

That is the primary casino-quant validation question.

The pipeline should ultimately be judged by four linked outcomes:

1. **Probability calibration** — were model probabilities statistically reliable?
2. **Closing-line validation** — did the best model edges consistently secure better prices than the close?
3. **Rank monotonicity** — did higher-ranked edge outperform lower-ranked edge in CLV and realized results over time?
4. **Role/opportunity integrity** — were probabilities assigned to players with real offensive scoring opportunity?

A single slate is diagnostic rather than statistically conclusive. This game nevertheless exposed several high-priority structural weaknesses.

---

# 2. SOURCE HIERARCHY

## Tier A — Frozen Model State

Primary model source:

`NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W01_NFL-SCORER-2026-W01-20260914T230509Z-MNF_0914.zip`

The frozen handoff remains authoritative for:

- model probabilities;
- model ranks;
- player eligibility;
- role scores;
- matchup classifications;
- conservative probabilities;
- fair prices;
- joint probabilities;
- pregame EV calculations.

No postgame result may be used to retroactively alter the frozen prediction state.

## Tier B — Results / Usage

ESPN game recap and box-score evidence:

- https://www.espn.com/nfl/game/_/gameId/401872931/broncos-chiefs
- https://www.espn.com/nfl/boxscore/_/gameId/401872931

Confirmed unique TD scorers:

- Patrick Mahomes
- Evan Engram
- Rashee Rice
- Kenneth Walker III

Kenneth Walker III scored twice.

## Tier C — Closing Market

Primary closing-market archive:

- https://fieldworklines.com/nfl/2026/week-1
- https://fieldworklines.com/nfl/2026/week-1/qb
- https://fieldworklines.com/nfl/2026/week-1/rb
- https://fieldworklines.com/nfl/2026/week-1/wr
- https://fieldworklines.com/nfl/2026/week-1/te

The strongest saved Fieldwork snapshot is timestamped:

`Sep 14, 2026 5:12 PM PDT / 8:12 PM ET`

Kickoff was approximately:

`5:15 PM PDT / 8:15 PM ET`

This is therefore a high-quality near-kickoff closing proxy.

The saved snapshot displays DraftKings prices and states that four books were reporting.

## Tier D — Supplemental Pregame Prices

Supplemental sources may be used only for context when a saved close is unavailable:

- https://www.sportsgambler.com/betting-tips/nfl/denver-broncos-vs-kansas-city-chiefs-prediction-odds-2026-09-14/
- https://sports.caliente.mx/es_MX/NFL/2026-09-14/Denver-Broncos-vs-Kansas-City-Chiefs

**Do not label an earlier or cross-book quote as exact CLV.**

---

# 3. EXECUTIVE CASINO-QUANT VERDICT

## Question 1 — Did high-ranked edge consistently beat the close?

**NO / NOT DEMONSTRATED.**

Seven players appeared on the model EV+ board.

Only four of those seven have a reliable near-kickoff quote in the strongest saved DraftKings snapshot:

- Cyrus Allen
- Emmett Johnson
- RJ Harvey
- Marvin Mims Jr.

Among those four:

- 2 had a better entry price than the DraftKings close;
- 1 was effectively flat;
- 1 had a worse entry price than the DraftKings close.

The three highest EV-ranked plays:

1. Nikko Remigio
2. Jalen Royals
3. Troy Franklin

do **not** appear in the strongest saved 20-player Fieldwork close snapshot.

Therefore the slate does **not** establish that the highest model edge consistently beat the close.

More importantly, an exact-book comparison is available for only one of the seven EV+ plays:

- Emmett Johnson: entry `+700 DK`, close `+750 DK`

That exact-book move was **against the model position**.

### Verdict

`EDGE_RANK_TO_CLOSE = FAIL / NOT VALIDATED`

---

## Question 2 — Did the model price the scoring market correctly?

**NO.**

All four actual touchdown scorers were materially underpriced by the model relative to the near-kickoff DraftKings market.

| Actual Scorer | Model Rank | Model TD P | Model Fair | DK Close | Close Break-Even | Model Minus Close |
|---|---:|---:|---:|---:|---:|---:|
| Kenneth Walker III | 1 | 31.30% | +219 | -125 | 55.56% | -24.26 pp |
| Rashee Rice | 4 | 21.61% | +363 | +175 | 36.36% | -14.75 pp |
| Patrick Mahomes | 26 | 5.51% | +1715 | +700 | 12.50% | -6.99 pp |
| Evan Engram | 27 | 5.39% | +1754 | +500 | 16.67% | -11.28 pp |

Average model shortfall on the four eventual scorers:

**approximately -14.3 percentage points.**

This does not mean the closing market is literally the "true probability." Sportsbook prices contain margin.

It does mean the model was systematically assigning materially less scoring probability to the players who scored than the closing market was.

The prior 20-player overlap audit produced:

| Metric | AITA Model | Raw Closing Market | Better |
|---|---:|---:|---|
| Brier Score | 0.158 | 0.137 | Market |
| Log Loss | 0.528 | 0.440 | Market |

The sportsbook probabilities above are raw break-even probabilities and include vig, so this is a diagnostic comparison rather than a pure vig-free benchmark.

### Verdict

`PROBABILITY_PRICING_VS_CLOSE = FAIL`

---

## Question 3 — Did high-ranked edge outperform lower-ranked edge?

**NO.**

The seven EV+ players finished:

`0 wins / 7 losses`

Equal-stake performance:

- Risked: `7.00u`
- Returned: `0.00u`
- P&L: `-7.00u`
- ROI: `-100%`

Top three EV-ranked plays:

- Nikko Remigio
- Jalen Royals
- Troy Franklin

Result:

`0-3 / -100% ROI`

Lower four EV-ranked plays:

- Cyrus Allen
- Emmett Johnson
- RJ Harvey
- Marvin Mims Jr.

Result:

`0-4 / -100% ROI`

Therefore there was no realized rank separation.

Outcome alone is noisy on one slate, so CLV should carry more weight than win/loss. But the available close data also fails to show clean rank monotonicity.

### Verdict

`EDGE_RANK_MONOTONICITY = FAIL / NO SIGNAL`

---

# 4. ENTRY-TO-CLOSE AUDIT OF THE EV+ BOARD

For American odds, implied probability is:

For positive odds `+a`:

`p = 100 / (a + 100)`

For negative odds `-a`:

`p = a / (a + 100)`

For this audit:

`CLV_pp = close_implied_probability - entry_implied_probability`

A positive number means the entry price was better than the closing comparison price.

**Important:** this is only true exact-book CLV when the entry and close are from the same sportsbook.

| EV Rank | Player | Entry | Trusted Near-Close | Comparison Type | Entry BE | Close BE | CLV Proxy | Result |
|---:|---|---:|---:|---|---:|---:|---:|---|
| 1 | Nikko Remigio | +3000 BR | CLOSE_UNAVAILABLE | — | 3.23% | — | — | Loss |
| 2 | Jalen Royals | +1500 FD | CLOSE_UNAVAILABLE | — | 6.25% | — | — | Loss |
| 3 | Troy Franklin | +1300 FD | CLOSE_UNAVAILABLE | — | 7.14% | — | — | Loss |
| 4 | Cyrus Allen | +1100 FD | +900 DK | CROSS_BOOK_CLOSE_PROXY | 8.33% | 10.00% | **+1.67 pp** | Loss |
| 5 | Emmett Johnson | +700 DK | +750 DK | **EXACT_BOOK_CLOSE** | 12.50% | 11.76% | **-0.74 pp** | Loss |
| 6 | RJ Harvey | +360 FD | +360 DK | CROSS_BOOK_CLOSE_PROXY | 21.74% | 21.74% | **0.00 pp** | Loss |
| 7 | Marvin Mims Jr. | +850 BR | +800 DK | CROSS_BOOK_CLOSE_PROXY | 10.53% | 11.11% | **+0.58 pp** | Loss |

Across the four rows with a usable near-close comparison:

- positive proxy CLV: `2/4`
- flat: `1/4`
- negative: `1/4`
- average proxy CLV: approximately `+0.38 percentage points`
- median proxy CLV: approximately `+0.29 percentage points`

**Do not report the +0.38 pp average as true portfolio CLV.**

Three rows are cross-book comparisons and the three highest EV-ranked players lack a trusted saved close.

The only exact-book EV+ close comparison was negative.

---

# 5. HIGH-RANKED EDGE VS LOWER-RANKED EDGE

The model's EV ranking did not show a clean monotonic relationship with closing-price performance.

Among the four rows with a near-close comparison:

| Relative Edge Rank | Player | Conservative EV | CLV Proxy |
|---:|---|---:|---:|
| 1 | Cyrus Allen | +18.93% | +1.67 pp |
| 2 | Emmett Johnson | +12.54% | -0.74 pp |
| 3 | RJ Harvey | +9.44% | 0.00 pp |
| 4 | Marvin Mims Jr. | +6.30% | +0.58 pp |

The sequence is not monotonic.

A valid production model should eventually demonstrate:

`higher EV rank -> better average exact-book CLV -> better long-run ROI`

That relationship was **not demonstrated on this slate**.

---

# 6. ROLE / OPPORTUNITY AUDIT

The largest failure was not the EV formula.

The largest failure was the probability input feeding the EV formula.

| Player | Model Raw P | Cons. P | Pregame Role Signal | Actual Offensive Usage | Audit |
|---|---:|---:|---|---|---|
| RJ Harvey | 24.78% | 23.79% | RB2 / role 87 | 3 rushes, 4 catches | Defensible opportunity, probability too aggressive |
| Troy Franklin | 12.37% | 10.77% | role 87 | 1 rush, 1 target, 0 catches | **ROLE FAILURE** |
| Nikko Remigio | 12.31% | 8.96% | role 94 | no offensive touch/target; return usage | **SEVERE ROLE FAILURE** |
| Emmett Johnson | 15.04% | 14.07% | RB2 / role 44 | 8 rushes, 2 catches | Legitimate opportunity |
| Jalen Royals | 14.26% | 9.87% | role 55 | no offensive box-score usage | **ROLE FAILURE** |
| Cyrus Allen | 11.00% | 9.91% | role 44 | 1 target, 0 catches | Low-opportunity miss |
| Marvin Mims Jr. | 10.89% | 11.19% | role 94 | no offensive catch/rush; return usage | **ROLE FAILURE** |

Five of the seven EV+ rows had little or no meaningful offensive opportunity.

This is not adequately explained by random touchdown variance.

The pipeline confused:

`active roster status / nominal depth`

with:

`real offensive scoring opportunity`

Those must become separate concepts.

---

# 7. GAME-SCRIPT AUDIT

Frozen game context:

- Kansas City projected points: `24.32`
- Denver projected points: `22.56`
- Projected total: `46.88`
- Projected KC margin: `+1.76`

Actual:

- Kansas City: `31`
- Denver: `10`
- Actual total: `41`
- Actual KC margin: `+21`

The critical miss was Denver.

The model allocated scorer probability under an assumption of roughly 22.6 Denver points.

Denver scored only 10 points and produced one offensive touchdown.

This inflated the available scoring mass for:

- RJ Harvey
- J.K. Dobbins
- Courtland Sutton
- Troy Franklin
- other Denver scorers

The team-scoring layer and player-allocation layer must be jointly audited.

---

# 8. BOARD-BY-BOARD FORMAL AUDIT AND REQUIRED PIPELINE CHANGES

## BOARD 1 — HANDOFF / ROSTER AUDIT

### Grade

`A- technical integrity / C role integrity`

### What worked

- roster identities were largely valid;
- stale/non-roster identities were quarantined;
- model version and slate were correctly frozen;
- Dataset-B contamination was prevented.

### What failed

Roster validation was treated too closely as role validation.

A player may be:

- active;
- on the correct team;
- at a valid position;
- high enough on a nominal depth chart;

and still have almost no offensive scoring opportunity.

### Required Python changes

Add distinct fields:

```text
roster_valid
active_status_valid
offensive_role_valid
special_teams_primary
projected_snap_share
projected_route_share
projected_target_share
projected_carry_share
projected_red_zone_opportunity
offensive_opportunity_score
role_source_count
role_source_agreement
role_uncertainty
```

### New gate

```text
ROSTER_VALID != OFFENSIVE_ROLE_VALID
```

A player cannot reach a primary scorer board solely because roster validation passes.

### Acceptance test

A return specialist with no meaningful offensive usage projection must never receive `CORE`, `STRONG VALUE`, or `SHARP` status.

---

## BOARD 2 — WHOLE-SLATE MOST PROBABLE SCORERS

### Grade

`C-`

### What worked

- Walker ranked #1 and scored twice;
- Rice ranked #4 and scored;
- aggregate unique-scorer expectation was approximately 3.65 versus four actual unique scorers.

### What failed

The probability mass was distributed to the wrong players.

Mahomes and Engram were buried at approximately ranks 26 and 27.

### Required Python changes

Separate:

```text
team_scoring_mass
player_opportunity_weight
player_td_conversion_weight
position_td_share
role_uncertainty_haircut
```

Recommended architecture:

```text
TEAM TD ENVIRONMENT
    ->
PLAYER OPPORTUNITY SHARE
    ->
POSITION / ROLE TD CONVERSION
    ->
PLAYER TD PROBABILITY
```

Do not allow weak-role players to obtain high scorer probability simply because residual team TD mass must be allocated somewhere.

### New diagnostic

```text
probability_mass_by_role_tier
```

The pipeline should print how much total scoring probability is assigned to:

- proven primary offensive roles;
- secondary roles;
- uncertain roles;
- special-teams / fringe roles.

A large tail allocation should trigger an audit warning.

---

## BOARD 3 — QB SCORER BOARD

### Grade

`D`

### Failure

Bo Nix was the top QB scorer at 8.82%.

Mahomes was approximately 5.51% and outside the primary QB board.

Mahomes scored on a 15-yard scramble.

The QB model was too centered on goal-line/sneak competition.

### Required Python changes

Decompose QB rushing-TD probability:

```text
p_qb_td =
    p_goal_line_sneak_td
  + p_designed_red_zone_rush_td
  + p_scramble_red_zone_td
  + p_open_field_scramble_td
  - overlap_adjustment
```

Add features:

```text
scramble_rate
scramble_yards_per_dropback
red_zone_scrambles
inside_20_designed_rush_share
inside_10_designed_rush_share
inside_5_sneak_share
pressure_escape_rate
historical_qb_rush_td_rate
team_pass_protection_pressure_expectation
```

### Acceptance test

Mobile QBs with meaningful scramble scoring paths cannot be evaluated only through inside-the-5 rushing usage.

---

## BOARD 4 — RB SCORER BOARD

### Grade

`B-`

### What worked

Walker was the #1 RB scorer and #1 overall scorer.

### What failed

Walker model probability:

`31.30%`

DraftKings near-close break-even:

`55.56%`

The model substantially understated the market's belief in Walker.

Denver RB probability was too aggressive relative to the team's actual scoring environment.

### Required Python changes

Add:

```text
projected_carry_share
projected_target_share
projected_goal_line_share
projected_inside_10_share
projected_inside_5_share
two_minute_role
third_down_role
team_red_zone_trip_distribution
rb_committee_entropy
```

For RB2s, apply uncertainty to scorer probability when role splitting is unresolved.

Do not use the same certainty model for:

- lead RB;
- committee RB;
- pass-catching RB;
- goal-line specialist.

---

## BOARD 5 — WR SCORER BOARD

### Grade

`C+`

### What worked

Rice was the model's #1 WR and scored.

### What failed

Royals, Remigio, Cyrus, Franklin and Mims received too much scoring probability relative to actual offensive opportunity.

### Required Python changes

WR scorer eligibility must use:

```text
projected_routes
route_participation
projected_targets
target_share
red_zone_target_share
end_zone_target_share
air_yard_share
first_read_share
slot_outside_alignment_if_reliable
offensive_snap_share
special_teams_share
```

### Hard rule

If:

```text
special_teams_primary == TRUE
```

and projected offensive role is below the validated threshold:

```text
PRIMARY_TD_BOARD = FALSE
EV_ACTIONABLE = FALSE
```

### Market-role corroboration

If no reliable internal route/target projection exists, use sportsbook offensive usage markets only as corroboration:

- receiving yards market present?
- receptions market present?
- multiple books posting?
- line size consistent with meaningful role?

Market presence must not replace internal modeling, but absence should raise uncertainty.

---

## BOARD 6 — TE SCORER BOARD

### Grade

`D+`

### Failure

Engram scored but was assigned only approximately 5.39%.

Near-close DraftKings price:

`+500 / 16.67% break-even`

Engram also led Denver with four catches for 43 yards.

### Required Python changes

Increase TE weighting on:

```text
route_share
target_share
red_zone_target_share
team_TE_target_share
TE1_depth_status
projected_receptions
projected_receiving_yards
```

### Sanity test

A TE1 with a legitimate receiving line and meaningful projected routes should not automatically rank below fringe WRs lacking offensive-volume evidence.

---

## BOARD 7 — MOST PROBABLE SCORERS BY MATCHUP

### Grade

`C-`

### Failure

The top matchup board captured Walker and Rice but omitted Mahomes and Engram.

### Required changes

Print two parallel ranks:

```text
RAW_MODEL_RANK
ROLE_ADJUSTED_RANK
```

Then print:

```text
ROLE_RANK_DELTA
```

Large rank increases driven by uncertain roles should trigger:

`ROLE_RANK_INSTABILITY`

---

## BOARD 8 — DEFENSIVE TD VULNERABILITY / CONTEXT

### Grade

`D+`

### Important caution

One game cannot prove a defensive matchup model is structurally wrong.

The problem is how strongly matchup modifiers were allowed to interact with weak role estimates.

### Required changes

Every defensive split must contain:

```text
sample_size
effective_sample_size
shrinkage_weight
league_baseline
opponent_adjustment
confidence_interval
regime_window
```

Use matchup as a modifier, not a substitute for opportunity.

Recommended structure:

```text
base_player_td_probability
    x role/opportunity adjustment
    x team scoring environment
    x defensive matchup modifier
```

Cap matchup modifiers when sample reliability is weak.

---

## BOARD 9 — CURRENT STRAIGHT-BET EV+

### Grade

`F`

### Failure

The EV formula was mathematically correct.

The probabilities entering the formula were not sufficiently role-safe.

This created enormous false-looking edge:

- Remigio +177.87%
- Royals +57.98%
- Franklin +50.76%

### Required new columns

```text
model_prob_raw
model_prob_conservative
market_implied_entry
probability_gap_pp
role_opportunity_score
role_uncertainty
market_role_corroboration
market_disagreement_flag
extreme_ev_flag
edge_source
price_source
price_timestamp
price_freshness_seconds
```

### New extreme-edge quarantine

Any unusually large EV must be audited before promotion.

Provisional rule:

```text
IF conservative_ev >= 40%
AND probability_gap_pp >= 5
THEN EXTREME_EDGE_AUDIT = TRUE
```

The bet should not automatically be rejected.

It should be quarantined until:

- role is independently validated;
- offensive opportunity is verified;
- player identity is clean;
- market definition is exact;
- price is fresh.

### Critical principle

`HUGE_EV` is a reason for **more scrutiny**, not less.

---

## BOARD 10 — SHARP RISK-ADJUSTED STRAIGHT PLAYS

### Grade

`F`

### Result

- RJ Harvey: loss
- Troy Franklin: loss
- Nikko Remigio: loss

### Audit

Harvey was a defensible bet that lost.

Franklin and Remigio were process failures because the final gate did not sufficiently validate offensive opportunity.

### New qualification order

A straight bet cannot enter the Sharp Board until it passes:

```text
1. Identity Gate
2. Active Roster Gate
3. Offensive Role Gate
4. Opportunity Gate
5. Team Scoring Environment Gate
6. Probability Calibration Gate
7. Market Definition Gate
8. Price Freshness Gate
9. Conservative EV Gate
10. Market-Disagreement Audit
```

Only after all gates pass should the player be ranked by EV.

### New statuses

```text
A_SHARP_CORE
B_STRONG_VALUE
C_PLAYABLE
WATCH_PRICE
WATCH_ROLE
WATCH_CALIBRATION
QUARANTINE_EXTREME_EDGE
PASS
```

---

## BOARD 11 — TWO-LEG PARLAYS

### Grade

`A risk discipline / outcome not relevant because no trade`

### What worked

- empirical joint probabilities were used;
- independence multiplication was avoided;
- no parlay EV was claimed without an actual quote;
- no price was fabricated.

### Required improvement

A parlay leg must pass the role-validity gate even when the joint-probability engine covers it.

Add:

```text
joint_probability_valid
leg1_role_valid
leg2_role_valid
parlay_quote_exact
parlay_quote_timestamp
parlay_close_quote
parlay_clv
```

Do not allow a weak-role straight player to become acceptable merely because a joint matrix contains that player.

---

## BOARD 12 — THREE-LEG PARLAYS

### Grade

`A risk discipline / outcome not relevant because no trade`

Same improvement as Board 11.

Also track calibration of empirical joint probabilities over rolling history:

```text
pair_brier
pair_logloss
triple_brier
triple_logloss
```

Do not judge joint-probability quality from one parlay outcome.

---

## BOARD 13 — WATCH LIST

### Grade

`B+`

### What worked

Several uncertain positions were prevented from becoming core recommendations.

### What must improve

The underlying probabilities remained too aggressive for multiple thin-role players.

Add explicit reason codes:

```text
WATCH_ROLE_UNCERTAIN
WATCH_PRICE_TOO_SHORT
WATCH_MARKET_DIVERGENCE
WATCH_INJURY
WATCH_DATA_MISSING
WATCH_SAMPLE_SIZE
```

A WATCH player can only be promoted when the specific failed gate is resolved.

---

## BOARD 14 — PASSES / REJECTIONS

### Grade

`Process logic mostly correct / calibration warning severe`

All four actual unique scorers were either passes or outside the actionable EV board:

- Walker
- Rice
- Mahomes
- Engram

This does **not** mean every pass was a bad betting decision.

A touchdown outcome does not retroactively make a negative-EV price good.

However, the fact that all four scorers were also materially underpriced by the model relative to the close is a genuine probability-calibration warning.

### New postgame fields

```text
pass_reason
result_td
close_implied_probability
model_minus_close_pp
false_negative_severity
role_valid
market_rank
model_rank
rank_error
```

This allows the system to distinguish:

- correct pass / player happened to score;
- bad probability / correct pass at price;
- bad probability causing missed value;
- bad role model;
- pure variance.

---

# 9. NEW CASINO-QUANT SCORECARD

The production model should not be promoted based on raw win rate.

The primary rolling scorecard should answer:

> **Did the highest-ranked edge beat the close, price correctly, and outperform lower-ranked edge?**

## CQ-1 — Exact-Book CLV

For every executed or promoted play:

```text
CLV_pp = close_break_even_probability - entry_break_even_probability
```

Positive is better.

Required outputs:

```text
mean_exact_book_clv
median_exact_book_clv
clv_positive_rate
clv_by_ev_decile
clv_by_sharp_grade
clv_by_position
clv_by_role_tier
```

Do not combine exact-book CLV and cross-book proxy CLV.

---

## CQ-2 — Edge-Rank Monotonicity

Bucket model edge into:

```text
TOP_DECILE
DECILE_2
DECILE_3
...
BOTTOM_POSITIVE_EDGE
```

Then measure:

```text
mean_clv
median_clv
roi
hit_rate
brier
logloss
```

A healthy model should show, over a large sample:

```text
higher edge bucket -> better CLV
higher edge bucket -> better long-run ROI
```

If the relationship is flat or inverted, the edge ranking is not trustworthy.

---

## CQ-3 — Probability Calibration

Track reliability buckets:

```text
0-5%
5-10%
10-15%
15-20%
20-30%
30-40%
40-50%
50%+
```

For each bucket:

```text
predicted_probability_mean
actual_td_rate
sample_size
calibration_error
brier_contribution
logloss_contribution
```

A player predicted at 20% should score approximately 20% of the time across a large sample.

---

## CQ-4 — Model vs Closing Market

For every player with a trusted close:

```text
model_probability
vig_adjusted_market_probability_if_available
raw_market_break_even
model_market_gap
result
```

Track:

```text
model_brier
market_brier
model_logloss
market_logloss
```

The long-run objective is not blind imitation of the market.

The objective is to prove the model adds information beyond the market.

---

## CQ-5 — Role Integrity

Track:

```text
primary_board_players_with_meaningful_offensive_role
EV_plus_players_with_meaningful_offensive_role
sharp_board_players_with_meaningful_offensive_role
special_teams_only_false_promotions
zero_opportunity_false_promotions
```

A model producing large EV on players with no offensive opportunity is failing before variance enters the equation.

---

# 10. CLOSING-LINE DATA QUALITY STANDARD

Every actionable straight bet must have a postgame closing-line record.

Required schema:

```text
game_id
slate_id
player_id
player_name
team
market
entry_book
entry_odds
entry_timestamp
close_book
close_odds
close_timestamp
close_source
close_quality
entry_implied_probability
close_implied_probability
clv_pp
```

Allowed `close_quality` values:

```text
EXACT_BOOK_CLOSE
SAME_MARKET_SHARP_BOOK_CLOSE
CROSS_BOOK_CLOSE_PROXY
EARLIER_PREGAME_ONLY
CLOSE_UNAVAILABLE
```

Only `EXACT_BOOK_CLOSE` should be used for the primary CLV KPI.

Do not fabricate or substitute a close.

---

# 11. POSTGAME DATASET-B SCHEMA

Create one row per modeled player.

Recommended output:

`POSTGAME_PLAYER_CALIBRATION.csv`

Columns:

```text
run_id
model_version
slate_date
game_id
player_id
player_name
team
opponent
position

model_rank
position_rank
model_probability_raw
model_probability_conservative
model_fair_odds
probability_tier
sharp_grade

roster_valid
offensive_role_valid
role_certainty_score
offensive_opportunity_score
special_teams_primary
projected_snap_share
projected_route_share
projected_target_share
projected_carry_share
projected_red_zone_share

entry_book
entry_odds
entry_timestamp
entry_implied_probability
conservative_ev

close_book
close_odds
close_timestamp
close_quality
close_implied_probability
clv_pp

actual_td_binary
actual_td_count
actual_carries
actual_targets
actual_receptions
actual_routes_if_available
actual_offensive_snaps_if_available
actual_red_zone_opportunities
actual_special_teams_snaps_if_available

brier_contribution
logloss_contribution
model_market_gap_entry
model_market_gap_close

role_failure_flag
market_disagreement_flag
extreme_ev_flag
calibration_failure_flag
audit_notes
```

---

# 12. REQUIRED NEW POSTGAME OUTPUT FILES

Each slate should generate:

```text
01_POSTGAME_PLAYER_CALIBRATION.csv
02_EXACT_CLOSING_LINES.csv
03_CLV_AUDIT.csv
04_EDGE_RANK_MONOTONICITY.csv
05_ROLE_FAILURES.csv
06_MARKET_DIVERGENCE.csv
07_BOARD_GRADES.json
08_CALIBRATION_SUMMARY.md
09_PAIR_JOINT_CALIBRATION.csv
10_TRIPLE_JOINT_CALIBRATION.csv
```

These files become Dataset B.

Dataset B must never contaminate the frozen pregame Dataset A.

---

# 13. AUTOMATED CALIBRATION FLAGS

Implement the following flags.

## ROLE_NO_OFFENSIVE_EVIDENCE

Trigger when:

```text
roster_valid == TRUE
AND meaningful_offensive_role_evidence == FALSE
```

Action:

```text
WATCH_OR_PASS
```

---

## SPECIAL_TEAMS_ROLE_CONFLICT

Trigger when:

```text
special_teams_primary == TRUE
AND offensive_opportunity_score < validated_threshold
```

Action:

```text
REMOVE_FROM_PRIMARY_SCORER_BOARD
```

---

## EXTREME_EDGE_AUDIT

Provisional trigger:

```text
conservative_ev >= 40%
AND model_market_probability_gap >= 5 percentage points
```

Action:

```text
QUARANTINE_UNTIL_ROLE_AND_PRICE_REVALIDATED
```

---

## MODEL_MARKET_DIVERGENCE

Trigger threshold should ultimately be learned by position and probability range.

Initial diagnostic:

```text
abs(model_probability - market_break_even_probability) >= 5 percentage points
```

Do not automatically force the model toward the market.

Use the flag to require deeper validation.

---

## CLOSE_MISSING

Trigger:

```text
actionable_bet == TRUE
AND exact_book_close_missing == TRUE
```

Action:

```text
CLV_STATUS = UNRESOLVED
```

The pipeline must never silently convert a proxy into exact CLV.

---

# 14. MODEL CALIBRATION ROADMAP

## Phase 1 — Fix Role State Before Probability Math

Priority:

1. split roster validity from offensive-role validity;
2. identify special-teams-primary players;
3. ingest projected snaps/routes/targets/carries;
4. create opportunity uncertainty;
5. block weak-role players from Sharp Board promotion.

This is the highest-priority fix.

---

## Phase 2 — Reallocate Team Scoring Mass

Preserve the useful aggregate team/scorer environment.

Rebuild player allocation using:

```text
team scoring expectation
x offensive opportunity share
x red-zone opportunity
x position conversion
x player finishing/conversion
x matchup modifier
```

Avoid dumping residual scoring probability into low-role depth players.

---

## Phase 3 — Rebuild Position Submodels

### QB

Add scramble and open-field rushing TD paths.

### RB

Model committee share and goal-line share separately.

### WR

Require route/target evidence.

### TE

Give TE1 route/target/red-zone role sufficient weight.

---

## Phase 4 — Add Market-Disagreement Diagnostics

The raw model probability must remain independently frozen.

Do not change a raw probability merely because the market disagrees.

Instead add:

```text
market_disagreement_flag
market_gap_pp
market_rank
model_rank
rank_disagreement
```

This preserves model independence while protecting the trading layer from unvalidated extreme disagreement.

---

## Phase 5 — Exact Closing-Line Capture

For every actionable row:

1. capture entry price;
2. store sportsbook and timestamp;
3. capture exact same-book closing price;
4. store close timestamp;
5. calculate exact-book CLV;
6. mark unavailable explicitly.

This is mandatory for real quant validation.

---

## Phase 6 — Walk-Forward Calibration

Do not tune solely to the 9/14 outcome.

Run calibration across historical and future slates using time-ordered walk-forward testing.

Primary metrics:

```text
Brier Score
Log Loss
Reliability Error
Exact-Book CLV
CLV Beat Rate
ROI
Edge-Rank Monotonicity
Role-Failure Rate
```

---

# 15. MODEL PROMOTION CRITERIA

Do not scale the model because of one good slate.

Do not kill the model because of one bad slate.

Promote only when rolling evidence demonstrates:

## Probability

- calibration curves are stable;
- Brier and log loss improve versus the current production baseline;
- extreme probability buckets are not systematically overconfident.

## Close

- mean exact-book CLV is positive with meaningful sample size;
- the confidence interval around mean CLV is favorable;
- top-ranked edge produces better CLV than lower-ranked edge.

## Ranking

- top EV buckets produce stronger CLV than lower EV buckets;
- realized ROI improves with model-edge rank over a large sample;
- ranking monotonicity survives multiple slates and regimes.

## Role

- near-zero false promotions of special-teams-only players;
- weak-role players rarely appear on A/B Sharp Boards;
- predicted opportunity aligns with actual snaps/routes/touches over time.

## Data

- actionable plays have exact entry records;
- actionable plays have exact closes whenever recoverable;
- missing closes are explicitly reported.

---

# 16. PROVISIONAL PRODUCTION GATES

Until sufficient calibration data exists, use conservative gating.

A player cannot become an A/B straight play if any of the following are true:

```text
roster_valid == FALSE
offensive_role_valid == FALSE
special_teams_primary == TRUE AND offensive_role_unconfirmed
price_unverified == TRUE
market_definition_unresolved == TRUE
role_source_count < required_minimum
opportunity_score below validated floor
extreme_edge_audit unresolved
```

A player may remain:

```text
WATCH
SATELLITE
PASS
```

but not `SHARP / CORE`.

---

# 17. SLATE-SPECIFIC BOARD GRADES

| Board | Grade | Core Finding | Required Action |
|---|---:|---|---|
| 1 Handoff / Roster | A- technical / C role | Identity good, role validation weak | Split roster vs offensive role |
| 2 Whole Slate | C- | Aggregate scorer count reasonable, allocation poor | Rebuild player probability allocation |
| 3 QB | D | Mahomes rushing path understated | Add scramble/open-field TD model |
| 4 RB | B- | Walker identified, magnitude wrong | Improve workload/goal-line share |
| 5 WR | C+ | Rice right, fringe WR mass too high | Mandatory route/target validation |
| 6 TE | D+ | Engram materially understated | Increase TE1 opportunity weighting |
| 7 Matchup | C- | Two scorers captured, two buried | Print raw vs role-adjusted rank |
| 8 Defense | D+ | Modifier too influential with weak roles | Reliability/shrinkage controls |
| 9 EV+ | F | Correct EV math, bad probability inputs | Extreme-edge quarantine |
| 10 Sharp Plays | F | Harvey defensible; Franklin/Remigio process failures | Hard opportunity gate |
| 11 2-Leg Parlays | A risk process | No fabricated pricing | Add leg role validity |
| 12 3-Leg Parlays | A risk process | No fabricated pricing | Joint calibration tracking |
| 13 Watch | B+ | Some weak plays held back | Add explicit watch reason codes |
| 14 Passes | Calibration warning | All actual scorers outside action board | Track false-negative severity |

---

# 18. WHAT SHOULD NOT CHANGE

Do **not** discard the following architecture:

- frozen pregame Dataset A;
- separate postgame Dataset B;
- model probability separated from sportsbook price;
- conservative EV math;
- roster quarantine;
- empirical pair/triple probabilities;
- refusal to multiply correlated scorer probabilities blindly;
- refusal to fabricate parlay prices;
- PASS rather than forced action;
- explicit buy-to/no-bet pricing.

Those controls are correct.

The failure was primarily upstream:

`ROLE / OPPORTUNITY -> PLAYER PROBABILITY -> EV`

not:

`EV FORMULA`

---

# 19. FINAL 9/14 CALIBRATION JUDGMENT

## Probability Model

`REQUIRES RECALIBRATION`

## Role Engine

`FAIL — PRIORITY 1`

## Team Scoring Environment

`REQUIRES RECALIBRATION`

## Player Probability Allocation

`FAIL`

## EV Formula

`PASS`

## EV Input Quality

`FAIL`

## Sharp Board Gating

`FAIL`

## Closing-Line Validation

`INCOMPLETE / FAILS EVIDENCE STANDARD`

## Exact-Book CLV Coverage

`INSUFFICIENT`

## Edge-Rank Monotonicity

`NOT DEMONSTRATED`

## Parlay Price Discipline

`PASS`

## Dataset Integrity

`PASS`

---

# 20. FINAL CASINO-QUANT ANSWER

### Did the high-ranked model edge consistently beat the close?

**No.**

The evidence is incomplete for the three highest EV-ranked players, and the four usable close comparisons were mixed rather than monotonic.

The only exact-book EV+ comparison moved against the model position.

### Did the model price the actual scoring market correctly?

**No.**

All four eventual touchdown scorers were assigned materially lower probabilities than their near-kickoff DraftKings break-even probabilities.

The closing market also produced better Brier and log-loss scores in the 20-player overlap diagnostic.

### Did higher-ranked edge outperform lower-ranked edge?

**No.**

The EV+ board went 0-7.

The top three went 0-3.

The lower four went 0-4.

There was no realized rank separation, and available CLV did not show clean edge-rank monotonicity.

### What is the core failure?

**The model approximately understood how much scoring probability existed, but distributed too much of that probability to the wrong players.**

The highest-priority fix is:

> **Build a real offensive-opportunity engine and make it a hard prerequisite for probability and EV promotion.**

### What is the production standard going forward?

The model earns promotion only when, across a meaningful rolling sample:

> **higher-ranked model edge consistently beats the exact-book close, remains probabilistically calibrated, and produces stronger long-run results than lower-ranked edge.**

That—not one-night hit rate—is the real casino-quant score.

---

# 21. REQUIRED NEXT IMPLEMENTATION ORDER

```text
1. REBUILD ROLE / OPPORTUNITY ENGINE
2. ADD SPECIAL-TEAMS-ONLY FILTER
3. REBUILD PLAYER TD-MASS ALLOCATION
4. ADD QB SCRAMBLE TD COMPONENT
5. IMPROVE TE1 OPPORTUNITY WEIGHTING
6. ADD MARKET-DIVERGENCE QUARANTINE
7. ADD EXACT-BOOK CLOSE CAPTURE
8. BUILD DATASET-B PLAYER CALIBRATION LEDGER
9. BUILD EDGE-RANK -> CLV MONOTONICITY REPORT
10. WALK-FORWARD BACKTEST BEFORE PROMOTION
```

**Do not optimize to the 9/14 winners. Optimize the system so that future high-ranked edge repeatedly proves itself against the close.**
