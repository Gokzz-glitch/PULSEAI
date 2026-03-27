import logging
import json
import os
import asyncio
import time
from datetime import datetime
import collections
import httpx  # type: ignore
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException  # type: ignore
from pydantic import BaseModel  # type: ignore
from signal_processing import process_ecg, extract_beat_window, FS, SEGMENT_LEN  # type: ignore
from ml_model import predict_arrhythmia, get_model_status  # type: ignore
from fhir_generator import generate_fhir_diagnostic_report  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from typing import List, Optional
from ingestion import DataIngestor  # type: ignore
from firebase_service import FirebaseService  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PulseAI Edge-Cloud Platform", version="2.1.0")

cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
allow_origins = [o.strip() for o in cors_origins.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Colab Cloud Inference Bridge ───────────────────────────────────────────────
COLAB_INFERENCE_URL: Optional[str] = os.getenv("COLAB_INFERENCE_URL", "").strip().rstrip("/") or None
if COLAB_INFERENCE_URL:
    logger.info(f"☁️  Colab inference bridge active: {COLAB_INFERENCE_URL}")
else:
    logger.info("💻 Local HCTG-Net mode active.")

class PatientSession(BaseModel):
    patient_id: str
    name: str
    age: int

class WirelessConfig(BaseModel):
    host: str
    port: int

BUFFER_SIZE = FS * 5
EVAL_EVERY = FS

# Global buffers and state
class State:
    def __init__(self):
        self.ecg_buffer = collections.deque(maxlen=BUFFER_SIZE)
        self._eval_counter = 0
        self.latest_prediction: Optional[dict] = None
        self.latest_diagnostic: Optional[dict] = None
        self.leads_off: bool = False
        self.active_patient: Optional[PatientSession] = None
        self.transition_until: float = 0.0  # Timestamp after which inference is re-enabled
        
        # Firebase Service Initialization
        self.firebase_service = FirebaseService(
            key_path=os.getenv("FIREBASE_KEY_PATH", r"g:\My Drive\PULSEAI\frontend\pulseasi-firebase-adminsdk-fbsvc-6dfddc1a68.json"),
            db_url=os.getenv("FIREBASE_DB_URL", "https://pulseasi-default-rtdb.asia-southeast1.firebasedatabase.app/"),
            on_alert=self.on_firebase_alert
        )

    def on_firebase_alert(self, report: str, bpm: int):
        """Callback to broadcast Firebase BPM alerts to all connected clients."""
        logger.info(f"🔥 Firebase Alert: {report}")
        payload = {
            "type": "firebase_alert",
            "message": report,
            "bpm": bpm,
            "timestamp": datetime.now().isoformat()
        }
        manager.broadcast_from_thread(json.dumps(payload))

state = State()

# --- Data Ingestion Engine ---
def on_raw_sample(val: float):
    """Callback for every raw sample received from ANY source."""
    state.ecg_buffer.append(val)
    
    state._eval_counter += 1
    if state._eval_counter >= EVAL_EVERY and len(state.ecg_buffer) >= SEGMENT_LEN:
        state._eval_counter = 0
        # Skip inference during the 2-second transition window after a mode switch
        if time.time() < state.transition_until:
            return
        asyncio.create_task(run_inference_cycle())

def on_status_change(is_on: bool):
    """Update leads off status and broadcast to clients."""
    if state.leads_off == (not is_on): return
    state.leads_off = not is_on
    manager.broadcast_from_thread(json.dumps({
        "type": "leads_off" if state.leads_off else "leads_on"
    }))

ingestor = DataIngestor(on_data_callback=on_raw_sample, on_status_callback=on_status_change)

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Active: {len(self.active_connections)}")

        initial_state = {
            "type": "snapshot",
            "leads_off": state.leads_off,
            "ecg_snapshot": [*state.ecg_buffer],
            "prediction": state.latest_prediction,
            "diagnostic": state.latest_diagnostic,
        }
        await websocket.send_text(json.dumps(initial_state))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def broadcast_from_thread(self, message: str):
        loop = self._loop
        if loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    manager.set_loop(asyncio.get_running_loop())
    try:
        await ingestor.start()
        logger.info(f"🚀 PulseAI Ingestion Engine started (Active Source: {ingestor.active_source})")
        # Start Firebase Service in a separate thread/background
        state.firebase_service.start()
    except Exception as exc:
        logger.error(f"Ingestion Engine failed to start: {exc}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Shutting down PulseAI platform...")
    await ingestor.stop()
    state.firebase_service.stop()

async def run_inference_cycle():
    """Trigger AI processing and broadcast results."""
    if len(state.ecg_buffer) < SEGMENT_LEN: return
    
    patient = state.active_patient
    pid = patient.patient_id if patient else "pulseai-global"
    cleaned = process_ecg(state.ecg_buffer)
    window = extract_beat_window(cleaned)
    
    res = await predict_logic(window, pid)
    state.latest_prediction = res
    if res.get("fhir_report"):
        state.latest_diagnostic = res["fhir_report"]
    
    manager.broadcast_from_thread(json.dumps({
        "type": "prediction",
        "patient_id": pid,
        **res,
        "ecg_snapshot": [*state.ecg_buffer]
    }))

async def predict_logic(window: list, pid: str) -> dict:
    result: dict = {}
    if COLAB_INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{COLAB_INFERENCE_URL}/predict",
                    json={"ecg_window": window, "patient_id": pid},
                    headers={"bypass-tunnel-reminder": "true"}
                )
                resp.raise_for_status()
                json_data = resp.json()
                if isinstance(json_data, dict):
                    result = json_data
        except Exception:
            result = predict_arrhythmia(window)
    else:
        result = predict_arrhythmia(window)

    if result.get("is_arrhythmia"):
        result.update({
            "fhir_report": generate_fhir_diagnostic_report(
                patient_id=pid,
                classification=str(result.get("classification", "Unknown")),
                confidence=float(result.get("confidence", 0.90)),
                explainability_map=result.get("explainability_map")
            )
        })
    return result

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/health")
async def health():
    model_status = get_model_status()
    patient = state.active_patient
    return {
        "status": "ok",
        "version": "2.1.0",
        "colab_bridge": COLAB_INFERENCE_URL or "disabled (local model)",
        "active_source": ingestor.active_source,
        "leads_off": state.leads_off,
        "buffer_samples": len(state.ecg_buffer),
        "active_patient": patient.patient_id if patient else None,
        **model_status,
    }

@app.post("/api/source")
async def set_source(source: str):
    """Switch the data source (SIMULATION, MQTT, SERIAL, BLUETOOTH, HTTP)."""
    ingestor.set_source(source)
    return {"status": "success", "new_source": ingestor.active_source}

@app.post("/api/config/wireless")
async def set_wireless_config(config: WirelessConfig):
    """Set the IP and Port for the wireless bridge."""
    ingestor.socket_remote_host = config.host
    ingestor.socket_remote_port = config.port
    logger.info(f"📶 Wireless config updated: {config.host}:{config.port}")
    return {"status": "success", "config": {"host": config.host, "port": config.port}}

@app.post("/api/simulation/mode")
async def set_simulation_mode(mode: str):
    """Set the disease simulation mode (0-7)."""
    ingestor.simulation_mode = mode
    # Trigger pristine simulation or live sensor mapping
    if mode == "7":
        ingestor.set_source("SERIAL")
    else:
        ingestor.set_source("SIMULATION")
    
    # Flush buffer + block inference for 2s so stale disease samples don't
    # produce false positives right after switching to Normal / another mode
    state.ecg_buffer.clear()
    state._eval_counter = 0
    state.transition_until = time.time() + 2.0  # 2 second transition grace period
    return {"status": "success", "mode": mode}

@app.post("/api/ingest")
async def ingest_data(value: float):
    """Manual data entry for 'farhter laptop' or direct connection."""
    await ingestor.ingest_http(value)
    return {"status": "data_received"}

@app.post("/api/patient")
async def register_patient(patient: PatientSession):
    state.active_patient = patient
    logger.info(f"Patient registered: {patient.patient_id} — {patient.name}, age {patient.age}")
    return {"status": "registered", "patient_id": patient.patient_id}

@app.get("/api/ecg")
async def get_ecg():
    return {"data": [*state.ecg_buffer], "leads_off": state.leads_off, "buffer_size": len(state.ecg_buffer)}

@app.get("/api/diagnostic")
async def get_latest_diagnostic():
    if state.latest_diagnostic:
        return state.latest_diagnostic
    if state.latest_prediction:
        return {"status": "monitoring", "last_prediction": state.latest_prediction}
    return {"status": "No data yet — waiting for ECG stream."}

@app.post("/api/predict")
async def predict_ecg_window(payload: dict):
    ecg_window = payload.get("ecg_window")
    if not ecg_window or len(ecg_window) < 10:
        raise HTTPException(status_code=400, detail="'ecg_window' must have at least 10 samples.")

    pid     = str(payload.get("patient_id", "pulseai-api"))
    cleaned = process_ecg(ecg_window)
    window  = extract_beat_window(cleaned)
    return await predict_logic(window, pid)
if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run(app, host="127.0.0.1", port=8000)
