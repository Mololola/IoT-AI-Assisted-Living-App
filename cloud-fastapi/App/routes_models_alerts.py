from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
import base64

import mongo
import schemas

router = APIRouter()

def to_oid(id: str) -> ObjectId:
    try:
        return ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

# -------------------------
# MODELS
# -------------------------

@router.post("/models", response_model=schemas.ModelOut)
async def upload_model(payload: schemas.ModelIn):
    db = mongo.db()

    # validate ISO datetime string
    try:
        datetime.fromisoformat(payload.version)
    except Exception:
        raise HTTPException(status_code=400, detail="version must be ISO datetime")

    # validate base64
    try:
        model_bytes = base64.b64decode(payload.model_data, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="model_data must be valid base64")

    doc = payload.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["model_bytes"] = model_bytes  # lets you download without re-decoding base64

    res = await db["models"].insert_one(doc)
    m = await db["models"].find_one({"_id": res.inserted_id})

    return {
        "id": str(m["_id"]),
        "version": m["version"],
        "training_samples": m["training_samples"],
        "anomaly_ratio": m["anomaly_ratio"],
        "feature_count": m["feature_count"],
        "created_at": m["created_at"],
        "notes": m.get("notes"),
    }

@router.get("/models", response_model=List[schemas.ModelOut])
async def list_models(limit: int = Query(50, ge=1, le=500)):
    db = mongo.db()
    cursor = db["models"].find({}, sort=[("created_at", -1)]).limit(limit)

    out = []
    async for m in cursor:
        out.append({
            "id": str(m["_id"]),
            "version": m["version"],
            "training_samples": m["training_samples"],
            "anomaly_ratio": m["anomaly_ratio"],
            "feature_count": m["feature_count"],
            "created_at": m["created_at"],
            "notes": m.get("notes"),
        })
    return out

@router.get("/models/latest", response_model=schemas.ModelOut)
async def latest_model():
    db = mongo.db()
    m = await db["models"].find_one({}, sort=[("created_at", -1)])
    if not m:
        raise HTTPException(status_code=404, detail="No models found")

    return {
        "id": str(m["_id"]),
        "version": m["version"],
        "training_samples": m["training_samples"],
        "anomaly_ratio": m["anomaly_ratio"],
        "feature_count": m["feature_count"],
        "created_at": m["created_at"],
        "notes": m.get("notes"),
    }

@router.get("/models/{id}")
async def download_model(id: str):
    db = mongo.db()
    m = await db["models"].find_one({"_id": to_oid(id)})
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")

    model_bytes = m.get("model_bytes")
    if model_bytes is None:
        # fallback for older docs
        model_bytes = base64.b64decode(m["model_data"])

    filename = f"model_{m['version']}.pkl".replace(":", "-")
    return Response(
        content=model_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# -------------------------
# ALERTS
# -------------------------

@router.post("/alerts", response_model=schemas.AlertOut)
async def create_alert(payload: schemas.AlertIn):
    db = mongo.db()

    try:
        datetime.fromisoformat(payload.timestamp)
    except Exception:
        raise HTTPException(status_code=400, detail="timestamp must be ISO datetime")

    doc = payload.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["acknowledged_at"] = datetime.utcnow() if payload.acknowledged else None

    res = await db["alerts"].insert_one(doc)
    a = await db["alerts"].find_one({"_id": res.inserted_id})

    return {
        "id": str(a["_id"]),
        "alert_id": a["alert_id"],
        "timestamp": a["timestamp"],
        "rule_type": a["rule_type"],
        "severity": a["severity"],
        "message": a["message"],
        "sensor_data": a.get("sensor_data"),
        "recommended_action": a["recommended_action"],
        "acknowledged": a.get("acknowledged", False),
        "acknowledged_at": a.get("acknowledged_at"),
        "created_at": a["created_at"],
    }

@router.get("/alerts", response_model=List[schemas.AlertOut])
async def list_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=500),
    since: Optional[str] = None,
):
    db = mongo.db()
    q = {}

    if severity is not None:
        q["severity"] = severity
    if acknowledged is not None:
        q["acknowledged"] = acknowledged
    if since is not None:
        try:
            q["created_at"] = {"$gte": datetime.fromisoformat(since)}
        except Exception:
            raise HTTPException(status_code=400, detail="since must be ISO date/datetime")

    cursor = db["alerts"].find(q, sort=[("created_at", -1)]).limit(limit)

    out = []
    async for a in cursor:
        out.append({
            "id": str(a["_id"]),
            "alert_id": a["alert_id"],
            "timestamp": a["timestamp"],
            "rule_type": a["rule_type"],
            "severity": a["severity"],
            "message": a["message"],
            "sensor_data": a.get("sensor_data"),
            "recommended_action": a["recommended_action"],
            "acknowledged": a.get("acknowledged", False),
            "acknowledged_at": a.get("acknowledged_at"),
            "created_at": a["created_at"],
        })
    return out

@router.get("/alerts/{id}", response_model=schemas.AlertOut)
async def get_alert(id: str):
    db = mongo.db()
    a = await db["alerts"].find_one({"_id": to_oid(id)})
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "id": str(a["_id"]),
        "alert_id": a["alert_id"],
        "timestamp": a["timestamp"],
        "rule_type": a["rule_type"],
        "severity": a["severity"],
        "message": a["message"],
        "sensor_data": a.get("sensor_data"),
        "recommended_action": a["recommended_action"],
        "acknowledged": a.get("acknowledged", False),
        "acknowledged_at": a.get("acknowledged_at"),
        "created_at": a["created_at"],
    }

@router.put("/alerts/{id}/acknowledge", response_model=schemas.AlertOut)
async def acknowledge_alert(id: str):
    db = mongo.db()
    _id = to_oid(id)

    a = await db["alerts"].find_one({"_id": _id})
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db["alerts"].update_one(
        {"_id": _id},
        {"$set": {"acknowledged": True, "acknowledged_at": datetime.utcnow()}}
    )

    a2 = await db["alerts"].find_one({"_id": _id})
    return {
        "id": str(a2["_id"]),
        "alert_id": a2["alert_id"],
        "timestamp": a2["timestamp"],
        "rule_type": a2["rule_type"],
        "severity": a2["severity"],
        "message": a2["message"],
        "sensor_data": a2.get("sensor_data"),
        "recommended_action": a2["recommended_action"],
        "acknowledged": a2.get("acknowledged", False),
        "acknowledged_at": a2.get("acknowledged_at"),
        "created_at": a2["created_at"],
    }
