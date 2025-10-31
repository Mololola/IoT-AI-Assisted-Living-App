"""
Step 2: MQTT Simulator for Local Testing
This simulates MQTT messages without needing a real broker
Perfect for VS Code development
"""

import json
import random
import threading
import time
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Callable

class MQTTSimulator:
    """Simulates MQTT broker and sensors for testing without real hardware"""
    
    def __init__(self):
        self.running = False
        self.message_queue = queue.Queue()
        self.subscribers = {}
        self.thread = None
        
    def subscribe(self, topic: str, callback: Callable):
        """Register a callback for a topic pattern"""
        self.subscribers[topic] = callback
        print(f"📡 Subscribed to: {topic}")
    
    def publish(self, topic: str, payload: Dict):
        """Publish a message to a topic"""
        message = {
            'topic': topic,
            'payload': json.dumps(payload),
            'timestamp': datetime.now().isoformat()
        }
        self.message_queue.put(message)
    
    def start(self):
        """Start the simulator"""
        self.running = True
        self.thread = threading.Thread(target=self._run_simulation)
        self.thread.daemon = True
        self.thread.start()
        print("🚀 MQTT Simulator started")
    
    def stop(self):
        """Stop the simulator"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("🛑 MQTT Simulator stopped")
    
    def _run_simulation(self):
        """Background thread that generates sensor data"""
        while self.running:
            # Generate random sensor data
            self._generate_sensor_data()
            
            # Process any queued messages
            self._process_messages()
            
            # Sleep to control data rate
            time.sleep(random.uniform(0.5, 2.0))
    
    def _generate_sensor_data(self):
        """Generate realistic sensor data"""
        # Current hour for time-based patterns
        current_hour = datetime.now().hour
        
        # Motion sensor
        if random.random() < 0.3:  # 30% chance
            motion_active = True if 7 <= current_hour <= 22 else (random.random() < 0.1)
            self.publish(
                "sensors/motion/living_room",
                {
                    "value": motion_active,
                    "location": "living_room",
                    "confidence": random.uniform(0.8, 1.0)
                }
            )
        
        # Temperature sensor
        if random.random() < 0.5:  # 50% chance
            base_temp = 21 if 7 <= current_hour <= 22 else 19
            temp = base_temp + random.gauss(0, 1.5)
            self.publish(
                f"sensors/temperature/room_{random.randint(1,3)}",
                {
                    "value": round(temp, 1),
                    "unit": "celsius",
                    "location": f"room_{random.randint(1,3)}"
                }
            )
        
        # Door sensor
        if random.random() < 0.1:  # 10% chance
            self.publish(
                "sensors/door/front",
                {
                    "value": random.choice(["open", "closed"]),
                    "location": "front_door"
                }
            )
        
        # Power sensor
        if random.random() < 0.2:  # 20% chance
            power = random.uniform(100, 2000) if 7 <= current_hour <= 22 else random.uniform(10, 100)
            self.publish(
                f"sensors/power/{random.choice(['oven', 'tv', 'washer'])}",
                {
                    "value": round(power, 1),
                    "unit": "watts",
                    "location": random.choice(['kitchen', 'living_room', 'utility'])
                }
            )
    
    def _process_messages(self):
        """Process queued messages and call subscribers"""
        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                topic = message['topic']
                
                # Find matching subscribers (simple pattern matching)
                for pattern, callback in self.subscribers.items():
                    if self._topic_matches(pattern, topic):
                        # Simulate MQTT message object
                        class MockMessage:
                            def __init__(self, topic, payload):
                                self.topic = topic
                                self.payload = payload.encode() if isinstance(payload, str) else payload
                        
                        mock_msg = MockMessage(topic, message['payload'])
                        callback(None, None, mock_msg)
                        
            except queue.Empty:
                break
    
    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """Check if topic matches pattern (supports + wildcard)"""
        pattern_parts = pattern.split('/')
        topic_parts = topic.split('/')
        
        if len(pattern_parts) != len(topic_parts):
            return False
        
        for p, t in zip(pattern_parts, topic_parts):
            if p != '+' and p != t:
                return False
        
        return True

class LocalDataCollector:
    """Collects data from the MQTT simulator for testing"""
    
    def __init__(self):
        self.data_queue = queue.Queue()
        self.simulator = MQTTSimulator()
        self.collected_data = []
        
    def on_message(self, client, userdata, msg):
        """Callback for incoming messages"""
        try:
            # Parse message
            topic_parts = msg.topic.split('/')
            sensor_type = topic_parts[1] if len(topic_parts) > 1 else "unknown"
            sensor_id = topic_parts[2] if len(topic_parts) > 2 else "unknown"
            
            # Parse payload
            payload = json.loads(msg.payload.decode())
            
            # Create sensor data
            sensor_data = {
                'timestamp': datetime.now().isoformat(),
                'sensor_type': sensor_type,
                'sensor_id': sensor_id,
                'value': payload.get('value'),
                'location': payload.get('location', ''),
                'raw_payload': payload
            }
            
            # Add to queue and collected data
            self.data_queue.put(sensor_data)
            self.collected_data.append(sensor_data)
            
            # Log it
            print(f"📊 {sensor_type}/{sensor_id}: {payload.get('value')} @ {payload.get('location', 'unknown')}")
            
        except Exception as e:
            print(f"❌ Error processing message: {e}")
    
    def start(self):
        """Start collecting data"""
        # Subscribe to all sensor topics
        self.simulator.subscribe("sensors/motion/+", self.on_message)
        self.simulator.subscribe("sensors/temperature/+", self.on_message)
        self.simulator.subscribe("sensors/door/+", self.on_message)
        self.simulator.subscribe("sensors/power/+", self.on_message)
        
        # Start simulator
        self.simulator.start()
        print("✅ Data collection started")
    
    def stop(self):
        """Stop collecting data"""
        self.simulator.stop()
        print(f"📈 Collected {len(self.collected_data)} data points")
    
    def get_recent_data(self, seconds: int = 60) -> List[Dict]:
        """Get data from the last N seconds"""
        cutoff = datetime.now() - timedelta(seconds=seconds)
        recent = [
            d for d in self.collected_data
            if datetime.fromisoformat(d['timestamp']) > cutoff
        ]
        return recent

# ======================== Test Functions ========================
def test_mqtt_simulator():
    """Test the MQTT simulator"""
    print("\n" + "="*50)
    print("🧪 TESTING MQTT SIMULATOR")
    print("="*50)
    
    # Create data collector
    collector = LocalDataCollector()
    
    print("\n📡 Starting data collection for 10 seconds...")
    print("Watch the simulated sensor data appear below:\n")
    
    # Start collection
    collector.start()
    
    # Run for 10 seconds
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    
    # Stop collection
    collector.stop()
    
    # Show statistics
    print("\n📊 Data Collection Statistics:")
    print(f"  Total points: {len(collector.collected_data)}")
    
    # Count by sensor type
    sensor_counts = {}
    for data in collector.collected_data:
        sensor_type = data['sensor_type']
        sensor_counts[sensor_type] = sensor_counts.get(sensor_type, 0) + 1
    
    print("\n  By sensor type:")
    for sensor_type, count in sensor_counts.items():
        print(f"    - {sensor_type}: {count} readings")
    
    # Show recent data
    recent = collector.get_recent_data(5)
    print(f"\n📈 Last 5 seconds: {len(recent)} readings")
    
    return collector

def simulate_anomaly_scenario():
    """Simulate an anomaly scenario"""
    print("\n" + "="*50)
    print("🚨 SIMULATING ANOMALY SCENARIO")
    print("="*50)
    
    simulator = MQTTSimulator()
    
    def anomaly_callback(client, userdata, msg):
        payload = json.loads(msg.payload.decode())
        value = payload.get('value')
        
        # Check for anomalies
        if msg.topic.startswith("sensors/temperature"):
            if value > 30 or value < 10:
                print(f"🔴 ANOMALY: Extreme temperature {value}°C!")
        elif msg.topic.startswith("sensors/power"):
            if value > 3000:
                print(f"🔴 ANOMALY: High power consumption {value}W!")
        elif msg.topic.startswith("sensors/motion"):
            hour = datetime.now().hour
            if value and (hour < 6 or hour > 23):
                print(f"🔴 ANOMALY: Motion detected at unusual hour!")
    
    # Subscribe with anomaly detection
    simulator.subscribe("sensors/+/+", anomaly_callback)
    
    print("\n🔍 Monitoring for anomalies...")
    print("Injecting some anomalous readings...\n")
    
    simulator.start()
    
    # Inject some anomalies
    time.sleep(2)
    simulator.publish("sensors/temperature/room1", {"value": 45, "unit": "celsius"})
    time.sleep(1)
    simulator.publish("sensors/power/oven", {"value": 5000, "unit": "watts"})
    time.sleep(1)
    simulator.publish("sensors/temperature/room2", {"value": -5, "unit": "celsius"})
    
    # Run for a bit
    time.sleep(5)
    
    simulator.stop()
    print("\n✅ Anomaly simulation complete")

if __name__ == "__main__":
    print("\n🚀 IoT ML System - MQTT Simulator Test")
    print("This simulates MQTT messages without needing a real broker\n")
    
    # Test basic simulation
    collector = test_mqtt_simulator()
    
    # Test anomaly detection
    simulate_anomaly_scenario()
    
    print("\n✅ MQTT simulation tests complete!")
    print("\nNext steps:")
    print("1. This simulator can replace real MQTT for development")
    print("2. Use the collected data to test ML training")
    print("3. No need for Mosquitto broker in VS Code!")