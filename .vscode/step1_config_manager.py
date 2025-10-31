"""
Step 1: Core Data Structures and Configuration Manager
Test this first to ensure basic functionality works
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# ======================== Setup Logging ========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ======================== Enums and Data Classes ========================
class SystemMode(Enum):
    TRAINING = "training"
    NORMAL = "normal"
    RETRAINING = "retraining"

@dataclass
class SensorData:
    """Structure for incoming sensor data"""
    timestamp: str
    sensor_type: str
    sensor_id: str
    value: Any
    location: str = ""
    
    def to_dict(self):
        return asdict(self)

@dataclass
class AnomalyEvent:
    """Structure for detected anomalies"""
    timestamp: str
    sensor_data: Dict
    anomaly_score: float
    context: Dict
    
    def to_dict(self):
        return asdict(self)

# ======================== Configuration Manager ========================
class ConfigManager:
    """Handles all configuration and state management"""
    
    def __init__(self, config_file="config.json", state_file="system_state.json"):
        self.config_file = config_file
        self.state_file = state_file
        self.config = self.load_config()
        self.state = self.load_state()
        
    def load_config(self) -> Dict:
        """Load user configuration from config.json"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                logger.info("✅ Configuration loaded successfully")
                return config
        except FileNotFoundError:
            logger.warning(f"⚠️ {self.config_file} not found, using defaults")
            return self.get_default_config()
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Return default configuration for testing"""
        default = {
            "mqtt": {
                "broker": "localhost",
                "port": 1883,
                "topics": ["sensors/motion/+", "sensors/temperature/+"],
                "username": "",
                "password": ""
            },
            "api": {
                "base_url": "http://localhost:8000/api",
                "endpoints": {
                    "backup": "/backup",
                    "anomaly": "/anomaly",
                    "heartbeat": "/heartbeat"
                },
                "timeout": 30,
                "retry_count": 3
            },
            "household": {
                "residents": 2,
                "sleep_start": "22:00",
                "sleep_end": "07:00"
            },
            "training": {
                "duration_hours": 1,
                "min_samples": 100,
                "save_raw_data": True
            },
            "anomaly_detection": {
                "contamination": 0.05,
                "window_size": 60,
                "retraining_threshold": 0.3
            }
        }
        return default
    
    def load_state(self) -> Dict:
        """Load system state from system_state.json"""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                logger.info(f"✅ System state loaded: Mode={state.get('mode', 'unknown')}")
                return state
        except FileNotFoundError:
            logger.info("🔧 No state file found, initializing new state")
            return self.initialize_state()
        except Exception as e:
            logger.error(f"❌ Error loading state: {e}")
            return self.initialize_state()
    
    def initialize_state(self) -> Dict:
        """Initialize system state for first run"""
        state = {
            "mode": SystemMode.TRAINING.value,
            "install_date": datetime.now().isoformat(),
            "training_start": None,
            "training_end": None,
            "last_backup": None,
            "model_version": 0,
            "total_anomalies": 0,
            "recent_anomaly_rate": 0.0
        }
        self.save_state(state)
        return state
    
    def save_state(self, state: Optional[Dict] = None):
        """Persist current state to disk"""
        if state:
            self.state = state
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug("💾 State saved successfully")
        except Exception as e:
            logger.error(f"❌ Error saving state: {e}")
    
    def update_state(self, **kwargs):
        """Update specific state fields"""
        self.state.update(kwargs)
        self.save_state()
        logger.info(f"📝 State updated: {kwargs}")

# ======================== Test Functions ========================
def test_config_manager():
    """Test the configuration manager"""
    print("\n" + "="*50)
    print("🧪 TESTING CONFIGURATION MANAGER")
    print("="*50)
    
    # Create manager
    config_mgr = ConfigManager()
    
    # Test config loading
    print("\n📋 Configuration loaded:")
    print(f"  - MQTT Broker: {config_mgr.config['mqtt']['broker']}")
    print(f"  - API URL: {config_mgr.config['api']['base_url']}")
    print(f"  - Residents: {config_mgr.config['household']['residents']}")
    print(f"  - Training duration: {config_mgr.config['training']['duration_hours']} hours")
    
    # Test state management
    print("\n📊 Current State:")
    print(f"  - Mode: {config_mgr.state['mode']}")
    print(f"  - Model Version: {config_mgr.state['model_version']}")
    print(f"  - Total Anomalies: {config_mgr.state['total_anomalies']}")
    
    # Test state update
    config_mgr.update_state(
        mode=SystemMode.NORMAL.value,
        model_version=1,
        total_anomalies=5
    )
    
    print("\n✅ State after update:")
    print(f"  - Mode: {config_mgr.state['mode']}")
    print(f"  - Model Version: {config_mgr.state['model_version']}")
    print(f"  - Total Anomalies: {config_mgr.state['total_anomalies']}")
    
    return config_mgr

def test_data_structures():
    """Test data structures"""
    print("\n" + "="*50)
    print("🧪 TESTING DATA STRUCTURES")
    print("="*50)
    
    # Test SensorData
    sensor = SensorData(
        timestamp=datetime.now().isoformat(),
        sensor_type="temperature",
        sensor_id="temp_01",
        value=22.5,
        location="living_room"
    )
    print(f"\n📡 Sensor Data: {sensor.to_dict()}")
    
    # Test AnomalyEvent
    anomaly = AnomalyEvent(
        timestamp=datetime.now().isoformat(),
        sensor_data=sensor.to_dict(),
        anomaly_score=0.85,
        context={"model_version": 1}
    )
    print(f"\n⚠️ Anomaly Event: {anomaly.to_dict()}")

if __name__ == "__main__":
    print("\n🚀 IoT ML System - Component Test Suite")
    print("This tests the basic configuration and data structures\n")
    
    # Run tests
    test_data_structures()
    config_mgr = test_config_manager()
    
    print("\n✅ Basic components test complete!")
    print("\nNext steps:")
    print("1. Create 'config.json' in your project folder")
    print("2. Run this script to verify configuration loads correctly")
    print("3. Check that 'system_state.json' is created")
    print("\nOnce this works, we'll add MQTT and ML components!")