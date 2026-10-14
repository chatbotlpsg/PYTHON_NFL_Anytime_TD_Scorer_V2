# NFL ANYTIME TD SCORER — FORMAL AUDIT & CALIBRATION REPORT

**League:** NFL
**Market:** `player_anytime_td`
**Slate date:** 2026-09-21 (Week 2, Monday Night Football)
**Game:** New York Giants @ Los Angeles Rams — SoFi Stadium
**Final:** Rams 28, Giants 6
**run_id:** `NFL-SCORER-2026-W02-20260921T232439Z-MNF_0921`
**Model version:** 0.3.0a1 · simulation_count = 500,000
**Dataset:** A = frozen Python handoff (immutable) · B = this audit record
**Report generated:** post-settlement, Dataset B
**File scope:** one league, one slate. Do not merge leagues or slates into this file.

---

## 1. EXECUTIVE VERDICT

| Question | Answer |
|---|---|
| Did the model beat the market on this slate? | **No.** Model Brier 0.0806 vs market Brier 0.0707 on the 14 commonly-priced rows. The market won despite carrying vig. |
| Did high-ranked model edge beat the close? | **NO EVIDENCE OF CLV. Partial DATA GAP.** No true closes captured. Close-proxy evidence shows the market moving *against* the model's top edge and *toward* the model's biggest fade. |
| Did high-ranked edge outperform lower-ranked edge? | **No.** The top three EV-ranked rows went 0-for-3 with **zero combined offensive touches**. There was no monotonic relationship between EV rank and outcome. |
| Was the pricing correct? | **No.** EV rank 1 was computed off an outlier book price roughly 2× longer than market consensus. The "edge" was book disagreement, not model edge. |
| Did the risk layer work? | **Yes.** The sharp board blocked all three EV+ rows at WATCH. The risk room is the only component that scored an A. |
| Net desk result | **No capital deployed. Zero loss. Three losers avoided.** |

**One-line casino-quant score: the model's probability signal was aggregate-calibrated but directionally wrong, its top-ranked edge was an artifact of a stale outlier price, and it lost the head-to-head accuracy test to a vig-inflated market.**

---

## 2. SETTLEMENT RECORD

### 2.1 Actual scorers

| Player (Team Pos) | TDs | Type | Model Rank | Model ATD | Board Status Pregame |
|---|---:|---|---:|---:|---|
| Davante Adams (LA WR) | 2 | Receiving, 31 yd + 11 yd | 3 | 24.3% | PASS — INSUFFICIENT_EV |
| Kyren Williams (LA RB) | 1 | Receiving, 10 yd | 1 | 40.2% | PASS — INSUFFICIENT_EV |
| **Terrance Ferguson (LA TE)** | 1 | Receiving, 5 yd | **UNRANKED** | **NO MODEL DRAWS** | `MARKET_NOT_PRICED` |

All four Rams touchdowns were passing scores from Matthew Stafford (22/31, 327 yds, 4 TD, 1 INT). **The Giants scored zero touchdowns** (two Dominic Zvada field goals). Los Angeles was 3-for-3 in the red zone; New York was 0-for-2.

### 2.2 EV+ board settlement

| EV Rank | Player (Team Pos) | Ref Price | Cons EV% | Result | Offensive Touches |
|---:|---|---:|---:|---|---:|
| 1 | Tyrone Tracy Jr. (NYG RB) | +1600 DK | +102.9% | **LOSS** | **0** |
| 2 | Braxton Berrios (NYG WR) | +3000 BR | +98.5% | **LOSS** | **0** |
| 3 | Odell Beckham Jr. (NYG WR) | +1700 DK/FD | +21.2% | **LOSS** | **0** |

Straight EV record: **0-3**. Combined touches across the three highest-EV rows on the slate: **zero**.

### 2.3 Parlay board settlement (one-player-once card)

| Ticket | Model Joint | Result |
|---|---:|---|
| Kyren Williams (LA RB) + Davante Adams (LA WR) | 9.15% | **WIN** (paper — never quoted) |
| Cam Skattebo (NYG RB) + Jaxson Dart (NYG QB) | 3.37% | LOSS |
| Tyrone Tracy Jr. (NYG RB) + Colby Parkinson (LA TE) | 1.97% | LOSS |
| Blake Corum (LA RB) + Konata Mumpfield (LA WR) + Malik Nabers (NYG WR) | 0.14% | LOSS |
| Devin Singletary (NYG RB) + Najee Harris (NYG RB) + Malachi Fields (NYG WR) | 0.08% | LOSS |

Parlay record: **1-4 paper**, with the win landing on the top-ranked joint row at model fair +992.

---

## 3. CALIBRATION ANALYSIS

### 3.1 Probability bucket calibration (15 active board rows)

| Bucket | n | Mean Model P | Expected Scorers | Actual | Delta |
|---|---:|---:|---:|---:|---:|
| ≥ 35% | 1 | 40.2% | 0.40 | 1 | **+0.60** |
| 20–35% | 2 | 22.6% | 0.45 | 1 | +0.55 |
| 15–20% | 2 | 16.6% | 0.33 | 0 | -0.33 |
| 10–15% | 6 | 12.1% | 0.73 | 0 | **-0.73** |
| < 10% | 4 | 9.0% | 0.36 | 0 | -0.36 |
| **TOTAL** | **15** | — | **2.27** | **2** | **-0.27** |

Aggregate calibration is excellent and misleading. The 10–15% bucket — six players, zero scorers — is where the model manufactured phantom probability mass, and it is exactly the bucket that feeds the EV+ board at longshot prices.

### 3.2 Team-level distribution failure

| Side | Expected Scorers | Actual Distinct Scorers | Error |
|---|---:|---:|---:|
| Los Angeles | 1.01 | 3 (incl. 1 unmodeled) | **-2.0 under** |
| New York | 1.26 | 0 | **+1.26 over** |

| Reconciliation Field | Model Mean | Actual | Error |
|---|---:|---:|---:|
| LA team points | 24.9 | 28 | -3.1 |
| NYG team points | 22.1 | 6 | **+16.1** |
| Game total | 47.0 | 34 | +13.0 |
| Model fair spread | LA -2.85 | LA -22 | **19.2 pts** |
| Market spread | LA -6.5 to -8.5 | LA -22 | 13.5 to 15.5 pts |

The market's game-script read was materially closer than the model's on every dimension. The model's spread error was 19.2 points; the market's was 13.5. The scorer board inherited that error — a near-even game script spread probability across both rosters, which is precisely why six NYG players sat in the 8–15% band and none scored.

### 3.3 Head-to-head accuracy: model vs market (Brier score, lower is better)

Computed across the 14 board rows with a posted market price. Market probability is raw implied from the best available American price, including vig, which *inflates* market probabilities and should penalize the market on non-scorers.

| Scorer | Model Brier | Market Brier | Winner |
|---|---:|---:|---|
| 14 commonly-priced board rows | **0.0806** | **0.0707** | **MARKET** |

The market beat the model by 12.3% relative error **while carrying the overround**. On a devigged basis the gap widens. Single-slate n=14, so this is directional, not conclusive, but it is the correct metric to track weekly and the sign is unambiguous.

---

## 4. THE CLV TEST — DID HIGH-RANKED EDGE BEAT THE CLOSE?

### 4.1 Close capture status

**TRUE CLOSE: NOT CAPTURED. CLV FORMALLY UNCOMPUTABLE FOR THIS SLATE.**

No timestamped pre-kick quote exists in Dataset B for any row. The only prices in evidence are:

1. The frozen Dataset-A market snapshot at `2026-09-21T23:25Z` — approximately 50 minutes before the `2026-09-22T00:15Z` kickoff. This is an **entry reference**, not a close.
2. Public pregame close-proxy prices sourced post-hoc from published odds articles, listed below. These are `CLOSE_PROXY` at best and most are pre-inactive-list, which makes them pre-news prices, not closes.

No price below may be used as a settled close. They are admitted only as **directional market-movement evidence**.

### 4.2 Close-proxy evidence table

| Player (Team Pos) | Early-Week / Pre-News Proxy | Dataset-A Reference (23:25Z) | Movement Direction | Quality |
|---|---|---|---|---|
| Davante Adams (LA WR) | +100 BetMGM · +105 bet365 · +110 BetMGM · +120 · +130 Fanatics | **-115 bet365 / -120 FD** | **STEAMED ~25–35 cents SHORTER** | CLOSE_PROXY |
| Kyren Williams (LA RB) | -175 to -195 BetMGM · -180 | **-165 DK** | Modestly longer at DK | CLOSE_PROXY |
| Tyrone Tracy Jr. (NYG RB) | +750 Fanatics · +850 bet365 | **+1600 DK / +1400 FD / +800 BR** | **DK/FD ~2× consensus — OUTLIER** | CLOSE_PROXY |
| Cam Skattebo (NYG RB) | +115 to +120 | +123 BR | Flat | CLOSE_PROXY |
| Blake Corum (LA RB) | +140 BetMGM · +200 | +210 BR | Drifted longer | CLOSE_PROXY |
| Colby Parkinson (LA TE) | +210 BetMGM | +270 BR | Drifted longer | CLOSE_PROXY |
| Malik Nabers (NYG WR) | +200 | +210 FD | Flat | CLOSE_PROXY |
| Isaiah Likely (NYG TE) | +260 to +290 | +300 DK | Flat to longer | CLOSE_PROXY |
| Tutu Atwell (LA WR) | +900 bet365 | +900 BR | Flat | CLOSE_PROXY |
| Puka Nacua (LA WR) | -105 to +105 BetMGM · +100 bet365 | **PULLED — not posted** | Removed on inactive ruling | CLOSE_PROXY |
| Braxton Berrios (NYG WR) | DATA GAP | +3000 BR | DATA GAP | **UNRECOVERABLE** |
| Odell Beckham Jr. (NYG WR) | DATA GAP | +1700 DK/FD | DATA GAP | **UNRECOVERABLE** |
| Jaxson Dart (NYG QB) | DATA GAP | +290 DK | DATA GAP | **UNRECOVERABLE** |

### 4.3 The casino-quant findings

**FINDING 1 — The market moved hard toward the model's largest fade, and that fade won twice.**

Davante Adams opened the day around +100 to +130 and was bet to -115/-120 by the Dataset-A snapshot once Nacua trended out. That is 25–35 cents of steam into a player the model priced at 24.3% and the board classified as PASS at -31.0% conservative EV. He scored twice for 195 yards. The sharpest observable money on the slate was on the exact row the model wanted to lay off. **This is negative CLV in the purest form: the model's position was on the wrong side of the one confirmed market move.**

**FINDING 2 — EV Rank 1 was not an edge. It was an outlier price.**

Market consensus on Tyrone Tracy Jr. sat at +750 to +850 (roughly 10.5–11.8% implied). The Dataset-A board took DraftKings at +1600 (5.9% implied) and computed +102.9% conservative EV off it. BetRivers, the same snapshot, had him at +800 — in line with consensus and worth only +7.4% conservative EV.

| Tracy Price Source | Implied | Conservative EV% | Reality |
|---|---:|---:|---|
| bet365 / Fanatics consensus | 10.5–11.8% | ≈ 0% to +7% | The honest number |
| BetRivers +800 (in snapshot) | 11.1% | +7.4% | In line with consensus |
| **DraftKings +1600 (EV Rank 1)** | **5.9%** | **+102.9%** | **Outlier, 2× consensus** |

The entire headline edge of the slate came from one book being roughly twice as long as every other book on a player who then recorded **zero offensive touches**. A price that far off consensus on a depth-chart player is a stale or limit-protected line, not an opportunity. The board had no guard against this.

**FINDING 3 — No monotonic relationship between edge rank and outcome.**

| Edge Rank | Conservative EV% | Outcome | Touches |
|---:|---:|---|---:|
| 1 | +102.9% | LOSS | 0 |
| 2 | +98.5% | LOSS | 0 |
| 3 | +21.2% | LOSS | 0 |
| Unranked (PASS, -20.1% EV) | — | **WIN** | 14 |
| Unranked (PASS, -31.0% EV) | — | **WIN ×2** | 8 rec |

The ranking was **inverted**. The two rows with the most negative EV on the board are the two rows that scored. That is the signature of a model whose probability error is correlated with price: it is long where the market is long because the market is right, and it is short where the market is short because the market is right.

**FINDING 4 — The unpriced player scored.**

Terrance Ferguson (LA TE) carried a live market at +230/+250 and `MISSING_SCORER_DRAWS_OR_PRICE` in Dataset A. He finished with 9 targets, 6 receptions, 54 yards and the fourth Rams touchdown — second-most-targeted player in the game. A model that cannot see the second-most-targeted player in a game cannot be trusted to allocate that game's remaining TD probability, which it then redistributed onto Parkinson and Higbee under a BAD_MATCHUP multiplier.

---

## 5. BOARD-BY-BOARD GRADES

| Board | Grade | Evidence | Root Cause |
|---|:---:|---|---|
| Matchup Probability | **B-** | Rank 1 (Kyren Williams, 40.2%) scored. Rank 3 (Adams) scored twice. | Headline call correct; mid-band inflated. |
| Slate Probability | **C** | 2.27 expected vs 2 actual in aggregate, but -2.0 on LA and +1.26 on NYG. | Game-script error (19.2-pt spread miss) spread mass onto the losing roster. |
| Defensive Mismatch | **D** | 1-for-5 on position verdicts. See 5.1. | Volume-allowed logic with no target-share conditioning. |
| Matchup EV+ | **F** | 0-for-3, zero touches. | Outlier price + prior-only role data. |
| Slate EV+ | **F** | Same three rows; no LA rows ever qualified. | EV computed on the longest book price, not consensus. |
| Sharp / Risk Room | **A** | Blocked all three EV+ rows at WATCH on role certainty and prior-only flags. | **This layer worked exactly as designed and saved the week.** |
| Parlay / Joint Probability | **B** | Top-ranked joint pair cashed; negative same-team correlation (-0.62 pp) held. | Joint math sound; leg selection inherited the probability error. |
| Packet Integrity | **C** | Nacua quarantine correct; Ferguson gap correct and costly; identity-join gaps correct. | Availability gate ran before final inactives were ingested. |

### 5.1 Defensive mismatch board — verdict-by-verdict

| Defense × Position | Verdict | Multiplier | Outcome | Correct? |
|---|---|---:|---|:---:|
| NYG D vs RB | TARGET (1.209) | 1.14 | LA rushed 163 yds, **0 rushing TD**; Williams scored receiving | **NO** |
| LA D vs RB | BAD_MATCHUP (0.715) | 0.86 | NYG RBs: 51 yds, 0 TD | **YES** |
| NYG D vs TE | BAD_MATCHUP (0.684) | 0.86 | **LA TE scored on 9 targets** | **NO** |
| LA D vs TE | TARGET (1.199) | 1.14 | Likely 5-33-0; Theo Johnson 0-for-4 | **NO** |
| NYG D vs WR | NEUTRAL (1.100) | 1.10 | **Adams 195 yds, 2 TD vs Tyler Nubin: 7 rec on 10 tgts, 143 yds, 1 TD allowed as nearest defender** | **NO** |

Score: **1 of 5**. Worse than the verdicts being wrong, the multipliers were applied in the wrong direction on three of the four scoring events: the board suppressed LA TE probability (0.86×) before the LA TE scored, and left LA WR at neutral before the LA WR went for 195 and two scores.

---

## 6. PYTHON PIPELINE PATCH SPECIFICATION

Each patch is written against the board it fixes. Patches are additive gates; none alter existing probability math.

### PATCH 1 — Outlier price guard (EV boards) · PRIORITY: CRITICAL

**Defect:** EV is computed off `american_odds` for the single best book without reference to cross-book consensus. This produced a +102.9% phantom edge.

**Spec:**
```
consensus_implied_prob = median(market_raw_implied_prob) across all books for that player
price_outlier_ratio    = consensus_implied_prob / best_price_implied_prob

IF price_outlier_ratio >= 1.60:
    model_status = PRICE_OUTLIER_SUSPECT
    ev_conservative_pct = recompute at consensus_implied_prob
    block promotion to EV+ board; route to WATCH
IF books_quoting < 3:
    model_status = THIN_MARKET_NO_CONSENSUS; cap conservative EV at consensus
```
New required columns: `consensus_implied_prob`, `books_quoting`, `price_outlier_ratio`, `ev_conservative_at_consensus_pct`.
**Backtest on this slate:** Tracy DK +1600 → ratio 1.86 → blocked. Edge drops from +102.9% to roughly +7%. Correct outcome.

### PATCH 2 — Prior-source gate (EV boards) · PRIORITY: CRITICAL

**Defect:** All three EV+ rows ran on `CURRENT_DEPTH_POSITION_PRIOR` with `scorer_games_observed = 0` and `external_consensus_status = MODEL_ONLY_SIGNAL`.

**Spec:**
```
IF scorer_prior_source == 'CURRENT_DEPTH_POSITION_PRIOR'
   AND scorer_games_observed == 0:
       max_promotion_tier = WATCH   # never EV+, never sharp
IF external_consensus_status == 'MODEL_ONLY_SIGNAL'
   AND role_certainty_score < 85:
       max_promotion_tier = WATCH
```
**Backtest:** removes Berrios and OBJ outright, and holds Tracy at WATCH. EV+ board goes from 3 losers to empty. Correct outcome.

### PATCH 3 — Depth-rank decay on historical priors · PRIORITY: HIGH

**Defect:** Tracy carried a 32-game prior from his RB1 season into a game where he took zero offensive snaps, producing 15.4%.

**Spec:**
```
depth_decay = {1: 1.00, 2: 0.70, 3: 0.40, 4+: 0.20}
p_role_adjusted = p_prior * depth_decay[depth_rank]
IF depth_rank >= 3 AND scorer_prior_source == 'PLAYER_HISTORY':
    flag ROLE_STALE_PRIOR and cap role_certainty_score at 60
```
**Backtest:** Tracy 15.4% → ~6.2%, landing near the +850 to +1600 market band instead of 2–3× above it.

### PATCH 4 — Identity-join hard fail · PRIORITY: HIGH

**Defect:** Najee Harris, Braxton Berrios, Darnell Mooney, Odell Beckham Jr. and Isaiah Likely all carried `NO_TD_HISTORY` despite extensive real NFL scoring history. These are ESPN-ID players whose GSIS history never joined.

**Spec:**
```
IF player_career_games >= 16 AND scorer_games_observed == 0:
    raise IDENTITY_JOIN_FAILURE (do not silently fall back to position prior)
    emit to NFL_SCORER_IDENTITY_GAP_BOARD_*.csv
    model_status = QUARANTINE_IDENTITY
```
A veteran with zero observed games is a join bug, never a data truth.

### PATCH 5 — Unpriced-player roster gate · PRIORITY: CRITICAL

**Defect:** Terrance Ferguson had a posted market and no model draws, and scored.

**Spec:**
```
FOR each (team, position) group:
    IF any player has a posted market price AND zero model draws:
        flag POSITION_GROUP_INCOMPLETE for that team+position
        suppress EV+ promotion for every player in that group
        emit NFL_SCORER_COVERAGE_GAP_BOARD_*.csv
```
**Backtest:** quarantines the LA TE group pregame, which is where the fourth touchdown landed.

### PATCH 6 — Post-inactives availability gate · PRIORITY: CRITICAL

**Defect:** The run executed at 23:25Z, after the 22:45Z inactive list, and still carried Puka Nacua, Jordan Whittington and C.J. Daniels as `ACTIVE_OR_UNLISTED`.

**Spec:**
```
IF (kickoff_utc - run_utc) < 120 minutes:
    REQUIRE official_inactives_ingested == True
    ELSE: handoff_status = FAIL, availability_gate = STALE
Additional signal: IF player has model probability >= 15%
                   AND zero books posting a price -> AVAILABILITY_SUSPECT
```
The second rule is the cheap one. Nacua at 24.7% with no posted market anywhere was the tell, and it was available inside the snapshot without any external feed.

### PATCH 7 — Target-share conditioning on the defensive mismatch board · PRIORITY: HIGH

**Defect:** 1-for-5. Verdicts are driven by `td_allowed_per_game` by position without reference to who the opposing offense actually feeds.

**Spec:**
```
effective_mismatch = position_td_vulnerability_ratio
                   * offense_position_target_share_last_3
                   * offense_position_rz_target_share_last_3
Suppress the multiplier entirely when:
    offense_position_target_share is DATA GAP
    OR the position group is flagged POSITION_GROUP_INCOMPLETE
Add individual-defender coverage data where available.
```
A 1.14 TARGET multiplier on NYG tight ends is worthless when the Giants throw 10 targets to Likely and still produce zero red-zone touchdowns. Volume allowed is not opportunity created.

### PATCH 8 — Game-script coupling to market spread · PRIORITY: MEDIUM

**Defect:** Model fair spread LA -2.85 vs market LA -6.5 to -8.5 vs actual -22. The near-even script spread TD mass evenly across both rosters.

**Spec:**
```
spread_disagreement_pts = abs(model_fair_spread - market_spread)
IF spread_disagreement_pts > 3.0:
    flag GAME_SCRIPT_DISAGREEMENT
    apply confidence haircut to every scorer row in that game
    block EV+ promotion for the underdog roster when the model is the
    materially more optimistic side on that roster
```

### PATCH 9 — Disagreement sign rule · PRIORITY: HIGH

**Defect:** `model_market_disagreement_pp` is treated as edge magnitude regardless of sign or player tier.

**Spec:**
```
IF disagreement_pp > 20 AND model_p < market_p AND depth_rank == 1:
    -> MARKET_LIKELY_CORRECT (model-suspect; do not treat the fade as value)
IF disagreement_pp > 20 AND model_p > market_p AND depth_rank >= 3:
    -> ROLE_STALENESS_ALARM (not an edge)
```
**Backtest:** Kyren Williams (22.8 pp, model below, depth 1) and Adams (30.2 pp, model below, depth 1) both flag model-suspect — both scored. Tracy (8.7 pp, model above, depth 3) flags staleness — zero touches. Three for three.

### PATCH 10 — Mandatory close capture · PRIORITY: CRITICAL

**Defect:** CLV, the only durable measure of whether this desk has an edge, is unrecoverable for this slate.

**Spec:**
```
Scheduler: T-minus 10 minutes to kickoff, snapshot every board player
           at every book; write NFL_SCORER_CLOSE_SNAPSHOT_*.csv with
           observed_utc per quote.
Required fields: run_id, player, book, american_odds, observed_utc,
                 close_quality IN (TRUE_CLOSE, CLOSE_PROXY, UNVERIFIED)
No slate may be graded complete without a close snapshot.
```

---

## 7. WEEKLY SCORECARD METRICS TO TRACK FROM HERE

Track these every slate. Single-slate values are noise; the slope over 8–10 slates is the real score.

| Metric | This Slate | Target |
|---|---:|---|
| Model Brier vs market Brier | 0.0806 vs 0.0707 — **LOSS** | Model below market, devigged |
| Expected vs actual scorers (aggregate) | 2.27 vs 2 — pass | within ±15% |
| Per-team scorer distribution error | -2.0 / +1.26 — **FAIL** | within ±1.0 per side |
| EV+ hit rate vs implied | 0-for-3 vs ~5.6% implied | above implied over 50+ rows |
| **CLV: % of EV+ rows that shorten by kickoff** | **UNCOMPUTABLE** | **> 55%** |
| Edge-rank monotonicity (top tercile vs bottom) | **INVERTED** | positive slope |
| Outlier-price share of EV+ rows | 100% (1 of 1 verifiable) | < 20% |
| Coverage gaps that scored | 1 (Ferguson) | 0 |
| Availability misses | 3 (Nacua, Whittington, Daniels) | 0 |

**The single most important line in this table is CLV, and this slate produced none.** Until close capture is automated, this desk cannot distinguish a good model from a lucky one. Patch 10 is the highest-value item in this document.

---

## 8. DATASET B RECORD

| Field | Value |
|---|---|
| Capital deployed | **$0.00** |
| Straight plays executed | None |
| Parlays executed | None |
| Realized P&L | $0.00 |
| Paper EV+ record | 0-3 |
| Paper parlay record | 1-4 |
| Avoided losses | 3 straight rows, all zero-touch |
| CLV captured | **NONE — DATA GAP** |
| Dataset A modified | **NO — frozen and intact** |

### Open items carried forward

1. Close snapshot automation (Patch 10) — blocking.
2. Confirm whether DraftKings' +1600 on Tracy was a stale line or a limit-protected posting. Determines whether Patch 1's threshold should be 1.60 or tighter.
3. Rebuild the LA tight end entity mapping before the next Rams slate.
4. Re-join GSIS history for the five identity-gap players.

---

## 9. FILE NAMING CONVENTION

One file per league, per slate. Never combine.

```
<LEAGUE>_<MARKET>_AUDIT_CALIBRATION_<SLATE_DATE>_<WEEK>_<SLATE_TAG>.md
```

| Example | Scope |
|---|---|
| `NFL_ANYTIME_TD_SCORER_AUDIT_CALIBRATION_2026-09-21_W02_MNF.md` | This file |
| `NFL_ANYTIME_TD_SCORER_AUDIT_CALIBRATION_2026-09-27_W03_SUN.md` | Next NFL scorer slate |
| `NFL_PLAYER_PROPS_AUDIT_CALIBRATION_2026-09-27_W03_SUN.md` | Separate market, same league |
| `NHL_GAME_AUDIT_CALIBRATION_2026-10-04.md` | Separate league |

---

## 10. SOURCES

**Settlement and role data**
- Official box score, scoring summary, drive chart and team stats: NYG @ LAR, 2026 Week 2, SoFi Stadium (final 6–28).
- ESPN game recap: Adams 8 receptions on 10 targets, 195 yards, 2 TD; Stafford 9-for-13, 219 yards, 2 TD on those passes in Week 2; Tyler Nubin allowed 7 catches on 10 targets for 143 yards and a touchdown as nearest defender per NFL Next Gen Stats.
- Fox Sports live blog: Stafford's four touchdown passes to Adams (×2), Kyren Williams and Terrance Ferguson.
- Giants official inactives report: Puka Nacua (hip), Jordan Whittington, C.J. Daniels inactive; Braxton Berrios elevated from the practice squad.

**Close-proxy market data (directional only, not settled closes)**
- bet365 odds article, 2026-09-21: Kyren Williams -165, Davante Adams -115, Puka Nacua +100, Tyrone Tracy Jr. +850, C.J. Daniels +900, Tutu Atwell +900.
- BetMGM: Kyren Williams -175 (as short as -195 elsewhere), Adams +100, Blake Corum +140, Colby Parkinson +210, Nacua -105/+105; separately Adams +110 and +120.
- Rotowire: Tracy +750 Fanatics, Adams +130 Fanatics.
- Sportsbook Review: Adams +105 bet365.
- Gambling911: Kyren Williams -180, Adams -120, Cam Skattebo +115, Malik Nabers +200, Blake Corum +200.
- CBS Sports: Isaiah Likely +290/+260.

**Dataset A**
- `NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W02_NFL-SCORER-2026-W02-20260921T232439Z-MNF_0921.zip`, market snapshot timestamp `2026-09-21T23:25Z`, frozen and unmodified.

---

*Dataset A was not altered at any point. All grading, calibration and patch recommendations are Dataset B artifacts. A winning bet is not automatically a good model read; a losing bet is not automatically a bad one. This slate produced three losing paper positions that the risk layer correctly blocked, and two winning fades that the EV layer correctly refused to buy at the posted price — the outcome and the process disagree in both directions, which is exactly why CLV capture is mandatory going forward.*
