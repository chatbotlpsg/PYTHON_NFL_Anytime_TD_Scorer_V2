# NFL ANYTIME TD SCORER — FORMAL AUDIT & CALIBRATION REPORT

**League:** NFL
**Market:** `player_anytime_td`
**Slate date:** 2026-09-17 (Week 2, TNF)
**Game:** Detroit Lions @ Buffalo Bills — Highmark Stadium, Orchard Park, NY
**Event ID:** NFL-EVT-58365DD44F7AD6B5
**Kickoff:** 2026-09-18T00:15Z
**Run ID:** NFL-SCORER-2026-W02-20260917T051012Z-TNF_0917
**Model version:** 0.3.0a1 | **Simulations:** 500,000
**Audit date:** 2026-10-03 | **Dataset:** B (audit only — Dataset A unaltered)

### File-naming convention (enforced from this run forward)

```text
<LEAGUE>_<MARKET>_AUDIT_CALIBRATION_<SLATE_DATE>_<SLATE_KEY>.md

One league per file. One slate per file. Never combine leagues. Never combine slates.
Examples:
  NFL_ANYTIME_TD_SCORER_AUDIT_CALIBRATION_2026-09-17_DET_AT_BUF.md
  NFL_ANYTIME_TD_SCORER_AUDIT_CALIBRATION_2026-09-20_SUN_MAIN.md
  NFL_PLAYER_PROPS_AUDIT_CALIBRATION_2026-09-20_SUN_MAIN.md
```

---

# 1. EXECUTIVE FINDING

The model's **ranking** was excellent. The model's **probability levels** were badly low. Because EV is computed from levels and not from ranks, the EV board inverted: every row it called value lost, and every row it called a pass won.

```text
Model ranking quality (AUC)        0.889   GOOD — top of class
Model calibration (Brier)          0.190   POOR
Market calibration (Brier)         0.130   BETTER THAN MODEL
Model expected distinct scorers    2.99    on the 18 priced rows
Market expected distinct scorers   4.96    (vigged)
ACTUAL distinct scorers            6       on those same 18 rows (8 game-wide)
Straight EV+ card                  0 for 5
Rows the board told us to PASS     6 for 6
```

**Root cause:** the simulation's team touchdown means (BUF 2.50 / DET 2.25 = 4.75 total) sat far below both the market and reality (10 offensive TDs). Too little scoring mass was distributed across too many players, which simultaneously (a) made real scorers look overpriced and (b) made depth players look like value. **The longshot EV tier was an artifact of a volume error, not an edge.**

---

# 2. GROUND TRUTH

Final: Buffalo Bills 41, Detroit Lions 31. Ten offensive touchdowns, eight distinct scorers, zero non-offensive touchdowns.

| Scorer | Team | TDs | Type |
|---|---|---:|---|
| Josh Allen | Buffalo Bills | 2 | rush, rush |
| Amon-Ra St. Brown | Detroit Lions | 2 | rec, rec |
| Jahmyr Gibbs | Detroit Lions | 1 | rec |
| James Cook | Buffalo Bills | 1 | rush |
| Sam LaPorta | Detroit Lions | 1 | rec |
| Joshua Palmer | Buffalo Bills | 1 | rec |
| Dawson Knox | Buffalo Bills | 1 | rec |
| Dalton Kincaid | Buffalo Bills | 1 | rec |

First TD: Josh Allen (1-yd rush, 9:13 Q1).

---

# 3. THE CASINO-QUANT SCORE

> *Did high-ranked model edge consistently beat the close, price correctly, and outperform lower-ranked edge across the slate?*

## 3.1 Did edge beat the close? — **NOT SCOREABLE. CLOSE DATA GAP.**

No timestamped pre-kick price was captured for any player at any book on this run. The frozen reference snapshot is 2026-09-17T05:11Z, roughly **19 hours before kickoff**, which is STALE under the desk's own definition and is not a close.

Secondary market evidence was sourced post-hoc for directional context only. **None of it carries a usable timestamp, so none of it is scored as CLV.** Tag: `MARKET_EVIDENCE_UNTIMESTAMPED`.

| Player | Frozen ref (05:11Z) | Day-of secondary evidence | Direction | Scored? |
|---|---:|---|---|---|
| Jahmyr Gibbs | −320 DK | −233 to −310 across books | drifted longer | NO — untimestamped |
| James Cook | −175 DK | −150 | drifted longer | NO |
| Josh Allen | −136 BR | −115 to −150 | flat | NO |
| Amon-Ra St. Brown | +105 FD | +100 to +125 | flat | NO |
| DJ Moore | +150 DK | +175 | drifted longer | NO |
| Dalton Kincaid | +188 | +200 | drifted longer | NO |
| Jameson Williams | +195 FD | +210 | drifted longer | NO |
| Joshua Palmer | +550 | +550 | flat | NO |
| Sione Vaki | +1000 DK | +950 | **shortened** | NO |
| Jacob Saylors | +2000 FD | none found | — | NO EVIDENCE |
| Tom Kennedy | +2800 DK | none found | — | NO EVIDENCE |
| Tay Martin | +3000 DK | none found | — | NO EVIDENCE |
| Skyler Bell | +2200 BR | none found | — | NO EVIDENCE |

**Reading, stated at the strength the evidence allows:** of the five rows the model called value, four have no observable market footprint at all and one (Vaki) moved toward the model by roughly 0.6 implied points. Meanwhile the starters the model hated drifted slightly longer, meaning the market itself was not confirming the model's direction. **There is no evidence that high-ranked model edge beat the close. There is also no evidence that it did not. The run simply failed to capture the data.** This is the single most important process failure of the slate.

## 3.2 Did it price correctly? — **NO.**

Scored on the 18 model-priced players with best-book reference prices:

| Metric | Model | Market (raw, vigged) | Verdict |
|---|---:|---:|---|
| Brier score (lower better) | **0.1904** | **0.1299** | Market wins by 32% |
| Σ predicted scorers | 2.99 | 4.96 | Actual 6 |
| Forecast-to-actual ratio | **0.50** | 0.83 | Model off by half |

Caveat held honestly: the market column carries vig, which inflates its probabilities and flatters it in a 10-touchdown game. De-vigged, the market's advantage narrows. It does not reverse — the model's shortfall is roughly 3 full scorers across one game.

Bucket calibration:

| Model bucket | n | Mean predicted | Actual hit rate | Error |
|---|---:|---:|---:|---|
| 40–50% | 2 | 44.7% | **100%** | −55.3 pp |
| 30–40% | 1 | 33.1% | **100%** | −66.9 pp |
| 20–30% | 1 | 20.1% | **100%** | −79.9 pp |
| 10–20% | 9 | 12.3% | **22.2%** | −9.9 pp |
| 5–10% | 10 | 8.2% | **20.0%** | −11.8 pp |

**Every bucket under-predicted. There is no bucket where the model was too high.** That is a level error, not noise.

## 3.3 Did high-ranked edge outperform low-ranked edge? — **NO. FULLY INVERTED.**

| Conservative-EV decile | Rows | Scored | Hit rate |
|---|---:|---:|---:|
| Top 5 by EV (the "value" board) | 5 | **0** | **0%** |
| Middle | 7 | 0 | 0% |
| Bottom 6 by EV (the "pass" board) | 6 | **6** | **100%** |

Point-biserial correlation between conservative EV% and outcome is strongly **negative**. The EV board was an anti-signal on this slate.

Contrast with raw probability rank, same 18 rows:

```text
Model probability AUC   0.889    (ranking is sound)
Market probability AUC  0.875    (model edges the market on ORDER)
```

**This is the decisive diagnostic. The model ranks better than the market and prices worse than the market.** The ranking engine is an asset. The level/calibration layer is the defect, and EV inherits the defect.

---

# 4. BOARD-BY-BOARD AUDIT

## BOARD S1 — Most Probable Scorers by Matchup

| Field | Result |
|---|---|
| Rows rendered | 8 (one position per team) |
| Scored | **6 of 8** — Gibbs, Cook, Allen, St. Brown, LaPorta, Kincaid |
| Blanked | Khalil Shakir, Jared Goff |
| Top-4 by probability | **4 of 4 scored** |
| Ranking verdict | **PASS** |
| Level verdict | **FAIL** — every row under-priced |
| 2+ TD verdict | **FAIL** — the two multi-TD scorers (Allen 5.8%, St. Brown 2.2%) carried near-floor 2+ probabilities |

The one-position-per-team filter and the imputed-prior exclusion both worked. DJ Moore, excluded by the imputed-prior rule, did not score; Shakir, who replaced him, also did not. Neutral on that swap, correct on the principle.

## BOARD S2 — Full-Slate Probability Board

Σ p across 19 modeled rows = 3.07 expected distinct scorers. Actual among those rows: 6. **Under-forecast by 96%.**

## BOARD 3/4 — Matchup and Slate EV+ Boards

| Row | Price | Model p | Cons EV% | Result |
|---|---:|---:|---:|---|
| Jacob Saylors (Detroit Lions) | +2000 | 17.2% | +172.3 | **NO TD** |
| Tom Kennedy (Detroit Lions) | +2800 | 9.3% | +120.2 | **NO TD** |
| Tay Martin (Detroit Lions) | +3000 | 8.2% | +93.6 | **NO TD** |
| Skyler Bell (Buffalo Bills) | +2200 | 10.7% | +70.4 | **NO TD** |
| Sione Vaki (Detroit Lions) | +1000 | 14.6% | +46.0 | **NO TD** |

**0 for 5. Paper P&L on the two carded rows: −2.00u.**

The PASS list, same board, same run:

| Row | Price | Cons EV% | Result | P&L if played |
|---|---:|---:|---|---:|
| Jahmyr Gibbs | −320 | −19.8 | **WON** | +0.31u |
| James Cook | −175 | −21.0 | **WON** | +0.57u |
| Josh Allen | −136 | −23.6 | **WON** | +0.74u |
| Amon-Ra St. Brown | +105 | −31.8 | **WON** | +1.05u |
| Sam LaPorta | +220 | −36.8 | **WON** | +2.20u |
| Dalton Kincaid | +188 | −44.2 | **WON** | +1.88u |

**6 for 6, +6.75u foregone.** Verdict: **CRITICAL FAILURE.**

## BOARD 5 — Sharp Risk-Adjusted Board

Ranked Vaki, Kennedy, Saylors. **0 for 3.** The overlay reordered a candidate pool that should never have been constructed. A sharp layer applied to a miscalibrated EV layer inherits the miscalibration. Verdict: **FAIL (inherited)**.

## BOARD 6 — Parlay / Joint Probability Board

| Ticket | Legs | Joint p | Independence | Result |
|---|---|---:|---:|---|
| A | Gibbs + Cook | 19.56% | 19.76% | **WON** |
| B | Allen + St. Brown | 6.75% | 6.66% | **WON** |
| C (flyer) | LaPorta + DJ Moore | 1.45% | 1.43% | LOST (Moore leg) |
| 3-leg alt | Gibbs + Cook + Allen | 6.12% | 6.54% | **WON** |

**Best board on the slate.** Pair and triple ordering tracked reality, and the losing leg was the one pre-flagged as soft. **But no quote was ever pulled on any ticket, so every winner is unrealized.** Verdict: **PASS on math, FAIL on execution capture.**

## RISK-ROOM DECISION LEDGER

| Call | Verdict |
|---|---|
| Quarantine Tay Martin / Skyler Bell (imputed prior) | **CORRECT** — both blank |
| Flag DJ Moore as soft leg | **CORRECT** — losing leg |
| Bench Vaki for thesis duplication | **CORRECT** — both blank |
| Diagnose flat-model structural disagreement | **CORRECT**, and understated |
| Conclude backups were therefore the EV | **WRONG** — inference ran backwards |
| Require live price before PLAY | **PROCESS CORRECT** — saved −2u, also left 3 winning tickets unpriced |

---

# 5. PYTHON PIPELINE PATCH SPECIFICATION

Dataset A is immutable for this run. The following are forward-looking build tickets.

## PATCH-01 — Team touchdown total anchoring **[P0, BLOCKING]**

**Defect:** simulated team TD means (4.75 combined) were disconnected from the market's implied game environment (total 53.5–54.5, implied ~6 offensive TDs) and from realized output (10).

**Fix:** anchor simulated team TD means to the game total and spread before player allocation.

```python
# new module: scorer/anchoring.py
implied_team_tds = f(game_total, spread, pace, pass_rate)   # fit on 3+ seasons
scale = implied_team_tds.sum() / sim_team_tds.sum()
if not 0.85 <= scale <= 1.15:
    raise AnchorDriftError(scale)          # fail closed, do not emit boards
sim_team_tds *= scale                      # rescale BEFORE player allocation
```

**Emit to manifest:** `team_td_anchor_scale`, `implied_total_tds_market`, `sim_total_tds_raw`, `anchor_status`.
**This run would have produced scale ≈ 1.26 and hard-failed, which is the correct outcome.**

## PATCH-02 — Probability calibration layer **[P0]**

**Defect:** no calibration. Metadata reads `SCORER_IDENTITY_PENDING_WALK_FORWARD_DATASET_B`, i.e. raw simulation output is being priced directly.

**Fix:** isotonic regression (or Platt scaling if n is thin) fit on prior-season anytime-TD outcomes, applied per position group, with monotonicity enforced. Rank order is the model's asset (AUC 0.889) — **the calibrator must be rank-preserving.**

```python
p_calibrated = isotonic_by_position[pos].transform(p_model_raw)
assert spearman(p_model_raw, p_calibrated) > 0.999   # order preserved
```

**Gate:** until a calibrator is fitted and validated, `ev_*` columns must be emitted as `NULL` with `model_status = CALIBRATION_PENDING_NO_EV`. **No EV board at all beats an inverted EV board.**

## PATCH-03 — Longshot-only EV guard **[P0]**

**Defect:** 5 of 5 EV+ rows were depth players; 0 of 14 starters qualified. That shape is a model-defect signature.

```python
ev_rows = board[board.ev_conservative_pct > 0]
starter_share = (ev_rows.depth_rank == 1).mean()
if len(ev_rows) >= 3 and ev_rows.p_model_raw.max() < 0.20:
    flag("LONGSHOT_ONLY_EV_TIER")          # every EV row is a longshot
    board.model_status = "CALIBRATION_ALARM_EV_SUPPRESSED"
```

Trigger condition: no EV+ row above 20% model probability while priced starters all show negative EV. **Suppress the board and raise an alarm.** This run trips it.

## PATCH-04 — Σp versus market mass reconciliation **[P1]**

```python
sum_p_model  = board.p_model_raw.sum()
sum_p_market = board.market_raw_implied_prob.sum() / est_overround
ratio = sum_p_model / sum_p_market
if ratio < 0.80 or ratio > 1.20:
    flag("SCORER_MASS_DISAGREEMENT", ratio)
```

This run: 2.99 model against ~4.96 vigged (~4.1 de-vigged) = ratio ≈ 0.73. Trips at P0 severity.

## PATCH-05 — Imputed-prior hard block **[P1]**

Players with `scorer_games_observed == 0` currently receive a default prior (0.3 carries, 5.0 receiving opportunities, 0.34 TD/g) and then appear on the EV board at 8–11% with triple-digit EV. Three of five EV+ rows came from this path.

```python
if scorer_games_observed == 0 or workload_is_default_prior:
    model_status   = "IMPUTED_PRIOR_NOT_TRADEABLE"
    ev_eligible    = False        # probability board only, never EV, never parlay leg
```

## PATCH-06 — Mandatory close capture **[P0, PROCESS]**

The pipeline must schedule a second market snapshot at **T-10 minutes** and write `NFL_SCORER_CLOSE_SNAPSHOT_*.csv` with `book`, `american_odds`, `captured_at_utc`, `minutes_to_kickoff`. Without it, CLV — the only unbiased measure of whether the edge is real — is permanently unrecoverable for that slate. **This run has no answer to its most important question, and that is a tooling failure, not a modeling one.**

## PATCH-07 — Parlay quote capture hook **[P2]**

Tickets A, B and the 3-leg alternative all won and none was priced. Emit the top 5 disjoint tickets to a `PARLAY_QUOTE_REQUEST_*.csv` so SGP quotes are pulled pregame as a matter of course.

## PATCH-08 — Board-level separation of rank and price **[P2]**

Given AUC 0.889 against Brier 0.190, publish a **Rank Board** (trustworthy today) distinctly from an **EV Board** (not trustworthy until PATCH-01/02 land). Ship the rank board, gate the EV board.

---

# 6. ACCEPTANCE TESTS BEFORE EV IS RE-ENABLED

```text
T1  Anchor scale within 0.85–1.15 on 20 consecutive backtest slates
T2  Calibration Brier <= market vigged Brier on a 50+ slate walk-forward
T3  Bucket hit rates within +/- 5 pp of predicted across all five buckets
T4  Rank AUC not degraded below 0.85 by the calibrator
T5  EV+ tier contains >= 1 starter (depth_rank 1, p > 0.20) on >= 60% of slates
T6  Close snapshot present for 100% of priced rows at T-10 minutes
T7  Zero imputed-prior rows on any EV or parlay board
```

---

# 7. CALIBRATION NOTES FOR THE RECORD

1. **Ranking is the model's asset; levels are its liability.** AUC 0.889 against market 0.875 says the simulation understands usage and matchup. Brier 0.190 against market 0.130 says it does not understand how often touchdowns happen. Fix the second without touching the first.
2. **Longshot-only EV is a defect signature, never an edge.** When the only positive-EV rows are backups, the correct output is an alarm, not a card.
3. **The joint-probability engine outperformed the marginal engine.** Pair and triple ordering was sound even while marginals were low. Worth splitting into separate calibration tracks.
4. **Imputed priors cost real money.** Three of five false-positive EV rows and the single losing parlay leg traced to default workload placeholders.
5. **No close means no score.** The casino-quant question asked of this slate cannot be answered. Every future run must capture T-10 prices before any board is treated as graded.
6. **A 10-TD game is one observation.** Nothing here is statistically conclusive on its own. The conclusions above are drawn from the *structure* of the errors — uniformly one-directional across every bucket — not from the slate's win/loss record.

---

# 8. SLATE SCORECARD

| Board | Grade | Basis |
|---|---|---|
| S1 matchup probability | **B** | 6/8 scored, top-4 perfect, levels low |
| Slate probability | **B−** | ranking sound, Σp off by half |
| Matchup EV+ | **F** | 0 for 5 |
| Slate EV+ | **F** | 0 for 5; pass list 6 for 6 |
| Sharp board | **F** | 0 for 3, inherited defect |
| Parlay math | **A−** | 3 of 4 tickets correct, soft leg correctly flagged |
| Parlay execution | **F** | zero quotes captured on three winning tickets |
| Risk room | **C+** | 4 of 6 calls correct; diagnosis right, inference backwards |
| Close / CLV capture | **F** | no data captured, CLV permanently unrecoverable |
| Handoff integrity | **PASS** | all contract files present, reconciliation OK, convergence OK |

**Realized paper P&L:** −2.00u on 2 carded straights.
**Opportunity cost on the pass list:** +6.75u.
**Unrealized on winning parlay tickets:** unquantifiable — no quotes pulled.

---

*Dataset A frozen and unmodified. All grading, pricing commentary, market evidence and patch specification above is Dataset B.*
