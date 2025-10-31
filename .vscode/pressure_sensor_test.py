"""
Pressure Sensor Test Script for House Replica
This script tests real pressure sensors via MQTT or direct GPIO
Designed for bed, window, and door pressure sensors
"""

import time
import json
from datetime import datetime
import paho.mqtt.client as mqtt

# For Raspberry Pi GPIO (uncomment if using direct GPIO)
# import RPi.GPIO as GPIO

class PressureSensorTester:
    """Test real pressure sensors in house replica"""
    
    def __init__(self, mode='mqtt'):
        """
        Initialize pressure sensor tester
        mode: 'mqtt' for MQTT communication, 'gpio' for direct GPIO
        """
        self.mode = mode
        self.mqtt_client = None
        
        # Pressure sensor configuration
        self.sensors = {
            'bed': {'pin': 17, 'threshold': 500, 'current': 0},
            'window_bedroom': {'pin': 18, 'threshold': 100, 'current': 0},
            'window_kitchen': {'pin': 27, 'threshold': 100, 'current': 0},
            'window_livingroom': {'pin': 22, 'threshold': 100, 'current': 0},
            'door_main': {'pin': 23, 'threshold': 150, 'current': 0},
            'door_bedroom': {'pin': 24, 'threshold': 150, 'current': 0},
            'door_bathroom': {'pin': 25, 'threshold': 150, 'current': 0}
        }
        
        if mode == 'mqtt':
            self._setup_mqtt()
        elif mode == 'gpio':
            self._setup_gpio()
    
    def _setup_mqtt(self):
        """Setup MQTT connection"""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.connect("localhost", 1883, 60)
        self.mqtt_client.loop_start()
        print("✅ MQTT client connected")
    
    def _setup_gpio(self):
        """Setup GPIO pins for direct reading (Raspberry Pi only)"""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            
            # Setup ADC for analog reading (you might need an ADC chip like MCP3008)
            # This is a placeholder - adapt to your specific hardware
            print("🔧 GPIO setup for pressure sensors")
            print("Note: You'll need an ADC for analog pressure readings")
            
        except ImportError:
            print("❌ RPi.GPIO not available - using simulation mode")
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            print("📡 Connected to MQTT broker")
        else:
            print(f"❌ MQTT connection failed: {rc}")
    
    def read_pressure_sensor(self, sensor_name):
        """
        Read pressure sensor value
        Returns: pressure value (0-1023 for analog sensors)
        """
        if self.mode == 'simulation':
            # Simulate pressure readings
            import random
            if 'bed' in sensor_name:
                # Simulate bed occupancy
                hour = datetime.now().hour
                if 22 <= hour or hour <= 7:
                    return random.uniform(600, 800)  # Occupied at night
                else:
                    return random.uniform(0, 50)  # Empty during day
            elif 'window' in sensor_name:
                return random.uniform(150, 200) if random.random() > 0.1 else 0
            elif 'door' in sensor_name:
                return random.uniform(180, 220) if random.random() > 0.2 else 0
        
        elif self.mode == 'gpio':
            # Read from actual GPIO/ADC
            # This is hardware-specific - adapt to your setup
            # Example for MCP3008 ADC:
            # return self.read_adc(self.sensors[sensor_name]['pin'])
            pass
        
        return 0
    
    def publish_sensor_data(self, sensor_name, value):
        """Publish sensor data via MQTT"""
        if self.mqtt_client:
            topic = f"sensors/pressure/{sensor_name}"
            
            # Determine sensor state
            sensor_config = self.sensors.get(sensor_name, {})
            threshold = sensor_config.get('threshold', 100)
            
            if 'bed' in sensor_name:
                state = 'occupied' if value > threshold else 'empty'
            elif 'window' in sensor_name:
                state = 'open' if value < threshold else 'closed'
            elif 'door' in sensor_name:
                state = 'open' if value < threshold else 'closed'
            else:
                state = 'unknown'
            
            payload = {
                'timestamp': datetime.now().isoformat(),
                'sensor_id': sensor_name,
                'value': value,
                'state': state,
                'threshold': threshold,
                'location': sensor_name.split('_')[1] if '_' in sensor_name else 'unknown'
            }
            
            self.mqtt_client.publish(topic, json.dumps(payload))
            return state
        return None
    
    def test_single_sensor(self, sensor_name):
        """Test a single pressure sensor"""
        print(f"\n🔧 Testing {sensor_name}...")
        
        # Read sensor
        value = self.read_pressure_sensor(sensor_name)
        self.sensors[sensor_name]['current'] = value
        
        # Publish via MQTT
        state = self.publish_sensor_data(sensor_name, value)
        
        # Display result
        print(f"  Value: {value:.1f}")
        print(f"  State: {state}")
        print(f"  Threshold: {self.sensors[sensor_name]['threshold']}")
        
        return value, state
    
    def test_all_sensors(self):
        """Test all pressure sensors"""
        print("\n" + "="*50)
        print("🔍 TESTING ALL PRESSURE SENSORS")
        print("="*50)
        
        results = {}
        for sensor_name in self.sensors.keys():
            value, state = self.test_single_sensor(sensor_name)
            results[sensor_name] = {'value': value, 'state': state}
            time.sleep(0.5)  # Small delay between readings
        
        return results
    
    def monitor_sensors(self, duration=60):
        """Monitor all sensors for a duration"""
        print(f"\n📊 Monitoring pressure sensors for {duration} seconds...")
        start_time = time.time()
        
        anomalies = []
        
        while time.time() - start_time < duration:
            current_hour = datetime.now().hour
            
            # Read all sensors
            for sensor_name in self.sensors.keys():
                value = self.read_pressure_sensor(sensor_name)
                state = self.publish_sensor_data(sensor_name, value)
                
                # Check for anomalies
                if 'bed' in sensor_name:
                    if 22 <= current_hour or current_hour <= 7:
                        if value < 500:  # Bed empty during sleep time
                            anomaly = {
                                'timestamp': datetime.now().isoformat(),
                                'sensor': sensor_name,
                                'issue': 'Bed empty during sleep hours',
                                'value': value
                            }
                            anomalies.append(anomaly)
                            print(f"  🚨 ANOMALY: {anomaly['issue']}")
                
                elif 'window' in sensor_name:
                    if current_hour < 6 or current_hour > 22:
                        if value < 100:  # Window open at night
                            anomaly = {
                                'timestamp': datetime.now().isoformat(),
                                'sensor': sensor_name,
                                'issue': 'Window open at night',
                                'value': value
                            }
                            anomalies.append(anomaly)
                            print(f"  🚨 ANOMALY: {anomaly['issue']}")
            
            time.sleep(2)  # Check every 2 seconds
        
        print(f"\n✅ Monitoring complete. Found {len(anomalies)} anomalies")
        return anomalies
    
    def calibrate_sensor(self, sensor_name):
        """Calibrate a pressure sensor"""
        print(f"\n🔧 Calibrating {sensor_name}...")
        print("Follow the instructions for calibration:")
        
        readings = []
        
        if 'bed' in sensor_name:
            print("\n1. Ensure bed is EMPTY")
            input("   Press Enter when ready...")
            empty_value = self.read_pressure_sensor(sensor_name)
            print(f"   Empty reading: {empty_value:.1f}")
            
            print("\n2. Sit/lie on the bed")
            input("   Press Enter when ready...")
            occupied_value = self.read_pressure_sensor(sensor_name)
            print(f"   Occupied reading: {occupied_value:.1f}")
            
            # Calculate threshold
            threshold = (empty_value + occupied_value) / 2
            print(f"\n✅ Suggested threshold: {threshold:.1f}")
            
        elif 'window' in sensor_name or 'door' in sensor_name:
            print("\n1. Ensure window/door is CLOSED")
            input("   Press Enter when ready...")
            closed_value = self.read_pressure_sensor(sensor_name)
            print(f"   Closed reading: {closed_value:.1f}")
            
            print("\n2. OPEN the window/door")
            input("   Press Enter when ready...")
            open_value = self.read_pressure_sensor(sensor_name)
            print(f"   Open reading: {open_value:.1f}")
            
            # Calculate threshold
            threshold = (closed_value + open_value) / 2
            print(f"\n✅ Suggested threshold: {threshold:.1f}")
        
        return threshold
    
    def run_anomaly_scenarios(self):
        """Run specific anomaly test scenarios"""
        print("\n" + "="*50)
        print("🚨 RUNNING ANOMALY TEST SCENARIOS")
        print("="*50)
        
        scenarios = [
            {
                'name': 'Night Security Check',
                'description': 'Check all windows and doors at night',
                'sensors': ['window_bedroom', 'window_kitchen', 'door_main'],
                'condition': lambda h: h >= 22 or h <= 6
            },
            {
                'name': 'Sleep Monitoring',
                'description': 'Check bed occupancy during sleep hours',
                'sensors': ['bed'],
                'condition': lambda h: 22 <= h or h <= 7
            },
            {
                'name': 'Away Mode',
                'description': 'All sensors should show closed/empty',
                'sensors': list(self.sensors.keys()),
                'condition': lambda h: 9 <= h <= 17  # Work hours
            }
        ]
        
        current_hour = datetime.now().hour
        
        for scenario in scenarios:
            if scenario['condition'](current_hour):
                print(f"\n🔍 {scenario['name']}")
                print(f"   {scenario['description']}")
                
                for sensor in scenario['sensors']:
                    value, state = self.test_single_sensor(sensor)
                    
                    # Check for issues
                    if sensor == 'bed' and scenario['name'] == 'Sleep Monitoring':
                        if state == 'empty':
                            print(f"   ⚠️ WARNING: Bed is empty during sleep hours!")
                    elif 'window' in sensor and scenario['name'] == 'Night Security Check':
                        if state == 'open':
                            print(f"   ⚠️ WARNING: Window is open at night!")
                    elif 'door' in sensor and scenario['name'] == 'Away Mode':
                        if state == 'open':
                            print(f"   ⚠️ WARNING: Door is open while away!")
                
                time.sleep(1)

def main():
    """Main test function"""
    print("\n" + "="*60)
    print("  🔧 PRESSURE SENSOR TEST SUITE")
    print("  House Replica IoT System")
    print("="*60)
    
    # Initialize tester (change to 'gpio' for real hardware)
    tester = PressureSensorTester(mode='simulation')  # Change to 'gpio' for real sensors
    
    while True:
        print("\n📋 Select Test Option:")
        print("1. Test all sensors once")
        print("2. Monitor sensors continuously")
        print("3. Calibrate a sensor")
        print("4. Run anomaly scenarios")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ")
        
        if choice == '1':
            results = tester.test_all_sensors()
            print("\n📊 Test Results:")
            for sensor, data in results.items():
                print(f"  {sensor}: {data['state']} ({data['value']:.1f})")
        
        elif choice == '2':
            duration = int(input("Monitor duration (seconds): "))
            anomalies = tester.monitor_sensors(duration)
            if anomalies:
                print("\n⚠️ Anomalies detected:")
                for a in anomalies:
                    print(f"  - {a['sensor']}: {a['issue']}")
        
        elif choice == '3':
            print("\nAvailable sensors:")
            for i, sensor in enumerate(tester.sensors.keys(), 1):
                print(f"  {i}. {sensor}")
            sensor_idx = int(input("Select sensor number: ")) - 1
            sensor_name = list(tester.sensors.keys())[sensor_idx]
            threshold = tester.calibrate_sensor(sensor_name)
            
        elif choice == '4':
            tester.run_anomaly_scenarios()
        
        elif choice == '5':
            print("\n👋 Exiting test suite")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()