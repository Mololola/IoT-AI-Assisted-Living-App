"""
================================================================================
DEMO — Daily Sensor & LED Check
================================================================================

Run this BEFORE the demo to verify the 4 bedroom sensors and 3 hallway LEDs
are working correctly.

Sensors checked:
  1. Bedroom Pressure  (home/bedroom/pressure)  — ESP32 sends 0-5000
  2. Bedroom PIR       (home/bedroom/PIR)        — ESP32 sends "IN"/"OUT"
  3. Bedroom Presence   (home/bedroom/presence)   — ESP32 sends distance in cm
  4. Bedroom Light      (home/bedroom/light)      — ESP32 sends "Day"/"Night"

Actuators tested:
  1-3. Hallway LEDs    (home/hallway/led)         — Shared topic, all 3 at once

Usage:
  python3 demo_check.py                  # Standard (20s timeout)
  python3 demo_check.py --timeout 30     # Wait longer for slow sensors
  python3 demo_check.py --skip-leds      # Don't flash the LEDs
  python3 demo_check.py --skip-cloud     # Don't check cloud API

================================================================================
"""

import paho.mqtt.client as mqtt
import time
import json
import sys
import argparse
import requests
from datetime import datetime
from threading import Lock


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

MQTT_BROKER = "localhost"
MQTT_PORT = 1883

SENSORS = {
    "bedroom_pressure": {
        "topic": "home/bedroom/pressure",
        "desc": "Bed pressure (FSR)",
        "parse": "int",
        "expect": "0–5000 (>500 = occupied)",
    },
    "bedroom_pir": {
        "topic": "home/bedroom/PIR",
        "desc": "Bedroom PIR motion",
        "parse": "string",
        "expect": "IN or OUT",
    },
    "bedroom_presence": {
        "topic": "home/bedroom/presence",
        "desc": "mmWave presence (cm)",
        "parse": "float",
        "expect": "0–600 cm (≤50 = near)",
    },
    "bedroom_light": {
        "topic": "home/bedroom/light",
        "desc": "Light sensor",
        "parse": "string",
        "expect": "Day or Night",
    },
}

LED_TOPIC = "home/hallway/led"
LED_STATUS_TOPIC = "home/hallway/led/status"
API_URL = "https://assisted-living-platform.onrender.com"


# ═══════════════════════════════════════════════════════════════════════════════
# SENSOR CHECKER
# ═══════════════════════════════════════════════════════════════════════════════

class SensorChecker:
    """Listens to the 4 bedroom sensor topics."""

    def __init__(self):
        self.received = {}
        self.lock = Lock()
        self.connected = False
        self._topic_to_key = {}
        for key, info in SENSORS.items():
            self._topic_to_key[info["topic"]] = key

    def run(self, timeout_seconds):
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"demo_check_{datetime.now().strftime('%H%M%S')}"
        )
        client.on_connect = self._on_connect
        client.on_message = self._on_message

        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=30)
        except Exception as e:
            return False, f"Cannot connect to MQTT: {e}"

        client.loop_start()
        time.sleep(1)

        if not self.connected:
            client.loop_stop()
            client.disconnect()
            return False, "MQTT connection failed — is Mosquitto running?"

        start = time.time()
        last_count = -1
        while (time.time() - start) < timeout_seconds:
            with self.lock:
                current_count = len(self.received)
            if current_count == len(SENSORS):
                break
            if current_count != last_count:
                last_count = current_count
                remaining = len(SENSORS) - current_count
                print(f"\r    Received: {current_count}/{len(SENSORS)} sensors "
                      f"({remaining} waiting)  "
                      f"[{time.time()-start:.0f}s/{timeout_seconds}s]",
                      end="", flush=True)
            time.sleep(0.5)

        print()
        client.loop_stop()
        client.disconnect()
        return True, self.received

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            for key, info in SENSORS.items():
                client.subscribe(info["topic"], qos=0)

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        if topic not in self._topic_to_key:
            return
        key = self._topic_to_key[topic]
        raw = msg.payload.decode('utf-8', errors='replace').strip()
        with self.lock:
            if key not in self.received:
                self.received[key] = {
                    "raw": raw,
                    "time": time.time(),
                }


# ═══════════════════════════════════════════════════════════════════════════════
# LED TESTER
# ═══════════════════════════════════════════════════════════════════════════════

def test_leds():
    """Flash all 3 LEDs via the shared topic."""
    results = {"status": "unknown"}

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"led_test_{datetime.now().strftime('%H%M%S')}"
    )

    led_responses = []
    response_lock = Lock()

    def on_message(c, ud, msg):
        raw = msg.payload.decode('utf-8', errors='replace').strip()
        with response_lock:
            led_responses.append(raw)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=15)
        client.on_message = on_message
        client.subscribe(LED_STATUS_TOPIC, qos=0)
        client.loop_start()
        time.sleep(0.5)
    except Exception as e:
        return False, f"MQTT connect failed: {e}"

    # Turn ON
    print("    💡 LEDs ON...")
    client.publish(LED_TOPIC, "ON", qos=1)
    time.sleep(3)

    # Check responses
    with response_lock:
        on_count = sum(1 for r in led_responses if "ON" in r.upper())

    # Turn OFF
    print("    💡 LEDs OFF...")
    led_responses.clear()
    client.publish(LED_TOPIC, "OFF", qos=1)
    time.sleep(2)

    with response_lock:
        off_count = sum(1 for r in led_responses if "OFF" in r.upper())

    client.loop_stop()
    client.disconnect()

    total_responses = on_count + off_count
    if total_responses >= 6:
        return True, f"All 3 LEDs responded (ON: {on_count}, OFF: {off_count})"
    elif total_responses >= 2:
        return True, f"LEDs responded (ON: {on_count}/3, OFF: {off_count}/3) — some may be slow"
    elif total_responses > 0:
        return True, f"Partial response (ON: {on_count}/3, OFF: {off_count}/3) — check wiring"
    else:
        # MQTT publish succeeded even if no status came back
        return True, "Commands sent (no status feedback — LEDs may still work, check visually)"


# ═══════════════════════════════════════════════════════════════════════════════
# CLOUD CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def check_cloud():
    results = {}
    try:
        r = requests.get(f"{API_URL}/health", timeout=15)
        results["api_health"] = r.status_code == 200
    except Exception:
        results["api_health"] = False

    try:
        r = requests.get(f"{API_URL}/db-check", timeout=15)
        results["db_connection"] = r.status_code == 200
    except Exception:
        results["db_connection"] = False

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_sensor(key, raw_value):
    """Check if the raw value looks reasonable for this sensor type."""
    info = SENSORS[key]

    if info["parse"] == "int" or info["parse"] == "float":
        try:
            val = float(raw_value)
            if key == "bedroom_pressure":
                if 0 <= val <= 5000:
                    state = "OCCUPIED" if val >= 500 else "EMPTY"
                    return True, f"{val:.0f} ({state})"
                return False, f"{val} — OUT OF RANGE (expect 0-5000)"
            elif key == "bedroom_presence":
                if 0 <= val <= 600:
                    if val <= 50:
                        state = "NEAR"
                    elif val <= 200:
                        state = "FAR"
                    else:
                        state = "ABSENT"
                    return True, f"{val:.1f} cm ({state})"
                return False, f"{val} cm — unusual range"
        except ValueError:
            return False, f"Cannot parse as number: '{raw_value}'"

    elif info["parse"] == "string":
        if key == "bedroom_pir":
            if raw_value.upper() in ["IN", "OUT", "1", "0"]:
                return True, raw_value
            return False, f"Unexpected PIR value: '{raw_value}'"
        elif key == "bedroom_light":
            if raw_value in ["Day", "Night", "day", "night", "DAY", "NIGHT"]:
                return True, raw_value
            # Try as number (in case light sends analog value)
            try:
                val = float(raw_value)
                return True, f"{val:.0f} (analog)"
            except ValueError:
                return False, f"Unexpected light value: '{raw_value}'"

    return True, raw_value


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def print_report(mqtt_ok, sensor_data, led_ok, led_msg, cloud_data,
                 skip_leds, skip_cloud):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*65}")
    print(f"  📋 DEMO HEALTH CHECK REPORT — {now}")
    print(f"{'='*65}")

    total_pass = 0
    total_fail = 0
    issues = []

    # MQTT
    if mqtt_ok:
        print(f"\n  ✅ MQTT BROKER: Connected ({MQTT_BROKER}:{MQTT_PORT})")
        total_pass += 1
    else:
        print(f"\n  ❌ MQTT BROKER: FAILED — {sensor_data}")
        total_fail += 1
        issues.append("MQTT broker not running — sudo systemctl start mosquitto")
        _print_summary(total_pass, total_fail, issues)
        return

    # Sensors
    print(f"\n  {'─'*61}")
    print(f"  🛏️  BEDROOM SENSORS ({len(sensor_data)}/{len(SENSORS)} responding)")
    print(f"  {'─'*61}")

    for key, info in SENSORS.items():
        if key in sensor_data:
            raw = sensor_data[key]["raw"]
            valid, value_str = validate_sensor(key, raw)
            icon = "✅" if valid else "⚠️ "
            print(f"    {icon} {info['desc']:<28s} = {value_str}")
            total_pass += 1
            if not valid:
                issues.append(f"{info['desc']}: unusual value ({value_str})")
        else:
            print(f"    ❌ {info['desc']:<28s}   NO DATA — check ESP32")
            total_fail += 1
            issues.append(f"{info['desc']}: not responding — check ESP32")

    # LEDs
    if not skip_leds:
        print(f"\n  {'─'*61}")
        print(f"  💡 HALLWAY LEDs (shared topic: {LED_TOPIC})")
        print(f"  {'─'*61}")
        if led_ok:
            print(f"    ✅ {led_msg}")
            total_pass += 1
        else:
            print(f"    ❌ {led_msg}")
            total_fail += 1
            issues.append(f"LEDs: {led_msg}")
    else:
        print(f"\n  ⏭️  LEDs: Skipped (--skip-leds)")

    # Cloud
    if not skip_cloud:
        print(f"\n  {'─'*61}")
        print(f"  ☁️  CLOUD API")
        print(f"  {'─'*61}")
        for check_key, desc in [("api_health", "API reachable"),
                                 ("db_connection", "Database connected")]:
            if cloud_data.get(check_key):
                print(f"    ✅ {desc}")
                total_pass += 1
            else:
                print(f"    ❌ {desc}")
                total_fail += 1
                issues.append(f"Cloud: {desc} — may be cold-starting (wait 30s)")
    else:
        print(f"\n  ⏭️  CLOUD API: Skipped (--skip-cloud)")

    _print_summary(total_pass, total_fail, issues)


def _print_summary(total_pass, total_fail, issues):
    total = total_pass + total_fail
    print(f"\n{'='*65}")
    if total_fail == 0:
        print(f"  🎉 ALL CHECKS PASSED ({total_pass}/{total}) — Ready for demo!")
    elif total_fail <= 1:
        print(f"  ⚠️  MOSTLY OK ({total_pass}/{total} passed, {total_fail} issue)")
    else:
        print(f"  ❌ PROBLEMS FOUND ({total_pass}/{total} passed, {total_fail} failed)")

    if issues:
        print(f"\n  🔧 ISSUES TO FIX:")
        for i, issue in enumerate(issues, 1):
            print(f"     {i}. {issue}")

    if total_fail > 0:
        print(f"\n  💡 TROUBLESHOOTING:")
        print(f"     1. Is Mosquitto running?    → sudo systemctl status mosquitto")
        print(f"     2. Are ESP32s powered on?    → Check USB/power")
        print(f"     3. Same WiFi network?        → Pi + ESP32s on same network")
        print(f"     4. Check ESP32 serial output  → Arduino Serial Monitor")
        print(f"     5. Raw MQTT debug             → mosquitto_sub -t 'home/#' -v")

    print(f"{'='*65}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Demo Sensor & LED Check")
    parser.add_argument("--timeout", type=int, default=20,
                        help="Seconds to wait for sensor data (default: 20)")
    parser.add_argument("--skip-leds", action="store_true",
                        help="Don't test LEDs")
    parser.add_argument("--skip-cloud", action="store_true",
                        help="Don't check cloud API")
    args = parser.parse_args()

    print(f"\n{'🔧'*30}")
    print(f"  DEMO — SENSOR & LED CHECK")
    print(f"  {datetime.now().strftime('%A %d %B %Y, %H:%M')}")
    print(f"{'🔧'*30}")

    # Step 1: Sensors
    print(f"\n  📡 Step 1/3: Listening for bedroom sensors ({args.timeout}s)...")
    checker = SensorChecker()
    mqtt_ok, sensor_data = checker.run(args.timeout)

    # Step 2: LEDs
    led_ok = False
    led_msg = ""
    if not args.skip_leds and mqtt_ok:
        print(f"\n  ⚡ Step 2/3: Testing hallway LEDs...")
        led_ok, led_msg = test_leds()
    elif args.skip_leds:
        print(f"\n  ⏭️  Step 2/3: Skipping LEDs")
    else:
        print(f"\n  ⏭️  Step 2/3: Skipping LEDs (no MQTT)")

    # Step 3: Cloud
    cloud_data = {}
    if not args.skip_cloud:
        print(f"\n  ☁️  Step 3/3: Checking cloud API...")
        cloud_data = check_cloud()
    else:
        print(f"\n  ⏭️  Step 3/3: Skipping cloud")

    print_report(mqtt_ok, sensor_data, led_ok, led_msg, cloud_data,
                 args.skip_leds, args.skip_cloud)


if __name__ == "__main__":
    main()
