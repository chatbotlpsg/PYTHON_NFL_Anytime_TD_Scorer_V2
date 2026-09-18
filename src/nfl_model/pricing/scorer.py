from __future__ import annotations

from datetime import datetime, timezone
import numpy as np
import pandas as pd

from nfl_model.pricing.ev import ev_pct
from nfl_model.pricing.fair_price import fair_american_odds
from nfl_model.pricing.buy_to import worst_acceptable_american
from nfl_model.pricing.odds import american_to_implied


def _age_minutes(ts: object) -> float | None:
    if ts is None or (isinstance(ts, float) and np.isnan(ts)):
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 60.0)
    except Exception:
        return None


def normalize_anytime_td_market(rows: pd.DataFrame) -> pd.DataFrame:
    """Normalize Odds-API anytime-TD rows to one YES selection per player/book when available."""
    if rows is None or rows.empty:
        return pd.DataFrame()
    out = rows.copy()
    out = out[out["market_key"].astype(str).eq("player_anytime_td")].copy()
    if out.empty:
        return out
    out["side"] = out["side"].fillna("").astype(str).str.upper()
    # Standard feed shape is description=<player>, name=Yes/No. If a book exposes the player as outcome name,
    # preserve the original description when present and treat a non-NO selection as the YES price.
    weird = out["player_name_raw"].isna() | out["player_name_raw"].astype(str).str.strip().eq("")
    out.loc[weird, "player_name_raw"] = out.loc[weird, "side"].str.title()
    out.loc[weird & ~out["side"].eq("NO"), "side"] = "YES"
    yes = out[out["side"].isin(["YES", "OVER"])].copy()
    yes["side"] = "YES"
    yes["line"] = 0.5
    return yes


def price_anytime_td_rows(
    odds_rows: pd.DataFrame,
    draws: dict[str, np.ndarray],
    player_map: pd.DataFrame,
    ev_floor: float = 0.06,
    market_trust: float = 0.28,
    week: int | None = None,
    week1_multiplier: float = 1.35,
    max_haircut_fraction: float = 0.80,
    max_market_age_minutes: float = 90.0,
    buy_to_extra_ev_margin: float = 0.01,
    hard_stop_extra_ev_margin: float = 0.00,
    convergence_checkpoints: list[int] | None = None,
    convergence_tolerance: float = 0.004,
) -> pd.DataFrame:
    if odds_rows is None or odds_rows.empty:
        return pd.DataFrame()
    out_rows = []
    pm = player_map.set_index("aita_player_id") if not player_map.empty else pd.DataFrame()
    work = odds_rows.copy()
    if "market_raw_implied_prob" not in work.columns:
        work["market_raw_implied_prob"] = pd.to_numeric(work["american_odds"], errors="coerce").map(lambda x: american_to_implied(float(x)) if pd.notna(x) else np.nan)
    consensus = work.groupby(["aita_event_id", "aita_player_id"], dropna=False)["market_raw_implied_prob"].median().to_dict()
    checkpoints = convergence_checkpoints or [25000, 50000, 100000, 200000, 500000]

    for _, row in work.iterrows():
        r = row.to_dict()
        pid = row.get("aita_player_id")
        if not pid or str(row.get("entity_status") or "RESOLVED") == "ENTITY_QUARANTINE":
            out_rows.append({**r, "model_status": "REJECTED", "rejection_reason": "ENTITY_FAILURE"})
            continue
        key = f"SCORER|{pid}|anytime"
        if key not in draws or pd.isna(row.get("american_odds")):
            out_rows.append({**r, "model_status": "MARKET_NOT_PRICED", "rejection_reason": "MISSING_SCORER_DRAWS_OR_PRICE"})
            continue
        meta = pm.loc[pid] if isinstance(pm, pd.DataFrame) and pid in pm.index else {}
        if isinstance(meta, pd.DataFrame): meta = meta.iloc[-1]
        if hasattr(meta, "get") and not bool(meta.get("critical_current_state_ok", True)):
            out_rows.append({**r, "model_status": "REJECTED", "rejection_reason": "DATA_QUALITY"})
            continue
        if hasattr(meta, "get") and not bool(meta.get("roster_verified_current", False)):
            out_rows.append({**r, "model_status": "REJECTED", "rejection_reason": "NOT_ON_CURRENT_ESPN_ROSTER"})
            continue
        if hasattr(meta, "get") and not bool(meta.get("available_for_simulation", False)):
            out_rows.append({**r, "model_status": "REJECTED", "rejection_reason": "CURRENT_AVAILABILITY_BLOCK"})
            continue
        if hasattr(meta, "get") and not bool(meta.get("primary_scorer_eligible", False)):
            out_rows.append({**r, "model_status": "REJECTED", "rejection_reason": "LOW_ROLE_LOTTERY_POOL"})
            continue
        if hasattr(meta, "get") and not bool(meta.get("sharp_board_eligible", True)):
            out_rows.append({
                **r,
                "model_status": "REJECTED",
                "rejection_reason": "EXTERNAL_CONSENSUS_DISAGREEMENT",
                "external_consensus_status": meta.get("external_consensus_status"),
                "external_consensus_score": meta.get("external_consensus_score"),
                "external_source_count": meta.get("external_source_count"),
            })
            continue
        age = _age_minutes(row.get("market_last_update") or row.get("book_last_update"))
        if age is not None and age > max_market_age_minutes:
            out_rows.append({**r, "market_age_minutes": age, "model_status": "REJECTED", "rejection_reason": "STALE_ODDS"})
            continue

        x = np.asarray(draws[key], dtype=np.int8)
        p_raw = float(np.mean(x >= 1))
        # Scorer calibration starts as identity. Shrinking low probabilities toward 50% would be structurally wrong.
        p_cal = p_raw
        p_mkt = consensus.get((row.get("aita_event_id"), pid))
        p_mkt = float(p_mkt) if p_mkt is not None and not pd.isna(p_mkt) else None
        p_blend = float(np.clip((1.0 - market_trust) * p_cal + market_trust * p_mkt, 0.001, 0.999)) if p_mkt is not None else p_cal

        role = float(meta.get("role_certainty_score", 60.0)) if hasattr(meta, "get") else 60.0
        fresh = float(meta.get("data_freshness_score", 80.0)) if hasattr(meta, "get") else 80.0
        disagreement = abs(p_raw - p_mkt) if p_mkt is not None else 0.0
        agreement = float(np.clip(100.0 - disagreement * 300.0, 20.0, 100.0))
        confidence = float(np.clip(0.50 * role + 0.25 * fresh + 0.25 * agreement, 0.0, 100.0))
        uncertainty = np.clip((1.0 - confidence / 100.0) * (week1_multiplier if week == 1 else 1.0), 0.0, 1.0)
        haircut = float(min(max_haircut_fraction, uncertainty))
        anchor = p_mkt if p_mkt is not None else max(0.01, p_raw * 0.80)
        p_cons = float(np.clip(anchor + (p_blend - anchor) * (1.0 - haircut), 0.001, 0.999))

        odds = float(row["american_odds"])
        raw_ev = ev_pct(p_raw, odds)
        blend_ev = ev_pct(p_blend, odds)
        cons_ev = ev_pct(p_cons, odds)
        recent = [c for c in checkpoints if c <= len(x)]
        estimates = [float(np.mean(x[:c] >= 1)) for c in recent]
        diffs = [abs(estimates[i] - estimates[i-1]) for i in range(1, len(estimates))]
        delta = max(diffs[-2:], default=0.0)
        conv = "CONVERGED" if len(estimates) < 2 or delta <= convergence_tolerance else "NOT_CONVERGED"
        status = "ACTIONABLE_AT_REFERENCE_PRICE" if cons_ev / 100.0 >= ev_floor and conv == "CONVERGED" else "REJECTED"
        rejection = "" if status.startswith("ACTIONABLE") else ("DATA_QUALITY" if conv != "CONVERGED" else "INSUFFICIENT_EV")

        out_rows.append({
            **r,
            "market_age_minutes": age,
            "p_model_raw": p_raw,
            "p_calibrated": p_cal,
            "market_consensus_raw_implied_prob": p_mkt,
            "market_reference_is_vig_free": False,
            "p_blend": p_blend,
            "p_conservative": p_cons,
            "uncertainty_haircut_fraction": haircut,
            "fair_odds_raw": fair_american_odds(p_raw),
            "fair_odds_blended": fair_american_odds(p_blend),
            "fair_odds_conservative": fair_american_odds(p_cons),
            "ev_raw_pct": raw_ev,
            "ev_blended_pct": blend_ev,
            "ev_conservative_pct": cons_ev,
            "minimum_required_ev_pct": ev_floor * 100.0,
            "buy_to_price": worst_acceptable_american(p_cons, ev_floor + buy_to_extra_ev_margin),
            "hard_stop_price": worst_acceptable_american(p_cons, ev_floor + hard_stop_extra_ev_margin),
            "role_certainty_score": role,
            "data_freshness_score": fresh,
            "model_agreement_score": agreement,
            "confidence_score": confidence,
            "external_consensus_status": meta.get("external_consensus_status") if hasattr(meta, "get") else None,
            "external_consensus_score": meta.get("external_consensus_score") if hasattr(meta, "get") else None,
            "external_source_count": meta.get("external_source_count") if hasattr(meta, "get") else None,
            "external_consensus_multiplier": meta.get("external_consensus_multiplier") if hasattr(meta, "get") else None,
            "fftoday_anytime_td_signal": meta.get("fftoday_anytime_td_signal") if hasattr(meta, "get") else None,
            "fantasypros_pos_rank": meta.get("fantasypros_pos_rank") if hasattr(meta, "get") else None,
            "pfr_pos_rank": meta.get("pfr_pos_rank") if hasattr(meta, "get") else None,
            "sharp_board_eligible": meta.get("sharp_board_eligible") if hasattr(meta, "get") else True,
            "probability_edge_vs_break_even_pp": (p_cons - float(row["market_raw_implied_prob"])) * 100.0,
            "model_market_disagreement_pp": disagreement * 100.0,
            "convergence_status": conv,
            "convergence_max_delta": delta,
            "convergence_estimates": str(estimates),
            "calibration_method": "SCORER_IDENTITY_PENDING_WALK_FORWARD_DATASET_B",
            "market_blend_method": "LOW_TRUST_RAW_IMPLIED_CONSENSUS_NOT_NOVIG",
            "model_status": status,
            "rejection_reason": rejection,
        })
    return pd.DataFrame(out_rows)
