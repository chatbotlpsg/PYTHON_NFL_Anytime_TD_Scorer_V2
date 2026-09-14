# AITA NFL 2026 Opportunity-First Prop Pipeline
## Data Sourcing, Modeling, Odds-Quota Management, Monte Carlo, EV, Boards, and Trading-Agent Handoff

**Status:** Architecture / coding-agent build specification  
**Season:** NFL 2026  
**Primary objective:** Build a Python pricing pipeline that finds sustainable expected-value opportunities in NFL player opportunity/volume markets, then exports an immutable ZIP for a separate Claude trading agent.  
**Core doctrine:** **Model opportunity first. Model production second. Price the market third. Trade outside Python.**

---

# 0. Executive Decision

The NFL V1 project should **not** attempt to model every sportsbook market.

The project should be concentrated around the markets closest to player opportunity because these are the markets where the causal chain is shortest and where changing player roles, coaching decisions, game script, and personnel can create mispricing.

## V1 Alpha Hierarchy

### Tier A1 — Flagship Opportunity Markets

1. **WR/TE receptions**
2. **RB rushing attempts**
3. **QB pass attempts**

### Tier A2 — Core Opportunity Derivatives

4. **QB pass completions**
5. **RB receptions**

### Tier B — Production Markets Generated From the Same Opportunity Engine

6. **WR/TE receiving yards**
7. **RB rushing yards**
8. **QB passing yards**
9. **RB receiving yards**

### Context / Anchor Markets

10. Full-game moneyline
11. Full-game spread
12. Full-game total

The mainline markets are **not the primary alpha objective**. They are used as high-information market anchors, game-script references, sanity checks, and calibration challengers.

The system should ultimately answer:

> What football state is most likely, what opportunity does that state create for each player, what distribution of player outcomes follows, what is the fair price of the sportsbook proposition, and is the posted market price sufficiently wrong after uncertainty is penalized?

The causal chain is:

```text
TEAM STATE
    ↓
PERSONNEL STATE
    ↓
GAME STATE
    ↓
EXPECTED PLAYS
    ↓
PASS / RUN DECISION PROCESS
    ↓
PLAYER OPPORTUNITY
    ↓
PLAYER PRODUCTION
    ↓
MONTE CARLO DISTRIBUTION
    ↓
FAIR PROBABILITY
    ↓
FAIR ODDS
    ↓
SPORTSBOOK PRICE
    ↓
EV%
    ↓
UNCERTAINTY HAIRCUT
    ↓
CONSERVATIVE EV%
    ↓
CORRELATION / THESIS OPTIMIZER
    ↓
FINAL BOARDS
    ↓
TRADING-AGENT HANDOFF ZIP
    ↓
PYTHON ENDS
```

---

# 1. Critical Data-Source Decision

## Do not use ESPN as the sole NFL modeling database.

ESPN should be an important **current-state and enrichment provider**, but not the sole historical modeling provider.

The recommended architecture is:

```text
NFLVERSE / NFLREADPY
    = historical modeling backbone

ESPN JSON ENDPOINTS
    = current-state operational / enrichment / QA layer

NWS / API.WEATHER.GOV
    = weather layer

THE ODDS API
    = current market-pricing layer

LOCAL AITA DATA STORE
    = normalized source of truth used by models
```

This separation is mandatory.

## Why

A serious NFL pricing system needs:

- play-by-play history,
- weekly player statistics,
- team statistics,
- snap counts,
- player participation,
- rosters,
- weekly rosters,
- injuries,
- depth charts,
- advanced player statistics,
- schedule and result history,
- live/current roster state,
- current injuries,
- current depth charts,
- current game schedule,
- weather,
- sportsbook odds.

No one free source should be trusted to provide all of these at the required quality and stability.

---

# 2. ESPN: What We Should Use It For

ESPN exposes JSON endpoints used by its sports products. They are extremely useful for this project because they provide no-auth current NFL data in a consistent cross-sport style.

However:

> **Treat ESPN's JSON endpoints as undocumented/unsupported interfaces, not as a guaranteed official developer API contract.**

Therefore the coding agent must place ESPN behind a provider adapter and never allow the rest of the model to depend directly on raw ESPN JSON structure.

## Recommended ESPN NFL endpoints

Base family:

```text
https://site.api.espn.com/apis/site/v2/sports/football/nfl/
```

### Weekly scoreboard / slate

```text
scoreboard
scoreboard?week={WEEK}&seasontype=2
```

Use for:

- NFL event IDs,
- current week,
- game dates,
- home/away teams,
- game status,
- final scores,
- slate construction,
- schedule QA.

### All teams

```text
teams
```

Use for:

- ESPN team IDs,
- abbreviations,
- display names,
- logos if desired,
- canonical team mapping.

### Team roster

```text
teams/{team_id}/roster
```

Use for:

- active roster state,
- player ESPN IDs,
- positions,
- current team assignments.

### Team depth chart

```text
teams/{team_id}/depthcharts
```

Use for:

- QB order,
- RB depth,
- WR/TE depth,
- current depth hierarchy,
- role-change detection.

### Team injuries

```text
teams/{team_id}/injuries
```

and/or league-wide:

```text
injuries
```

Use for:

- injury status,
- affected player,
- injury description/status,
- current availability state.

### Transactions

```text
transactions
```

Use for:

- signing,
- waiver,
- release,
- roster movement,
- rapid Week 1 / in-season roster changes.

### Team schedule

```text
teams/{team_id}/schedule
```

Use as schedule cross-check only. Do not make 32 separate schedule calls if the scoreboard already provides the required current slate.

### Game summary

```text
summary?event={espn_event_id}
```

Use for:

- box score,
- leaders,
- game-level details,
- current-game QA,
- final result enrichment.

Do **not** use ESPN game summary as the historical play-by-play backbone when nflverse already gives us a purpose-built historical dataset.

---

# 3. ESPN Must Be Isolated Behind a Provider Interface

The coding agent should create something conceptually equivalent to:

```text
providers/
    espn/
        client.py
        schemas.py
        normalize.py
        endpoints.py
        health.py
```

The rest of the pipeline should call internal methods such as:

```python
get_weekly_slate()
get_teams()
get_rosters()
get_depth_charts()
get_injuries()
get_transactions()
get_game_summary()
```

The model should never scatter raw ESPN URLs throughout feature code.

## Required ESPN controls

Every ESPN fetch must:

1. timestamp the request,
2. save raw JSON,
3. hash the payload,
4. validate expected top-level structure,
5. normalize into internal tables,
6. record provider health,
7. retry transient failures,
8. fail gracefully if a non-critical ESPN endpoint changes.

Example raw storage:

```text
data/raw/espn/2026/week_01/
    scoreboard_2026-09-XXT120000Z.json
    teams_2026-09-XXT120005Z.json
    roster_KC_2026-09-XXT120010Z.json
    injuries_KC_2026-09-XXT120011Z.json
    ...
```

Do not overwrite previous snapshots.

---

# 4. NFLVERSE / NFLREADPY Is the Historical Modeling Backbone

The preferred historical source is `nflreadpy`, the Python interface into nflverse datasets.

This should supply the bulk of the historical research state.

## Required nflreadpy datasets

### Play-by-play

```python
load_pbp()
```

Use to build:

- EPA/play,
- success rate,
- offensive pace,
- pass rate,
- neutral pass rate,
- score-state tendencies,
- down/distance tendencies,
- third-down behavior,
- red-zone behavior,
- explosive play rates,
- sacks,
- scrambles,
- pressure-compatible derived features where available,
- drive outcomes,
- field position,
- game-state transitions.

### Player game/season statistics

```python
load_player_stats()
```

Use for:

- attempts,
- completions,
- passing yards,
- rushing attempts,
- rushing yards,
- targets,
- receptions,
- receiving yards,
- touchdowns,
- player weekly histories.

### Team statistics

```python
load_team_stats()
```

Use for:

- team offense and defense baselines,
- recent rolling states,
- opponent adjustments.

### Schedules

```python
load_schedules()
```

Use for:

- historical game identities,
- home/away,
- dates,
- outcomes,
- rest,
- travel sequencing,
- season/week indexing.

### Rosters

```python
load_rosters()
load_rosters_weekly()
```

Use for:

- historical player-team assignments,
- weekly roster state,
- injury/status changes,
- player ID mapping.

### Snap counts

```python
load_snap_counts()
```

Use for:

- offensive snap share,
- defensive snap share,
- weekly role persistence,
- sudden role expansion/contraction.

### Participation

```python
load_participation()
```

Use for:

- play-level involvement,
- historical player participation,
- better route/role inference where fields allow,
- personnel-conditioned opportunity analysis.

### Injuries

```python
load_injuries()
```

Use for:

- historical injury designations,
- practice participation,
- injury-related role transitions.

### Depth charts

```python
load_depth_charts()
```

Use for:

- historical depth hierarchy,
- role priors,
- replacement-player logic.

### Next Gen Stats-derived data

```python
load_nextgen_stats()
```

Use when additive for:

- QB passing characteristics,
- receiving efficiency,
- rushing behavior.

### PFR advanced statistics

```python
load_pfr_advstats()
```

Use as an advanced-stat enrichment layer where appropriate.

### FTN charting

```python
load_ftn_charting()
```

Use only if licensing, schema, and historical coverage are acceptable for the project.

---

# 5. Source-of-Truth Matrix

The coding agent should implement explicit precedence.

| Data | Primary | Secondary / QA | Notes |
|---|---|---|---|
| Current weekly slate | ESPN scoreboard | nflverse schedules | ESPN operational source |
| Historical schedules/results | nflverse | ESPN | nflverse backbone |
| Current rosters | ESPN roster | nflverse weekly rosters | reconcile conflicts |
| Historical rosters | nflverse | ESPN where available | historical model |
| Current depth charts | ESPN | nflverse depth charts | cache frequently during role-change weeks |
| Historical depth charts | nflverse | — | priors |
| Current injuries | ESPN | nflverse injuries | latest status critical |
| Historical injuries | nflverse | — | training/role priors |
| Historical PBP | nflverse | ESPN summary only QA | never depend on ESPN for historical PBP |
| Snap counts | nflverse | ESPN box score if useful | key role input |
| Participation | nflverse | — | key player role input |
| Current final score | ESPN | The Odds API scores / nflverse later | rapid grading |
| Current sportsbook prices | The Odds API | manual trading-agent verification | archive every response |
| Historical odds | AITA local archive | paid provider later | free Odds API does not provide historical |
| Weather | NWS API | stadium roof configuration | outdoor games only |
| Stadium / roof metadata | local static table | ESPN venue | version-controlled |

---

# 6. Internal Entity Resolution Is Mandatory

Never join sources by player display name alone.

We will have:

- ESPN team ID,
- ESPN athlete ID,
- nflverse player ID,
- GSIS ID,
- external sportsbook player description,
- internal AITA player ID.

Build:

```text
entity_map_team
entity_map_player
entity_map_event
```

## Internal player identity

Example columns:

```text
aita_player_id
full_name
normalized_name
position
current_team
espn_athlete_id
gsis_id
nflverse_id
pfr_id
birth_date
active_flag
last_verified_at
```

## Internal team identity

```text
aita_team_id
team_abbr
team_name
espn_team_id
nflverse_team_abbr
odds_api_team_name
```

## Internal event identity

```text
aita_event_id
season
week
kickoff_utc
home_team_id
away_team_id
espn_event_id
odds_api_event_id
```

### Rule

If a player cannot be resolved uniquely:

```text
STATUS = ENTITY_QUARANTINE
```

Do not silently guess.

---

# 7. Weather Layer

Use the National Weather Service API for outdoor games.

Base:

```text
https://api.weather.gov
```

Maintain a local stadium table:

```text
stadium_id
stadium_name
latitude
longitude
roof_type
surface
team
```

For outdoor or retractable-roof games expected to be open, capture:

- temperature,
- wind speed,
- wind gust,
- precipitation probability,
- precipitation type if available,
- humidity if useful,
- severe-weather alerts.

## Weather logic

```text
DOME / CLOSED ROOF
    → weather impact = 0

RETRACTABLE / UNKNOWN
    → status flag

OUTDOOR
    → NWS forecast
```

Weather should mainly influence:

- pass efficiency,
- completion probability,
- deep passing,
- kicking/field position,
- potentially pace,
- total scoring distribution.

Do not overfit small weather effects.

Wind should receive more attention than generic “bad weather” narratives.

---

# 8. The Odds API — Exact V1 Market Plan

The Odds API is used **only for market pricing**.

Current sport key:

```text
americanfootball_nfl
```

## Featured mainline markets

Use the standard league odds endpoint:

```text
h2h
spreads
totals
```

These three can be retrieved for the NFL slate in one call.

Recommended bookmakers:

```text
draftkings
fanduel
betrivers
```

These are three bookmakers, which fit inside one equivalent bookmaker-region group for quota purposes.

The Odds API currently treats each group of up to 10 explicitly requested bookmakers as the equivalent of one region.

## Primary player opportunity market keys

We actually need only **four unique API market keys** for the five flagship families because one reception market contains WR, TE, and RB reception props.

```text
player_receptions
player_rush_attempts
player_pass_attempts
player_pass_completions
```

These cover:

- WR receptions,
- TE receptions,
- RB receptions,
- RB rushing attempts,
- QB passing attempts,
- QB completions.

## Secondary production market keys

```text
player_reception_yds
player_rush_yds
player_pass_yds
```

Total V1 prop keys if every opportunity + production market is requested:

```text
7 unique player markets
```

Do **not** request TD markets, longest-play markets, defensive props, alternate markets, or SGP markets in V1.

---

# 9. The Odds API Free-Plan Constraint

As verified on 2026-08-29:

```text
Starter plan price = $0/month
Starter quota      = 500 credits/month
```

Historical odds are not available on the free plan.

Therefore we must behave like a constrained trading desk.

## Current quota mechanics

For event odds:

```text
usage cost =
number of unique markets returned
×
number of bookmaker regions/equivalent bookmaker groups
```

When explicitly requesting up to 10 bookmakers:

```text
equivalent regions = 1
```

Therefore:

```text
4 opportunity markets × 1 group
= max 4 credits per game
```

and:

```text
7 all-V1 player markets × 1 group
= max 7 credits per game
```

For a full 16-game slate:

```text
4 opportunity markets:
16 × 4 = 64 credits maximum
```

Full V1 opportunity + yardage:

```text
16 × 7 = 112 credits maximum
```

Mainline NFL h2h/spreads/totals via the normal `/odds` endpoint:

```text
3 markets × 1 group = 3 credits
```

for the entire returned NFL slate, not 3 credits per event.

That distinction is critical.

---

# 10. Credit-Conservation Strategy

The model should have a dedicated:

```text
ODDS QUOTA GOVERNOR
```

No Odds API call should happen directly from modeling code.

All calls pass through:

```text
providers/odds_api/quota.py
```

## Mandatory quota ledger

Store:

```text
timestamp
endpoint
event_id
markets_requested
markets_returned
bookmakers
estimated_cost
actual_last_request_cost
requests_used
requests_remaining
request_hash
response_hash
```

Read these response headers after every call:

```text
x-requests-remaining
x-requests-used
x-requests-last
```

## Hard rule

If:

```text
remaining_credits < configured_safety_reserve
```

the pipeline must refuse non-essential pulls.

Suggested monthly safety reserve:

```text
100 credits
```

Adjust after real usage is observed.

---

# 11. The Free-Plan Weekly Odds Workflow

## Stage 0 — No-Odds Modeling

Monday / early week:

Run all football-data ingestion and modeling with **zero Odds API credits**.

Build:

- slate,
- current roster state,
- injuries,
- depth charts,
- team ratings,
- player role priors,
- preliminary opportunity distributions,
- preliminary production distributions.

The model should already know which games/players are potentially interesting **before spending prop credits**.

## Stage 1 — Mainline Anchor Pull

Pull:

```text
h2h
spreads
totals
```

for:

```text
draftkings,fanduel,betrivers
```

Maximum normal cost:

```text
3 credits
```

Use mainlines to create:

- market-implied game strength,
- market-implied total environment,
- market disagreement diagnostics,
- market priors for game-state calibration.

## Stage 2 — Full-Slate Opportunity Pull

Near the first serious execution window, pull only:

```text
player_receptions
player_rush_attempts
player_pass_attempts
player_pass_completions
```

for each active event.

Maximum 16-game cost:

```text
64 credits
```

This is the flagship pricing scan.

## Stage 3 — Shortlist

After comparing opportunity props with the simulation:

```text
identify candidate games/players first
```

Only then request production markets for those shortlisted events:

```text
player_reception_yds
player_rush_yds
player_pass_yds
```

Example:

```text
6 shortlisted games × 3 markets = 18 credits max
```

## Stage 4 — Reprice Only Candidates

Before ZIP generation, re-query **only the exact candidate event/market combinations that remain actionable**.

Example:

```text
6 games × average 2 candidate market families
≈ 12 credits
```

A typical controlled week can therefore look like:

```text
Mainlines                   3
Opportunity full slate     64
Targeted yardage           18
Candidate reprice          12
--------------------------------
Approx weekly total        97 credits
```

Four such weeks:

```text
388 credits
```

leaving roughly:

```text
112-credit reserve
```

under a 500-credit monthly plan.

Actual usage can be lower because the API charges event-odds requests based on unique markets actually returned, and empty data does not consume usage.

---

# 12. Do Not Poll The Odds API

The free plan must **not** be used as a pseudo-live odds feed.

Never:

```text
poll every 5 minutes
poll every 15 minutes
refresh entire slate after every model run
request all player markets repeatedly
```

Instead:

```text
MODEL FIRST
MARKET SECOND
REPRICE ONLY WHAT MATTERS
```

This is a core architectural rule.

---

# 13. Avoid Wasting Credits on Market Discovery

The Odds API offers an event-markets endpoint that costs a credit per event.

On the free plan, we should generally avoid spending 16 credits simply asking what markets exist.

Instead request the known fixed V1 market keys directly.

Because empty responses do not count toward usage and the event-odds cost is based on unique markets returned, this is usually more quota-efficient for our fixed market universe.

Only use the event-markets endpoint in diagnostics or when provider behavior changes.

---

# 14. Cache Every Odds Response

Historical Odds API endpoints are unavailable on the free plan.

Therefore:

> AITA must create its own historical odds archive from Day 1.

Every odds response is valuable research data.

Save raw JSON before normalization.

Example:

```text
data/raw/odds_api/2026/week_01/
    mainlines_20260908T180000Z.json
    event_<id>_opportunity_20260909T140000Z.json
    event_<id>_reprice_20260909T163000Z.json
```

Normalized snapshots:

```text
market_snapshot
```

Columns:

```text
snapshot_id
snapshot_time_utc
aita_event_id
bookmaker
market_key
player_id
player_name_raw
side
line
american_odds
decimal_odds
last_update
source_response_hash
```

This becomes our future:

- entry-line history,
- line-movement database,
- CLV database,
- market-efficiency research set,
- model-vs-market training source.

---

# 15. Request Deduplication

The quota governor must compute a deterministic request fingerprint.

Example fingerprint inputs:

```text
endpoint
sport
event_id
sorted(markets)
sorted(bookmakers)
odds_format
```

If the same request was made within the configured TTL, use the cached response unless explicitly forced.

Suggested default:

```text
odds_cache_ttl_minutes = 30
```

For final execution repricing:

```text
force_refresh = true
```

only on shortlisted candidate markets.

---

# 16. Dry-Run Cost Estimator

Before hitting The Odds API, support:

```bash
python -m nfl_model odds-plan --season 2026 --week 1
```

Output:

```text
Events: 16
Opportunity markets: 4
Bookmaker groups: 1

Expected max opportunity cost: 64 credits
Mainline cost: 3 credits
Secondary shortlisted allowance: 18 credits
Reprice allowance: 12 credits

Planned max: 97
Current remaining: 500
Post-run projected remaining: 403

STATUS: APPROVED
```

If projected usage violates reserve:

```text
STATUS: BLOCKED_BY_QUOTA_GOVERNOR
```

---

# 17. Football Data Refresh Cadence

## Mostly static

Refresh weekly or when season begins:

- team metadata,
- stadium metadata,
- team ID maps.

## Early week

Refresh:

- weekly slate,
- team rosters,
- transactions,
- depth charts,
- injuries.

## Daily / before production run

Refresh:

- injuries,
- roster,
- depth chart,
- transactions,
- weather,
- slate status.

## Final model run

Refresh immediately before pricing:

- injuries,
- depth chart,
- weather,
- market prices.

ESPN calls do not consume The Odds API quota, but we should still cache and behave politely.

---

# 18. Week 1 Requires a Special Data Policy

Week 1 is not Week 10.

The pipeline must recognize:

- new quarterbacks,
- rookies,
- new coordinators,
- new offensive systems,
- changed offensive lines,
- new RB committees,
- changed WR rooms,
- changed depth charts,
- preseason ambiguity,
- limited current-season samples.

## Week 1 modeling priority

Use:

```text
historical player/team priors
+
current roster
+
current depth chart
+
coordinator priors
+
preseason usage information where reliable
+
injury state
+
market anchor
```

Do not let small preseason box-score samples overpower stable priors.

## Role uncertainty

Every player role should be a distribution.

Example:

```text
WR route participation:
P10     72%
Median  84%
P90     93%
```

RB backfield share:

```text
P10     49%
Median  62%
P90     74%
```

A Monte Carlo draw should sample role uncertainty rather than treating role as known.

---

# 19. Canonical Weekly Data Tables

The normalized layer should include at minimum:

```text
dim_team
dim_player
dim_stadium
dim_event

fact_schedule
fact_roster_snapshot
fact_depth_chart_snapshot
fact_injury_snapshot
fact_transaction_snapshot
fact_weather_snapshot

fact_pbp
fact_player_game
fact_team_game
fact_snap_count
fact_participation

fact_market_snapshot
```

Derived state:

```text
team_state
player_role_state
qb_state
rb_state
receiver_state
matchup_state
game_state_prior
```

Model outputs:

```text
game_sim_summary
player_opportunity_sim_summary
player_production_sim_summary
market_price
ev_price
correlation_matrix
thesis_cluster
```

---

# 20. Team-State Layer

Build time-decayed team states.

## Offensive state

At minimum:

```text
epa_per_play
success_rate
early_down_epa
early_down_success
neutral_pass_rate
pace
plays_per_game
third_down_rate
red_zone_td_rate
explosive_pass_rate
explosive_run_rate
sack_rate_allowed
turnover_rate
```

## Defensive state

```text
epa_allowed_per_play
success_rate_allowed
early_down_epa_allowed
pass_epa_allowed
rush_epa_allowed
pressure-compatible indicators
sack_rate
explosive_pass_allowed
explosive_run_allowed
third_down_defense
red_zone_defense
```

## Time decay

Recent information matters more.

Conceptually:

```math
weight(age) = exp(-lambda * age)
```

Do not use a simple current-season average when richer rolling state is available.

---

# 21. QB-State Layer

QB state should be separate from team offense.

Core variables:

```text
dropbacks
attempt_rate
completion_rate
CPOE-type measures where available
EPA/dropback
yards/attempt
air yards
deep attempt rate
sack rate
scramble rate
designed rush rate
pressure performance
turnover rate
```

QB uncertainty increases for:

- rookies,
- first starts,
- injury returns,
- changed teams,
- changed coordinators.

---

# 22. Coaching / Philosophy Layer

Track:

```text
head_coach
offensive_coordinator
defensive_coordinator
```

and offensive tendencies such as:

```text
neutral_pass_rate
pass_rate_over_expected
early_down_pass_rate
pace
no_huddle
red_zone_pass_rate
leading_run_rate
trailing_pass_rate
fourth_down_aggressiveness
```

For a coordinator change:

```text
team historical tendency
```

must be partially shrunk toward:

```text
new coordinator historical tendency
```

with uncertainty.

---

# 23. Game-State Engine

The player model starts with the game.

Build distributions for:

```text
home_points
away_points
margin
total
home_win
away_win
team_offensive_plays
team_drives
```

The model should operate at a drive or possession/game-state level, not merely independent final-score regressions.

Key state:

```text
quarter
clock
score_difference
field_position
possession
timeouts if modeled
offense
defense
```

Possible drive outcomes:

```text
TD
FG
punt
turnover
turnover_on_downs
safety
end_half
```

---

# 24. Opportunity Engine: Team Plays

First price the number of offensive opportunities.

Model:

```math
TeamPlays =
f(
pace,
first_down_rate,
third_down_conversion,
turnovers,
opponent,
game_script,
clock_state
)
```

Output distribution:

```text
P10
P25
median
mean
P75
P90
```

Player opportunity cannot be trusted if team play volume is wrong.

---

# 25. Opportunity Engine: Pass / Run

For each simulation state:

```math
P(pass) =
f(
team_tendency,
score_state,
quarter,
down,
distance,
opponent,
coach,
QB,
time_remaining
)
```

Pass rate must change with game script.

Example concept:

```text
trailing materially:
pass tendency ↑

neutral:
baseline

leading materially late:
run tendency ↑
```

Do not hard-code universal percentages. Learn team/coach-conditioned effects from historical PBP and shrink where samples are limited.

---

# 26. QB Pass Attempts

Start from dropbacks:

```math
Dropbacks = offensive passing-play opportunities
```

Then:

```math
PassAttempts =
Dropbacks
-
Sacks
-
Scrambles
-
other non-attempt dropback outcomes
```

Mobile QBs require explicit scramble treatment.

Output:

```text
mean attempts
median attempts
attempt distribution
P(attempts > each sportsbook line)
```

---

# 27. RB Rushing Attempts

Do not model one generic RB share.

Track separate role shares:

```text
early_down_share
short_yardage_share
goal_line_share
two_minute_share
passing_down_share
```

Then:

```math
RBCarries =
sum over simulated rush opportunities
P(RB receives carry | state)
```

The biggest carry drivers:

```text
team rush volume
score state
backfield share
short-yardage role
goal-line role
QB rush behavior
coach tendencies
```

---

# 28. Receiver Route Engine

For WR/TE props, route participation matters more than raw snap percentage.

Core state:

```math
RouteParticipation =
RoutesRun / TeamDropbacks
```

Build role estimates by player and personnel grouping where possible.

Possible labels:

```text
WR1
WR2
WR3/slot
outside
slot
TE1
move_TE
blocking_TE
```

The role engine should estimate:

```text
route_share_distribution
```

rather than one fixed number.

---

# 29. Target Engine

For each route:

```math
P(Target | Route)
```

conditioned on:

```text
player target-rate prior
QB tendencies
coverage/matchup
route role
target depth
game script
personnel
other active receivers
injuries
```

When another target-earner is absent, target redistribution must not be naïve.

Do not simply divide missing targets equally.

Use historical and archetype-based redistribution.

---

# 30. Catch Engine

For each simulated target:

```math
P(Catch | Target)
```

conditioned on:

```text
QB
receiver
target depth
coverage
pressure/game environment
weather
```

Then:

```math
Receptions =
sum Bernoulli(Catch)
```

This produces a natural reception distribution.

---

# 31. Primary Reception Markets

The same `player_receptions` API market prices:

- WR receptions,
- TE receptions,
- RB receptions.

This is quota-efficient.

The model must classify each player by position and route role.

For each line:

```text
Over X.5
Under X.5
```

calculate directly from the simulation distribution.

Example:

```math
P(Over 4.5) = P(Receptions >= 5)
```

---

# 32. Production Engine Comes After Opportunity

Only after opportunity is calibrated should the model generate yards.

## Receiving

Conceptually:

```text
route
→ target?
→ target depth
→ catch?
→ YAC
→ receiving yards
```

Prefer:

```math
ReceivingYards = AirYards + YAC
```

over a simplistic average yards-per-reception multiplier.

## Rushing

Simulate rush outcomes from a heavy-tailed gain distribution conditioned on:

```text
RB
offensive line
opponent run defense
down/distance
score state
QB threat
```

## Passing

Passing yards emerge from completed target outcomes.

This automatically ties QB and receiver outcomes together.

---

# 33. Why Joint Simulation Matters

A single simulation should generate:

```text
QB attempts
QB completions
QB passing yards

RB carries
RB rushing yards
RB targets
RB receptions
RB receiving yards

WR routes
WR targets
WR receptions
WR receiving yards
```

from the same game state.

Therefore correlations are structural rather than guessed.

Example:

```text
QB attempts over
WR1 receptions over
WR1 yards over
```

are naturally correlated because they share the same simulated passing environment.

---

# 34. Monte Carlo Design

The simulator should eventually target enough draws for stable probability estimates, but simulation count must be justified by convergence.

Start with:

```text
50,000
```

development draws.

Production goal:

```text
100,000–500,000
```

if runtime is acceptable.

## Convergence gate

For each priced market compare estimated probabilities at:

```text
25k
50k
100k
200k
```

Do not increase draw count if fair probabilities are already stable within the target tolerance.

---

# 35. Parameter Uncertainty Must Be Simulated

Do not only simulate football randomness.

Also simulate uncertainty in inputs.

Example per simulation:

```text
sample player route share
sample RB backfield share
sample team pace
sample pass tendency
sample target rate
sample catch probability
sample efficiency parameters
```

This is how Week 1 uncertainty propagates into the final EV.

---

# 36. Four Probability Layers

Every sportsbook proposition should have:

## Raw Monte Carlo probability

```text
p_raw
```

## Calibrated probability

```text
p_calibrated
```

After historical reliability correction.

## Blended probability

```text
p_blend
```

After appropriate market anchoring.

## Conservative probability

```text
p_conservative
```

After uncertainty penalty.

These should never be collapsed into one undocumented “model probability.”

---

# 37. Market Anchoring

Mainline spread/total markets are efficient information sources.

Use vig-free market information as an anchor for the game environment.

Conceptually:

```math
p_blend =
w_model * p_model
+
w_market * p_market
```

but do not use a single universal weight.

Market weight should depend on:

```text
market type
liquidity
historical model calibration
historical CLV
model disagreement
season/week uncertainty
```

Player props should generally receive less market anchoring than NFL mainlines if our role/opportunity engine is proven to add information.

---

# 38. Market Trust Score

Create an empirically learned:

```text
market_trust_score
```

Initial values are placeholders only.

Example concept:

```text
spread                  high
total                   high
QB passing yards        medium-high
WR receiving yards      medium
WR receptions           medium
RB rushing attempts     medium
```

The score must later be updated from:

- CLV,
- calibration,
- realized ROI,
- sample size.

---

# 39. EV Engine

For American odds convert to decimal payout and calculate expected value per dollar risked.

For a proposition with net profit `b` per $1 risked:

```math
EV = p_true * b - (1 - p_true)
```

```math
EV% = 100 * EV
```

Calculate separately:

```text
raw_ev_pct
calibrated_ev_pct
blend_ev_pct
conservative_ev_pct
```

The primary ranking metric is:

```text
conservative_ev_pct
```

not raw EV.

---

# 40. No-Vig Logic

When both Over and Under prices are available from the same bookmaker/line:

1. convert both to raw implied probabilities,
2. remove vig,
3. calculate a vig-free market probability,
4. compare model probability against fair market probability,
5. preserve the actual payout price for EV computation.

Store both:

```text
market_raw_implied_prob
market_novig_prob
```

---

# 41. Extreme-Disagreement Guardrail

If model and market disagree beyond a configurable threshold:

```text
EXTREME_MODEL_MARKET_DISAGREEMENT
```

Do not automatically call it the best bet.

Run checks:

```text
player identity correct?
line correct?
side correct?
roster current?
injury state current?
depth chart current?
role estimate reasonable?
book market stale?
simulator bug?
unit conversion correct?
```

Only after passing validation can the row return to the board.

---

# 42. Edge-Type Classification

Each candidate receives one or more labels:

```text
ROLE_EDGE
VOLUME_EDGE
GAME_SCRIPT_EDGE
MATCHUP_EDGE
EFFICIENCY_EDGE
MARKET_LAG_EDGE
MULTI_FACTOR_EDGE
```

Example:

```text
WR receptions O4.5
Conservative EV: +6.8%

Primary reason:
ROLE_EDGE

Secondary:
PASS_VOLUME_EDGE
MATCHUP_EDGE
```

This context goes to the trading agent.

---

# 43. Edge Decomposition

Where feasible, quantify approximate drivers.

Example:

```text
+2.1% route-role component
+1.5% target-rate component
+1.0% expected pass-volume component
+0.7% matchup component
+0.5% other
```

Do not pretend this decomposition is exact if the model is nonlinear.

It is an attribution diagnostic, not a mathematical proof of independent causal contributions.

---

# 44. Model Disagreement

Maintain multiple challenger estimates where practical:

```text
baseline model
structural opportunity model
market-anchored model
```

Calculate model dispersion.

High dispersion:

```text
confidence ↓
conservative EV ↓
```

Example:

```text
Model A 52%
Model B 68%
Model C 59%

STATUS = HIGH_MODEL_DISAGREEMENT
```

---

# 45. Opportunity Versus Production Edge

The pipeline should identify what the bet is buying.

Example RB:

```text
Book:
carries 15.5
rush yards 73.5

Model:
carries median 19
rush yards median 78
```

Interpretation:

```text
strong volume edge
modest efficiency edge
```

The model may prefer:

```text
RB carries Over
```

over:

```text
RB rushing yards Over
```

The reverse can also occur.

---

# 46. Thesis Optimizer

Candidate bets should be grouped by latent thesis.

Example factors:

```text
PASS_VOLUME_UP
PASS_VOLUME_DOWN
RUN_VOLUME_UP
RUN_VOLUME_DOWN
WR1_ROLE_UP
WR1_ROLE_DOWN
RB_COMMITTEE_CONCENTRATED
RB_COMMITTEE_DILUTED
PACE_UP
PACE_DOWN
EXPLOSIVE_PASS_UP
```

If several props express the same thesis, do not blindly recommend all.

Rank by:

```text
conservative EV
confidence
variance
liquidity
correlation
market quality
```

Then identify:

```text
BEST_EXPRESSION
SECONDARY_EXPRESSION
REDUNDANT_EXPOSURE
```

---

# 47. Cross-Market Consistency

The model must police itself.

Examples of impossible or suspicious surfaces:

```text
QB attempts very high
WR1 targets high
WR2 targets high
TE targets high
RB targets high
but team plays low
```

or:

```text
team scoring very high
all major player production very low
```

Not every unusual combination is impossible, but it must be flagged.

The sum of player opportunities must reconcile to team-level opportunity.

---

# 48. Over/Under Diagnostics Must Be Separate

Track historical performance by:

```text
market_key
direction
```

Do not assume Over and Under edges behave symmetrically.

Example audit buckets:

```text
player_receptions OVER
player_receptions UNDER

player_rush_attempts OVER
player_rush_attempts UNDER
```

This matters because public bias, role decay, and bookmaker shading can be directional.

---

# 49. Role Certainty Score

Create a Week 1-sensitive:

```text
role_certainty_score: 0–100
```

Inputs may include:

```text
returning starter
same team
same coordinator
same QB
historical route/snap stability
depth-chart stability
injury replacement status
preseason role evidence
rookie status
new-team status
recent transactions
```

Role uncertainty must lower conservative probability confidence.

---

# 50. Data Quality Gates Before Modeling

The pipeline must stop or quarantine on critical issues.

## Event gate

```text
home/away mismatch
kickoff mismatch
duplicate event
unknown team
```

## Player gate

```text
unmapped player
duplicate ambiguous name
position mismatch
player assigned to wrong team
```

## Injury gate

```text
critical player injury snapshot stale
injury feed unavailable
```

## Odds gate

```text
unknown market key
missing player mapping
invalid odds
line missing
book timestamp stale
```

## Simulation gate

```text
team opportunity totals do not reconcile
negative probabilities
probabilities > 1
player carries > team rushes
player receptions > team completions
```

---

# 51. Provider Health Report

Every run should produce:

```text
NFL_PROVIDER_HEALTH_2026-W01.json
```

Example:

```json
{
  "espn_scoreboard": "OK",
  "espn_rosters": "OK",
  "espn_depthcharts": "OK",
  "espn_injuries": "OK",
  "nflverse_pbp": "OK",
  "nflverse_snap_counts": "OK",
  "nws_weather": "OK",
  "odds_api": "OK",
  "odds_credits_remaining": 403
}
```

If a critical provider is degraded:

```text
RUN_STATUS = DEGRADED
```

and confidence penalties should apply where appropriate.

---

# 52. Weekly Orchestration — “The Concert”

This is how all providers and model layers play together.

```text
STEP 01
Load configuration
    ↓
STEP 02
Build / refresh entity maps
    ↓
STEP 03
Load historical nflverse cache
    ↓
STEP 04
Fetch ESPN weekly slate
    ↓
STEP 05
Fetch ESPN current rosters
    ↓
STEP 06
Fetch ESPN depth charts
    ↓
STEP 07
Fetch ESPN injuries
    ↓
STEP 08
Fetch ESPN transactions
    ↓
STEP 09
Reconcile entities and availability
    ↓
STEP 10
Fetch NWS weather for relevant outdoor games
    ↓
STEP 11
Build team state
    ↓
STEP 12
Build QB state
    ↓
STEP 13
Build RB role state
    ↓
STEP 14
Build receiver route/target state
    ↓
STEP 15
Build coaching/tendency state
    ↓
STEP 16
Build matchup state
    ↓
STEP 17
Simulate game states
    ↓
STEP 18
Simulate team play volume
    ↓
STEP 19
Simulate pass/run allocation
    ↓
STEP 20
Simulate QB opportunity
    ↓
STEP 21
Simulate RB opportunity
    ↓
STEP 22
Simulate WR/TE opportunity
    ↓
STEP 23
Simulate player production
    ↓
STEP 24
Create raw probability surface
    ↓
STEP 25
Pull mainline market anchor
    ↓
STEP 26
Calibrate / blend game state
    ↓
STEP 27
Quota governor approves prop pull
    ↓
STEP 28
Pull flagship opportunity props
    ↓
STEP 29
Normalize sportsbook prices
    ↓
STEP 30
Calculate fair odds + EV
    ↓
STEP 31
Shortlist candidate games
    ↓
STEP 32
Pull yardage props only for shortlist
    ↓
STEP 33
Calculate production-market EV
    ↓
STEP 34
Apply uncertainty / conservative EV
    ↓
STEP 35
Run cross-market consistency
    ↓
STEP 36
Generate joint correlation matrix
    ↓
STEP 37
Run thesis optimizer
    ↓
STEP 38
Reprice final candidate markets
    ↓
STEP 39
Generate boards
    ↓
STEP 40
Generate audit manifest
    ↓
STEP 41
Build handoff ZIP
    ↓
PYTHON PIPELINE ENDS
```

---

# 53. CLI Design

Recommended production interface:

```bash
python -m nfl_model run \
  --season 2026 \
  --week 1 \
  --mode production
```

Additional commands:

```bash
python -m nfl_model ingest-football --season 2026 --week 1

python -m nfl_model simulate --season 2026 --week 1

python -m nfl_model odds-plan --season 2026 --week 1

python -m nfl_model fetch-mainlines --season 2026 --week 1

python -m nfl_model fetch-opportunity-odds --season 2026 --week 1

python -m nfl_model fetch-shortlist-yardage --season 2026 --week 1

python -m nfl_model reprice --season 2026 --week 1

python -m nfl_model boards --season 2026 --week 1

python -m nfl_model package --season 2026 --week 1

python -m nfl_model audit --season 2026 --week 1
```

---

# 54. Configuration, Not Hardcoding

Markets belong in YAML/TOML configuration.

Example:

```yaml
odds:
  sport_key: americanfootball_nfl

  bookmakers:
    - draftkings
    - fanduel
    - betrivers

  mainlines:
    - h2h
    - spreads
    - totals

  opportunity_markets:
    - player_receptions
    - player_rush_attempts
    - player_pass_attempts
    - player_pass_completions

  production_markets:
    - player_reception_yds
    - player_rush_yds
    - player_pass_yds

  monthly_credit_reserve: 100
  cache_ttl_minutes: 30
```

Do not hardcode API keys.

Use:

```text
ODDS_API_KEY
```

environment variable.

Never write the API key into:

- logs,
- ZIP,
- Markdown,
- CSV,
- JSON manifest.

---

# 55. Reproducibility

Every model run needs:

```text
run_id
model_version
git_commit
season
week
run_timestamp_utc
data_snapshot_ids
config_hash
random_seed
simulation_count
provider_versions
```

Output:

```text
NFL_RUN_MANIFEST_2026-W01.json
```

The trading agent must know exactly which run produced the board.

---

# 56. Raw Data Must Be Immutable

Architecture:

```text
data/
    raw/
    normalized/
    features/
    model/
    outputs/
```

Rules:

```text
raw = append only
normalized = reproducible from raw
features = reproducible from normalized
model outputs = reproducible from features + version
```

Never manually edit a raw provider response.

---

# 57. Testing Strategy

## Unit tests

Test:

- American-odds conversion,
- no-vig conversion,
- EV math,
- player identity matching,
- team identity matching,
- quota-cost estimation,
- role-share reconciliation,
- pass-attempt accounting,
- probability extraction from simulation draws.

## Provider fixture tests

Store sample ESPN, nflverse, NWS, and Odds API responses.

Tests must run offline.

Never hit live APIs from standard unit tests.

## Integration tests

Given frozen fixtures:

```text
Week X fixture
```

the pipeline should produce deterministic board rows.

## Regression tests

Prevent model changes from silently changing:

```text
event count
player count
market count
EV math
ZIP schema
```

---

# 58. Main Boards

## Board 1 — Game Pricing

```text
moneyline
spread
total
```

## Board 2 — Opportunity Prop Board

```text
player
position
team
opponent
market
line
book
odds
p_raw
p_calibrated
p_blend
p_conservative
fair_odds
conservative_ev_pct
role_certainty
model_agreement
edge_type
```

## Board 3 — Production Prop Board

Same structure for:

```text
passing yards
rushing yards
receiving yards
```

## Board 4 — EV Play Board

Only markets clearing required thresholds.

## Board 5 — Edge Leaderboard

Rank by:

```text
conservative EV
confidence
model agreement
market quality
```

## Board 6 — Rejection Board

Required rejection reasons:

```text
INSUFFICIENT_EV
ROLE_UNCERTAINTY
MODEL_DISAGREEMENT
STALE_ODDS
ENTITY_FAILURE
MARKET_MISSING
EXTREME_MODEL_MARKET_DISAGREEMENT
CORRELATED_DUPLICATE
DATA_QUALITY
QUOTA_NOT_REPRICED
```

## Board 7 — Correlation Matrix

Derived from joint Monte Carlo draws.

## Board 8 — Thesis Board

Shows:

```text
underlying thesis
candidate expressions
best expression
secondary expression
redundant expressions
```

---

# 59. Initial EV Floors

These are **starting research thresholds only**, not permanent truth.

Suggested conservative EV floors:

```text
WR/TE receptions        +3% to +5%
RB rushing attempts     +3% to +5%
QB pass attempts        +3% to +4%
QB completions          +3% to +4%
RB receptions           +4% to +5%

receiving yards         +4% to +6%
rushing yards           +4% to +6%
passing yards           +4% to +5%
```

The audit system must eventually replace these assumptions with empirical thresholds.

---

# 60. Confidence Score

Candidate score can conceptually combine:

```math
Confidence =
f(
role_certainty,
model_agreement,
data_freshness,
sample_strength,
market_history,
calibration_history
)
```

Do not let raw EV dominate a low-confidence row.

---

# 61. Conservative EV

The exact formula should be calibrated, but the structure is:

```text
raw model probability
    ↓
calibration
    ↓
market blend
    ↓
uncertainty haircut
    ↓
conservative probability
    ↓
conservative EV
```

The uncertainty haircut should become stronger for:

- new players,
- rookies,
- new teams,
- new coordinators,
- unknown roles,
- injuries,
- provider disagreement,
- model dispersion.

---

# 62. Trading-Agent ZIP

Final artifact:

```text
NFL_TRADING_AGENT_HANDOFF_2026-W01.zip
```

Minimum contents:

```text
README.md

NFL_SLATE_2026-W01.csv

NFL_TEAM_STATE_2026-W01.csv
NFL_PLAYER_ROLE_STATE_2026-W01.csv

NFL_GAME_PRICING_BOARD_2026-W01.csv
NFL_OPPORTUNITY_PROP_BOARD_2026-W01.csv
NFL_PRODUCTION_PROP_BOARD_2026-W01.csv

NFL_EV_PLAY_BOARD_2026-W01.csv
NFL_EDGE_LEADERBOARD_2026-W01.csv
NFL_REJECTION_BOARD_2026-W01.csv
NFL_THESIS_BOARD_2026-W01.csv

NFL_CORRELATION_MATRIX_2026-W01.csv
NFL_UNCERTAINTY_REPORT_2026-W01.csv
NFL_PROVIDER_HEALTH_2026-W01.json
NFL_ODDS_QUOTA_REPORT_2026-W01.json

NFL_MARKET_SNAPSHOT_2026-W01.csv

NFL_MODEL_METADATA.json
NFL_DATA_LINEAGE.json
NFL_RUN_MANIFEST_2026-W01.json

NFL_FINAL_BOARDS_2026-W01.md
```

Optional:

```text
NFL_MONTE_CARLO_SUMMARY_2026-W01.parquet
```

---

# 63. Python Ends at the ZIP

This boundary is non-negotiable.

```text
PYTHON:
football data
→ state estimation
→ simulation
→ pricing
→ EV
→ uncertainty
→ correlation
→ boards
→ ZIP

STOP
```

The Python model does not behave like a discretionary trader.

---

# 64. Separate Claude NFL Trading Agent

Claude receives:

```text
NFL_TRADING_AGENT_HANDOFF_2026-W01.zip
```

Its responsibilities are:

- read the model boards,
- understand edge type,
- inspect market freshness,
- verify that the price is still actionable,
- recognize injury/news changes after the Python snapshot,
- avoid redundant correlated exposure,
- choose the best expression of a model thesis,
- classify Tier A / Tier B / Watch / Pass,
- preserve Python probabilities rather than inventing hidden replacements.

Claude must not silently rewrite:

```text
p_conservative
```

If it disagrees with the model, it should:

```text
PASS
```

or:

```text
FLAG FOR RERUN
```

not manufacture a new probability.

---

# 65. Postgame Audit Loop

After each completed game:

Fetch outcome data.

Immediate:

```text
ESPN final score / box score
```

Later:

```text
nflverse PBP/player stats/snap/participation update
```

Grade:

```text
bet result
player opportunity prediction
player production prediction
game-state prediction
```

---

# 66. Closing-Line Archive Under Free Odds Plan

Because historical odds are not included in the free Odds API plan, closing-line research requires us to save our own snapshots.

For each executed/model-qualified candidate, reserve quota for a later snapshot as close to kickoff as operationally practical.

Store:

```text
entry_price
final_model_reprice
close_proxy_price
```

Label the provenance precisely.

If the true final close was not captured, do not call an earlier snapshot “official close.”

Use:

```text
CLOSE_PROXY_LOCAL_ARCHIVE
```

unless it truly corresponds to the designated closing timestamp.

---

# 67. Calibration Metrics

Track by market **and direction**:

```text
sample_count
average_raw_ev
average_conservative_ev
realized_roi
CLV
win_rate
Brier
log_loss
calibration_error
```

Buckets:

```text
0–2%
2–4%
4–6%
6–10%
10%+
```

Higher predicted EV should ultimately correspond to higher realized ROI / stronger CLV if the edge engine is real.

---

# 68. Role-Model Audit

For each player prop, also audit the causal chain.

Example WR:

```text
projected routes
actual routes / inferred participation

projected targets
actual targets

projected receptions
actual receptions

projected yards
actual yards
```

This tells us whether failure came from:

```text
ROLE
TARGET RATE
CATCH RATE
EFFICIENCY
```

instead of simply recording win/loss.

---

# 69. RB Audit

Track:

```text
projected team rush attempts
actual team rush attempts

projected RB share
actual RB share

projected carries
actual carries

projected rushing yards
actual rushing yards
```

This is how we determine whether carries are actually the stronger market.

---

# 70. QB Audit

Track:

```text
projected team plays
actual team plays

projected dropbacks
actual dropbacks

projected pass attempts
actual attempts

projected completions
actual completions

projected passing yards
actual passing yards
```

---

# 71. Promotion / Demotion of Markets

At sufficient sample:

If:

```text
player_receptions
```

shows:

- positive CLV,
- calibrated probabilities,
- monotonic EV-to-ROI,
- stable role forecasting,

then increase its market trust in our model and potentially lower the EV entry threshold.

If:

```text
player_pass_yds
```

shows poor CLV and miscalibration:

- increase market anchoring,
- raise EV threshold,
- reduce rank,
- or temporarily remove it.

Market hierarchy must become empirical.

---

# 72. API Failure Behavior

## ESPN failure

If current depth/injury data cannot be validated:

```text
critical affected games → NO BET / DEGRADED
```

Do not substitute stale data invisibly.

## nflverse failure

Use local cached historical dataset if checksum/version is valid.

## NWS failure

Use last recent forecast if within TTL and flag stale; otherwise increase uncertainty for outdoor games.

## Odds API failure

Do not invent or reuse old market prices as current.

Output:

```text
MARKET_NOT_PRICED
```

---

# 73. Security

Secrets:

```text
ODDS_API_KEY
```

must be loaded from environment or secret manager.

`.env`:

```text
gitignored
```

No secrets in ZIP.

No secrets in logs.

No full API URLs containing the key should be written to logs.

Sanitize query strings.

---

# 74. Performance

Use:

- Polars where convenient for nflreadpy outputs,
- Parquet for large normalized historical datasets,
- vectorized feature generation,
- deterministic caching,
- multiprocessing / vectorized Monte Carlo where safe.

Do not optimize prematurely at the cost of auditability.

Correctness and reproducibility first.

---

# 75. Recommended Repository Layout

```text
NFL_MODEL/
├── pyproject.toml
├── README.md
├── configs/
│   ├── nfl_2026.yaml
│   ├── markets.yaml
│   └── stadiums.yaml
├── src/
│   └── nfl_model/
│       ├── cli.py
│       ├── config.py
│       ├── ids/
│       │   ├── teams.py
│       │   ├── players.py
│       │   └── events.py
│       ├── providers/
│       │   ├── espn/
│       │   ├── nflverse/
│       │   ├── nws/
│       │   └── odds_api/
│       ├── storage/
│       ├── normalize/
│       ├── features/
│       │   ├── team.py
│       │   ├── qb.py
│       │   ├── rb.py
│       │   ├── receivers.py
│       │   ├── coaching.py
│       │   └── matchup.py
│       ├── models/
│       │   ├── game_state.py
│       │   ├── plays.py
│       │   ├── pass_run.py
│       │   ├── qb_opportunity.py
│       │   ├── rb_opportunity.py
│       │   ├── receiver_opportunity.py
│       │   ├── production.py
│       │   └── calibration.py
│       ├── simulation/
│       │   ├── monte_carlo.py
│       │   ├── draws.py
│       │   └── convergence.py
│       ├── pricing/
│       │   ├── odds.py
│       │   ├── novig.py
│       │   ├── fair_price.py
│       │   ├── ev.py
│       │   └── conservative.py
│       ├── portfolio/
│       │   ├── correlation.py
│       │   └── thesis_optimizer.py
│       ├── boards/
│       ├── package/
│       └── audit/
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── regression/
└── data/
    ├── raw/
    ├── normalized/
    ├── features/
    ├── cache/
    └── outputs/
```

---

# 76. Development Order

## Phase 1 — Data Foundation

Build:

- provider clients,
- raw caching,
- entity maps,
- normalized schemas,
- Week 1 slate ingestion.

No modeling until this is stable.

## Phase 2 — Historical State

Build:

- PBP features,
- team state,
- QB state,
- snap/role state,
- coaching state.

## Phase 3 — Opportunity Engine

Build in this order:

1. team plays,
2. pass/run,
3. QB attempts,
4. RB carries,
5. routes,
6. targets,
7. receptions,
8. QB completions.

## Phase 4 — Game-State Monte Carlo

Unify the opportunity variables inside one simulation.

## Phase 5 — Production

Add:

- passing yards,
- rushing yards,
- receiving yards.

## Phase 6 — Pricing

Add:

- mainline market anchor,
- Odds API quota governor,
- prop normalization,
- no-vig,
- fair odds,
- EV,
- conservative EV.

## Phase 7 — Trading Intelligence

Add:

- edge type,
- model disagreement,
- correlations,
- thesis optimizer,
- best-expression ranking.

## Phase 8 — Handoff

Generate ZIP.

## Phase 9 — Audit

Grade everything after the slate.

---

# 77. Non-Negotiable V1 Scope Control

Do not add before the core engine is validated:

```text
TD props
first TD
longest reception
longest rush
defensive props
kicker props
SGP optimizer
live betting
alternate props
futures
```

These can become later modules.

The first goal is to prove that:

```text
routes
targets
receptions
carries
attempts
completions
```

can be priced better than the market.

---

# 78. Coding-Agent Acceptance Criteria

The build is not “done” because it runs.

V1 is acceptable when:

1. Week slate can be fetched and normalized.
2. All active players are mapped across sources.
3. Historical nflverse datasets load from cache reproducibly.
4. Current ESPN rosters/depth/injuries update cleanly.
5. Weather is assigned only where relevant.
6. Game/team opportunity reconciles.
7. Player opportunity reconciles to team totals.
8. Monte Carlo converges.
9. The Odds API quota governor prevents accidental overuse.
10. Mainline prices can be pulled in one low-cost slate request.
11. Opportunity props use only the four approved V1 market keys.
12. Production markets are pulled only after shortlist.
13. Every price response is archived.
14. EV math passes unit tests.
15. Extreme disagreements are quarantined.
16. Correlation is generated from joint simulation.
17. Thesis optimizer identifies redundant exposure.
18. All final boards contain data provenance.
19. Handoff ZIP is deterministic.
20. Python performs no trading-agent discretion after ZIP creation.

---

# 79. Final Architecture Lock

The model to build is:

```text
AITA NFL OPPORTUNITY-FIRST PLAYER ALPHA PIPELINE
```

Its defining principles are:

```text
1. NFLVERSE FOR HISTORICAL FOOTBALL DEPTH.
2. ESPN FOR CURRENT OPERATIONAL NFL STATE.
3. NWS FOR WEATHER.
4. THE ODDS API ONLY FOR CURRENT MARKET PRICING.
5. CACHE EVERYTHING.
6. NEVER JOIN BY NAME ALONE.
7. MODEL TEAM PLAYS BEFORE PLAYER PROPS.
8. MODEL OPPORTUNITY BEFORE PRODUCTION.
9. SIMULATE ROLE UNCERTAINTY.
10. PRICE ONLY A SMALL APPROVED MARKET UNIVERSE.
11. SPEND ODDS CREDITS ONLY AFTER MODELING.
12. CONSERVATIVE EV, NOT RAW EV, DRIVES RANKING.
13. JOINT MONTE CARLO DRIVES CORRELATIONS.
14. THESIS OPTIMIZER SELECTS THE BEST EXPRESSION.
15. PYTHON ENDS AT THE HANDOFF ZIP.
16. THE SEPARATE CLAUDE TRADING AGENT MAKES THE FINAL TRADE DECISION.
17. EVERY WEEK FEEDS BACK INTO CLV, ROI, CALIBRATION, AND ROLE ACCURACY.
```

The project should behave less like a prediction bot and more like a sportsbook pricing desk:

```text
SOURCE
→ NORMALIZE
→ ESTIMATE STATE
→ SIMULATE
→ PRICE
→ COMPARE MARKET
→ HAIRCUT UNCERTAINTY
→ RANK EDGE
→ CONTROL CORRELATION
→ PACKAGE
→ AUDIT
→ RECALIBRATE
```

---

# 80. Research Verification Snapshot — 2026-08-29

The coding agent should re-check external provider documentation before finalizing provider code because interfaces and quotas can change.

## The Odds API

Verified current facts:

- Starter plan: **FREE / $0**, **500 credits per month**.
- Current NFL odds and player props are available on the free usage plan.
- NFL player props are queried one event at a time using the event-odds endpoint.
- Event-odds usage is based on unique markets returned × regions/equivalent bookmaker groups.
- Up to 10 explicitly selected bookmakers count as one region-equivalent group.
- `/sports` does not consume quota.
- `/events` does not consume quota.
- Historical odds are not available on the free plan.
- Current NFL player market keys include:
  - `player_pass_attempts`
  - `player_pass_completions`
  - `player_pass_yds`
  - `player_receptions`
  - `player_reception_yds`
  - `player_rush_attempts`
  - `player_rush_yds`

References:

- https://the-odds-api.com/
- https://the-odds-api.com/liveapi/guides/v4/
- https://the-odds-api.com/sports/nfl-odds.html
- https://the-odds-api.com/sports-odds-data/betting-markets.html

## nflreadpy / nflverse

Verified current `nflreadpy` functions include:

- play-by-play,
- player stats,
- team stats,
- schedules,
- players,
- rosters,
- weekly rosters,
- snap counts,
- Next Gen Stats-derived data,
- participation,
- injuries,
- depth charts,
- PFR advanced stats,
- other football datasets.

References:

- https://nflreadpy.nflverse.com/
- https://nflreadpy.nflverse.com/api/load_functions/

## ESPN JSON endpoints

Community-documented ESPN endpoint families currently expose NFL:

- scoreboard,
- teams,
- team rosters,
- depth charts,
- injuries,
- transactions,
- game summary.

These interfaces do not constitute a stable official ESPN developer contract; isolate them behind adapters and schema validation.

Representative endpoint family:

- https://site.api.espn.com/apis/site/v2/sports/football/nfl/

Community endpoint references:

- https://github.com/stylo-stack/ESPN-API-Documentation
- https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b

## National Weather Service

NWS provides open forecast data through `api.weather.gov`, including point-to-grid lookups and hourly forecasts.

References:

- https://api.weather.gov
- https://www.weather.gov/documentation/services-web-api

---

# 81. Final Instruction to the Coding Agent

Build this system in layers.

Do **not** begin by writing a giant monolithic simulator.

First make the data reliable.

Then make opportunity accounting reconcile.

Then make probabilities calibrated.

Then attach prices.

Then calculate EV.

Then package for the trading agent.

The core economic question is never:

> Who will have a good game?

It is:

> Given the current personnel, coaching, matchup, and game-state distribution, what is the correct probability distribution for this player's opportunity, what price should the proposition trade at, and does the available sportsbook price compensate us sufficiently after uncertainty and correlation are considered?

That is the AITA NFL V1 standard.
