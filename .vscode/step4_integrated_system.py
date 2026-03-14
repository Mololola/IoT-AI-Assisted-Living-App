"""
Step 4: Integrated IoT ML System for VS Code
This combines all components into a working system you can run locally
No Raspberry Pi or MQTT broker needed!
"""

import json
import os
import time
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

# ======================== INTEGRATED SYSTEM ========================
class IoTMLSystemLocal:
    """Complete IoT ML System for local development"""
    
    def __init__(self):
        print("🚀 Initializing IoT ML System (Local Development Mode)")
        
        # Create directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('models', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        # Initialize components
        self.config = self._load_config()
        self.state = self._load_state()
        self.mode = self.state.get('mode', 'training')
        
        # Data structures
        self.sensor_buffer = []
        self.training_data = []
        self.anomaly_log = []
        self.data_queue = queue.Queue()
        
        # ML components
        self.model = None
        self.scaler = StandardScaler()
        self.model_version = 0
        
        # Control flags
        self.running = False
        self.simulator_thread = None
        self.processor_thread = None
        
        print(f"  ✅ System initialized in {self.mode.upper()} mode")
    
    def _load_config(self) -> Dict:
        """Load configuration"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except:
            # Default config for testing
            return {
                'household': {
                    'residents': 2,
                    'sleep_start': '22:00',
                    'sleep_end': '07:00'
                },
                'training': {
                    'duration_hours': 0.1,  # 6 minutes for testing
                    'min_samples': 50
                },
                'anomaly_detection': {
                    'contamination': 0.05,
                    'window_size': 30,
                    'retraining_threshold': 0.3
                }
            }
    
    def _load_state(self) -> Dict:
        """Load system state"""
        try:
            with open('system_state.json', 'r') as f:
                return json.load(f)
        except:
            # Initialize new state
            state = {
                'mode': 'training',
                'install_date': datetime.now().isoformat(),
                'model_version': 0,
                'total_anomalies': 0,
                'training_samples': 0
            }
            self._save_state(state)
            return state
    
    def _save_state(self, state: Dict = None):
        """Save system state"""
        if state:
            self.state = state
        with open('system_state.json', 'w') as f:
            json.dump(self.state, f, indent=2)
    
    # ======================== SENSOR SIMULATION ========================
    def _simulate_sensors(self):
        """Simulate sensor data generation"""
        while self.running:
            current_hour = datetime.now().hour
            
            # Generate various sensor data
            sensor_data = []
            
            # Temperature sensors
            for room_id in range(1, 4):
                base_temp = 21 if 7 <= current_hour <= 22 else 19
                temp = base_temp + random.gauss(0, 1.5)
                sensor_data.append({
                    'timestamp': datetime.now().isoformat(),
                    'sensor_type': 'temperature',
                    'sensor_id': f'temp_{room_id}',
                    'value': round(temp, 1),
                    'location': f'room_{room_id}'
                })
            
            # Motion sensors
            if random.random() < 0.3:
                motion_prob = 0.7 if 7 <= current_hour <= 22 else 0.1
                for room_id in range(1, 3):
                    if random.random() < motion_prob:
                        sensor_data.append({
                            'timestamp': datetime.now().isoformat(),
                            'sensor_type': 'motion',
                            'sensor_id': f'motion_{room_id}',
                            'value': True,
                            'location': f'room_{room_id}'
                        })
            
            # Door sensor
            if random.random() < 0.1:
                sensor_data.append({
                    'timestamp': datetime.now().isoformat(),
                    'sensor_type': 'door',
                    'sensor_id': 'door_front',
                    'value': random.choice(['open', 'closed']),
                    'location': 'entrance'
                })
            
            # Power sensors
            if random.random() < 0.2:
                appliances = [
                    ('oven', 1500 if 11 <= current_hour <= 13 or 17 <= current_hour <= 20 else 50),
                    ('tv', 200 if 19 <= current_hour <= 23 else 10),
                    ('washer', 2000 if 9 <= current_hour <= 11 else 0)
                ]
                for appliance, base_power in appliances:
                    power = base_power + random.uniform(-50, 50) if base_power > 0 else 0
                    sensor_data.append({
                        'timestamp': datetime.now().isoformat(),
                        'sensor_type': 'power',
                        'sensor_id': f'power_{appliance}',
                        'value': max(0, round(power, 1)),
                        'location': 'utility'
                    })
            
            # Inject anomalies occasionally (for testing)
            if self.mode == 'normal' and random.random() < 0.05:  # 5% anomaly rate
                anomaly_type = random.choice(['temperature', 'power', 'motion'])
                
                if anomaly_type == 'temperature':
                    sensor_data.append({
                        'timestamp': datetime.now().isoformat(),
                        'sensor_type': 'temperature',
                        'sensor_id': 'temp_anomaly',
                        'value': random.choice([5, 40]),  # Extreme temperature
                        'location': 'unknown'
                    })
                elif anomaly_type == 'power':
                    sensor_data.append({
                        'timestamp': datetime.now().isoformat(),
                        'sensor_type': 'power',
                        'sensor_id': 'power_anomaly',
                        'value': random.uniform(4000, 6000),  # Very high power
                        'location': 'unknown'
                    })
                elif anomaly_type == 'motion' and (current_hour < 6 or current_hour > 23):
                    sensor_data.append({
                        'timestamp': datetime.now().isoformat(),
                        'sensor_type': 'motion',
                        'sensor_id': 'motion_night',
                        'value': True,
                        'location': 'hallway'
                    })
            
            # Add to queue
            for data in sensor_data:
                self.data_queue.put(data)
            
            time.sleep(random.uniform(1, 3))  # Vary data rate
    
    # ======================== DATA PROCESSING ========================
    def _process_data(self):
        """Process incoming sensor data"""
        while self.running:
            try:
                # Get data from queue
                data = self.data_queue.get(timeout=1)
                
                # Add to buffer
                self.sensor_buffer.append(data)
                if len(self.sensor_buffer) > 1000:
                    self.sensor_buffer = self.sensor_buffer[-500:]  # Keep last 500
                
                # Process based on mode
                if self.mode == 'training':
                    self._process_training_data(data)
                elif self.mode == 'normal':
                    self._process_normal_data(data)
                
                # Display current data
                self._display_data(data)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Processing error: {e}")
    
    def _process_training_data(self, data: Dict):
        """Process data in training mode"""
        self.training_data.append(data)
        self.state['training_samples'] = len(self.training_data)
        
        # Check if training should complete
        if self._should_complete_training():
            self._complete_training()
    
    def _process_normal_data(self, data: Dict):
        """Process data in normal mode (anomaly detection)"""
        # Get recent window
        window_size = self.config['anomaly_detection']['window_size']
        current_time = datetime.fromisoformat(data['timestamp'])
        window_start = current_time - timedelta(seconds=window_size)
        
        window_data = [
            d for d in self.sensor_buffer
            if datetime.fromisoformat(d['timestamp']) >= window_start
        ]
        
        if len(window_data) >= 5 and self.model:
            # Perform anomaly detection
            is_anomaly, score, details = self._detect_anomaly(window_data)
            
            if is_anomaly:
                self._handle_anomaly(data, score, details)
    
    def _should_complete_training(self) -> bool:
        """Check if training should complete"""
        # Check sample count
        min_samples = self.config['training']['min_samples']
        if len(self.training_data) >= min_samples:
            return True
        
        # Check duration
        if self.state.get('training_start'):
            start = datetime.fromisoformat(self.state['training_start'])
            duration = datetime.now() - start
            max_duration = self.config['training']['duration_hours'] * 3600
            if duration.total_seconds() >= max_duration:
                return True
        
        return False
    
    def _complete_training(self):
        """Complete training and switch to normal mode"""
        print("\n" + "="*50)
        print("📚 COMPLETING TRAINING")
        print("="*50)
        
        # Train model
        success = self._train_model()
        
        if success:
            # Save model
            self._save_model()
            
            # Update state
            self.mode = 'normal'
            self.state['mode'] = 'normal'
            self.state['training_end'] = datetime.now().isoformat()
            self.state['model_version'] = self.model_version
            self._save_state()
            
            print("✅ Training complete! Switched to NORMAL mode")
            print("🔍 Now detecting anomalies...")
        else:
            print("❌ Training failed, continuing in training mode")
    
    # ======================== ML FUNCTIONS ========================
    def _extract_features(self, sensor_data: List[Dict]) -> np.ndarray:
        """Simple feature extraction"""
        features = []
        
        if not sensor_data:
            return np.zeros(10)
        
        df = pd.DataFrame(sensor_data)
        
        # Time features
        latest = datetime.fromisoformat(sensor_data[-1]['timestamp'])
        features.append(latest.hour)
        features.append(latest.minute)
        
        # Sensor statistics
        for sensor_type in ['temperature', 'motion', 'power']:
            type_data = df[df['sensor_type'] == sensor_type] if 'sensor_type' in df else pd.DataFrame()
            
            if not type_data.empty and 'value' in type_data:
                values = pd.to_numeric(type_data['value'], errors='coerce').dropna()
                if not values.empty:
                    features.extend([values.mean(), values.std() if len(values) > 1 else 0])
                else:
                    features.extend([0, 0])
            else:
                features.extend([0, 0])
        
        # Total events
        features.append(len(df))
        features.append(df['sensor_id'].nunique() if 'sensor_id' in df else 0)
        
        return np.array(features[:10])  # Return exactly 10 features
    
    def _train_model(self) -> bool:
        """Train the ML model"""
        if len(self.training_data) < 20:
            print("❌ Insufficient training data")
            return False
        
        print(f"🎯 Training model with {len(self.training_data)} samples...")
        
        # Create windows
        windows = []
        window_size = 10  # Simplified window size
        
        for i in range(0, len(self.training_data) - window_size, 5):
            windows.append(self.training_data[i:i+window_size])
        
        if len(windows) < 5:
            print("❌ Insufficient windows")
            return False
        
        # Extract features
        X = np.array([self._extract_features(w) for w in windows])
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model = IsolationForest(
            contamination=self.config['anomaly_detection']['contamination'],
            random_state=42,
            n_estimators=50
        )
        self.model.fit(X_scaled)
        self.model_version += 1
        
        print(f"✅ Model trained successfully (version {self.model_version})")
        return True
    
    def _detect_anomaly(self, sensor_data: List[Dict]) -> tuple:
        """Detect anomalies in sensor data"""
        if not self.model:
            return False, 0.0, {}
        
        features = self._extract_features(sensor_data)
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        prediction = self.model.predict(features_scaled)[0]
        score = self.model.score_samples(features_scaled)[0]
        
        is_anomaly = prediction == -1
        
        details = {
            'prediction': 'anomaly' if is_anomaly else 'normal',
            'score': float(score),
            'features': features.tolist()
        }
        
        return is_anomaly, score, details
    
    def _handle_anomaly(self, data: Dict, score: float, details: Dict):
        """Handle detected anomaly"""
        self.state['total_anomalies'] = self.state.get('total_anomalies', 0) + 1
        
        anomaly_info = {
            'timestamp': data['timestamp'],
            'sensor': f"{data['sensor_type']}/{data['sensor_id']}",
            'value': data['value'],
            'score': score,
            'details': details
        }
        
        self.anomaly_log.append(anomaly_info)
        
        # Display anomaly
        print(f"\n🚨 ANOMALY DETECTED!")
        print(f"  Sensor: {anomaly_info['sensor']}")
        print(f"  Value: {anomaly_info['value']}")
        print(f"  Score: {score:.3f}")
        
        # Save to file
        with open('data/anomalies.json', 'a') as f:
            f.write(json.dumps(anomaly_info) + '\n')
        
        self._save_state()
    
    def _save_model(self):
        """Save the trained model"""
        if not self.model:
            return
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'version': self.model_version,
            'timestamp': datetime.now().isoformat()
        }
        
        filename = f"models/model_v{self.model_version}.pkl"
        joblib.dump(model_data, filename)
        joblib.dump(model_data, "models/model_latest.pkl")
        
        print(f"💾 Model saved: {filename}")
    
    def _load_model(self) -> bool:
        """Load a saved model"""
        try:
            model_data = joblib.load("models/model_latest.pkl")
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.model_version = model_data['version']
            print(f"✅ Model loaded (version {self.model_version})")
            return True
        except:
            print("❌ No saved model found")
            return False
    
    # ======================== DISPLAY FUNCTIONS ========================
    def _display_data(self, data: Dict):
        """Display incoming data"""
        # Simple rate limiting for display
        if random.random() < 0.2:  # Show 20% of data
            sensor = f"{data['sensor_type']}/{data['sensor_id']}"
            value = data['value']
            print(f"  📊 {sensor}: {value}")
    
    def display_status(self):
        """Display current system status"""
        print("\n" + "="*50)
        print("📊 SYSTEM STATUS")
        print("="*50)
        print(f"Mode: {self.mode.upper()}")
        print(f"Model Version: {self.model_version}")
        print(f"Buffer Size: {len(self.sensor_buffer)} samples")
        print(f"Total Anomalies: {self.state.get('total_anomalies', 0)}")
        
        if self.mode == 'training':
            print(f"Training Samples: {len(self.training_data)}/{self.config['training']['min_samples']}")
        
        if self.anomaly_log:
            print(f"\nRecent Anomalies:")
            for anomaly in self.anomaly_log[-5:]:
                print(f"  - {anomaly['timestamp']}: {anomaly['sensor']} = {anomaly['value']}")
    
    # ======================== CONTROL FUNCTIONS ========================
    def start(self):
        """Start the system"""
        print("\n🚀 Starting IoT ML System...")
        
        # Set training start time if in training mode
        if self.mode == 'training' and not self.state.get('training_start'):
            self.state['training_start'] = datetime.now().isoformat()
            self._save_state()
        
        # Load model if in normal mode
        if self.mode == 'normal':
            if not self._load_model():
                print("⚠️ No model found, switching to training mode")
                self.mode = 'training'
                self.state['mode'] = 'training'
                self.state['training_start'] = datetime.now().isoformat()
                self._save_state()
        
        self.running = True
        
        # Start threads
        self.simulator_thread = threading.Thread(target=self._simulate_sensors)
        self.simulator_thread.daemon = True
        self.simulator_thread.start()
        
        self.processor_thread = threading.Thread(target=self._process_data)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
        print(f"✅ System started in {self.mode.upper()} mode")
        
        if self.mode == 'training':
            print(f"📚 Training for {self.config['training']['duration_hours']*60} minutes...")
            print(f"📊 Need {self.config['training']['min_samples']} samples")
    
    def stop(self):
        """Stop the system"""
        print("\n🛑 Stopping system...")
        self.running = False
        
        if self.simulator_thread:
            self.simulator_thread.join(timeout=2)
        if self.processor_thread:
            self.processor_thread.join(timeout=2)
        
        self._save_state()
        print("✅ System stopped")
    
    def reset(self):
        """Reset the system to training mode"""
        print("\n🔄 Resetting system...")
        
        self.mode = 'training'
        self.training_data = []
        self.anomaly_log = []
        self.model = None
        self.model_version = 0
        
        self.state = {
            'mode': 'training',
            'install_date': datetime.now().isoformat(),
            'model_version': 0,
            'total_anomalies': 0,
            'training_samples': 0
        }
        self._save_state()
        
        print("✅ System reset to training mode")

# ======================== MAIN FUNCTION ========================
def main():
    """Run the IoT ML System"""
    print("\n" + "="*60)
    print("  🏠 IoT ML SYSTEM - LOCAL DEVELOPMENT VERSION")
    print("="*60)
    print("\nThis version runs entirely in VS Code without external dependencies!")
    
    # Create system
    system = IoTMLSystemLocal()
    
    try:
        # Start system
        system.start()
        
        # Run until interrupted
        print("\n📡 System running... Press Ctrl+C to stop")
        print("📊 Watch for sensor data and anomalies below:\n")
        
        while True:
            time.sleep(10)
            system.display_status()
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
    
    finally:
        system.stop()
        print("\n✅ Session complete!")
        
        # Show summary
        print("\n📈 SESSION SUMMARY:")
        print(f"  - Mode: {system.mode}")
        print(f"  - Data collected: {len(system.sensor_buffer)} samples")
        print(f"  - Anomalies detected: {system.state.get('total_anomalies', 0)}")
        
        if os.path.exists('data/anomalies.json'):
            print("\n💾 Anomalies saved to: data/anomalies.json")
        if os.path.exists('models/model_latest.pkl'):
            print("💾 Model saved to: models/model_latest.pkl")

if __name__ == "__main__":
    main()