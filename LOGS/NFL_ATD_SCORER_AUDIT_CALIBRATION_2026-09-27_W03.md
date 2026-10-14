# NFL Anytime TD Scorer — Formal Audit & Calibration Report

**League:** NFL · **Market:** player_anytime_td  
**Slate:** 2026-09-27 (Season 2026, Week 3, Sunday, 13 games)  
**Run ID:** NFL-SCORER-2026-W03-20260927T150000Z-W3_SUN_DAY_0927  
**Model:** AITA_NFL_TOUCHDOWN_SCORER v0.4.0a1 · 500,000 simulations  
**Frozen price snapshot:** 2026-09-27 15:05Z (FanDuel / DraftKings / BetRivers)  
**Audit date:** 2026-10-04  
**Audit basis:** Dataset B only. Dataset A (frozen Python handoff) was read, not modified.  
**Grading mode:** PAPER_GRADE. No actual entries were supplied, so every bet is 1 unit at the best frozen book.

---

## 0. Executive Verdict — The Casino-Quant Score

The question this report answers:

> Did high-ranked model edge consistently beat the close, price correctly, and outperform lower-ranked edge across the slate?

| Test | Verdict | Evidence |
|---|---|---|
| **1. Beat the close (CLV)** | **UNANSWERED — CLOSE DATA GAP** | No verifiable closing anytime-TD prices were found for any of the 22 EV+ rows (see §4). CLV cannot be claimed in either direction. |
| **2. Price correctly** | **FAIL** | The top-edge quintile was priced at 12.7% average by the model. It hit 5.8%. The market said 6.9%. The model roughly doubled the true probability of its own best edges. |
| **3. Outperform lower-ranked edge** | **FAIL** | Top-edge quintile ROI −38.8% vs second quintile +24.7%. Spearman correlation between model-EV rank and realized P&L = **0.003** (p = 0.96). Top 5 and top 10 edges went 0-for-10. |
| **Model information beyond market** | **NOT DEMONSTRATED** | Adding model log-odds to market log-odds improved log-likelihood by 0.55 (likelihood-ratio χ² = 1.10, p ≈ 0.29). Market alone beat model alone on Brier and log loss. |
| **Aggregate calibration** | **PASS** | 45 scorers vs 45.08 expected across 415 modeled players. Brier 0.0860, an 11% improvement over a base-rate guess. |
| **Selection / pass discipline** | **PASS** | Rejected rows lost −45.2u at their prices (−19.1% ROI). Weak-offense suppression went 0/8 vs 1.95 expected. |

**One-line verdict:** the pipeline is well calibrated in total but not sharp at the margin. Its EV board is driven by a structural longshot overpricing that the market corrects, so model-ranked edge did not produce a higher hit rate or better ROI than lower-ranked rows on this slate. One slate is a small sample; the direction of the evidence is clear, but its magnitude is not yet reliable.

---

## 1. Data Provenance

| Item | Source | Status |
|---|---|---|
| Model probabilities, ranks, EV, joint probabilities | Frozen handoff ZIP (Dataset A) | PASS, unmodified |
| Entry price | Frozen 15:05Z snapshot, best of FD/DK/BR | REFERENCE_PRICE_ONLY |
| Closing price | Searched; see §4 | **CLOSE DATA GAP** |
| Results | CBS Sports gametrackers (NYJ@DET, CAR@CLE, LAC@BUF); legionreport/BALLDONTLIE scoring summaries and fantasydata box scores (other 10 games); team-site and Field Level Media recaps for cross-checks | Verified, all 13 games |
| Actual entries | Not supplied | PAPER_GRADE |

**Settlement and availability notes**

- **SETTLEMENT_DEFINITION_MISMATCH:** Myles Price (MIN) scored on an 86-yard punt return. The model target is a miss; the book result depends on that book's return-TD rule.
- **VOID:** Jayden Daniels (WAS) did not play. He is excluded from scoring.
- **Defensive TD:** Kain Medrano (WAS) returned an interception for a touchdown. This is not modeled; it may settle WAS D/ST markets.
- **Played but injured in-game (graded normally):** Achane (MIA), Hall (NYJ), Coker (CAR), Etienne (NO).

---

## 2. Final Results (offensive rushing/receiving TDs)

| Game | Final | TD scorers |
|---|---|---|
| NYJ @ DET | 24–31 | Jahmyr Gibbs ×3, Amon-Ra St. Brown, Kenyon Sadiq, Jeremy Ruckert, Garrett Wilson |
| CAR @ CLE | 18–21 | Harold Fannin Jr. ×2, John Metchie III |
| LAC @ BUF | 16–24 | Josh Allen ×2, James Cook, Keaton Mitchell |
| CIN @ PIT | 27–30 | Ja'Marr Chase, Tee Higgins, Mike Gesicki, Roman Wilson, Ben Skowronek, DK Metcalf |
| HOU @ IND | 17–19 | Keenan Allen, Foster Moreau, Woody Marks |
| KC @ MIA | 24–10 | Kenneth Walker III ×2, Travis Kelce, Ollie Gordon II |
| NE @ JAX | 6–35 | Josh Cameron, Jakobi Meyers, Parker Washington, Chris Rodriguez Jr., Bhayshul Tuten |
| SEA @ WAS | 31–33 | Jaxon Smith-Njigba ×2, Cooper Kupp, Eric Saubert, Rachaad White, Treylon Burks, Terry McLaurin |
| TEN @ NYG | 7–12 | Wan'Dale Robinson |
| ARI @ SF | 30–36 | George Kittle ×2, Christian McCaffrey, Mike Evans, Deebo Samuel, Michael Wilson, Jeremiyah Love, Jacoby Brissett |
| MIN @ TB | 23–16 | Jordan Addison, Ted Hurst III (Myles Price punt-return TD is not a model target) |
| BAL @ DAL (Rio) | 34–31 | Derrick Henry ×2, Chris Moore, Matt Hibner, Javonte Williams, Jake Ferguson, KaVontae Turpin |
| LV @ NO | 35–27 | Juwan Johnson ×2, Noah Fant ×2, Michael Mayer, Mike Washington Jr., Cody White, Brock Bowers |

The slate had 65 offensive TD events across 55 distinct scorers.

---

## 3. Probability Board Calibration (market-blind)

### 3.1 Global metrics (415 modeled players; Daniels void)

| Metric | Value |
|---|---|
| Brier score | **0.0860** (base-rate benchmark 0.0967 → +11.0% skill) |
| Log loss | 0.2992 |
| Σ expected scorers vs actual | 45.08 vs **45** |
| Σ expected 2+ TD vs actual | 4.41 vs **8** (**under**) |
| Offensive TD events captured by model universe | 54 / 65 (83%) |

### 3.2 Reliability table

| Bin | N | Mean predicted | Actual | Gap | Verdict |
|---|---:|---:|---:|---:|---|
| ≥50% | 2 | 54.8% | 50.0% | −4.8 | OK (n tiny) |
| 40–50% | 4 | 45.5% | 75.0% | +29.5 | Under (n tiny) |
| 30–40% | 10 | 34.9% | 30.0% | −4.9 | OK |
| 20–30% | 22 | 24.5% | 31.8% | +7.3 | Under |
| 10–20% | 142 | 14.0% | 14.8% | +0.8 | OK |
| <10% | 235 | 5.7% | 4.3% | −1.4 | Slight over |

### 3.3 Allocation errors (where the mass went wrong)

| Dimension | Expected | Actual | Finding |
|---|---:|---:|---|
| RB scorers | 16.11 | 13 | Over-allocated to RB |
| TE scorers | 4.90 | 9 (+4 TE events by unmodeled TEs) | **Severely under-allocated to TE** |
| WR scorers | 20.91 | 21 | OK |
| QB rushing scorers | 3.15 | 2 | Slight over |
| Unpriced modeled players (156) | 12.68 | **0** | **Mass assigned to players the market doesn't even price** |
| Players the market priced but the model had no draws for (96) | 0 (model) / 6.09 (market) | **10** | Coverage gap |

**Key calibration finding:** the totals look right because two large errors cancel. The model assigns about 12.7 expected scorers to deep players nobody prices (0 scored). Meanwhile 10 scorers came from players the books priced but the model never simulated: Fant, Mayer, Ruckert, Saubert, Hibner, Chris Moore, Burks, Hurst, Skowronek, and Keaton Mitchell.

### 3.4 Probability-board ranks

| List | Hits | Expected |
|---|---:|---:|
| Slate top 5 | 4 | 2.47 |
| Slate top 10 | 6 | 4.41 |
| Slate top 20 | 8 | 7.54 |
| Matchup rank-1 (13 games) | 4 | 5.33 |

The model's ordering of high-probability scorers worked: Gibbs, Henry, McCaffrey, Cook, Allen, and Walker all scored. The issue is how much probability it gave each of them relative to the market price (§5).

---

## 4. Closing-Line (CLV) Audit

### 4.1 Sourcing attempt

The agent searched public sources for closing (kickoff) anytime-TD prices on the slate. Results:

| Source found | Player / price | Timestamp | Usable as close? | Reason |
|---|---|---|---|---|
| Dimers model article | Jacory Croskey-Merritt +230 (Caesars) | 2026-09-27 10:59 ET | **No** | Pre-snapshot, different book |
| BetMGM blog | Kenneth Walker III −210; De'Von Achane +105 | ~Sep 25 | **No** | Days before kickoff |
| Bleacher Nation | Jahmyr Gibbs −360 | Sep 23 | **No** | Days before kickoff |
| Sportsbook Review article | Chase Brown +100 (FanDuel) | Page updated 4:24 PM ET | **No** | Updated after the 1:00 PM kickoff; not a pregame close |
| RotoBaller picks | JSN +100 (FD), Jefferson +155 (FD), T. McMillan +190 (DK) | ~Sep 26–27 | **No** | Publication-time quotes, not closes |

**Result:** none of the 22 EV+ rows has a verifiable close. CLV = **CLOSE DATA GAP** for the entire EV board. The agent does not estimate closes.

### 4.2 What *can* be measured: entry-price quality versus the 3-book consensus

This is line-shopping quality at the 15:05Z snapshot. It is **not CLV**.

| Statistic | Value |
|---|---|
| EV+ rows priced at all 3 books | 22 / 22 |
| Best-book implied below consensus implied | 21 / 22 (Myles Price was tied) |
| Average shopping gain | ≈ +0.9 pp implied probability (range 0.0 – 1.6 pp) |

Interpretation: the pipeline reliably captured the best available number at snapshot time. Whether that number held, improved, or worsened into kickoff is unknown.

### 4.3 CLV verdict

**Not determinable.** The pipeline currently has no closing-price capture, so this question cannot be answered on any slate until §8 item P-1 is implemented.

---

## 5. Edge-Ranking Test — Did High-Ranked Edge Outperform?

All 259 modeled players with a frozen price were ranked by **model EV at the best book** (EV = p_model × decimal − 1) and split into quintiles. Every row is a 1-unit paper bet.

### 5.1 Quintile table

| Quintile | N | Mean model EV | Mean edge (model − market, pp) | Model p | Market implied | **Actual** | Hits | Model Σp | Market Σ | **P&L** | **ROI** | Model Brier | Market Brier | Median odds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Q1 (top edge)** | 52 | +117.8% | +5.7 | 12.7% | 6.9% | **5.8%** | 3 | 6.58 | 3.60 | **−20.2u** | **−38.8%** | 0.059 | **0.051** | +1800 |
| Q2 | 52 | −27.0% | −7.5 | 19.3% | 26.7% | **30.8%** | 16 | 10.03 | 13.91 | **+12.9u** | **+24.7%** | 0.202 | **0.181** | +385 |
| Q3 | 51 | −45.2% | −12.3 | 14.8% | 27.0% | 19.6% | 10 | 7.53 | 13.79 | −6.2u | −12.2% | 0.161 | 0.175 | +310 |
| Q4 | 52 | −56.2% | −13.2 | 10.3% | 23.4% | 23.1% | 12 | 5.33 | 12.18 | −15.2u | −29.3% | 0.167 | **0.130** | +360 |
| Q5 (bottom edge) | 52 | −72.9% | −15.0 | 5.6% | 20.6% | 7.7% | 4 | 2.93 | 10.72 | −27.4u | −52.7% | **0.074** | 0.101 | +418 |

### 5.2 Top-K concentration

| Top-K by model EV | Hits | Model expected | Market expected | P&L |
|---|---:|---:|---:|---:|
| Top 5 | 0 | 0.77 | 0.17 | −5.0u |
| Top 10 | 0 | 1.54 | 0.41 | −10.0u |
| Top 22 (handoff EV+ set) | 1 | 2.98 | 0.98 | −6.0u |
| Top 52 (Q1) | 3 | 6.58 | 3.60 | −20.2u |

### 5.3 Statistical tests

| Test | Result | Read |
|---|---|---|
| Spearman (model-EV rank vs realized P&L) | ρ = 0.003, p = 0.96 | **No ordering power** |
| Logistic, market log-odds only | slope 0.993 ± 0.198, intercept −0.273, LL −103.93 | Market well-ordered; intercept is the vig |
| Logistic, model log-odds only | slope 0.974 ± 0.220, LL −107.96 | Model ordering works, but is worse than market |
| Logistic, model + market | model 0.325 ± 0.319, market 0.766 ± 0.287, LL −103.38 | Model adds ~0 beyond market (LR χ² 1.10, p ≈ 0.29) |
| Log loss on priced players | model 0.4276 vs market 0.4059 | Market better |
| Brier on priced players | model 0.1326 vs market 0.1272 | Market better |

### 5.4 Price-bucket reliability (where the miscalibration lives)

| Price bucket | N | Model p | Market implied | **Actual** | P&L (bet all) |
|---|---:|---:|---:|---:|---:|
| Favorites (shorter than +100) | 15 | **36.3%** | 59.9% | **60.0%** | −0.6u |
| +100 to +149 | 12 | 29.8% | 45.8% | 8.3% | −10.0u |
| +150 to +399 | 89 | 13.5% | 28.6% | 27.0% | −4.4u |
| +400 to +999 | 74 | 7.8% | 14.2% | 9.5% | −25.2u |
| +1000 and longer | 68 | **8.2%** | 5.5% | **5.9%** | −15.0u |

This is the core finding. The model is **compressed**: it is far too low on favorites (36% vs 60% actual) and too high on longshots (8.2% vs 5.9% actual). Every model EV+ edge comes from the longshot side of that compression. The market is close to correct at both ends.

### 5.5 Verdict on ranked edge

**High-ranked edge did not outperform lower-ranked edge.** The best realized quintile was Q2, the mildly EV-negative group of mid-priced starters. Q1 returned the second-worst ROI. The only fully consistent relationship is that the worst-edge quintile also performed worst, and that comes from the market's vig rather than from model skill.

---

## 6. Board-by-Board Grades

### 6.1 Straight EV board (22 rows, paper)

| Tier | N | Hits | Expected (Σ conservative p) | P&L | ROI |
|---|---:|---:|---:|---:|---:|
| ELITE / SHARP VALUE | 9 | 0 | 0.96 | −9.0u | −100% |
| PLAYABLE VALUE | 4 | 1 (Turpin +1000) | 0.67 | +7.0u | +175% |
| MARGINAL / WATCH | 9 | 0 (1 if the book pays Price's punt-return TD) | 1.28 | −9.0u (+6.0u if paid) | −100% |
| **Total** | 22 | 1 | 2.91 | **−11.0u** | **−50.0%** |

The model's conservative probabilities summed to 2.91 expected hits; 1 occurred. The market's raw implied sum was 1.84 expected hits, so the market was closer.

### 6.2 Sharp board (12 rows)

| Board | Hits | Expected | P&L |
|---|---:|---:|---:|
| Sharp 12 | 0 | 1.53 | −12.0u |
| Sharp top 5 | 0 | 0.93 | −5.0u |
| Raw-EV top 12 (control) | 0 | 1.34 | −12.0u |

The sharp re-ranking added no measurable value on this slate, and neither ordering found a winner. The one EV hit, Turpin, was ranked last by EV and excluded from the sharp 12 for having a thin cushion.

### 6.3 Defensive mismatch board (19 rows)

| Group | N | Hits | Expected |
|---|---:|---:|---:|
| Mismatch board | 19 | **8** | 5.70 |
| TARGET verdict (matchup board) | 41 | **12** | 7.79 |
| Raw defensive ratio R > 1.20 (capped at 1.14) | 21 | **7** | 3.90 |
| BAD_MATCHUP verdict | 31 | 7 | 6.33 |
| Named capped trio (Judkins, Freiermuth, Barner) | 3 | 0 | 0.53 |

**The defensive signal outperformed.** Matchup-favored players beat their probabilities, and the capped group outperformed its capped probability. This is the most promising single component on this slate.

### 6.4 Parlay card (5 cards, NOT TRADED)

| # | Legs | Joint p | Result |
|---:|---|---:|---|
| 1 | Jonathan Taylor (IND) + Bucky Irving (TB) + Jacory Croskey-Merritt (WAS) | 6.82% | MISS (0/3) |
| 2 | Jahmyr Gibbs (DET) + Chase Brown (CIN) + Cam Skattebo (NYG) | 7.67% | MISS (1/3) |
| 3 | Bhayshul Tuten (JAX) + Tee Higgins (CIN) | 6.91% | **HIT** |
| 4 | Derrick Henry (BAL) + James Cook (BUF) | 21.05% | **HIT** |
| 5 | Josh Allen (BUF) + Travis Etienne (NO) | 10.36% | MISS (1/2) |

The card went 2/5 against 0.53 expected hits. No P&L is claimed because no executable quote was ever captured.

### 6.5 Rejection board (full market, best price per player)

| Rejection reason | N | Hits | Market expected | P&L if bet |
|---|---:|---:|---:|---:|
| INSUFFICIENT_EV | 131 | 33 | 38.27 | −21.6u |
| STARTER_GATE_FAILED | 85 | **8** | 9.33 | −18.2u |
| MISSING_SCORER_DRAWS_OR_PRICE | 96 | **10** | 6.09 | **+27.5u** |
| VERY_WEAK_OFFENSE_ZERO_CURRENT_SEASON_TDS | 21 | 3 | 4.77 | −5.5u |
| ENTITY_FAILURE (mostly D/ST rows) | 62 | 0* | 7.31 | — |

\* D/ST TDs (e.g., WAS) were not graded in this pass.

**Scorers the starter gate rejected:** Woody Marks (+270), Chris Rodriguez Jr. (+265), Rachaad White (+360), Ollie Gordon II (+540), Mike Washington Jr. (+550), Foster Moreau (+1000), Josh Cameron (+1400), Cody White (+1500).

**Scorers missing from the simulation:** Michael Mayer (+420), Ted Hurst III (+425), Chris Moore (+450), Keaton Mitchell (+600), Noah Fant (+700), Jeremy Ruckert (+1050), Eric Saubert (+1600), Treylon Burks (+1600), Matt Hibner (+1700), Ben Skowronek (+2800).

---

## 7. Root-Cause Diagnosis

| # | Defect | Evidence | Impact on boards |
|---|---|---|---|
| D-1 | **Probability compression** toward a positional prior (favorites too low, longshots too high) | Favorites: model 36% vs actual 60%. +1000 and longer: model 8.2% vs actual 5.9% | Creates false EV on longshots; under-ranks favorites; the EV board is systematically on the wrong side |
| D-2 | **No market anchoring** (calibration pending; the market blend is raw-implied and low-trust) | Market log loss 0.406 vs model 0.428. The model adds ~0 information beyond market | EV is computed off an unanchored probability |
| D-3 | **Universe / starter-gate error** | 156 unpriced modeled players carried 12.7 expected scorers and produced 0. 18 scorers were rejected by the gate or never simulated | Probability mass sits on the wrong depth players; TE2s and RB2s are missed |
| D-4 | **Poisson dispersion too thin** | 2+ TD games: 4.41 expected vs 8 actual | Under-prices bell-cows' multi-TD tails and correlated parlays |
| D-5 | **Position allocation** | TE 4.90 expected vs 9 (+4 unmodeled); RB 16.1 vs 13 | Systematic TE under-allocation |
| D-6 | **No close capture** | §4 | CLV is unmeasurable, so edge quality can't be validated |
| D-7 | Defensive multiplier hard cap at ±14% | Capped R > 1.20 group: 7 hits vs 3.90 expected | The signal may be truncated (needs multi-week evidence) |

---

## 8. Python Pipeline Improvement Plan (board-level)

These are proposals for the **next** model version. Dataset A for this slate stays frozen.

### P-1 — Closing-price capture (fixes D-6) · Priority: CRITICAL

```text
module: market/close_capture.py   (new)
trigger: per game, at commence_time − 5 min (and a fallback at −1 min)
pull:    player_anytime_td for every player in MARKET_SNAPSHOT, all configured books
write:   NFL_SCORER_CLOSE_SNAPSHOT_<season>-W<wk>.csv
         cols: run_id, aita_event_id, player_id, book, close_american, close_ts, close_quality
compute: clv_pp = implied(close) − implied(entry); clv_pct = dec(entry)/dec(close) − 1
board:   add CLV columns to EV, sharp, and parlay boards on the postgame rerun
quota:   ~13 games × 1 call per book-market; respect the existing ODDS_QUOTA_REPORT guard
```

### P-2 — Market-anchored probability blend (fixes D-1 and D-2) · Priority: CRITICAL

```text
p_mkt_fair = devig(raw_implied)   # per-game normalization of Σ implied to the model's team-TD expectation,
                                  # or a power/Shin devig per book; median across books
logit(p_final) = w · logit(p_model) + (1 − w) · logit(p_mkt_fair)
initial w = 0.25   (best in-sample Brier on this slate: 0.1254 vs 0.1257 market-only, 0.1326 model-only)
EV, buy-to, and hard-stop are computed from p_final, not p_model
```

- On this slate, the in-sample devig factor was Σactual / Σraw-implied ≈ 0.83 (0.81 across the full market). That fit uses this slate's own outcomes, so do **not** hard-code it.
- Walk-forward fit w each week, using only prior weeks.

### P-3 — Longshot shrinkage gate (fixes D-1 on the EV board) · Priority: HIGH

```text
if american_odds >= +1000:
    p_final = p_mkt_fair + k · (p_final − p_mkt_fair)   # k = 0.5 initially
if |p_model − p_mkt_fair| > 8 pp and american_odds >= +700:
    status = WATCH (never PLAY) unless role_certainty ≥ 95 AND ≥ 2 books are EV+ after the blend
```

Rationale: Q1 (median +1800) went −38.8% ROI, and the model overpriced it 2× relative to the outcome.

### P-4 — Universe and starter-gate repair (fixes D-3 and D-5) · Priority: HIGH

```text
rule A: every player present in MARKET_SNAPSHOT must be simulated (no MISSING_SCORER_DRAWS for priced players)
rule B: STARTER_GATE_FAILED players are still simulated with a role-share prior;
        the gate only blocks PLAY status, not probability generation
rule C: players never priced by any book get p capped at 2% (or excluded) and their mass is
        redistributed within the team's TD budget
rule D: TE allocation — add TE2 and red-zone TE share; check team TE share vs 3-season league share
```

On this slate, rule A would have added 10 scorers to the model universe, rule B would have covered 8 more, and rule C would have removed 12.7 expected scorers that produced 0.

### P-5 — Dispersion upgrade (fixes D-4) · Priority: MEDIUM

```text
replace Poisson(λ_player) with Negative-Binomial(λ, r) or a gamma-mixed Poisson
fit r by position from multi-season player-game TD counts
target: Σ P(2+ TD) within ±20% of realized over a rolling 4-week window
also feeds the joint pair/triple boards (correlated multi-TD paths)
```

### P-6 — Defensive multiplier cap test (D-7) · Priority: MEDIUM (evidence-gated)

```text
A/B in walk-forward: cap 1.14 (current) vs 1.20 vs uncapped-with-shrinkage
  M = 1 + s · (R − 1), s fitted
keep the change only if walk-forward Brier improves over ≥ 6 weeks
```

### P-7 — Board ranking logic · Priority: HIGH

| Board | Current sort | Proposed sort |
|---|---|---|
| EV+ board | Conservative EV% from p_model | Conservative EV% from p_final (P-2), after the P-3 gate |
| Sharp board | Blend of EV, confidence, disagreement | Blended edge in pp × confidence, with a hard block when the model–market gap exceeds 8 pp at +700 or longer, and ≥ 2 EV+ books required |
| Matchup board | p_model | Unchanged (it worked), plus a market-implied column and a model-vs-market flag |
| Mismatch board | λ × R | Unchanged; add the P-6 multiplier |
| Parlay board | Empirical joint p | Joint p from p_final draws; keep quote-required gating |

### P-8 — Automated postgame grading module · Priority: MEDIUM

```text
module: audit/grade_week.py (new)
inputs: frozen handoff, results feed (box score), close snapshot (P-1)
outputs: per-board Brier/LL, quintile ROI table (§5.1), CLV by tier, reliability bins,
         rejection-reason outcome table (§6.5), as NFL_ATD_SCORER_AUDIT_<date>_W<wk>.md
```

---

## 9. Promotion Gates (walk-forward, minimum 8 slates)

A new model version is **not** promoted to capital use until all of these hold:

| Gate | Threshold |
|---|---|
| Brier on priced players | Model ≤ market (raw devig) |
| Log-likelihood ratio, model + market vs market | Model coefficient > 0 with p < 0.05 |
| Top-quintile CLV (from P-1) | Mean CLV ≥ +1.0 pp, with ≥ 55% of rows beating the close |
| Quintile monotonicity | Spearman(EV rank, ROI) > 0 across pooled slates; Q1 ROI ≥ Q3 ROI |
| Reliability | Each bin with n ≥ 50 within ±3 pp |
| 2+ TD calibration | Σ predicted within ±20% of realized |
| Coverage | ≥ 95% of offensive TD events scored by modeled players |

**Current status vs gates (this slate):** FAIL on Brier, LLR, quintile monotonicity, 2+ TD, and coverage. CLV is UNMEASURED. Reliability is a partial pass.

---

## 10. Calibration Ledger Entry (append to Dataset-B history)

```text
slate=2026-09-27 W3 | run=NFL-SCORER-2026-W03-20260927T150000Z-W3_SUN_DAY_0927 | model=0.4.0a1
players=415 | brier=0.0860 | logloss=0.2992 | sum_p=45.08 | sum_y=45 | sum_p2=4.41 | sum_y2=8
priced=259 | brier_model=0.1326 | brier_mkt=0.1272 | ll_model=0.4276 | ll_mkt=0.4059
quintile_roi=Q1 −38.8 | Q2 +24.7 | Q3 −12.2 | Q4 −29.3 | Q5 −52.7 | spearman_ev_pl=0.003
ev_board=1/22, −11.0u paper | sharp=0/12, −12.0u | mismatch=8/19 vs 5.70 | parlay=2/5 (not traded)
clv=CLOSE_DATA_GAP | coverage=54/65 | unpriced_mass=12.68→0 | settlement_flags=Price punt-return TD
```

---

## 11. Open Data Gaps

- Closing prices for all EV, sharp, and parlay rows (blocks CLV).
- Actual entries and stakes (blocks real P&L).
- Book house rules on return TDs (Myles Price settlement).
- Individual availability verification for most of the 415 modeled players.
- Executable parlay/SGP quotes.
- D/ST touchdown grading for ENTITY_FAILURE rows.

---

**Bottom line:** On the 2026-09-27 NFL slate, high-ranked model edge **did not** price correctly (top quintile: 12.7% model vs 5.8% actual) and **did not** outperform lower-ranked edge (Q1 −38.8% ROI vs Q2 +24.7%; Spearman 0.003). Whether it beat the close is **unmeasured** because no closing prices exist in the pipeline. The fix order is: (1) close capture, (2) market-anchored blending, (3) longshot shrinkage, (4) universe and starter-gate repair, (5) negative-binomial dispersion. Re-test against the promotion gates after 8 walk-forward slates.
