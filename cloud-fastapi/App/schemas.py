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
