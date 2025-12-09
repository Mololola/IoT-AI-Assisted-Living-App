"""
MQTT Sensor Test Utility - Fixed for paho-mqtt 2.0
Verifies sensor data is being received correctly via MQTT
Tests pressure, motion (PIR), and presence (mmWave) sensors individually
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import threading

class MQTTSensorTester:
    """Test utility for verifying MQTT sensor connections"""
    
    def __init__(self, broker_ip="localhost"):
        self.mqtt_broker = broker_ip
        self.mqtt_port = 1883
        
        # Topics from updated technical note
        self.topics = {
            'pressure': 'home/bedroom/pressure',
            'motion': 'home/bedroom/PIR',
            'presence': 'home/bedroom/presence'
        }
        
        # Data storage
        self.last_data = {
            'pressure': {'value': None, 'timestamp': None, 'count': 0},
            'motion': {'value': None, 'timestamp': None, 'count': 0},
            'presence': {'value': None, 'timestamp': None, 'count': 0}
        }
        
        self.test_active = False
        self.current_test = None
        
        # MQTT Client (Fixed for paho-mqtt 2.0)
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            f"RaspberryPi_Tester_{datetime.now().strftime('%H%M%S')}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            print("✅ Connected to MQTT Broker")
        else:
            print(f"❌ Failed to connect, return code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"⚠️ Unexpected disconnection")
    
    def on_message(self, client, userdata, msg):
        """Process incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8').strip()
            timestamp = datetime.now()
            
            # Identify sensor
            sensor = None
            for s, t in self.topics.items():
                if topic == t:
                    sensor = s
                    break
            
            if sensor:
                self.last_data[sensor]['value'] = payload
                self.last_data[sensor]['timestamp'] = timestamp
                self.last_data[sensor]['count'] += 1
                
                # Display if testing this sensor
                if self.current_test == sensor:
                    self.display_sensor_data(sensor, payload, timestamp)
                    
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def display_sensor_data(self, sensor, value, timestamp):
        """Display formatted sensor data"""
        time_str = timestamp.strftime('%H:%M:%S.%f')[:-3]
        
        if sensor == 'pressure':
            try:
                pressure_bar = float(value)
                state = self.get_pressure_state(pressure_bar)
                print(f"[{time_str}] 🛏️ PRESSURE: {pressure_bar:.2f} Bar - {state}")
                
                # Visual bar graph
                bar_length = int(pressure_bar * 20)
                bar = '█' * bar_length + '░' * (20 - bar_length)
                print(f"            {bar} ({pressure_bar:.2f}/2.0)")
                
            except ValueError:
                print(f"[{time_str}] ❌ Invalid pressure value: {value}")
        
        elif sensor == 'motion':
            state_icon = "🚶" if value == "IN" else "🛑"
            print(f"[{time_str}] {state_icon} MOTION: {value}")
            if value == "IN":
                print("            ⚠️ Motion detected - Person IN room")
            else:
                print("            ✅ No motion - Person OUT of room")
        
        elif sensor == 'presence':
            try:
                distance_cm = int(value)
                state = self.get_presence_state(distance_cm)
                print(f"[{time_str}] 📏 PRESENCE: {distance_cm} cm - {state}")
                
                # Visual distance indicator
                if distance_cm < 50:
                    print("            👤 Very close (< 50cm)")
                elif distance_cm < 200:
                    print("            🚶 In room (50-200cm)")
                else:
                    print("            ⚫ No presence detected")
                    
            except ValueError:
                print(f"[{time_str}] ❌ Invalid distance value: {value}")
        
        print("-" * 60)
    
    def get_pressure_state(self, pressure_bar):
        """Determine pressure state"""
        if pressure_bar < 0.1:
            return "🟢 EMPTY"
        elif pressure_bar > 0.5:
            return "🔴 OCCUPIED"
        else:
            return "🟡 UNCERTAIN"
    
    def get_presence_state(self, distance_cm):
        """Determine presence state"""
        if distance_cm < 50:
            return "NEAR"
        elif distance_cm < 200:
            return "FAR"
        else:
            return "ABSENT"
    
    def test_pressure_sensor(self):
        """Test pressure sensor"""
        print("\n" + "="*60)
        print("  🛏️ PRESSURE SENSOR TEST")
        print("="*60)
        print("Topic: " + self.topics['pressure'])
        print("Expected: Pressure values in Bar (0.0 - 2.0)")
        print("-" * 60)
        
        self.current_test = 'pressure'
        self.client.subscribe(self.topics['pressure'])
        
        print("\n📊 Monitoring pressure sensor...")
        print("   - Press the sensor to see values change")
        print("   - Values update every time pressure changes")
        print("   - Or every 30 seconds if no change")
        print("\nPress Ctrl+C to stop\n")
        
        self.test_active = True
        start_time = time.time()
        last_count = 0
        
        while self.test_active:
            try:
                time.sleep(1)
                
                # Show status every 5 seconds
                if time.time() - start_time >= 5:
                    count = self.last_data['pressure']['count']
                    if count == last_count:
                        print(f"⏳ Waiting for data... (received {count} messages)")
                    last_count = count
                    start_time = time.time()
                    
            except KeyboardInterrupt:
                break
        
        self.client.unsubscribe(self.topics['pressure'])
        self.test_active = False
        
        # Summary
        print(f"\n📈 Test Summary:")
        print(f"   Total messages: {self.last_data['pressure']['count']}")
        if self.last_data['pressure']['value']:
            print(f"   Last value: {self.last_data['pressure']['value']} Bar")
    
    def test_motion_sensor(self):
        """Test PIR motion sensor"""
        print("\n" + "="*60)
        print("  🚶 PIR MOTION SENSOR TEST")
        print("="*60)
        print("Topic: " + self.topics['motion'])
        print("Expected: IN/OUT states")
        print("GPIO: Pin 3 (from updated technical note)")
        print("-" * 60)
        
        self.current_test = 'motion'
        self.client.subscribe(self.topics['motion'])
        
        print("\n📊 Monitoring PIR sensor...")
        print("   - Walk in front of sensor to trigger")
        print("   - IN = Motion detected")
        print("   - OUT = No motion")
        print("   - 3 second debounce prevents rapid toggles")
        print("\nPress Ctrl+C to stop\n")
        
        self.test_active = True
        start_time = time.time()
        last_state = None
        state_changes = 0
        
        while self.test_active:
            try:
                time.sleep(0.5)
                
                # Check for state changes
                current_state = self.last_data['motion']['value']
                if current_state and current_state != last_state:
                    state_changes += 1
                    last_state = current_state
                
                # Status update
                if time.time() - start_time >= 5:
                    if self.last_data['motion']['count'] == 0:
                        print(f"⏳ Waiting for PIR data...")
                    else:
                        print(f"📊 State changes: {state_changes} | Messages: {self.last_data['motion']['count']}")
                    start_time = time.time()
                    
            except KeyboardInterrupt:
                break
        
        self.client.unsubscribe(self.topics['motion'])
        self.test_active = False
        
        # Summary
        print(f"\n📈 Test Summary:")
        print(f"   Total messages: {self.last_data['motion']['count']}")
        print(f"   State changes: {state_changes}")
        if self.last_data['motion']['value']:
            print(f"   Last state: {self.last_data['motion']['value']}")
    
    def test_presence_sensor(self):
        """Test mmWave presence sensor"""
        print("\n" + "="*60)
        print("  📏 mmWAVE PRESENCE SENSOR TEST")
        print("="*60)
        print("Topic: " + self.topics['presence'])
        print("Expected: Distance in centimeters")
        print("UART: RX=GPIO 18, TX=GPIO 19")
        print("-" * 60)
        
        self.current_test = 'presence'
        self.client.subscribe(self.topics['presence'])
        
        print("\n📊 Monitoring mmWave sensor...")
        print("   - Stand in front of sensor")
        print("   - Move closer/farther to see distance change")
        print("   - Updates every 0.5 seconds")
        print("\nPress Ctrl+C to stop\n")
        
        self.test_active = True
        start_time = time.time()
        min_dist = float('inf')
        max_dist = 0
        
        while self.test_active:
            try:
                time.sleep(0.5)
                
                # Track min/max
                if self.last_data['presence']['value']:
                    try:
                        dist = int(self.last_data['presence']['value'])
                        min_dist = min(min_dist, dist)
                        max_dist = max(max_dist, dist)
                    except:
                        pass
                
                # Status update
                if time.time() - start_time >= 5:
                    if self.last_data['presence']['count'] == 0:
                        print(f"⏳ Waiting for mmWave data...")
                    else:
                        print(f"📊 Range: {min_dist}-{max_dist}cm | Messages: {self.last_data['presence']['count']}")
                    start_time = time.time()
                    
            except KeyboardInterrupt:
                break
        
        self.client.unsubscribe(self.topics['presence'])
        self.test_active = False
        
        # Summary
        print(f"\n📈 Test Summary:")
        print(f"   Total messages: {self.last_data['presence']['count']}")
        if min_dist < float('inf'):
            print(f"   Distance range: {min_dist} - {max_dist} cm")
        if self.last_data['presence']['value']:
            print(f"   Last distance: {self.last_data['presence']['value']} cm")
    
    def test_all_sensors(self):
        """Monitor all sensors simultaneously"""
        print("\n" + "="*60)
        print("  📊 ALL SENSORS MONITORING")
        print("="*60)
        
        # Subscribe to all topics
        for topic in self.topics.values():
            self.client.subscribe(topic)
            print(f"Subscribed: {topic}")
        
        print("\n🎯 Monitoring all sensors...")
        print("Press Ctrl+C to stop\n")
        
        self.test_active = True
        last_display = time.time()
        
        while self.test_active:
            try:
                # Display status every 2 seconds
                if time.time() - last_display >= 2:
                    print(f"\n📊 SENSOR STATUS [{datetime.now().strftime('%H:%M:%S')}]")
                    print("-" * 50)
                    
                    # Pressure
                    if self.last_data['pressure']['value']:
                        p_val = self.last_data['pressure']['value']
                        try:
                            p_bar = float(p_val)
                            p_state = self.get_pressure_state(p_bar)
                            print(f"🛏️ Pressure: {p_bar:.2f} Bar - {p_state}")
                        except:
                            print(f"🛏️ Pressure: {p_val}")
                    else:
                        print(f"🛏️ Pressure: No data")
                    
                    # Motion
                    if self.last_data['motion']['value']:
                        m_val = self.last_data['motion']['value']
                        m_icon = "🚶" if m_val == "IN" else "🛑"
                        print(f"{m_icon} Motion:   {m_val}")
                    else:
                        print(f"🚶 Motion:   No data")
                    
                    # Presence
                    if self.last_data['presence']['value']:
                        d_val = self.last_data['presence']['value']
                        try:
                            d_cm = int(d_val)
                            d_state = self.get_presence_state(d_cm)
                            print(f"📏 Distance: {d_cm} cm - {d_state}")
                        except:
                            print(f"📏 Distance: {d_val}")
                    else:
                        print(f"📏 Distance: No data")
                    
                    # Message counts
                    print(f"\n📨 Messages received:")
                    print(f"   Pressure: {self.last_data['pressure']['count']}")
                    print(f"   Motion:   {self.last_data['motion']['count']}")
                    print(f"   Presence: {self.last_data['presence']['count']}")
                    print("-" * 50)
                    
                    last_display = time.time()
                
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                break
        
        # Unsubscribe all
        for topic in self.topics.values():
            self.client.unsubscribe(topic)
        
        self.test_active = False
    
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            print(f"Connecting to MQTT broker at {self.mqtt_broker}...")
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()
            time.sleep(1)
            return True
        except Exception as e:
            print(f"❌ Could not connect: {e}")
            print("\nTroubleshooting:")
            print("1. Check if Mosquitto is running: sudo systemctl status mosquitto")
            print("2. If using localhost, make sure you're on the Raspberry Pi")
            print("3. If using IP, verify the correct IP address")
            return False
    
    def disconnect_mqtt(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker")

def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("  🔬 MQTT SENSOR TEST UTILITY")
    print("  Verify Sensor Connections")
    print("="*60)
    
    # Get MQTT broker IP
    print("\nMQTT Broker Configuration:")
    print("1. Use default (192.168.1.100) - For remote broker")
    print("2. Enter custom IP - For specific network address")
    print("3. Use localhost - For broker on THIS Raspberry Pi")
    print("\n💡 Since you're running on the Pi with Mosquitto, choose option 3")
    
    choice = input("\nSelect (1-3): ")
    if choice == '2':
        broker_ip = input("Enter MQTT broker IP: ")
    elif choice == '3':
        broker_ip = "localhost"
    else:
        broker_ip = "192.168.1.100"
    
    print(f"\nUsing broker: {broker_ip}")
    
    tester = MQTTSensorTester(broker_ip)
    
    # Connect to MQTT
    if not tester.connect_mqtt():
        print("\n❌ Failed to connect to MQTT broker")
        print("\nPlease check:")
        print("  - Mosquitto is running: sudo systemctl status mosquitto")
        print("  - If stopped, start it: sudo systemctl start mosquitto")
        return
    
    while True:
        print("\n" + "="*60)
        print("  SENSOR TEST MENU")
        print("="*60)
        print("1. Test Pressure Sensor (Bar values)")
        print("2. Test PIR Motion Sensor (IN/OUT)")
        print("3. Test mmWave Presence Sensor (Distance)")
        print("4. Monitor All Sensors")
        print("5. Check MQTT Connection")
        print("6. Exit")
        print("-" * 60)
        
        choice = input("Select test (1-6): ")
        
        if choice == '1':
            tester.test_pressure_sensor()
        elif choice == '2':
            tester.test_motion_sensor()
        elif choice == '3':
            tester.test_presence_sensor()
        elif choice == '4':
            tester.test_all_sensors()
        elif choice == '5':
            print("\n🔍 Checking MQTT connection...")
            # Test publish/subscribe
            test_topic = "test/connection"
            test_msg = f"test_{datetime.now().strftime('%H%M%S')}"
            
            received = threading.Event()
            
            def test_callback(client, userdata, msg):
                if msg.payload.decode() == test_msg:
                    received.set()
            
            tester.client.message_callback_add(test_topic, test_callback)
            tester.client.subscribe(test_topic)
            time.sleep(0.5)
            tester.client.publish(test_topic, test_msg)
            
            if received.wait(timeout=2):
                print("✅ MQTT connection is working!")
            else:
                print("❌ MQTT test failed - check broker")
            
            tester.client.unsubscribe(test_topic)
            tester.client.message_callback_remove(test_topic)
            
        elif choice == '6':
            print("\nExiting...")
            break
        else:
            print("Invalid choice")
        
        if choice in ['1', '2', '3', '4']:
            input("\nPress Enter to return to menu...")
    
    tester.disconnect_mqtt()
    print("Goodbye!")

if __name__ == "__main__":
    main()
