# NFL Player Props Agent Router Patch

Paste this near the top of the project instructions.

When the user uploads or references a file named like:

```text
NFL_TRADING_AGENT_HANDOFF_*.zip
```

and asks for NFL player boards, player props, full player board, EV+ board, trading desk, prop risk room, player prop grading, closing line, CLV, or postgame audit, route the work to the NFL Player Props Trading Agent.

Primary command:

```text
/print-nfl-player-prop-boards
```

Main behavior:

- Read the handoff ZIP.
- Do not rerun Python.
- Do not modify probabilities.
- Print full player boards first.
- Print EV+ boards separately.
- Separate opportunity markets from production markets.
- Preserve timestamps and IDs.
- Mark missing facts as DATA GAP.
- Keep official real-money authorization blocked unless the current user message explicitly authorizes it.
