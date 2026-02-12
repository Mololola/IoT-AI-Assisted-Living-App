from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
from routes_models_alerts import router as models_alerts_router
import mongo

@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo.connect()
    try:
        # Optional: do a quick ping on startup to surface errors in logs
        database = mongo.db()
        await database.command("ping")
        print("MongoDB ping ok")
        yield
    finally:
        mongo.close()

app = FastAPI(lifespan=lifespan)

app.include_router(models_alerts_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/db-check")
async def db_check():
    try:
        database = mongo.db()
        await database.command("ping")

        col = database["render_smoketest"]
        write = await col.insert_one({"source": "render", "ok": True})
        doc = await col.find_one({"_id": write.inserted_id})

        return {
            "mongo_ping": "ok",
            "db": database.name,
            "inserted_id": str(write.inserted_id),
            "roundtrip_ok": doc is not None,
        }
    except Exception as e:
        # Return the actual error so we can diagnose immediately
        raise HTTPException(status_code=500, detail=str(e))

class ResidentIn(BaseModel):
    name: str
    room: str
    notes: str | None = None

@app.post("/residents")
async def create_resident(payload: ResidentIn):
    database = mongo.db()
    doc = payload.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)

    result = await database["residents"].insert_one(doc)
    return {"inserted_id": str(result.inserted_id)}

@app.get("/residents")
async def list_residents(limit: int = 20):
    database = mongo.db()
    cursor = database["residents"].find({}).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(length=limit)

    # convert ObjectId to string for JSON
    for it in items:
        it["_id"] = str(it["_id"])
    return {"items": items}