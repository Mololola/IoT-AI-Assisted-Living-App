"""
Step 3: Feature Engineering and ML Training
This implements the ML components using simulated data
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import os
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Import our previous components
import sys
sys.path.append('.')  # Add current directory to path

class FeatureEngineering:
    """Extract features from sensor data for ML"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._get_default_config()
        self.window_size = self.config.get('window_size', 60)
        
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'window_size': 60,
            'household': {
                'sleep_start': '22:00',
                'sleep_end': '07:00',
                'residents': 2
            }
        }
    
    def extract_features(self, sensor_data: List[Dict]) -> np.ndarray:
        """Extract features from a window of sensor data"""
        if not sensor_data:
            return np.array([])
        
        features = []
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(sensor_data)
        
        # Time-based features
        latest_timestamp = sensor_data[-1]['timestamp']
        current_time = datetime.fromisoformat(latest_timestamp)
        
        # Basic time features
        hour = current_time.hour
        day_of_week = current_time.weekday()
        is_weekend = day_of_week >= 5
        
        # Check if it's sleep time
        sleep_start_hour = int(self.config['household']['sleep_start'].split(':')[0])
        sleep_end_hour = int(self.config['household']['sleep_end'].split(':')[0])
        is_sleep_time = hour >= sleep_start_hour or hour <= sleep_end_hour
        
        features.extend([
            hour,                    # Hour of day (0-23)
            day_of_week,            # Day of week (0-6)
            int(is_weekend),        # Weekend flag
            int(is_sleep_time),     # Sleep time flag
            current_time.minute     # Minute of hour
        ])
        
        # Sensor-specific features
        sensor_types = df['sensor_type'].unique() if 'sensor_type' in df else []
        
        # Motion features
        motion_data = df[df['sensor_type'] == 'motion'] if 'motion' in sensor_types else pd.DataFrame()
        if not motion_data.empty:
            motion_count = len(motion_data[motion_data['value'] == True])
            motion_frequency = motion_count / max(len(motion_data), 1)
        else:
            motion_count = 0
            motion_frequency = 0
        features.extend([motion_count, motion_frequency])
        
        # Temperature features
        temp_data = df[df['sensor_type'] == 'temperature'] if 'temperature' in sensor_types else pd.DataFrame()
        if not temp_data.empty and 'value' in temp_data:
            temps = pd.to_numeric(temp_data['value'], errors='coerce').dropna()
            if not temps.empty:
                temp_mean = temps.mean()
                temp_std = temps.std() if len(temps) > 1 else 0
                temp_min = temps.min()
                temp_max = temps.max()
            else:
                temp_mean = temp_std = temp_min = temp_max = 20  # Default values
        else:
            temp_mean = temp_std = temp_min = temp_max = 20
        features.extend([temp_mean, temp_std, temp_min, temp_max])
        
        # Door features
        door_data = df[df['sensor_type'] == 'door'] if 'door' in sensor_types else pd.DataFrame()
        door_events = len(door_data)
        door_open_count = len(door_data[door_data['value'] == 'open']) if not door_data.empty else 0
        features.extend([door_events, door_open_count])
        
        # Power features
        power_data = df[df['sensor_type'] == 'power'] if 'power' in sensor_types else pd.DataFrame()
        if not power_data.empty and 'value' in power_data:
            power_values = pd.to_numeric(power_data['value'], errors='coerce').dropna()
            if not power_values.empty:
                power_sum = power_values.sum()
                power_mean = power_values.mean()
                power_max = power_values.max()
            else:
                power_sum = power_mean = power_max = 0
        else:
            power_sum = power_mean = power_max = 0
        features.extend([power_sum, power_mean, power_max])
        
        # Activity level features
        total_events = len(df)
        unique_sensors = df['sensor_id'].nunique() if 'sensor_id' in df else 0
        features.extend([total_events, unique_sensors])
        
        # Ensure we always return the same number of features
        while len(features) < 20:
            features.append(0)
        
        return np.array(features[:20])  # Always return exactly 20 features
    
    def create_feature_matrix(self, data_windows: List[List[Dict]]) -> np.ndarray:
        """Create feature matrix from multiple data windows"""
        feature_matrix = []
        
        for window in data_windows:
            features = self.extract_features(window)
            if features.size > 0:
                feature_matrix.append(features)
        
        if not feature_matrix:
            return np.array([]).reshape(0, 20)
        
        return np.array(feature_matrix)
    
    def get_feature_names(self) -> List[str]:
        """Get names of all features"""
        return [
            'hour', 'day_of_week', 'is_weekend', 'is_sleep_time', 'minute',
            'motion_count', 'motion_frequency',
            'temp_mean', 'temp_std', 'temp_min', 'temp_max',
            'door_events', 'door_open_count',
            'power_sum', 'power_mean', 'power_max',
            'total_events', 'unique_sensors',
            'reserved_1', 'reserved_2'
        ]

class MLModelManager:
    """Manages ML model training and prediction"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._get_default_config()
        self.feature_eng = FeatureEngineering(config)
        self.model = None
        self.scaler = StandardScaler()
        self.model_version = 0
        self.training_stats = {}
        
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'contamination': 0.05,
            'window_size': 60,
            'household': {
                'sleep_start': '22:00',
                'sleep_end': '07:00',
                'residents': 2
            }
        }
    
    def create_sliding_windows(self, data: List[Dict], window_size: int = 60) -> List[List[Dict]]:
        """Create sliding windows from sensor data"""
        if not data:
            return []
        
        windows = []
        
        # Sort data by timestamp
        sorted_data = sorted(data, key=lambda x: x['timestamp'])
        
        # Create overlapping windows
        for i in range(0, len(sorted_data), max(1, window_size // 2)):  # 50% overlap
            window_start = datetime.fromisoformat(sorted_data[i]['timestamp'])
            window_end = window_start + timedelta(seconds=window_size)
            
            window = [
                d for d in sorted_data[i:]
                if datetime.fromisoformat(d['timestamp']) <= window_end
            ]
            
            if len(window) >= 5:  # Minimum 5 data points per window
                windows.append(window)
        
        return windows
    
    def train_model(self, training_data: List[Dict]) -> Tuple[bool, str]:
        """Train the anomaly detection model"""
        print("\n🎯 Starting model training...")
        
        if len(training_data) < 20:
            return False, "Insufficient training data (need at least 20 samples)"
        
        # Create sliding windows
        windows = self.create_sliding_windows(training_data)
        print(f"  📊 Created {len(windows)} training windows")
        
        if len(windows) < 5:
            return False, "Insufficient windows for training"
        
        # Extract features
        X = self.feature_eng.create_feature_matrix(windows)
        print(f"  🔧 Extracted features: {X.shape}")
        
        if X.shape[0] < 5:
            return False, "Insufficient features extracted"
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Isolation Forest
        contamination = self.config.get('contamination', 0.05)
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
            max_samples='auto'
        )
        
        self.model.fit(X_scaled)
        
        # Calculate training statistics
        predictions = self.model.predict(X_scaled)
        anomaly_scores = self.model.score_samples(X_scaled)
        
        self.training_stats = {
            'n_samples': X.shape[0],
            'n_features': X.shape[1],
            'n_anomalies': sum(predictions == -1),
            'anomaly_rate': sum(predictions == -1) / len(predictions),
            'score_mean': float(np.mean(anomaly_scores)),
            'score_std': float(np.std(anomaly_scores)),
            'score_min': float(np.min(anomaly_scores)),
            'score_max': float(np.max(anomaly_scores))
        }
        
        self.model_version += 1
        
        print(f"  ✅ Model trained successfully (v{self.model_version})")
        print(f"  📈 Training samples: {self.training_stats['n_samples']}")
        print(f"  🎯 Detected anomalies: {self.training_stats['n_anomalies']} ({self.training_stats['anomaly_rate']:.1%})")
        
        return True, f"Model trained with {X.shape[0]} samples"
    
    def predict(self, sensor_data: List[Dict]) -> Tuple[bool, float, Dict]:
        """Predict if current data is anomalous"""
        if self.model is None:
            return False, 0.0, {"error": "No model trained"}
        
        # Extract features
        features = self.feature_eng.extract_features(sensor_data)
        
        if features.size == 0:
            return False, 0.0, {"error": "No features extracted"}
        
        # Scale and predict
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        prediction = self.model.predict(features_scaled)[0]
        anomaly_score = self.model.score_samples(features_scaled)[0]
        
        # Get feature importance (approximation based on deviation from mean)
        feature_values = features_scaled[0]
        feature_importance = {}
        feature_names = self.feature_eng.get_feature_names()
        
        for i, (name, value) in enumerate(zip(feature_names, feature_values)):
            if abs(value) > 1.5:  # More than 1.5 std from mean
                feature_importance[name] = float(abs(value))
        
        # Prepare detailed results
        details = {
            'prediction': 'anomaly' if prediction == -1 else 'normal',
            'anomaly_score': float(anomaly_score),
            'threshold': float(np.percentile(self.model.score_samples(self.scaler.transform(self.feature_eng.create_feature_matrix(self.create_sliding_windows(sensor_data)))), 5)) if len(sensor_data) > 20 else -0.5,
            'feature_importance': feature_importance,
            'data_points': len(sensor_data)
        }
        
        is_anomaly = prediction == -1
        
        return is_anomaly, float(anomaly_score), details
    
    def save_model(self, filepath: str = "model.pkl") -> bool:
        """Save the trained model"""
        if self.model is None:
            print("❌ No model to save")
            return False
        
        try:
            # Save model, scaler, and metadata
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'version': self.model_version,
                'config': self.config,
                'training_stats': self.training_stats,
                'feature_names': self.feature_eng.get_feature_names(),
                'timestamp': datetime.now().isoformat()
            }
            
            joblib.dump(model_data, filepath)
            print(f"💾 Model saved to {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving model: {e}")
            return False
    
    def load_model(self, filepath: str = "model.pkl") -> bool:
        """Load a saved model"""
        try:
            if not os.path.exists(filepath):
                print(f"❌ Model file not found: {filepath}")
                return False
            
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.model_version = model_data.get('version', 0)
            self.training_stats = model_data.get('training_stats', {})
            
            print(f"✅ Model loaded from {filepath} (v{self.model_version})")
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False

# ======================== Test Functions ========================
def test_feature_engineering():
    """Test feature extraction"""
    print("\n" + "="*50)
    print("🧪 TESTING FEATURE ENGINEERING")
    print("="*50)
    
    # Create sample data
    sample_data = [
        {'timestamp': datetime.now().isoformat(), 'sensor_type': 'temperature', 'sensor_id': 'temp1', 'value': 22.5, 'location': 'room1'},
        {'timestamp': datetime.now().isoformat(), 'sensor_type': 'motion', 'sensor_id': 'motion1', 'value': True, 'location': 'room1'},
        {'timestamp': datetime.now().isoformat(), 'sensor_type': 'door', 'sensor_id': 'door1', 'value': 'open', 'location': 'front'},
        {'timestamp': datetime.now().isoformat(), 'sensor_type': 'power', 'sensor_id': 'power1', 'value': 150.5, 'location': 'kitchen'},
    ]
    
    # Extract features
    fe = FeatureEngineering()
    features = fe.extract_features(sample_data)
    
    print(f"\n📊 Extracted {len(features)} features:")
    feature_names = fe.get_feature_names()
    for name, value in zip(feature_names[:len(features)], features):
        if value != 0:  # Only show non-zero features
            print(f"  - {name}: {value:.2f}")
    
    return fe

def test_ml_training():
    """Test ML model training with simulated data"""
    print("\n" + "="*50)
    print("🧪 TESTING ML MODEL TRAINING")
    print("="*50)
    
    # Generate training data
    print("\n📊 Generating training data...")
    training_data = []
    
    for i in range(100):  # Generate 100 data points
        timestamp = (datetime.now() - timedelta(minutes=100-i)).isoformat()
        
        # Mix of different sensor readings
        training_data.extend([
            {'timestamp': timestamp, 'sensor_type': 'temperature', 'sensor_id': f'temp{i%3}', 
             'value': 20 + random.gauss(0, 2), 'location': f'room{i%3}'},
            {'timestamp': timestamp, 'sensor_type': 'motion', 'sensor_id': f'motion{i%2}', 
             'value': random.random() < 0.3, 'location': f'room{i%2}'},
        ])
        
        if i % 5 == 0:  # Occasional door events
            training_data.append({'timestamp': timestamp, 'sensor_type': 'door', 'sensor_id': 'door1', 
                                'value': random.choice(['open', 'closed']), 'location': 'front'})
        
        if i % 3 == 0:  # Power readings
            training_data.append({'timestamp': timestamp, 'sensor_type': 'power', 'sensor_id': 'oven', 
                                'value': random.uniform(10, 500), 'location': 'kitchen'})
    
    print(f"  Generated {len(training_data)} data points")
    
    # Train model
    ml = MLModelManager()
    success, message = ml.train_model(training_data)
    
    if success:
        print(f"\n✅ {message}")
        
        # Test prediction
        print("\n🔍 Testing predictions:")
        
        # Normal scenario
        normal_data = training_data[-20:]  # Last 20 points
        is_anomaly, score, details = ml.predict(normal_data)
        print(f"\n  Normal scenario:")
        print(f"    - Prediction: {details['prediction']}")
        print(f"    - Score: {score:.3f}")
        
        # Anomaly scenario (extreme values)
        anomaly_data = [
            {'timestamp': datetime.now().isoformat(), 'sensor_type': 'temperature', 
             'sensor_id': 'temp1', 'value': 45, 'location': 'room1'},  # Very high temp
            {'timestamp': datetime.now().isoformat(), 'sensor_type': 'power', 
             'sensor_id': 'oven', 'value': 5000, 'location': 'kitchen'},  # Very high power
        ]
        
        is_anomaly, score, details = ml.predict(anomaly_data)
        print(f"\n  Anomaly scenario:")
        print(f"    - Prediction: {details['prediction']}")
        print(f"    - Score: {score:.3f}")
        if details.get('feature_importance'):
            print(f"    - Suspicious features: {list(details['feature_importance'].keys())}")
        
        # Save model
        ml.save_model("test_model.pkl")
        
        return ml
    else:
        print(f"❌ Training failed: {message}")
        return None

if __name__ == "__main__":
    print("\n🚀 IoT ML System - ML Components Test")
    print("Testing feature engineering and model training\n")
    
    import random
    
    # Test feature engineering
    fe = test_feature_engineering()
    
    # Test ML training
    ml = test_ml_training()
    
    print("\n✅ ML component tests complete!")
    print("\nNext steps:")
    print("1. The model is saved as 'test_model.pkl'")
    print("2. You can load and use this model for predictions")
    print("3. Ready to integrate with MQTT simulator!")