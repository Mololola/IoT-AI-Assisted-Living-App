# simulation.py — v4 IMPROVED with validation, better constants, and robust handling
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional, Tuple
import math
import uuid
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION CONSTANTS (extracted from magic numbers)
# ============================================================================
class Config:
    # Time windows
    QUIET_START = 22  # inclusive
    QUIET_END = 6     # exclusive
    WINDOW_MIN = 15
    HOP_MIN = 5
    RNG_SEED = 42
    
    # Oven detection
    OVEN_W_THR = 300
    OVEN_MIN_THR = 30
    OVEN_OFF_HYST = 200
    OVEN_OFF_MIN = 3
    
    # Anomaly detection
    ANOM_PCTL_PER_HOUR = 97.5
    MIN_ALERT_GAP_MIN = 30
    DEBOUNCE_STABLE_REQ = 2
    
    # Anomaly candidacy thresholds
    QUIET_THRESHOLD_FACTOR = 0.90
    QUIET_LOW_MOTION_MAX = 30
    HIGH_MOTION_THRESHOLD = 60
    PRESSURE_ONLY_MOTION_MIN = 12
    QUIET_TRANSITIONS_ANOMALY = 3
    
    # Sleep detection
    SLEEP_MIN_PRESS = 1
    SLEEP_MIN_SESSION_MIN = 60
    SLEEP_TURNOVER_THRESHOLD = 5
    SLEEP_IMMOBILITY_GAP_MIN = 240  # 4 hours
    
    # Data validation
    REQUIRED_COLUMNS = ["hall_motion", "kitchen_motion", "bedroom_motion", "oven_power_w"]
    ROOMS = ["hall", "kitchen", "bedroom"]


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================
def validate_input_dataframe(df: pd.DataFrame) -> None:
    """Validate that input DataFrame has required structure."""
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a DatetimeIndex")
    
    missing = set(Config.REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    if len(df) < Config.WINDOW_MIN:
        raise ValueError(f"DataFrame must have at least {Config.WINDOW_MIN} rows for windowing")
    
    # Check for reasonable frequency (should be ~1 minute)
    if len(df) > 1:
        median_diff = df.index.to_series().diff().median()
        if median_diff > pd.Timedelta(minutes=2):
            logger.warning(f"Data frequency appears to be > 2 minutes (median: {median_diff}). Expected ~1 minute.")


# ============================================================================
# CORE DETECTION FUNCTIONS
# ============================================================================
def is_quiet_hour(hour: int) -> int:
    """Check if hour falls within quiet hours."""
    return int(hour >= Config.QUIET_START or hour < Config.QUIET_END)


def debounce_series(s: pd.Series, stable_req: int = Config.DEBOUNCE_STABLE_REQ) -> pd.Series:
    """
    Debounce binary series: require 'stable_req' consecutive values to change state.
    Handles gaps in data gracefully by treating missing indices as maintaining current state.
    """
    on_count = 0
    off_count = 0
    state = 0
    out = []
    
    for v in s.values:
        if pd.isna(v):
            # Treat NaN as maintaining current state
            out.append(state)
            continue
            
        if v == 1:
            on_count += 1
            off_count = 0
            if state == 0 and on_count >= stable_req:
                state = 1
        else:
            off_count += 1
            on_count = 0
            if state == 1 and off_count >= stable_req:
                state = 0
        out.append(state)
    
    return pd.Series(out, index=s.index, dtype=int)


def infer_current_room(row: pd.Series, prev_room: Optional[str], rooms: List[str] = Config.ROOMS) -> Optional[str]:
    """Infer current room from presence sensors."""
    active = [r for r in rooms if row.get(f"{r}_present", 0) == 1]
    if not active:
        return None
    if prev_room in active:
        return prev_room
    return active[0]


def count_room_transitions(window_df: pd.DataFrame) -> int:
    """Count room transitions in a window, handling None values."""
    rooms = window_df["current_room"].tolist()
    transitions = 0
    
    prev = None
    for room in rooms:
        if room is not None and prev is not None and room != prev:
            transitions += 1
        if room is not None:
            prev = room
    
    return transitions


def make_features(win: pd.DataFrame) -> Dict:
    """Extract features from a time window."""
    feat = {}
    
    # Motion features
    motion_cols = ["hall_motion", "kitchen_motion", "bedroom_motion"]
    feat["motion_sum"] = float(win[motion_cols].sum().sum())
    feat["unique_rooms"] = int((win[motion_cols].sum(axis=0) > 0).sum())
    
    # Oven features
    oven_on_min = int((win["oven_power_w"] > Config.OVEN_W_THR).sum())
    feat["oven_on_time_min"] = float(oven_on_min)
    feat["oven_on_frac"] = oven_on_min / Config.WINDOW_MIN
    
    # Room transitions
    feat["room_transitions"] = count_room_transitions(win)
    
    # Temporal features
    last_ts = win.index[-1]
    h = last_ts.hour
    feat["hour"] = h
    feat["is_quiet"] = is_quiet_hour(h)
    
    # Derived features
    feat["motion_sum_sqrt"] = math.sqrt(feat["motion_sum"])
    feat["sin_hour"] = math.sin(2 * math.pi * h / 24.0)
    feat["cos_hour"] = math.cos(2 * math.pi * h / 24.0)
    
    return feat


def is_candidate_anomaly(row: pd.Series) -> bool:
    """
    Determine if a window is a candidate anomaly.
    Includes suppression rules for pressure-only quiet hours.
    """
    h = row["ts"].hour
    adj_thr = row["threshold"] * (Config.QUIET_THRESHOLD_FACTOR if row["is_quiet"] == 1 else 1.0)
    
    # Pressure-only quiet-hour suppression
    if (row["is_quiet"] == 1
        and row["unique_rooms"] == 1
        and row["room_transitions"] == 0
        and row["oven_on_frac"] == 0
        and row["motion_sum"] <= Config.QUIET_LOW_MOTION_MAX):
        return False
    
    # Activity requirements
    pressure_only = (row["unique_rooms"] == 1 and row["oven_on_frac"] == 0)
    hard_activity = (
        (row["is_quiet"] == 1 and row["room_transitions"] >= Config.QUIET_TRANSITIONS_ANOMALY) or
        (row["motion_sum"] > Config.HIGH_MOTION_THRESHOLD) or
        (pressure_only and row["motion_sum"] >= Config.PRESSURE_ONLY_MOTION_MIN)
    )
    
    return (row["anomaly_score"] >= adj_thr) and hard_activity


# ============================================================================
# GUARD DETECTORS
# ============================================================================
def oven_left_on_guard(p_series: pd.Series) -> List[Dict]:
    """
    Detect oven left on with hysteresis.
    Returns list of alert dictionaries.
    """
    alerts = []
    streak = 0
    off_streak = 0
    on_start = None
    
    for t, w in p_series.items():
        if w > Config.OVEN_W_THR:
            if streak == 0:
                on_start = t
            streak += 1
            
            if streak == Config.OVEN_MIN_THR:
                alerts.append({
                    "ts_start": on_start,
                    "ts_end": t,
                    "type": "guard",
                    "label": "oven_left_on",
                    "score": None,
                    "features": {"power_w": int(w), "minutes_on": int(streak)},
                    "explanations": [f"Oven power > {Config.OVEN_W_THR}W for ≥{Config.OVEN_MIN_THR} min"]
                })
            
            off_streak = 0
        else:
            if w < Config.OVEN_OFF_HYST:
                off_streak += 1
            
            if off_streak >= Config.OVEN_OFF_MIN:
                streak = 0
                off_streak = 0
                on_start = None
    
    return alerts


def sleep_sessions_from_bed(df_minutes: pd.DataFrame) -> List[Dict]:
    """
    Detect sleep sessions and possible immobility from bedroom pressure.
    Works across day boundaries by checking quiet hours per timestamp.
    """
    pressed = (df_minutes["bedroom_motion"] >= Config.SLEEP_MIN_PRESS).astype(int)
    
    sessions = []
    in_sess = False
    s_start = None
    alerts_local = []
    
    # Build sessions
    for t, v in pressed.items():
        if v == 1 and is_quiet_hour(t.hour):
            if not in_sess:
                in_sess = True
                s_start = t
        else:
            if in_sess:
                sessions.append((s_start, t))
                in_sess = False
    
    if in_sess and s_start is not None:
        sessions.append((s_start, pressed.index[-1] + pd.Timedelta(minutes=1)))
    
    # Analyze each session
    for (s, e) in sessions:
        dur_min = int((e - s).total_seconds() // 60)
        if dur_min < Config.SLEEP_MIN_SESSION_MIN:
            continue
        
        # Get segment data
        seg_idx = pd.date_range(s, e - pd.Timedelta(minutes=1), freq="1min")
        seg_idx = seg_idx.intersection(df_minutes.index)
        if len(seg_idx) == 0:
            continue
        
        seg = df_minutes.loc[seg_idx, "bedroom_motion"]
        turnover_minutes = seg[seg >= Config.SLEEP_TURNOVER_THRESHOLD].index.tolist()
        turnovers = len(turnover_minutes)
        
        # Info: sleep session
        alerts_local.append({
            "ts_start": s,
            "ts_end": e - pd.Timedelta(seconds=1),
            "type": "info",
            "label": "sleep_session",
            "score": None,
            "features": {
                "duration_min": dur_min,
                "turnovers": int(turnovers),
                "quiet_hours": 1
            },
            "explanations": [
                f"Continuous bed pressure for {dur_min} min during quiet hours",
                f"{turnovers} position changes detected"
            ]
        })
        
        # Guard: possible immobility
        if Config.SLEEP_IMMOBILITY_GAP_MIN > 0:
            times = [s] + turnover_minutes + [e]
            max_gap = 0
            for i in range(1, len(times)):
                gap = int((times[i] - times[i-1]).total_seconds() // 60)
                if gap > max_gap:
                    max_gap = gap
            
            if max_gap >= Config.SLEEP_IMMOBILITY_GAP_MIN:
                alerts_local.append({
                    "ts_start": s,
                    "ts_end": e - pd.Timedelta(seconds=1),
                    "type": "guard",
                    "label": "possible_immobility",
                    "score": None,
                    "features": {
                        "max_gap_min": int(max_gap),
                        "threshold_min": int(Config.SLEEP_IMMOBILITY_GAP_MIN)
                    },
                    "explanations": [
                        f"No turnover ≥{Config.SLEEP_TURNOVER_THRESHOLD} for ≥{Config.SLEEP_IMMOBILITY_GAP_MIN} min during sleep"
                    ]
                })
    
    return alerts_local


# ============================================================================
# ANOMALY INCIDENT GROUPING
# ============================================================================
def group_anomaly_incidents(df_anom: pd.DataFrame) -> List[Dict]:
    """Group anomaly windows into incidents with temporal proximity."""
    incidents = []
    cur = []
    
    for _, row in df_anom.iterrows():
        if not cur:
            cur = [row]
            continue
        
        gap = (row["ts"] - cur[-1]["ts"]).total_seconds() / 60.0
        if gap <= Config.MIN_ALERT_GAP_MIN:
            cur.append(row)
        else:
            incidents.append(cur)
            cur = [row]
    
    if cur:
        incidents.append(cur)
    
    out = []
    for inc in incidents:
        start = inc[0]["ts"]
        end = inc[-1]["ts"]
        peak = max(inc, key=lambda r: r["anomaly_score"])
        
        label = ("night_wandering" 
                 if peak["is_quiet"] == 1 and peak["room_transitions"] >= Config.QUIET_TRANSITIONS_ANOMALY 
                 else "unusual_activity")
        
        out.append({
            "ts_start": start,
            "ts_end": end,
            "type": "anomaly",
            "label": label,
            "score": float(peak["anomaly_score"]),
            "features": {
                "motion_sum": int(peak["motion_sum"]),
                "unique_rooms": int(peak["unique_rooms"]),
                "room_transitions": int(peak["room_transitions"]),
                "oven_on_frac": float(peak["oven_on_frac"]),
                "is_quiet": int(peak["is_quiet"])
            },
            "explanations": [
                "High motion during quiet hours" if peak["is_quiet"] == 1 else "Unusual activity vs routine",
                "Frequent room transitions" if peak["room_transitions"] >= Config.QUIET_TRANSITIONS_ANOMALY else "Activity spike"
            ]
        })
    
    return out


# ============================================================================
# MAIN PIPELINE
# ============================================================================
def run_pipeline_from_df(df_input: pd.DataFrame, 
                         save_output: bool = True, 
                         tag: str = "from_df",
                         household_id: str = "H1") -> List[Dict]:
    """
    Run full detection pipeline on input DataFrame.
    
    Args:
        df_input: DataFrame with DatetimeIndex and required sensor columns
        save_output: Whether to save alerts to JSON file
        tag: Tag for output filename
        household_id: Household identifier for alerts
    
    Returns:
        List of alert dictionaries
    """
    logger.info(f"Starting pipeline for {len(df_input)} rows")
    
    # Validate input
    validate_input_dataframe(df_input)
    df_local = df_input.copy()
    
    # ========== 1. Presence Detection ==========
    for room in Config.ROOMS:
        if f"{room}_present_raw" not in df_local.columns:
            df_local[f"{room}_present_raw"] = (df_local[f"{room}_motion"] > 0).astype(int)
    
    for room in Config.ROOMS:
        df_local[f"{room}_present"] = debounce_series(df_local[f"{room}_present_raw"])
    
    # ========== 2. Current Room Trace ==========
    current_rooms = []
    prev_r = None
    for _, row in df_local.iterrows():
        cr = infer_current_room(row, prev_r)
        current_rooms.append(cr)
        prev_r = cr
    df_local["current_room"] = current_rooms
    
    # ========== 3. Windowing + Features ==========
    windows = []
    feature_rows = []
    
    for end_idx in range(Config.WINDOW_MIN - 1, len(df_local), Config.HOP_MIN):
        win = df_local.iloc[end_idx - (Config.WINDOW_MIN - 1): end_idx + 1]
        if len(win) == Config.WINDOW_MIN:
            windows.append(df_local.index[end_idx])
            feature_rows.append(make_features(win))
    
    if len(windows) == 0:
        logger.warning("No complete windows found")
        return []
    
    X = pd.DataFrame(feature_rows)
    X["ts"] = windows
    
    # ========== 4. Isolation Forest Training ==========
    model_cols = ["motion_sum_sqrt", "unique_rooms", "oven_on_frac", 
                  "room_transitions", "sin_hour", "cos_hour", "is_quiet"]
    
    train_idx = [i for i, w in enumerate(windows) if w.hour < 12]
    if len(train_idx) < 10:
        logger.warning("Insufficient training data (< 10 windows)")
        train_idx = list(range(min(len(windows), 50)))
    
    X_train = X.iloc[train_idx]
    
    scaler = StandardScaler().fit(X_train[model_cols])
    X_scaled = scaler.transform(X[model_cols])
    
    if_model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=Config.RNG_SEED
    ).fit(scaler.transform(X_train[model_cols]))
    
    dec = if_model.decision_function(X_scaled)
    X["anomaly_score"] = -dec
    
    # ========== 5. Adaptive Thresholds ==========
    thr_by_hour = (X.groupby(X["ts"].dt.hour)["anomaly_score"]
                   .quantile(Config.ANOM_PCTL_PER_HOUR / 100.0)
                   .to_dict())
    
    global_thr = np.quantile(X["anomaly_score"], Config.ANOM_PCTL_PER_HOUR / 100.0)
    X["threshold"] = X["ts"].dt.hour.map(lambda h: thr_by_hour.get(h, global_thr))
    
    # ========== 6. Candidate Detection ==========
    X["is_candidate"] = X.apply(is_candidate_anomaly, axis=1)
    
    # ========== 7. Guards ==========
    guard_alerts = oven_left_on_guard(df_local["oven_power_w"])
    sleep_alerts = sleep_sessions_from_bed(df_local)
    
    # ========== 8. Anomaly Incident Grouping ==========
    cand = X[X["is_candidate"]].copy()
    anomaly_incidents = group_anomaly_incidents(cand)
    
    # ========== 9. Normalize Alerts ==========
    def normalize_alert(a: Dict) -> Dict:
        return {
            "id": str(uuid.uuid4()),
            "ts_start": a["ts_start"].isoformat(),
            "ts_end": a["ts_end"].isoformat(),
            "type": a["type"],
            "label": a["label"],
            "score": a["score"],
            "features": a["features"],
            "explanations": a["explanations"],
            "snoozed_until": None,
            "ack_status": "new",
            "household_id": household_id,
            "policy_context": {
                "quiet_hours": f"{Config.QUIET_START:02d}:00-{Config.QUIET_END:02d}:00"
            }
        }
    
    alerts = [normalize_alert(a) for a in (guard_alerts + anomaly_incidents + sleep_alerts)]
    
    logger.info(f"Generated {len(alerts)} alerts: "
                f"{sum(1 for a in alerts if a['type']=='guard')} guards, "
                f"{sum(1 for a in alerts if a['type']=='anomaly')} anomalies, "
                f"{sum(1 for a in alerts if a['type']=='info')} info")
    
    # ========== 10. Save Output ==========
    if save_output:
        from datetime import date
        out_path = f"alerts_{date.today().isoformat()}_{tag}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"alerts": alerts}, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {out_path}")
    
    return alerts


# ============================================================================
# DEMO DATA GENERATION
# ============================================================================
def generate_demo_data() -> pd.DataFrame:
    """Generate 24-hour demo dataset with injected anomalies."""
    start = datetime(2025, 1, 1, 0, 0, 0)
    minutes = 24 * 60
    ts = pd.date_range(start, periods=minutes, freq="1min")
    
    rng = np.random.default_rng(Config.RNG_SEED)
    
    def day_night_rate(hour):
        return 2.5 if 8 <= hour < 22 else 0.3
    
    data = {
        "hall_motion": [],
        "kitchen_motion": [],
        "bedroom_motion": [],
        "oven_power_w": []
    }
    
    for t in ts:
        r = day_night_rate(t.hour)
        data["hall_motion"].append(rng.poisson(r))
        data["kitchen_motion"].append(rng.poisson(r * 0.8))
        data["bedroom_motion"].append(rng.poisson(0.6 if is_quiet_hour(t.hour) else 0.1))
        data["oven_power_w"].append(0)
    
    df = pd.DataFrame(data, index=ts)
    
    # Normal lunch cooking
    df.loc[(df.index.hour == 13) & (df.index.minute < 25), "oven_power_w"] = 850
    
    # Inject night wandering at 2 AM
    mask_wander_motion = (df.index.hour == 2) & (df.index.minute < 25)
    df.loc[mask_wander_motion, ["hall_motion", "kitchen_motion"]] += rng.poisson(3.5, size=(mask_wander_motion.sum(), 2))
    
    # Create room transitions
    block_times = df[mask_wander_motion].index
    for i, t in enumerate(block_times):
        if i % 4 < 2:
            df.loc[t, "hall_motion"] += 2
        else:
            df.loc[t, "kitchen_motion"] += 2
    
    # Inject oven left on at 11 PM
    mask_oven = (df.index.hour == 23)
    df.loc[mask_oven, "oven_power_w"] = 900
    
    return df


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    logger.info("Generating demo data...")
    df = generate_demo_data()
    
    logger.info("Running detection pipeline...")
    alerts = run_pipeline_from_df(df, save_output=True, tag="sim")
    
    print("\n" + "="*60)
    print("ALERTS JSON PAYLOAD")
    print("="*60)
    print(json.dumps({"alerts": alerts}, indent=2))