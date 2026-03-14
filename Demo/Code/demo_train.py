"""
================================================================================
DEMO — Train the Night Wandering Model
================================================================================

Generates synthetic "normal bedroom at night" data and trains an Isolation Forest.
Run this BEFORE the demo day. No sensors needed — it creates fake data.

WHAT IT TRAINS ON (normal patterns):
  - Person sleeping in bed: pressure HIGH, presence NEAR, PIR quiet, light NIGHT
  - Brief bathroom trip: short absence then return (normal, not anomaly)
  - Evening settle-in: person getting into bed

WHAT WILL BE ANOMALOUS (flagged during demo):
  - Person out of bed for extended time at night
  - Bed empty + presence absent + PIR out + light night = NIGHT WANDERING

Usage:
  python3 demo_train.py                            # Default training
  python3 demo_train.py --config demo_config.json  # Custom config

Output:
  models/demo_model.pkl    — Trained Isolation Forest
  models/demo_scaler.pkl   — Feature scaler
  models/demo_stats.json   — Training statistics

After training, run:  python3 demo_run.py

================================================================================
"""

import json
import os
import sys
import argparse
import numpy as np
import joblib
import logging
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("demo_train")


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE NAMES — 12 bedroom-focused features
# ═══════════════════════════════════════════════════════════════════════════════

FEATURE_NAMES = [
    "hour_normalized",           # 0–1 (hour / 24)
    "is_sleep_time",             # 1 if 22–07, else 0
    "bed_occupancy_rate",        # % of window with pressure > occupied threshold
    "bed_pressure_mean",         # Mean pressure value (normalized 0–1)
    "bed_pressure_std",          # Pressure variation in window
    "presence_near_rate",        # % of window with presence ≤ near_cm
    "presence_mean_distance",    # Mean distance (normalized 0–1, /600)
    "presence_std_distance",     # Distance variation in window
    "pir_in_rate",               # % of window where PIR = IN (person in room)
    "light_night_rate",          # % of window where light = Night
    "bed_transitions",           # Occupied↔Empty transitions (normalized)
    "stillness_score",           # Combined low-PIR + stable-pressure score
]

NUM_FEATURES = len(FEATURE_NAMES)


def extract_features(window, config):
    """Extract 12 features from a window of sensor snapshots."""
    n = len(window)
    if n == 0:
        return np.zeros(NUM_FEATURES)

    th = config["thresholds"]
    hours = np.array([s["sim_hour"] for s in window])
    avg_hour = np.mean(hours)

    pressures = np.array([s["pressure"] for s in window])
    distances = np.array([s["presence_cm"] for s in window])
    pir_states = np.array([s["pir_in"] for s in window])
    light_states = np.array([s["light_night"] for s in window])

    # 1. Hour normalized
    f_hour = avg_hour / 24.0

    # 2. Is sleep time (22:00–07:00)
    f_sleep = 1.0 if (avg_hour >= 22 or avg_hour < 7) else 0.0

    # 3. Bed occupancy rate
    occupied = np.array([1.0 if p >= th["pressure_occupied"] else 0.0 for p in pressures])
    f_bed_occ = np.mean(occupied)

    # 4. Bed pressure mean (normalized to 0–1)
    f_pres_mean = np.mean(pressures) / 5000.0

    # 5. Bed pressure std (normalized)
    f_pres_std = np.std(pressures) / 5000.0

    # 6. Presence near rate
    near = np.array([1.0 if d <= th["presence_near_cm"] else 0.0 for d in distances])
    f_near_rate = np.mean(near)

    # 7. Presence mean distance (normalized, /600)
    f_dist_mean = np.clip(np.mean(distances) / 600.0, 0, 1)

    # 8. Presence distance std
    f_dist_std = np.std(distances) / 600.0

    # 9. PIR in-room rate
    f_pir_in = np.mean(pir_states)

    # 10. Light night rate
    f_light_night = np.mean(light_states)

    # 11. Bed transitions (normalized: 0 transitions = 0, many = high)
    transitions = sum(1 for i in range(1, n) if occupied[i] != occupied[i - 1])
    f_transitions = min(transitions / 10.0, 1.0)

    # 12. Stillness score: high when pressure stable + low PIR activity
    pressure_stability = 1.0 / (1.0 + np.var(pressures) / 1e6)
    pir_quiet = 1.0 - np.mean(pir_states)  # Inverted: quiet = 1
    f_stillness = (pressure_stability * 0.5 + pir_quiet * 0.5)

    features = [
        f_hour, f_sleep, f_bed_occ, f_pres_mean, f_pres_std,
        f_near_rate, f_dist_mean, f_dist_std,
        f_pir_in, f_light_night, f_transitions, f_stillness,
    ]

    assert len(features) == NUM_FEATURES
    return np.array(features, dtype=np.float64)


# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC DATA GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_training_data(config, num_nights=5):
    """
    Generate synthetic normal bedroom data for multiple simulated nights.

    Each night (22:00–07:00 = 9 hours) produces ~64,800 samples at 2Hz.
    We also include evening settle-in (21:00–22:00) and morning (07:00–08:00).

    Normal patterns include:
      - Deep sleep: person in bed, stable pressure, near presence, no PIR, dark
      - Light sleep: slight pressure variation, occasional tiny movements
      - Bathroom trips: 1-2 per night, person leaves bed for 2-5 minutes then returns
      - Settle-in: getting into bed, pressure ramps up
      - Wake up: pressure drops, light changes, person gets up
    """
    data = []
    sample_rate = config["ml"]["sample_rate_hz"]
    th = config["thresholds"]

    print(f"  Generating {num_nights} simulated nights...")
    print(f"  Each night: 21:00–08:00 (11 hours × {sample_rate}Hz = "
          f"{11 * 3600 * sample_rate:,} samples)")

    for night in range(num_nights):
        night_data = []

        # Simulate 21:00 to 08:00 (11 hours)
        total_samples = 11 * 3600 * sample_rate
        bathroom_trip_times = _random_bathroom_trips(num_trips=np.random.randint(0, 3))

        for sample_idx in range(total_samples):
            # Current simulated hour
            sec = sample_idx / sample_rate
            hour = 21.0 + sec / 3600.0
            if hour >= 24:
                hour -= 24  # Wrap past midnight

            noise = np.random.normal(0, 1)

            # Determine state
            is_bathroom_trip = _in_bathroom_trip(sec, bathroom_trip_times)

            if is_bathroom_trip:
                # Person is out of bed (brief bathroom trip — NORMAL)
                snapshot = {
                    "sim_hour": hour,
                    "pressure": max(0, 50 + abs(noise * 20)),      # Low/empty
                    "presence_cm": 300 + abs(noise * 50),           # Far/absent
                    "pir_in": 0.0,                                   # Out of room
                    "light_night": 1.0,                              # Still dark
                }
            elif hour >= 21 and hour < 22:
                # Evening settle-in: gradually getting into bed
                progress = (hour - 21.0)  # 0 to 1
                if progress < 0.5:
                    # Still up, moving around
                    snapshot = {
                        "sim_hour": hour,
                        "pressure": max(0, 100 + noise * 30),
                        "presence_cm": max(0, 40 + noise * 20),
                        "pir_in": 1.0 if np.random.random() > 0.3 else 0.0,
                        "light_night": 0.0,  # Light still on
                    }
                else:
                    # Getting into bed
                    snapshot = {
                        "sim_hour": hour,
                        "pressure": max(0, 800 + noise * 100),
                        "presence_cm": max(0, 25 + noise * 10),
                        "pir_in": 1.0 if np.random.random() > 0.6 else 0.0,
                        "light_night": 1.0 if progress > 0.8 else 0.0,
                    }
            elif (hour >= 22 or hour < 6.5):
                # Deep sleep
                snapshot = {
                    "sim_hour": hour,
                    "pressure": max(0, 1200 + noise * 80),          # Solidly in bed
                    "presence_cm": max(0, 20 + abs(noise * 8)),     # Very near
                    "pir_in": 0.0,                                   # No motion
                    "light_night": 1.0,                              # Dark
                }
                # Occasional toss/turn
                if np.random.random() < 0.02:
                    snapshot["pressure"] += np.random.normal(0, 200)
                    snapshot["pir_in"] = 1.0
            elif hour >= 6.5 and hour < 7.5:
                # Waking up: gradual transitions
                progress = (hour - 6.5) / 1.0
                snapshot = {
                    "sim_hour": hour,
                    "pressure": max(0, 1200 - progress * 1000 + noise * 100),
                    "presence_cm": max(0, 20 + progress * 80 + noise * 15),
                    "pir_in": 1.0 if np.random.random() > (0.7 - progress * 0.5) else 0.0,
                    "light_night": 0.0 if progress > 0.3 else 1.0,
                }
            else:
                # Morning, out of bed (07:30–08:00)
                snapshot = {
                    "sim_hour": hour,
                    "pressure": max(0, 50 + abs(noise * 20)),
                    "presence_cm": max(0, 100 + abs(noise * 50)),
                    "pir_in": 1.0 if np.random.random() > 0.4 else 0.0,
                    "light_night": 0.0,
                }

            # Clamp values
            snapshot["pressure"] = max(0, min(5000, snapshot["pressure"]))
            snapshot["presence_cm"] = max(0, min(600, snapshot["presence_cm"]))
            night_data.append(snapshot)

        data.extend(night_data)
        print(f"    Night {night + 1}/{num_nights}: {len(night_data):,} samples")

    print(f"  Total: {len(data):,} samples")
    return data


def _random_bathroom_trips(num_trips):
    """Generate random bathroom trip start times (as offset seconds from 21:00)."""
    trips = []
    for _ in range(num_trips):
        # Trips happen during sleep hours (22:00–06:00 = offset 3600–32400)
        start_sec = np.random.randint(3600, 32400)
        duration_sec = np.random.randint(120, 300)  # 2–5 minutes
        trips.append((start_sec, start_sec + duration_sec))
    return trips


def _in_bathroom_trip(current_sec, trips):
    for start, end in trips:
        if start <= current_sec <= end:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING
# ═══════════════════════════════════════════════════════════════════════════════

def train_model(data, config):
    """Extract features, scale, train Isolation Forest."""
    ml_cfg = config["ml"]
    ws = ml_cfg["window_size"]
    step = ml_cfg["window_step"]

    print(f"\n  📊 Extracting features...")
    print(f"     Window: {ws} samples ({ws / ml_cfg['sample_rate_hz']:.0f}s)")
    print(f"     Step: {step} samples ({step / ml_cfg['sample_rate_hz']:.1f}s)")

    feature_vectors = []
    for i in range(0, len(data) - ws, step):
        window = data[i:i + ws]
        fv = extract_features(window, config)
        feature_vectors.append(fv)

    X = np.array(feature_vectors)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    print(f"     Generated {len(X):,} vectors × {X.shape[1]} features")

    # Feature stats
    print(f"\n  📈 Feature statistics:")
    for i, name in enumerate(FEATURE_NAMES):
        col = X[:, i]
        print(f"     {i + 1:2d}. {name:28s} "
              f"mean={np.mean(col):7.4f}  std={np.std(col):7.4f}  "
              f"min={np.min(col):7.4f}  max={np.max(col):7.4f}")

    # Scale
    print(f"\n  ⚖️  Scaling features...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train
    contamination = ml_cfg["contamination"]
    n_estimators = ml_cfg["n_estimators"]
    print(f"\n  🌲 Training Isolation Forest...")
    print(f"     Trees: {n_estimators}  |  Contamination: {contamination}")

    model = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=42,
        max_samples="auto",
        n_jobs=-1
    )
    model.fit(X_scaled)

    # Evaluate
    predictions = model.predict(X_scaled)
    scores = model.score_samples(X_scaled)
    n_normal = int(np.sum(predictions == 1))
    n_anomaly = int(np.sum(predictions == -1))

    print(f"\n  ✅ Model trained!")
    print(f"     Normal:  {n_normal:,} ({n_normal / len(X) * 100:.1f}%)")
    print(f"     Anomaly: {n_anomaly:,} ({n_anomaly / len(X) * 100:.1f}%)")
    print(f"     Scores:  [{np.min(scores):.4f}, {np.max(scores):.4f}]")
    print(f"     Mean:    {np.mean(scores):.4f} ± {np.std(scores):.4f}")

    return model, scaler, {
        "total_samples": len(data),
        "feature_vectors": len(X),
        "feature_count": NUM_FEATURES,
        "feature_names": FEATURE_NAMES,
        "normal": n_normal,
        "anomaly": n_anomaly,
        "anomaly_ratio": round(n_anomaly / len(X), 4),
        "score_mean": round(float(np.mean(scores)), 4),
        "score_std": round(float(np.std(scores)), 4),
        "contamination": contamination,
        "n_estimators": n_estimators,
        "window_size": ws,
        "window_step": step,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Train Demo Night Wandering Model")
    parser.add_argument("--config", default="demo_config.json")
    parser.add_argument("--nights", type=int, default=5,
                        help="Number of simulated nights to generate (default: 5)")
    args = parser.parse_args()

    # Load config
    with open(args.config) as f:
        config = json.load(f)

    print("\n" + "=" * 65)
    print("  🧠 DEMO — TRAIN NIGHT WANDERING MODEL")
    print(f"  Features: {NUM_FEATURES}  |  Algorithm: Isolation Forest")
    print(f"  Simulated nights: {args.nights}")
    print("=" * 65)

    # Generate synthetic data
    print(f"\n  📦 STEP 1: Generate synthetic training data\n")
    data = generate_training_data(config, num_nights=args.nights)

    # Train
    print(f"\n  🧠 STEP 2: Train Isolation Forest\n")
    model, scaler, stats = train_model(data, config)

    # Save
    os.makedirs(os.path.dirname(config["paths"]["model_file"]) or ".", exist_ok=True)

    model_path = config["paths"]["model_file"]
    scaler_path = config["paths"]["scaler_file"]
    stats_path = config["paths"]["stats_file"]

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    stats["trained_at"] = datetime.now().isoformat()
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n  💾 Saved:")
    print(f"     Model:  {model_path}")
    print(f"     Scaler: {scaler_path}")
    print(f"     Stats:  {stats_path}")

    # Quick anomaly test
    print(f"\n  🧪 STEP 3: Quick anomaly test\n")
    _test_anomaly_detection(model, scaler, config)

    print(f"\n{'=' * 65}")
    print(f"  ✅ TRAINING COMPLETE — Model ready for demo!")
    print(f"  ▶  Next: python3 demo_run.py")
    print(f"{'=' * 65}\n")


def _test_anomaly_detection(model, scaler, config):
    """Generate a few test windows to verify the model works."""
    ws = config["ml"]["window_size"]

    # Normal: person sleeping
    normal_window = []
    for i in range(ws):
        normal_window.append({
            "sim_hour": 2.0,
            "pressure": 1200 + np.random.normal(0, 50),
            "presence_cm": 20 + abs(np.random.normal(0, 5)),
            "pir_in": 0.0,
            "light_night": 1.0,
        })

    fv_normal = extract_features(normal_window, config)
    fv_scaled = scaler.transform(fv_normal.reshape(1, -1))
    pred = model.predict(fv_scaled)[0]
    score = model.score_samples(fv_scaled)[0]
    print(f"     Normal sleep:     pred={'NORMAL' if pred == 1 else 'ANOMALY':8s}  "
          f"score={score:.4f}")

    # Anomaly: person out of bed at night (NIGHT WANDERING)
    anomaly_window = []
    for i in range(ws):
        anomaly_window.append({
            "sim_hour": 2.0,
            "pressure": 30 + abs(np.random.normal(0, 10)),     # Empty bed
            "presence_cm": 400 + abs(np.random.normal(0, 50)),  # Not in room
            "pir_in": 0.0,                                       # No motion
            "light_night": 1.0,                                  # Dark
        })

    fv_anomaly = extract_features(anomaly_window, config)
    fv_scaled = scaler.transform(fv_anomaly.reshape(1, -1))
    pred = model.predict(fv_scaled)[0]
    score = model.score_samples(fv_scaled)[0]
    print(f"     Night wandering:  pred={'NORMAL' if pred == 1 else 'ANOMALY':8s}  "
          f"score={score:.4f}")

    # Edge case: bathroom trip (brief absence)
    trip_window = []
    for i in range(ws):
        if i < ws * 0.7:
            # In bed
            trip_window.append({
                "sim_hour": 3.0,
                "pressure": 1200 + np.random.normal(0, 50),
                "presence_cm": 20 + abs(np.random.normal(0, 5)),
                "pir_in": 0.0,
                "light_night": 1.0,
            })
        else:
            # Brief trip
            trip_window.append({
                "sim_hour": 3.0,
                "pressure": 50 + abs(np.random.normal(0, 20)),
                "presence_cm": 300 + abs(np.random.normal(0, 40)),
                "pir_in": 0.0,
                "light_night": 1.0,
            })

    fv_trip = extract_features(trip_window, config)
    fv_scaled = scaler.transform(fv_trip.reshape(1, -1))
    pred = model.predict(fv_scaled)[0]
    score = model.score_samples(fv_scaled)[0]
    print(f"     Bathroom trip:    pred={'NORMAL' if pred == 1 else 'ANOMALY':8s}  "
          f"score={score:.4f}")


if __name__ == "__main__":
    main()
