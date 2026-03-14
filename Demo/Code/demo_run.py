"""
================================================================================
DEMO — Night Wandering Detection (Bedroom + Hallway LEDs)
================================================================================

THE DEMO SCRIPT. Run this on demo day after pre-training.

SIMULATED TIME:
  Starts at 22:00 (configurable with --start-hour).
  Runs at 60x speed by default (1 real minute = 1 simulated hour).
  So from 22:00 to 02:00 takes ~4 real minutes.
  Use --speed to change: --speed 30 means 1 real min = 30 simulated min.

  The clock is displayed on screen so the supervisor sees:
    SIM 02:15 AM  |  Bed: EMPTY   Pres: ABSENT ...

  When you see it's ~2 AM, trigger the anomaly by removing pressure,
  stepping away from presence, etc.

CLOUD API (Daniel):
  On startup, this script:
    1. Creates a resident profile in the database
    2. Uploads the trained model (if not already uploaded)
  During runtime:
    3. Pushes every alert (Rule + ML) to POST /alerts
  So Luis's app can show alerts in real time.

DETECTION LOGIC (all must be true simultaneously):
  Pressure:  bed EMPTY   (< 500)
  Presence:  ABSENT      (> 200 cm)
  PIR:       OUT         (no motion in room)
  Light:     NIGHT       (dark)
  Clock:     Sleep hours (22:00-07:00 simulated)

  -> NIGHT WANDERING DETECTED -> LEDs ON + Alert

  Person returns (pressure > 500 OR presence < 50)
  -> Wait 5s grace period -> LEDs OFF

USAGE:
  python3 demo_run.py                           # Default: start 22:00, 60x speed
  python3 demo_run.py --start-hour 23           # Start at 23:00
  python3 demo_run.py --speed 30                # Slower: 1 min = 30 sim-min
  python3 demo_run.py --speed 120               # Faster: 1 min = 2 sim-hours
  python3 demo_run.py --rules-only              # No ML, just rule engine
  python3 demo_run.py --no-cloud                # Skip cloud API calls

================================================================================
"""

import paho.mqtt.client as mqtt
import numpy as np
import json
import time
import os
import sys
import base64
import argparse
import joblib
import logging
import requests
from datetime import datetime
from collections import deque
from threading import Lock

# ===========================================================================
# LOGGING
# ===========================================================================

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/demo_run.log"),
    ]
)
logger = logging.getLogger("demo_run")


# ===========================================================================
# SIMULATED CLOCK
# ===========================================================================

class SimulatedClock:
    """
    A clock that starts at a given hour and advances at accelerated speed.

    Example: start_hour=22.0, speed=60
      1 real second  = 1 simulated minute
      1 real minute  = 1 simulated hour
      4 real minutes = 22:00 -> 02:00
    """

    def __init__(self, start_hour=22.0, speed=60):
        self.start_hour = start_hour
        self.speed = speed
        self.real_start = time.time()

    def now(self):
        """Returns current simulated hour as float (0.0-23.99)."""
        elapsed_real = time.time() - self.real_start
        elapsed_sim_hours = (elapsed_real * self.speed) / 3600.0
        sim_hour = self.start_hour + elapsed_sim_hours
        return sim_hour % 24.0

    def now_str(self):
        """Returns simulated time as 'HH:MM' string."""
        h = self.now()
        hours = int(h) % 24
        minutes = int((h % 1) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def now_label(self):
        """Returns simulated time as ' 2:15 AM' style string."""
        h = self.now()
        hours = int(h) % 24
        minutes = int((h % 1) * 60)
        ampm = "AM" if hours < 12 else "PM"
        h12 = hours if hours <= 12 else hours - 12
        if h12 == 0:
            h12 = 12
        return f"{h12:2d}:{minutes:02d} {ampm}"

    def is_sleep_time(self):
        """True during 22:00-07:00."""
        h = self.now()
        return h >= 22.0 or h < 7.0

    def elapsed_real(self):
        """Real seconds since start."""
        return time.time() - self.real_start

    def elapsed_str(self):
        """Real elapsed time as 'Xm Ys'."""
        e = self.elapsed_real()
        m = int(e // 60)
        s = int(e % 60)
        return f"{m}m {s:02d}s"


# ===========================================================================
# FEATURE EXTRACTION - Must match demo_train.py exactly
# ===========================================================================

FEATURE_NAMES = [
    "hour_normalized",
    "is_sleep_time",
    "bed_occupancy_rate",
    "bed_pressure_mean",
    "bed_pressure_std",
    "presence_near_rate",
    "presence_mean_distance",
    "presence_std_distance",
    "pir_in_rate",
    "light_night_rate",
    "bed_transitions",
    "stillness_score",
]

NUM_FEATURES = len(FEATURE_NAMES)


def extract_features(window, config):
    """Extract 12 features from a window - matches demo_train.py exactly."""
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

    f_hour = avg_hour / 24.0
    f_sleep = 1.0 if (avg_hour >= 22 or avg_hour < 7) else 0.0

    occupied = np.array([1.0 if p >= th["pressure_occupied"] else 0.0 for p in pressures])
    f_bed_occ = np.mean(occupied)
    f_pres_mean = np.mean(pressures) / 5000.0
    f_pres_std = np.std(pressures) / 5000.0

    near = np.array([1.0 if d <= th["presence_near_cm"] else 0.0 for d in distances])
    f_near_rate = np.mean(near)
    f_dist_mean = np.clip(np.mean(distances) / 600.0, 0, 1)
    f_dist_std = np.std(distances) / 600.0

    f_pir_in = np.mean(pir_states)
    f_light_night = np.mean(light_states)

    transitions = sum(1 for i in range(1, n) if occupied[i] != occupied[i - 1])
    f_transitions = min(transitions / 10.0, 1.0)

    pressure_stability = 1.0 / (1.0 + np.var(pressures) / 1e6)
    pir_quiet = 1.0 - np.mean(pir_states)
    f_stillness = (pressure_stability * 0.5 + pir_quiet * 0.5)

    features = [
        f_hour, f_sleep, f_bed_occ, f_pres_mean, f_pres_std,
        f_near_rate, f_dist_mean, f_dist_std,
        f_pir_in, f_light_night, f_transitions, f_stillness,
    ]

    assert len(features) == NUM_FEATURES
    return np.array(features, dtype=np.float64)


# ===========================================================================
# SENSOR MANAGER - Handles Mia's ESP32 data formats
# ===========================================================================

class DemoSensorManager:
    """
    MQTT manager for 4 bedroom sensors + LED control.
    Handles Mia's actual ESP32 formats:
      - Pressure:  integer 0-5000 (ADC mapped)
      - PIR:       "IN" / "OUT" strings
      - Presence:  float distance in cm
      - Light:     "Day" / "Night" strings
    """

    def __init__(self, config):
        self.config = config
        self.lock = Lock()
        self.connected = False

        self.pressure = 0.0
        self.pir_in = False
        self.presence_cm = 600.0
        self.light_night = False

        self.last_update = {
            "pressure": 0.0, "pir": 0.0,
            "presence": 0.0, "light": 0.0,
        }

        self.buffer = deque(maxlen=5000)

        cid = f"{config['mqtt']['client_id_prefix']}_{datetime.now().strftime('%H%M%S')}"
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=cid
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def connect(self):
        broker = self.config["mqtt"]["broker"]
        port = self.config["mqtt"]["port"]
        logger.info(f"Connecting to MQTT {broker}:{port}...")
        try:
            self.client.connect(broker, port, keepalive=60)
            self.client.loop_start()
            time.sleep(2)
            return self.connected
        except Exception as e:
            logger.error(f"MQTT error: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            for key, topic in self.config["mqtt"]["sensors"].items():
                client.subscribe(topic, qos=1)
            logger.info("MQTT connected - listening to 4 bedroom sensors")
        else:
            self.connected = False
            logger.error(f"MQTT connect failed: rc={rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self.connected = False
        if rc != 0:
            logger.warning(f"MQTT disconnected: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8').strip()
            now = time.time()

            with self.lock:
                if topic == self.config["mqtt"]["sensors"]["bedroom_pressure"]:
                    try:
                        self.pressure = float(payload)
                    except ValueError:
                        pass
                    self.last_update["pressure"] = now

                elif topic == self.config["mqtt"]["sensors"]["bedroom_pir"]:
                    p = payload.upper()
                    self.pir_in = p in ["IN", "1", "TRUE", "MOTION"]
                    self.last_update["pir"] = now

                elif topic == self.config["mqtt"]["sensors"]["bedroom_presence"]:
                    try:
                        self.presence_cm = float(payload)
                    except ValueError:
                        pass
                    self.last_update["presence"] = now

                elif topic == self.config["mqtt"]["sensors"]["bedroom_light"]:
                    p = payload.lower()
                    if p in ["night", "0"]:
                        self.light_night = True
                    elif p in ["day", "1"]:
                        self.light_night = False
                    else:
                        try:
                            self.light_night = float(payload) < 50
                        except ValueError:
                            pass
                    self.last_update["light"] = now

        except Exception:
            pass

    def take_snapshot(self, sim_hour):
        """Snapshot current sensors, stamped with the SIMULATED hour."""
        with self.lock:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "sim_hour": sim_hour,
                "pressure": self.pressure,
                "presence_cm": self.presence_cm,
                "pir_in": 1.0 if self.pir_in else 0.0,
                "light_night": 1.0 if self.light_night else 0.0,
            }
        self.buffer.append(snapshot)
        return snapshot

    def get_recent_window(self, window_size):
        if len(self.buffer) < window_size:
            return None
        return list(self.buffer)[-window_size:]

    def publish_led(self, on):
        payload = "ON" if on else "OFF"
        topic = self.config["mqtt"]["actuators"]["hallway_led"]
        self.client.publish(topic, payload, qos=1, retain=True)

    def get_sensor_status(self):
        th = self.config["thresholds"]
        with self.lock:
            bed = "OCCUPIED" if self.pressure >= th["pressure_occupied"] else "EMPTY"
            if self.presence_cm <= th["presence_near_cm"]:
                pres = "NEAR"
            elif self.presence_cm <= th["presence_far_cm"]:
                pres = "FAR"
            else:
                pres = "ABSENT"
            pir = "IN" if self.pir_in else "OUT"
            light = "NIGHT" if self.light_night else "DAY"
        return bed, pres, pir, light

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()


# ===========================================================================
# RULE ENGINE
# ===========================================================================

class DemoRuleEngine:
    """Deterministic night wandering detection - active from second 1."""

    def __init__(self, config):
        self.config = config
        self.last_alert_time = 0
        self.cooldown_sec = config["demo"]["alert_cooldown_sec"]

    def check(self, snapshot, sim_clock):
        """Returns alert dict if night wandering detected, else None."""
        th = self.config["thresholds"]
        now = time.time()

        bed_empty = snapshot["pressure"] < th["pressure_occupied"]
        presence_absent = snapshot["presence_cm"] > th["presence_far_cm"]
        pir_out = snapshot["pir_in"] == 0.0
        is_night = sim_clock.is_sleep_time()

        if bed_empty and presence_absent and pir_out and is_night:
            if (now - self.last_alert_time) < self.cooldown_sec:
                return None

            self.last_alert_time = now
            return {
                "alert_id": f"RULE_NIGHT_WANDERING_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "rule_type": "NIGHT_WANDERING",
                "severity": "HIGH",
                "message": f"Person out of bed at {sim_clock.now_label()} - "
                           f"bed empty, not in room, dark",
                "recommended_action": "Check on resident - possible disorientation",
                "source": "RULE_ENGINE",
                "anomaly_score": None,
                "sensor_data": {
                    "bed_pressure": round(snapshot["pressure"], 1),
                    "presence_cm": round(snapshot["presence_cm"], 1),
                    "pir_state": "OUT",
                    "light_state": "NIGHT",
                    "simulated_time": sim_clock.now_str(),
                }
            }
        return None


# ===========================================================================
# ML ENGINE
# ===========================================================================

class DemoMLEngine:
    """Wraps the trained Isolation Forest model from demo_train.py."""

    def __init__(self, config):
        self.config = config
        self.model = None
        self.scaler = None
        self.is_loaded = False
        self.last_alert_time = 0
        self.cooldown_sec = config["demo"]["alert_cooldown_sec"]

    def load(self, model_path=None, scaler_path=None):
        mp = model_path or self.config["paths"]["model_file"]
        sp = scaler_path or self.config["paths"]["scaler_file"]
        if not os.path.exists(mp) or not os.path.exists(sp):
            return False
        self.model = joblib.load(mp)
        self.scaler = joblib.load(sp)
        self.is_loaded = True
        logger.info(f"ML model loaded from {mp}")
        return True

    def predict(self, window):
        if not self.is_loaded:
            return False, 0.0, None
        features = extract_features(window, self.config)
        features = np.nan_to_num(features, nan=0.0)
        scaled = self.scaler.transform(features.reshape(1, -1))
        pred = self.model.predict(scaled)[0]
        score = self.model.score_samples(scaled)[0]
        return (pred == -1), float(score), features

    def check_and_alert(self, window, snapshot, sim_clock):
        now = time.time()
        if (now - self.last_alert_time) < self.cooldown_sec:
            return None

        is_anomaly, score, features = self.predict(window)
        if not is_anomaly:
            return None

        self.last_alert_time = now

        is_sleep = sim_clock.is_sleep_time()
        bed_occ = features[2]
        pir_rate = features[8]

        if is_sleep and bed_occ < 0.3:
            rule_type, severity = "ML_BED_EMPTY_NIGHT", "HIGH"
            msg = f"ML: Unusual absence from bed at {sim_clock.now_label()}"
            action = "Check on resident"
        elif is_sleep and pir_rate < 0.1:
            rule_type, severity = "ML_NIGHT_WANDERING", "HIGH"
            msg = f"ML: Bed empty with no room presence at {sim_clock.now_label()}"
            action = "Check for disorientation"
        else:
            rule_type, severity = "ML_GENERAL_ANOMALY", "MEDIUM"
            msg = f"ML: Unusual pattern detected (score: {score:.3f})"
            action = "Review sensor data"

        return {
            "alert_id": f"ML_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(now) % 10000:04d}",
            "timestamp": datetime.now().isoformat(),
            "rule_type": rule_type,
            "severity": severity,
            "message": msg,
            "recommended_action": action,
            "source": "ML_ENGINE",
            "anomaly_score": round(score, 4),
            "sensor_data": {
                "bed_pressure": round(snapshot["pressure"], 1),
                "presence_cm": round(snapshot["presence_cm"], 1),
                "pir_state": "IN" if snapshot["pir_in"] else "OUT",
                "light_state": "NIGHT" if snapshot["light_night"] else "DAY",
                "simulated_time": sim_clock.now_str(),
                "feature_summary": {
                    FEATURE_NAMES[i]: round(float(features[i]), 4)
                    for i in range(len(features))
                }
            }
        }


# ===========================================================================
# ALERT MANAGER - Save locally + push to cloud
# ===========================================================================

class DemoAlertManager:
    """Handles alerts: saves locally, pushes to Daniel's cloud API."""

    def __init__(self, config, cloud_enabled=True):
        self.config = config
        self.cloud_enabled = cloud_enabled
        self.alerts = []
        os.makedirs(config["paths"]["alerts_dir"], exist_ok=True)

    def process(self, alert):
        if alert is None:
            return
        self.alerts.append(alert)

        # Save locally
        fp = os.path.join(self.config["paths"]["alerts_dir"],
                          f"{alert['alert_id']}.json")
        with open(fp, "w") as f:
            json.dump(alert, f, indent=2)

        # Push to cloud
        cloud_status = ""
        if self.cloud_enabled:
            try:
                r = requests.post(
                    f"{self.config['api']['base_url']}/alerts",
                    json=alert,
                    timeout=self.config["api"]["timeout"]
                )
                if r.status_code == 200:
                    cloud_status = f"  cloud: pushed (id={r.json().get('id', '?')})"
                else:
                    cloud_status = f"  cloud: failed ({r.status_code})"
            except Exception:
                cloud_status = "  cloud: offline"
        else:
            cloud_status = "  cloud: disabled (--no-cloud)"

        # Console output
        sev = alert["severity"]
        icon = {"HIGH": "\U0001f6a8", "MEDIUM": "\u26a0\ufe0f", "LOW": "\u2139\ufe0f"}.get(sev, "?")
        src = alert.get("source", "")
        score_str = ""
        if alert.get("anomaly_score") is not None:
            score_str = f"  |  ML score: {alert['anomaly_score']:.4f}"

        print(f"\n\n  {icon} [{src}] {sev}: {alert['message']}")
        print(f"     -> {alert['recommended_action']}")
        print(f"     {cloud_status}{score_str}")
        print()


# ===========================================================================
# LED CONTROLLER
# ===========================================================================

class DemoLEDController:
    """Controls 3 hallway LEDs based on night wandering detection."""

    def __init__(self, config, sensor_mgr):
        self.config = config
        self.sensor_mgr = sensor_mgr
        self.leds_on = False
        self.person_returned_at = None
        self.grace_period = config["demo"]["led_grace_period_sec"]
        self.action_log = []

    def update(self, snapshot, wandering_detected):
        th = self.config["thresholds"]
        person_in_bed = snapshot["pressure"] >= th["pressure_occupied"]
        person_near = snapshot["presence_cm"] <= th["presence_near_cm"]
        person_back = person_in_bed or person_near

        if wandering_detected and not self.leds_on:
            self.leds_on = True
            self.person_returned_at = None
            self.sensor_mgr.publish_led(True)
            self._log("ON", snapshot)
            logger.info("LEDs ON - night wandering detected")

        elif self.leds_on and person_back:
            if self.person_returned_at is None:
                self.person_returned_at = time.time()
            elif (time.time() - self.person_returned_at) >= self.grace_period:
                self.leds_on = False
                self.person_returned_at = None
                self.sensor_mgr.publish_led(False)
                self._log("OFF", snapshot)
                logger.info("LEDs OFF - person returned to bed")

        elif self.leds_on and not person_back:
            self.person_returned_at = None

    def _log(self, action, snapshot):
        self.action_log.append({
            "action": action,
            "time": datetime.now().isoformat(),
            "pressure": snapshot["pressure"],
            "presence_cm": snapshot["presence_cm"],
        })


# ===========================================================================
# CLOUD SETUP - Upload model + create resident on startup
# ===========================================================================

def cloud_setup(config):
    """
    Push initial data to Daniel's cloud API so Luis's app has content.
      1. Create a resident profile
      2. Upload the trained model
    """
    api = config["api"]["base_url"]
    timeout = config["api"]["timeout"]
    results = {}

    print(f"\n  Setting up cloud API ({api})...")

    # 1. Create resident
    resident = {
        "name": "Maria Garcia",
        "room": "Bedroom (demo - night wandering detection)",
        "notes": "Demo resident - 78 years old, lives alone, mild mobility issues"
    }
    try:
        r = requests.post(f"{api}/residents", json=resident, timeout=timeout)
        if r.status_code == 200:
            rid = r.json().get("id", "?")
            print(f"     Resident created (id={rid})")
            results["resident"] = True
        else:
            print(f"     Resident: {r.status_code} - {r.text[:60]}")
            results["resident"] = False
    except Exception as e:
        print(f"     Resident: {str(e)[:50]}")
        results["resident"] = False

    # 2. Upload model
    model_path = config["paths"]["model_file"]
    stats_path = config["paths"]["stats_file"]

    if os.path.exists(model_path) and os.path.exists(stats_path):
        try:
            with open(model_path, "rb") as f:
                model_b64 = base64.b64encode(f.read()).decode("utf-8")
            with open(stats_path) as f:
                stats = json.load(f)

            payload = {
                "version": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "training_samples": stats.get("total_samples", 0),
                "anomaly_ratio": stats.get("anomaly_ratio", 0.0),
                "feature_count": NUM_FEATURES,
                "model_data": model_b64,
                "notes": f"Demo model - {stats.get('feature_vectors', 0)} windows, "
                         f"{stats.get('normal', 0)} normal, {stats.get('anomaly', 0)} anomaly, "
                         f"12 bedroom features, Isolation Forest"
            }

            r = requests.post(f"{api}/models", json=payload, timeout=30)
            if r.status_code == 200:
                mid = r.json().get("id", "?")
                print(f"     Model uploaded (id={mid}, "
                      f"{len(model_b64)//1024}KB)")
                results["model"] = True
            else:
                print(f"     Model upload: {r.status_code}")
                results["model"] = False
        except Exception as e:
            print(f"     Model upload: {str(e)[:50]}")
            results["model"] = False
    else:
        print(f"     Model not found locally - skipping upload")
        results["model"] = False

    # 3. Verify DB contents
    try:
        r = requests.get(f"{api}/residents", timeout=timeout)
        n_residents = len(r.json()) if r.status_code == 200 else "?"
        r2 = requests.get(f"{api}/models", timeout=timeout)
        n_models = len(r2.json()) if r2.status_code == 200 else "?"
        r3 = requests.get(f"{api}/alerts", params={"limit": 1}, timeout=timeout)
        n_alerts = "accessible" if r3.status_code == 200 else "error"
        print(f"     DB status: {n_residents} resident(s), "
              f"{n_models} model(s), alerts {n_alerts}")
    except Exception:
        print(f"     DB status: could not verify")

    return results


# ===========================================================================
# MAIN DEMO LOOP
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(description="Demo - Night Wandering Detection")
    parser.add_argument("--config", default="demo_config.json")
    parser.add_argument("--rules-only", action="store_true",
                        help="Rule engine only, no ML")
    parser.add_argument("--model", default=None,
                        help="Path to model .pkl file")
    parser.add_argument("--start-hour", type=float, default=22.0,
                        help="Simulated start hour (default: 22.0 = 10 PM)")
    parser.add_argument("--speed", type=float, default=60.0,
                        help="Time acceleration factor (default: 60 = "
                             "1 real min = 1 sim hour)")
    parser.add_argument("--no-cloud", action="store_true",
                        help="Disable cloud API calls")
    args = parser.parse_args()

    # Load config
    with open(args.config) as f:
        config = json.load(f)

    # Create dirs
    os.makedirs(config["paths"]["alerts_dir"], exist_ok=True)
    os.makedirs(config["paths"]["logs_dir"], exist_ok=True)

    # Calculate timing info for display
    hours_to_2am = (26.0 - args.start_hour) % 24
    real_mins_to_2am = (hours_to_2am * 3600) / args.speed / 60

    print("\n" + "=" * 65)
    print("  DEMO - NIGHT WANDERING DETECTION")
    print("=" * 65)
    print(f"  Sensors:  4 (bedroom)  |  LEDs: 3 (hallway)")
    print(f"  Features: {NUM_FEATURES}  |  Detection: Rules + ML")
    print(f"  ---")
    print(f"  SIMULATED CLOCK:")
    print(f"     Start time:  {int(args.start_hour):02d}:00")
    if args.speed >= 60:
        print(f"     Speed:       {args.speed:.0f}x "
              f"(1 real min = {args.speed / 60:.0f} sim hour(s))")
    else:
        print(f"     Speed:       {args.speed:.0f}x "
              f"(1 real min = {args.speed:.0f} sim min)")
    print(f"     ~{real_mins_to_2am:.1f} real minutes until 02:00 AM")
    print(f"  ---")

    # Cloud setup
    cloud_enabled = not args.no_cloud
    if cloud_enabled:
        cloud_setup(config)
    else:
        print(f"\n  Cloud disabled (--no-cloud flag)")

    # Create components
    sim_clock = SimulatedClock(start_hour=args.start_hour, speed=args.speed)
    sensor_mgr = DemoSensorManager(config)
    rule_engine = DemoRuleEngine(config)
    ml_engine = DemoMLEngine(config)
    alert_mgr = DemoAlertManager(config, cloud_enabled=cloud_enabled)

    # Connect MQTT
    print(f"\n  Connecting to MQTT...")
    if not sensor_mgr.connect():
        print("  MQTT connection failed. Is Mosquitto running?")
        print("     Try: sudo systemctl status mosquitto")
        sys.exit(1)
    print("  MQTT connected")

    # Load ML model
    ml_active = False
    if not args.rules_only:
        mp = args.model or config["paths"]["model_file"]
        if ml_engine.load(mp):
            ml_active = True
            print("  ML Engine: ACTIVE")
        else:
            print("  ML Engine: INACTIVE (run demo_train.py first)")
    else:
        print("  Rules-only mode (--rules-only)")

    print("  Rule Engine: ACTIVE")

    # LED controller
    led_ctrl = DemoLEDController(config, sensor_mgr)
    sensor_mgr.publish_led(False)

    # Main loop params
    sample_rate = config["ml"]["sample_rate_hz"]
    sample_interval = 1.0 / sample_rate
    detect_interval = config["ml"]["detection_interval_sec"]
    window_size = config["ml"]["window_size"]
    last_ml_check = 0
    last_display_time = 0
    sample_count = 0

    print(f"\n  Demo running! (Ctrl+C to stop)")
    print(f"  Sample rate: {sample_rate}Hz  |  ML check: every {detect_interval}s")
    print(f"{'=' * 65}\n")

    # Header
    print(f"  SIM TIME   | Real    | {'Bed':>8s}  {'Pres':>6s}  "
          f"{'PIR':>3s}  {'Light':>5s} | LEDs | Status")
    print(f"  {'=' * 58}")

    try:
        while True:
            loop_start = time.time()
            sim_hour = sim_clock.now()

            # Sample sensors (stamped with simulated hour)
            snapshot = sensor_mgr.take_snapshot(sim_hour)
            sample_count += 1

            # Rule Engine (always)
            rule_alert = rule_engine.check(snapshot, sim_clock)
            wandering_detected = rule_alert is not None
            if rule_alert:
                alert_mgr.process(rule_alert)

            # ML Engine (if loaded)
            now = time.time()
            if ml_active and (now - last_ml_check) >= detect_interval:
                last_ml_check = now
                window = sensor_mgr.get_recent_window(window_size)
                if window is not None:
                    ml_alert = ml_engine.check_and_alert(window, snapshot, sim_clock)
                    if ml_alert:
                        alert_mgr.process(ml_alert)
                        if not wandering_detected:
                            wandering_detected = True

            # LED Control
            led_ctrl.update(snapshot, wandering_detected)

            # Display (every 0.5 seconds)
            if (now - last_display_time) >= 0.5:
                last_display_time = now
                bed, pres, pir, light = sensor_mgr.get_sensor_status()
                led_str = " ON" if led_ctrl.leds_on else "  -"

                # Status text
                if wandering_detected:
                    status = "!! WANDERING"
                elif led_ctrl.leds_on and led_ctrl.person_returned_at:
                    remaining = led_ctrl.grace_period - (now - led_ctrl.person_returned_at)
                    status = f"<- Back ({remaining:.0f}s)"
                elif sim_clock.is_sleep_time():
                    status = ".. Sleeping"
                else:
                    status = "ok Awake"

                sim_time = sim_clock.now_label()
                real_elapsed = sim_clock.elapsed_str()

                print(f"\r  {sim_time}  | {real_elapsed:>6s}  | "
                      f"{bed:>8s}  {pres:>6s}  {pir:>3s}  {light:>5s} "
                      f"| {led_str} | {status:<16s}",
                      end="", flush=True)

            # Wait
            elapsed = time.time() - loop_start
            sleep_time = max(0, sample_interval - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n\n  Demo stopped after {sample_count:,} samples "
              f"({sim_clock.elapsed_str()} real time)")

    finally:
        sensor_mgr.publish_led(False)

        if led_ctrl.action_log:
            log_path = os.path.join(config["paths"]["logs_dir"], "led_actions.json")
            with open(log_path, "w") as f:
                json.dump(led_ctrl.action_log, f, indent=2)

        sensor_mgr.disconnect()

        # Summary
        print(f"\n{'=' * 65}")
        print(f"  DEMO SESSION SUMMARY")
        print(f"{'=' * 65}")
        print(f"  Simulated:  {int(args.start_hour):02d}:00 -> {sim_clock.now_str()}")
        print(f"  Real time:  {sim_clock.elapsed_str()}")
        print(f"  Samples:    {sample_count:,}")
        print(f"  Alerts:     {len(alert_mgr.alerts)}")
        print(f"  LED events: {len(led_ctrl.action_log)}")

        if alert_mgr.alerts:
            rule_a = [a for a in alert_mgr.alerts if a["source"] == "RULE_ENGINE"]
            ml_a = [a for a in alert_mgr.alerts if a["source"] == "ML_ENGINE"]
            high = [a for a in alert_mgr.alerts if a["severity"] == "HIGH"]
            print(f"    Rule Engine: {len(rule_a)}")
            print(f"    ML Engine:   {len(ml_a)}")
            print(f"    HIGH:        {len(high)}")

        if cloud_enabled:
            print(f"\n  Cloud: all alerts at {config['api']['base_url']}/alerts")
            print(f"  Luis's app:")
            print(f"    GET /alerts?severity=HIGH")
            print(f"    GET /alerts?acknowledged=false")
            print(f"    PUT /alerts/<id>/acknowledge")

        print(f"\n  Local files:")
        print(f"    Alerts:  {config['paths']['alerts_dir']}/")
        print(f"    LED log: {config['paths']['logs_dir']}/led_actions.json")
        print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
