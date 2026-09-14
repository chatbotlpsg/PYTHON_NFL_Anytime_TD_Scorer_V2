# NFL Player Props Close / CLV / Grading Protocol

Post-handoff records belong to Dataset B.

Required fields:

```text
run_id
candidate_id
forecast_id
player
team
opponent
market
side
line
python_reference_book
python_reference_odds
python_reference_timestamp
python_p_conservative
python_fair_odds
python_ev_conservative_pct
buy_to_price
hard_stop_price
trading_agent_decision
actual_entry_book
actual_entry_line
actual_entry_odds
actual_entry_timestamp
closing_book_or_consensus
closing_line
closing_odds
closing_timestamp
close_quality_flag
player_result
bet_grade
roi_pct
clv_price_delta
clv_probability_delta
clv_positive_flag
audit_notes
```

Do not equate win/loss with model correctness. Grade forecast quality, EV quality, CLV, result, and process separately.
