# NFL Player Props Full Player Board Protocol

Full player forecast boards are market-blind. They are for calibration and player-distribution visibility.

Print these boards in order:

1. All Player Forecast Board
2. Passing Forecast Board
3. Rushing Forecast Board
4. Receiving Forecast Board

Columns:

```text
Date | Time | Game | Player | Pos | Team | Opp | Stat | Mean | Median | P10-P90 | Reference Line | Ref Source | Model Side | Model Prob | O/U/Push | Role Certainty | Directional Strength | Forecast Gate
```

Rules:

- Do not include EV columns.
- Do not call a market-blind lean a play.
- Mark model-native reference lines as MODEL_NATIVE.
- Preserve forecast_id when row-level detail is needed.
- Sort by kickoff time, game, board category, directional strength, model probability.
