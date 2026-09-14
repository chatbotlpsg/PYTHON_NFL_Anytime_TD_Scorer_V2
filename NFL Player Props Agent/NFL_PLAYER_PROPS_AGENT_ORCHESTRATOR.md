# NFL Player Props Agent Orchestrator

## Agent sequence

1. **Handoff Intake Agent**
   - validates ZIP, manifest, run metadata, required CSV files, row counts, and timestamps.

2. **Full Player Board Agent**
   - writes all player forecast boards: all-player, passing, rushing, receiving.
   - no EV language.

3. **Market-Lined Pick Agent**
   - writes probability-first market-lined boards.
   - no EV promotion.

4. **EV+ Board Agent**
   - ranks only positive price-sensitive EV candidates.
   - uses conservative EV, buy-to, hard-stop, confidence, and risk flags.

5. **Opportunity Market Agent**
   - handles WR/TE receptions, RB rushing attempts, QB pass attempts, QB completions, RB receptions.

6. **Production Market Agent**
   - handles receiving yards, rushing yards, passing yards, RB receiving yards.

7. **Role / Depth / Injury Agent**
   - audits player availability, role certainty, depth rank, entity status, and freshness.

8. **Market Price Agent**
   - checks price, line, book, timestamp, and post-handoff line movement when authorized.

9. **Correlation / Thesis Agent**
   - detects duplicate same-game/player/thesis exposures and selects best expression.

10. **Gatekeeper Agent**
    - assigns PASS / WATCH / VALUE / ELITE / PAPER_ONLY / BLOCKED.

11. **Close / CLV / Result Agents**
    - used only after entry/close/result facts are supplied or verified.

12. **Dataset B Recap Agent**
    - creates permanent recap and calibration evidence.
