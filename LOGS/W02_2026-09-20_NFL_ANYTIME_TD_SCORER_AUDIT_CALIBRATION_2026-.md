# NFL ANYTIME TD SCORER — FORMAL AUDIT & CALIBRATION REPORT

**League:** NFL
**Market:** `player_anytime_td` (YES)
**Slate:** 2026-09-20 (Sunday) — 2026 Week 2
**Run ID:** `NFL-SCORER-2026-W02-20260920T163420Z-SUN_DAY_0920`
**Model version:** 0.3.0a1 · config hash `0726eaed…` · git `f162a18e`
**Simulations:** 500,000
**Dataset A status:** FROZEN — not modified by this audit
**Dataset B owner:** Trading Agent
**Report date:** 2026-09-24
**File convention:** `<LEAGUE>_<MARKET>_AUDIT_CALIBRATION_<SEASON-WEEK>_<SLATE-DATE>.md` — one file per league, one file per slate. Do not merge slates or leagues into a single file.

---

## 0. EXECUTIVE SUMMARY

The Week 2 anytime-TD board returned **+35.00 units on 88 flat 1u positions (+39.8% ROI)** and **failed every process test applied to it.**

| Test | Result |
|---|---|
| Did the board make money? | **YES** — +35.00u, +39.8% ROI |
| Did it hit its own probability forecast? | **NO** — 5 hits vs 8.23 conservatively expected (−39%) |
| Did high-ranked edge beat the close? | **NO — INVERTED.** Top edge quartile +0.40pp CLV; bottom quartile +2.83pp |
| Did high-ranked edge outperform low-ranked edge on result? | **NO** — top 10 edge went 1-for-10; the one hit carried the entire slate |
| Did the model price correctly vs market? | **NO** — model sat below market on 43 of 46 comparable players, mean −16.51pp |
| Were per-player probabilities better than a flat base rate? | **NO** — Brier 0.1022 vs 0.0867 base-rate benchmark |
| Is the profit attributable to edge? | **NO** — remove one +4500 winner and the board is −10.00u (−11.5%) |

**Verdict: PROFITABLE SLATE, FAILED PROCESS. Do not promote this configuration.**

---

## 1. THE CASINO-QUANT SCORE

> *Did high-ranked model edge consistently beat the close, price correctly, and outperform lower-ranked edge across the slate?*

**Answer: No, on all three counts. The relationship runs backwards.**

### 1.1 Edge rank vs closing-line value

EV+ board sorted by `ev_conservative_pct` descending, split into quartiles. CLV subset = 24 positions with a recovered close.

| Edge quartile | n | Mean claimed EV | Beat close | Mean CLV (pp) | Hits |
|---|---:|---:|---:|---:|---:|
| **Q1 — highest edge** | 6 | **+127.7%** | 3 / 6 | **+0.40** | 1 |
| Q2 | 6 | +55.4% | 4 / 6 | +0.88 | 1 |
| Q3 | 6 | +26.6% | 4 / 6 | +1.30 | 2 |
| **Q4 — lowest edge** | 6 | **+12.6%** | **6 / 6** | **+2.83** | 0 |

**Monotonic and inverted.** Every step down in claimed edge produced *better* closing-line value. The rows the model was most confident about were the rows the market moved against us on.

- `corr(edge_rank, CLV) = +0.337` — higher rank number (less edge) → better CLV
- `corr(claimed EV%, CLV) = −0.205` — more claimed edge → worse CLV

A board with genuine edge produces the opposite signs. This one produces a negative edge-to-CLV relationship on both measures.

### 1.2 Edge rank vs realized result

Full 88-position board, flat 1u:

| Edge quartile | n | Hits | Expected (p_cons) | P&L |
|---|---:|---:|---:|---:|
| Q1 — highest edge | 22 | 1 | 2.08 | **+24.00u** |
| Q2 | 22 | 2 | 1.97 | +25.00u |
| Q3 | 22 | 2 | 2.02 | +8.00u |
| Q4 — lowest edge | 22 | 0 | 2.16 | −22.00u |

Q1's +24.00u comes from a **single** hit — Ryan Miller (MIA) at +4500, edge rank 10, role certainty 44. Q1 went 1-for-22 against 2.08 expected. Q2 beat its own forecast (2 vs 1.97). The apparent Q1 advantage is one longshot, not a gradient.

**Top 10 edge rows:** mean claimed EV **+223.8%**, result **1-for-10**, P&L +36.00u — entirely Miller.
**Bottom 10 edge rows:** mean claimed EV +7.6%, result 0-for-10, P&L −10.00u.

### 1.3 Did the model price correctly?

Probability board vs market-implied probability at the close, 46 players with recovered closes:

| | n | Hits | Hit rate |
|---|---:|---:|---:|
| Model **above** market | 3 | **0** | 0.0% |
| Model **below** market | 43 | 8 | 18.6% |

**Mean gap: −16.51 percentage points.** The model prices below the market on 93% of comparable players, and the three cases where it claimed an edge — D'Andre Swift (+11.8pp), Adam Trautman (+4.7pp), Kenneth Walker III (+2.3pp) — all lost.

Representative top-of-board gaps:

| Player | Model | Market (close) | Gap |
|---|---:|---:|---:|
| Derrick Henry (BAL) | 53.6% | 71.4% (−250) | −17.9 pp |
| Christian McCaffrey (SF) | 42.9% | 71.0% (−245) | −28.1 pp |
| Javonte Williams (DAL) | 25.6% | 63.6% (−175) | −38.0 pp |
| Aaron Jones (MIN) | 17.1% | 54.5% (−120) | −37.4 pp |
| Omarion Hampton (LAC) | 28.0% | 60.6% (−154) | −32.6 pp |

**This single defect explains the shape of the entire board** — see §4.1.

---

## 2. DATA QUALITY AUDIT

### 2.1 Result capture

| Item | Status |
|---|---|
| Games covered | 14 / 14 |
| Scorers recorded | 44 (10 with 2+ TD) |
| Non-scorers recorded | 48 |
| DNP / voids | 0 |
| Scorers inside priced universe (438) | **42 / 44 (95.5%)** — 2 misses were defensive TDs, correctly out of scope |
| Sampling | **SCORER-WEIGHTED** — 48% in-sample hit rate vs ~10% true base rate |

Because capture was scorer-first, all grading in this report uses the **conditional method**: any priced player absent from the results file is treated as a non-scorer. This is a *ceiling* on model performance — an uncaptured scorer can only move results in the model's favor.

### 2.2 Closing-price capture — three rounds

| Round | Rows | Closes found | Timestamped | Same book as entry |
|---|---:|---:|---:|---:|
| 1 — full slate | 276 | **0** | 0 | 0 |
| 2 — scorers only | 44 | 40 | 0 | 9 |
| 3 — non-scorers | 126 | 56 (44%) | 0 | **1** |

**Final: 80 unique closes. Zero capture timestamps. One strict same-book comparison across the entire slate.**

Book distribution on round 3: BetMGM 34, Caesars 17, FanDuel 4, BetRivers 1. Our entry book was DraftKings / FanDuel / BetRivers.

### 2.3 ⛔ CLV IS NOT STRICTLY GRADEABLE FOR WEEK 2

All CLV figures in this report are **indicative cross-book price movement**, not CLV. Three reasons:

1. **Book mismatch** — 55 of 56 round-3 closes came from a book we did not price. BetMGM systematically posts shorter longshot prices than DK/BR, so a DK-entry-to-BetMGM-close comparison measures book spread, not line movement.
2. **No timestamps** — every `close_timestamp_utc` is `DATA GAP`. Sources are preview articles, not quote captures.
3. **Coverage inverted against priority** — EV+ rows came back 20/84 (24%) while the chalk probability board came back 36/42 (86%), because preview articles cover Bijan Robinson and not Dillon Bell.

**The same-book control proves the point.** Of three FanDuel-entry-to-FanDuel-close comparisons:

| Player | Entry | Close | Movement |
|---|---|---|---:|
| Jaylen Wright (MIA) | FD +1400 | FD +1300 | +0.48 pp |
| Darius Cooper (PHI) | FD +1800 | FD +1800 | **0.00 pp** |
| Cody White (LV) | FD +2500 | FD +2500 | **0.00 pp** |

**When the book is held constant, the movement disappears.** The headline "17 of 24 beat the close, +1.35pp mean" is a book-spread artifact. Brian Robinson Jr. at +8.57pp (DK +400 vs BetMGM +250) is the clearest example.

### 2.4 Entity resolution failures

| Player | Result | Defect |
|---|---|---|
| Darren Waller (CAR TE) | **2 TD** | `MISSING_SCORER_DRAWS_OR_PRICE` — no model probability at all; roster feed did not resolve him |
| Oronde Gadsden II (LAC TE) | 1 TD | `MARKET_NOT_PRICED` |
| Kyle Juszczyk (SF FB) | 1 TD | `ENTITY_FAILURE` |
| Nate Adkins (DEN TE) | 1 TD | `LOW_ROLE_LOTTERY_POOL` |

Additionally, **17 of 44 scorers fell outside the printed 168-row board** because of the 12-per-game print cut — including Rashod Bateman, Tyler Warren, DeVonta Smith, AJ Barner and Tank Bigsby, all of whom were priced and modeled but never printed.

---

## 3. BOARD-BY-BOARD GRADES

| Board | Grade | Evidence |
|---|---|---|
| Probability — top 10 | **PASS** | 4 hits vs 3.70 expected |
| Probability — ranks 21–60 | **FAIL** | 1 hit vs 5.50 expected |
| Probability — full 438 universe | **MARGINAL** | 42 actual vs 37.1 expected (+13%) |
| Calibration (Brier) | **FAIL** | 0.1022 vs 0.0867 base-rate benchmark |
| TE position module | **FAIL** | 10 actual vs 4.92 expected (+103%) |
| RB position module | PASS | 11 actual vs 13.53 expected |
| WR position module | PASS | 17 actual vs 16.63 expected |
| QB position module | PASS | 3 actual vs 2.05 expected |
| Defensive mismatch overlay | **DIRECTIONALLY SUPPORTED** | TARGET 58.3% vs BAD_MATCHUP 35.7% hit rate at lower avg probability; n=12, not validated |
| EV+ board — result | **PASS, SINGLE-OUTCOME DEPENDENT** | +35.00u; −10.00u excluding one +4500 |
| EV+ board — process | **FAIL** | 5 hits vs 8.23 expected; 0-for-9 on best-evidence rows |
| Edge-rank ordering | **FAIL — INVERTED** | See §1.1, §1.2 |
| Sharp / risk-adjusted board | **UNGRADED** | 8 of 14 promoted names have no result row |
| Parlay board | **NOT TRADED** | No executable quote ever obtained |
| CLV / execution | **NOT STRICTLY GRADEABLE** | n=1 same-book |
| Universe coverage | **PASS** | 42/44 scorers priced |
| Entity resolution | **FAIL** | 2-TD scorer unpriced; 4 total defects |

---

## 4. CALIBRATION FINDINGS

*Evidence only. Dataset A remains frozen. Nothing below is applied retroactively to Week 2 probabilities.*

### 4.1 ROOT CAUSE — the favorite gap drives the entire board shape

The model prices favorites **17 to 38 percentage points below market**. Consequence chain:

```
model under-prices favorites
  → every favorite fails the EV filter (all showed negative EV at reference price)
    → the only rows surviving are longshots where the model floor > thin market price
      → EV+ board becomes 79 of 88 positions at +1000 or longer
        → board outcome is determined by longshot variance, not by edge
```

**This is structural, not slate-specific. It will reproduce every week until the favorite calibration is fixed.** The "longshot edge" the board appears to find is an artifact of this gap, not a discovery.

### 4.2 Calibration by probability band (438 priced players)

| Band | n | Expected | Actual | Verdict |
|---|---:|---:|---:|---|
| 0–5% | 43 | 1.5 | 1 | Good |
| 5–10% | 98 | 7.6 | 8 | Good |
| **10–15%** | 107 | 12.9 | **19** | **Under-forecast** |
| 15–20% | 28 | 4.7 | 3 | Over-forecast |
| **20–25%** | 14 | 3.1 | **0** | **Badly over-forecast** |
| 25–35% | 18 | 5.1 | 4 | Slight over |
| 35%+ | 5 | 2.1 | 3 | Good |

The **15–25% band is the failure zone**: 42 players, 7.8 expected, **3 actual**. That band is exactly where the model must separate a lead back from a committee back, and it did not.

### 4.3 Role certainty is anti-predictive on this slate

| Role certainty | n | Hits | Expected | P&L |
|---|---:|---:|---:|---:|
| ≤ 50 | 33 | 2 | 2.70 | **+39.00u** |
| 51–80 | 16 | 2 | 1.60 | +24.00u |
| **81–95** | 25 | **0** | 2.38 | **−25.00u** |
| 96–100 | 14 | 1 | 1.56 | −3.00u |

The gate intended to protect the board went 1-for-39 in its two highest tiers. One slate, opposite of prior — **track, do not act.**

### 4.4 Price tier concentration

| Price tier | n | Hits | Expected | P&L |
|---|---:|---:|---:|---:|
| +400 to +1000 | 14 | 1 | 1.93 | −3.00u |
| +1001 to +2000 | 37 | 2 | 3.60 | +3.00u |
| +2001 to +3000 | 26 | 1 | 2.04 | 0.00u |
| **+3001 and longer** | 11 | 1 | 0.65 | **+35.00u** |

100% of net P&L came from the 11 longest-priced positions on the board.

### 4.5 Position module

TE priced at roughly **half** realized rate (10 vs 4.92 on 96 players). The defensive vulnerability layer was already flagging TE as the weakest opposing group in multiple games while the player-side probabilities stayed low — the two modules disagreed and the defensive one was right.

### 4.6 `p_conservative` blend direction

The blend pulls favorites **up** toward market (Henry: p_model 53.6% → p_cons 60.6%) while leaving longshots high relative to thin market prices. This is a structural property of the blend, not a slate observation, and it mechanically guarantees the longshot concentration described in §4.1.

---

## 5. PYTHON PIPELINE IMPROVEMENT TICKETS

Ordered by expected impact. All are Dataset-A pipeline changes; none alter Week 2.

### P0-1 — Recalibrate the favorite band
**Defect:** model runs 17–38pp below market on players priced −100 or shorter.
**Impact:** determines the shape of every EV board produced.
**Action:** fit a market-anchored isotonic or Platt correction on the top probability decile using multi-week closing-line data. Re-run Week 2 as a backtest; a corrected model should surface at least some favorite-side EV rather than exclusively longshots.
**Acceptance:** mean model-minus-market gap on the top decile within ±5pp; EV+ board no longer >85% longshot by construction.

### P0-2 — Add a CLV-ordering regression gate to the handoff
**Defect:** nothing in the pipeline detects that edge rank is inversely related to CLV.
**Action:** emit `NFL_SCORER_CLV_RANK_DIAGNOSTIC_*.csv` after each graded slate with `corr(edge_rank, clv_pp)` and per-quartile CLV. Fail the model card when the correlation is positive (edge → worse CLV) across a rolling 3-slate window.
**Acceptance:** diagnostic present in every handoff; rolling correlation reported on the model card.

### P0-3 — Fix entity resolution before board print
**Defect:** Darren Waller scored twice with no model probability; 3 further scorers lost to `MARKET_NOT_PRICED` / `ENTITY_FAILURE`.
**Action:** block the handoff from printing when any player with a live sportsbook anytime-TD price is unresolved in the roster feed. Emit an explicit unresolved-entity list.
**Acceptance:** zero priced-but-unmodeled players at handoff, or the run fails closed.

### P1-1 — Recalibrate the 15–25% probability band
**Defect:** 42 players, 7.8 expected, 3 actual.
**Action:** isolate committee-back and WR2/WR3 rows inside this band; check whether touch-share dispersion is being under-weighted relative to red-zone share.
**Acceptance:** band-level expected-vs-actual within ±25% over a rolling 4-slate window.

### P1-2 — Rebuild the TE red-zone module
**Defect:** TE forecast at ~50% of realized on a 96-player sample; disagrees with the defensive vulnerability layer.
**Action:** reconcile the TE player-side module against `position_td_vulnerability_ratio`. Where the defense layer flags TE as weakest group, the player-side module should respond.
**Acceptance:** TE expected-vs-actual within ±25% over 4 slates.

### P1-3 — Deepen the board print
**Defect:** 17 of 44 scorers were priced and modeled but never printed, due to the 12-per-game cut.
**Action:** print every priced player with role certainty ≥ 90 regardless of rank, or raise the cut to 18 per game.
**Acceptance:** ≥ 80% of slate scorers appear on a printed board.

### P1-4 — Re-examine the defensive multiplier cap
**Defect:** cap is ±14%; the observed TARGET-vs-BAD_MATCHUP spread (58.3% vs 35.7% hit rate) is larger than the model is permitted to express.
**Action:** track the realized spread over 4+ slates before widening. Do not widen on n=12.
**Acceptance:** decision logged with ≥4 slates of evidence.

### P2-1 — Reconsider the `p_conservative` blend direction
**Defect:** the blend pulls favorites toward market and leaves longshots high, mechanically producing longshot-only EV boards.
**Action:** evaluate a symmetric blend, or apply the conservative haircut proportionally to price rather than to model-market distance.
**Acceptance:** EV+ board price distribution is no longer >85% concentrated at +1000 or longer purely by construction.

### P2-2 — Suspend the role-certainty gate pending evidence
**Defect:** role 81–100 went 1-for-39 with −28.00u while role ≤50 produced +39.00u.
**Action:** do not change the gate on one slate. Log tier-level performance in the diagnostic file and revisit at 4 slates.

---

## 6. TRADING-AGENT PROCESS TICKETS

### T0-1 — Live close capture is mandatory
Retroactive historical-provider lookup cannot produce book-matched, timestamped, full-universe closes. Three capture rounds over four days produced **one** strict comparison.

**Required standard, Week 3 forward:**
- Snapshot **DK / FD / BR** at **T−5 minutes per game**
- Every priced player on the board, **not only the ones we like**
- Store the capture timestamp with each quote
- Preview-article and historical-provider prices are **secondary reference only** and must never populate `closing_american_odds`

### T0-2 — Full-board result capture
Capture must be board-driven, not scorer-driven. Every printed player needs a result row including the zeros, or the sample is conditioned on the outcome and calibration cannot be computed without the conditional workaround used here.

### T1-1 — Sharp-board results are the priority gap
Eight of fourteen sharp-board names have no result. The sharp board is the desk's thesis that role certainty and convergence add value over raw EV, and Week 2 produced **no answer**.

---

## 7. DATASET B LEDGER SUMMARY

| Field | Value |
|---|---|
| Positions graded | 88 (EV+ board, flat 1u, reference price) |
| Hits | 5 |
| Expected hits (`p_model_raw`) | 10.01 |
| Expected hits (`p_conservative`) | 8.23 |
| P&L | **+35.00 u** |
| ROI | **+39.8%** |
| P&L excluding largest winner | **−10.00 u (−11.5%)** |
| Winners | Ryan Miller +4500, Cody White +2500 (2 TD), Jalen Royals +2000, Darius Cooper +1800, Cam Ward +1000 |
| CLV | **NOT STRICTLY GRADEABLE** (n=1 same-book) |
| Actual money staked | None reported — paper grade |
| Parlays | None quoted, none taken |

**Winner CLV detail:** Royals **−2.32pp** (market drifted 20-1 → 40-1 and he scored anyway), Cooper **0.00pp**, White **0.00pp**, Ward +2.02pp (cross-book), Miller **no close recovered**.

---

## 8. PROMOTION DECISION

**DO NOT PROMOTE.**

The configuration produced a profitable slate on a single longshot outcome while failing calibration, failing edge-ordering, failing the model-versus-market price test, and producing no strictly measurable CLV. A +39.8% ROI on 88 positions with 5 hits against 8.23 expected is variance with a favorable tail draw, not demonstrated edge.

**Gate for promotion:** P0-1, P0-2 and P0-3 closed, plus **three consecutive slates** of live, book-matched, timestamped closing-price capture showing a non-positive `corr(edge_rank, clv_pp)`.

---

## 9. CARRY-FORWARD WATCH LIST

| # | Item | Status at W02 | Re-check |
|---|---|---|---|
| 1 | Favorite gap (model vs market, top decile) | −16.5 pp mean | Every slate |
| 2 | `corr(edge_rank, clv_pp)` | +0.337 (inverted) | Every slate, rolling 3 |
| 3 | 15–25% probability band | 3 of 42 vs 7.8 expected | Rolling 4 |
| 4 | TE module | 10 vs 4.92 expected | Rolling 4 |
| 5 | Role-certainty tiers | 81–100 went 1-for-39 | Rolling 4 |
| 6 | Defensive mismatch overlay | TARGET 58.3% vs BAD 35.7%, n=12 | Rolling 4 |
| 7 | Same-book close capture rate | 1 of 80 | Every slate — target 100% |
| 8 | Sharp-board result coverage | 6 of 14 | Every slate — target 100% |

---

## APPENDIX A — EV+ POSITIONS WITH RECOVERED CLOSES (n=24)

| Edge rank | Player | Claimed EV | Entry | Close | Close book | Δ pp | Scored |
|---:|---|---:|---|---|---|---:|:-:|
| 3 | Bam Knight (ARI) | +258.8% | FD +3500 | +2000 | BetMGM | +1.98 | ❌ |
| 12 | Devin Duvernay (ARI) | +154.7% | BR +3000 | +3300 | BetMGM | −0.28 | ❌ |
| 23 | Jalen Royals (KC) | +96.3% | DK +2000 | +4000 | FanDuel | **−2.32** | ✅ |
| 25 | Drew Sample (CIN) | +90.7% | DK +1400 | +1300 | FanDuel | +0.48 | ❌ |
| 26 | Eric Saubert (SEA) | +88.1% | DK +2200 | +3000 | BetMGM | −1.12 | ❌ |
| 31 | Jaleel McLaughlin (CLE) | +77.5% | FD +2200 | +1150 | BetMGM | +3.65 | ❌ |
| 34 | Cody White (LV) | +69.0% | FD +2500 | +2500 | **FanDuel** | **0.00** | ✅ |
| 36 | Kirk Cousins (LV) | +63.1% | FD +2200 | +1450 | BetMGM | +2.10 | ❌ |
| 39 | Cyrus Allen (KC) | +56.7% | FD +1900 | +3000 | BetMGM | −1.77 | ❌ |
| 44 | Chimere Dike (TEN) | +50.1% | DK +1400 | +1250 | BetMGM | +0.74 | ❌ |
| 45 | Adam Trautman (DEN) | +48.3% | DK +850 | +675 | BetMGM | +2.38 | ❌ |
| 48 | John Metchie III (CAR) | +45.0% | BR +1200 | +950 | BetMGM | +1.83 | ❌ |
| 59 | Cam Ward (TEN) | +31.1% | FD +1000 | +800 | Caesars | +2.02 | ✅ |
| 61 | Noah Fant (NO) | +30.3% | BR +1150 | +900 | Caesars | +2.00 | ❌ |
| 63 | Elic Ayomanor (TEN) | +27.9% | BR +950 | +625 | BetMGM | +4.27 | ❌ |
| 64 | Darius Cooper (PHI) | +27.7% | FD +1800 | +1800 | **FanDuel** | **0.00** | ✅ |
| 67 | Calvin Ridley (TEN) | +23.5% | DK +950 | +800 | Caesars | +1.59 | ❌ |
| 69 | Travis Hunter (JAX) | +19.0% | DK +1100 | +1500 | BetMGM | −2.08 | ❌ |
| 70 | Aaron Rodgers (PIT) | +18.9% | DK +1900 | +1300 | BetMGM | +2.14 | ❌ |
| 71 | Dyami Brown (WAS) | +18.6% | DK +1000 | +725 | BetMGM | +3.03 | ❌ |
| 76 | Jaylen Wright (MIA) | +13.6% | FD +1400 | +1300 | **FanDuel** | **+0.48** | ❌ |
| 78 | Brian Robinson Jr. (ATL) | +9.7% | DK +400 | +250 | BetMGM | +8.57 | ❌ |
| 82 | Ollie Gordon II (MIA) | +8.0% | DK +1100 | +1050 | BetMGM | +0.36 | ❌ |
| 87 | Troy Franklin (DEN) | +6.3% | BR +850 | +675 | BetMGM | +2.38 | ❌ |

**Bold rows are the only strict same-book comparisons on the slate.**

---

## APPENDIX B — TOP 10 EDGE ROWS (FULL DETAIL)

| Rank | Player | Book / Price | Claimed EV | p_model | p_cons | Role | Close | Scored |
|---:|---|---|---:|---:|---:|---:|---|:-:|
| 1 | Simi Fehoko (ARI) | DK +3000 | +261.8% | 17.0% | 11.7% | 94 | DATA GAP | ❌ |
| 2 | Kameron Johnson (TB) | BR +2400 | +259.1% | 20.6% | 14.4% | 98 | DATA GAP | ❌ |
| 3 | Bam Knight (ARI) | FD +3500 | +258.8% | 15.0% | 10.0% | 84 | +2000 BetMGM | ❌ |
| 4 | Eli Heidenreich (PIT) | FD +4000 | +253.4% | 15.7% | 8.6% | 44 | DATA GAP | ❌ |
| 5 | Chris Blair (ATL) | DK +4000 | +230.2% | 12.7% | 8.1% | 65 | DATA GAP | ❌ |
| 6 | Dareke Young (LV) | BR +5500 | +215.4% | 8.6% | 5.6% | 44 | DATA GAP | ❌ |
| 7 | Efton Chism III (NE) | DK +2000 | +209.7% | 21.8% | 14.7% | 87 | DATA GAP | ❌ |
| 8 | Dylan Laube (LV) | BR +2200 | +202.3% | 18.0% | 13.1% | 98 | DATA GAP | ❌ |
| 9 | Ben Skowronek (PIT) | BR +2400 | +182.3% | 15.1% | 11.3% | 94 | DATA GAP | ❌ |
| 10 | **Ryan Miller (MIA)** | DK +4500 | +165.2% | 9.4% | 5.8% | 44 | **DATA GAP** | **✅** |

Mean claimed EV +223.8%. Result 1-for-10. **The only winner is also the only position whose close was never recovered** — the single most consequential data gap of the slate.

---

*Dataset A frozen. This document is Dataset B audit history. No probability, rank, or reference price in the Week 2 handoff was altered by this report.*
