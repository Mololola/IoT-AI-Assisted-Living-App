from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal
from datetime import datetime

Severity = Literal["HIGH", "MEDIUM", "LOW", "INFO"]

# -------------------------
# MODELS
# -------------------------

class ModelIn(BaseModel):
    version: str = Field(..., description="ISO timestamp e.g. 2026-02-05T16:50:00")
    training_samples: int
    anomaly_ratio: float
    feature_count: int = 33
    model_data: str = Field(..., description="Base64 encoded .pkl file")
    notes: Optional[str] = None


class ModelOut(BaseModel):
    id: str
    version: str
    training_samples: int
    anomaly_ratio: float
    feature_count: int
    created_at: datetime
    notes: Optional[str] = None

# -------------------------
# ALERTS
# -------------------------

class AlertIn(BaseModel):
    alert_id: str
    timestamp: str = Field(..., description="ISO timestamp e.g. 2026-02-05T16:53:11")
    rule_type: str
    severity: Severity
    message: str
    sensor_data: Optional[Dict[str, Any]] = None
    recommended_action: str
    acknowledged: bool = False


class AlertOut(BaseModel):
    id: str
    alert_id: str
    timestamp: str
    rule_type: str
    severity: Severity
    message: str
    sensor_data: Optional[Dict[str, Any]] = None
    recommended_action: str
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

# -------------------------
# EXCEPTIONS
# -------------------------

class ExceptionIn(BaseModel):
    date: str
    start_time: str
    end_time: str
    type: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    message: Optional[str] = None
    timestamp: str


class ExceptionOut(ExceptionIn):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
    
# -------------------------
# SENSOR READINGS
# -------------------------

class SensorReadingIn(BaseModel):
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: str


class SensorReadingOut(SensorReadingIn):
    id: str
    created_at: datetime
    
# -------------------------
# ACTUATORS
# -------------------------

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ActuatorCommandIn(BaseModel):
    topic: str
    payload: str
    actuator_id: str


class ActuatorCommandOut(ActuatorCommandIn):
    id: str
    status: str
    created_at: datetime