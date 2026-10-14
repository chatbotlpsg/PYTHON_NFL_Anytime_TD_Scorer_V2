# NFL Anytime TD Scorer — Grade & Audit User Input Prompt
## Slate: 2026-09-28 · Week 3 · MNF · PHI @ CHI

Copy everything inside the block below into the chat. Attach the files listed under ATTACHED.

```text
/grade-nfl-scorer-week
/build-nfl-scorer-recap

You are the AITA NFL Anytime Touchdown Scorer Trading Agent, running the
postgame grading and Dataset-B audit for the 2026-09-28 Week 3 MNF slate
(PHI @ CHI, Soldier Field, kickoff 2026-09-29 00:15Z).

======================================================================
ATTACHED
======================================================================

1. CONTROLLING handoff (Dataset A — frozen, immutable):
   NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W03_NFL-SCORER-2026-W03-20260928T215506Z-W3_MNF_0928_CASE_ERTZ_SCENARIO.zip
   run_id = NFL-SCORER-2026-W03-20260928T215506Z-W3_MNF_0928_CASE_ERTZ_SCENARIO
   model_version = 0.4.1a1 · sim_count = 500000

2. ARCHIVED handoff (comparison only — never grade decisions off it):
   NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W03_NFL-SCORER-2026-W03-20260928T213042Z-W3_MNF_0928_LATE.zip
   run_id = NFL-SCORER-2026-W03-20260928T213042Z-W3_MNF_0928_LATE
   model_version = 0.4.0a1

3. RESULTS (Dataset B — I supply):
   - Final score
   - Every offensive rushing/receiving TD scorer (player, team, TD type)
   - Any non-offensive TDs (return, fumble recovery, defensive) — listed separately
   - Confirmed actives/inactives (Caleb Williams OUT, Dallas Goedert OUT,
     Case Keenum CHI QB starter, Zach Ertz PHI TE starter)

4. ENTRIES (Dataset B — I supply; if blank, treat as NO ENTRY):
   - Straight scorer bets: player, book, entry price, stake, entry timestamp
   - Parlay/SGP bets: legs, book, quoted payout, stake, entry timestamp

5. CLOSE PRICES (Dataset B — I supply; if blank, write DATA GAP):
   - Closing / last-available anytime-TD price per player per book, with timestamp

======================================================================
HARD RULES
======================================================================

- Dataset A is frozen. Do NOT alter, rerun, re-rank, or "correct" any model
  probability, fair price, EV, buy-to, hard-stop, or joint probability.
- Never fabricate a result, scorer, closing price, entry, SGP payout, or timestamp.
  Missing → DATA GAP / NO ENTRY / CLOSE NOT CAPTURED.
- A winning bet is not automatically a good model read. A losing bet is not
  automatically a bad model read. Grade process and outcome separately.
- Passing TDs do not credit the passer (handoff scorer definition).
  Non-offensive TDs are graded as settlement events only, not model misses.
- Keep the probability board, EV board, sharp board, and parlay board graded
  separately.
- Apply my standing board rules: one player used once across the parlay card,
  full names with team in parentheses.

======================================================================
STEP 0 — GRADING HANDOFF CHECK
======================================================================

Print one line:

Grade check: run_id=[controlling run_id] | slate=2026-09-28 W3 MNF | results=[SUPPLIED/DATA GAP] | entries=[n] | closes=[SUPPLIED/PARTIAL/DATA GAP] | grade=[PASS/WARN/FAIL]

Confirm the result set matches the slate (PHI @ CHI only) and that every
scorer in the results maps to a player in the handoff or is flagged
UNMODELED_SCORER.

======================================================================
STEP 1 — SCORER RESULT LEDGER
======================================================================

| Player | Team | Pos | Model ATD % (controlling) | Model ATD % (archived) | Scored? | TDs | TD Type | 2+ TD Hit? |
|---|---|---|---:|---:|---|---:|---|---|

Include every player on the controlling slate probability board (12 rows),
plus any actual scorer not on the board (flag UNMODELED_SCORER, and state
whether they were starter-gated out, unpriced, or absent from the handoff).

======================================================================
STEP 2 — PROBABILITY BOARD GRADE (calibration, not betting)
======================================================================

Using the 12 controlling slate-board rows:

- Brier score and log loss for anytime-TD probabilities
- Same metrics for the archived run's comparable rows
- Expected scorers (sum of model probabilities) vs actual scorer count
- Reliability buckets: 30%+, 20–30%, 10–20%, <10% — expected vs actual hit rate
- Team-level check: model mean team TDs (CHI 2.62 / PHI 2.15) vs actual
  offensive TDs by team

One-sample caveat required: a single game is not calibration evidence on its
own; record it for the rolling Dataset-B sample.

======================================================================
STEP 3 — OVERRIDE & DEFECT AUDIT (required this slate)
======================================================================

Grade the two defects flagged at trade time:

A. GENERIC-PRIOR DEFECT — Case Keenum (12.5%) and Zach Ertz (9.2%) were priced
   from CURRENT_DEPTH_POSITION_PRIOR (0 games observed), not their own history.
   - Did Keenum score? Did Ertz score?
   - Was the QUARANTINE on Keenum's +76.7% EV correct process?
   - Record the outcome without using it to "validate" or "refute" the prior.

B. TEAM-TOTAL CARRYOVER DEFECT — CHI team scoring (27.0 pts / 2.62 TDs) was not
   reduced for the Caleb → Keenum change.
   - Actual CHI points and offensive TDs vs the model's 27.0 / 2.62
   - Did CHI pass-catcher TD output (Odunze, Loveland, Burden, Raymond)
     support or contradict the overstatement concern?

C. AVAILABILITY REDISTRIBUTION — Goedert's share moved to Smith, Wicks,
   Barkley, Covey. Grade whether the PHI redistribution looked directionally
   right.

Output a short Python fix-ticket status:
- Fix 1: ESPN→GSIS history mapping for override players (Keenum 15168, Ertz 15835)
- Fix 2: QB starter override must recompute team scoring + game context
Mark each STILL OPEN / EVIDENCE SUPPORTS / EVIDENCE NEUTRAL.

======================================================================
STEP 4 — STRAIGHT EV BOARD GRADE
======================================================================

| Player | Team | Book | Frozen Ref Price | Agent Status | Entry Price | Close Price | Price Move | CLV | Result | Stake | P&L |
|---|---|---|---:|---|---:|---:|---|---|---|---:|---:|

Rows to grade:
- Rome Odunze (Chicago Bears) — DK +500 PLAY-eligible at reduced stake
  (agent-tightened buy-to +467); BR +440 / FD +430 WATCH
- Britain Covey (Philadelphia Eagles) — FD +2700 WATCH, lotto-size only
- Case Keenum (Chicago Bears) — QUARANTINE
- Colston Loveland (Chicago Bears) — PASS, +4.0% below 6% floor

CLV rules:
- CLV = entry implied probability vs close implied probability, reported in pp
  and as % price change.
- Close only from supplied timestamped evidence. Otherwise CLOSE NOT CAPTURED.
- Do not overwrite frozen reference prices.

Also grade the Odunze stress test: did the price survive to kickoff at ≥ +467?

======================================================================
STEP 5 — SHARP BOARD GRADE
======================================================================

Grade each sharp-board call (PLAY / WATCH / QUARANTINE / PASS) on process:
- Was the classification consistent with the information at trade time?
- Did the close move toward or away from the sharp read?
- Outcome recorded separately from process grade.

Process grade scale: A (correct process, clean execution) → F (gate violated).

======================================================================
STEP 6 — PARLAY CARD GRADE
======================================================================

| # | Legs | Empirical Joint P | Fair Odds | Min Quote | Actual Quote | Entered? | Legs Hit | Result | P&L |
|---|---|---:|---:|---:|---:|---|---|---|---:|

Card:
A. Rome Odunze (Chicago Bears) + Saquon Barkley (Philadelphia Eagles) — 7.60%, fair +1216, min +1322
B. D'Andre Swift (Chicago Bears) + DeVonta Smith (Philadelphia Eagles) — 5.89%, fair +1598, min +1734
C. Colston Loveland (Chicago Bears) + Jalen Hurts (Philadelphia Eagles) — 4.17%, fair +2299, min +2491

Rules:
- If no SGP quote was captured, the row stays NOT YET TRADEABLE; grade the
  joint-probability math only (did the combination hit?).
- If a quote was captured, compute EV at entry:
  EV per $1 = p_joint × profit_per_dollar(quote) − (1 − p_joint)
- Also report how the top 3 joint pairs and top 3 joint triples resolved.

======================================================================
STEP 7 — SLATE SCORECARD
======================================================================

| Board | Grade | Key Evidence |
|---|---|---|
| Probability board | | |
| EV board | | |
| Sharp board | | |
| Parlay math board | | |
| Market-price / CLV | | |
| Override handling | | |

Plus: total stake, total P&L, ROI, number of bets with positive CLV.

======================================================================
STEP 8 — DATASET-B RECAP FILE (downloadable .md)
======================================================================

Create ONE downloadable Markdown file for this league and this slate only
(do not merge with any other league or slate):

NFL_ANYTIME_TD_SCORER_RECAP_2026-09-28_W3_MNF.md

Sections:
1. Slate Metadata (both run_ids, model versions, handoff timestamps, overrides)
2. Frozen Python Outputs (top probability scorers, EV candidates, sharp
   candidates, parlay card, rejections — as frozen)
3. Actual Entries (straight, parlay/SGP, overrides, timestamps)
4. Closing Price Audit (entry, close, movement, CLV, source)
5. Results (scorers, settlement, P&L)
6. Board Grades (probability, EV, sharp, parlay, market-price, override handling)
7. Defect & Fix-Ticket Log (generic prior, team-total carryover)
8. Lessons for Calibration — evidence only; no retroactive change to Dataset A

======================================================================
FINAL LINE
======================================================================

Bottom line: [scorers hit / modeled], [EV entries won-lost, P&L, ROI],
[CLV +/− count], [parlays entered/hit], and whether the trade-time
quarantines and gates held up on process.
```
