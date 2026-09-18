# AITA NFL Anytime TD Scorer v0.2.0a1 — Sharpness / Roster Integrity Upgrade

## Why this release exists

The 9/13 handoff exposed a material model-governance failure mode: historical player identities could remain eligible even when the player was not verified on the current ESPN team roster. Because anytime-TD prices can be long, those stale/deep names could also surface as attractive EV rows and distract the downstream Trading Agent.

v0.2.0a1 changes the ordering of the scorer model so **eligibility and probability quality come before price and EV**.

## New decision stack

`CURRENT ROSTER -> AVAILABILITY -> DEPTH/ROLE -> ESPN TEAM LEADERS -> FANTASY CONTEXT -> TD MATCHUP CONTEXT -> TD STYLE -> QB CANNIBALIZATION -> MONTE CARLO -> MOST-PROBABLE BOARDS -> ODDS -> EV`

The Odds API is no longer capable of creating or promoting the primary scorer universe. It only prices players after the probability universe has been frozen.

## Hard roster gate

A scorer must be:

- verified on the current ESPN roster for his modeled team;
- active on that roster;
- not blocked by OUT/IR/PUP/SUSPENDED injury status;
- a QB/RB/WR/TE;
- meaningful enough in depth/fantasy role to enter the primary scorer universe.

Historical nflverse rows remain useful for priors and recent form, but history alone cannot certify current roster eligibility.

## Primary vs audit universe

The full model audit board can retain deeper verified names for diagnostics. Primary matchup/slate boards require current-roster verification, primary-role eligibility and the configured minimum model TD probability. Deep players are explicitly rejected from actionable EV as `LOW_ROLE_LOTTERY_POOL`.

## ESPN current-state expansion

The model now ingests ESPN team leaders to corroborate current QB/RB/WR/TE role and production. The current roster remains the identity authority; the leader feed adds current statistical context and role certainty.

## Fantasy context

ESPN fantasy weekly projections and fantasy points are joined to current player identities. The model exports fantasy position ranks and applies only a capped role multiplier.

Yahoo Fantasy is implemented as an optional official-API corroboration layer. It requires Yahoo OAuth access and a league key. When not configured, the pipeline records the provider as skipped instead of scraping or fabricating Yahoo projections.

## Defensive TD vulnerability

The model now derives opponent TD vulnerability from nflverse PBP:

- rushing vs receiving TD path;
- TDs allowed by QB/RB/WR/TE;
- inside-5 TDs;
- red-zone 6-20 TDs;
- 21+ yard explosive TDs;
- red-zone trips / TD rate where available;
- recency weighting;
- small-sample labeling;
- target / neutral / bad-matchup position verdict.

Total yards are deliberately not used as a stand-in for red-zone TD vulnerability.

Slot vs outside WR vulnerability is not inferred from standard PBP because the necessary alignment data is not reliably present. The board marks this unresolved rather than manufacturing a split.

## TD repeatability profile

Each scorer is profiled by where historical TDs came from. Goal-line/red-zone scorers receive a small capped repeatability advantage; distance-only scorers receive a modest repeatability haircut because 21+ yard scores are less dependent on repeatable short-yardage opportunity.

## QB goal-line competition

The model calculates QB rush attempts inside the 5, QB share of team goal-line rush attempts, rushing TDs and detected sneaks. This becomes a capped competition modifier for the team's RB/WR/TE scoring paths and a self-scoring modifier for the QB rushing-TD path.

## New board order

1. QB most-probable slate board
2. RB most-probable slate board
3. WR most-probable slate board
4. TE most-probable slate board
5. Whole-slate most-probable scorer board
6. Matchup most-probable scorer boards
7. Sportsbook scorer market snapshot
8. Straight EV+ boards
9. Joint pair/triple probability boards

This is intentional: **most probable is not the same thing as best price**.

## Validation

- Python compile: PASS
- Automated test suite: 35/35 PASS
- Upgraded scorer demo handoff audit: PASS
- Missing required handoff artifacts: 0
- Forbidden Dataset-B/CLV artifacts: 0
