import logging
import json
import os
import asyncio
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import paho.mqtt.client as mqtt
from signal_processing import process_ecg, extract_beat_window, FS, SEGMENT_LEN
from ml_model import predict_arrhythmia
from fhir_generator import generate_fhir_diagnostic_report
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PulseAI Edge-Cloud Platform", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT   = 1883
MQTT_TOPIC  = "pulseai/ecg/data"

# ── Colab Cloud Inference Bridge ───────────────────────────────────────────────
# Set COLAB_INFERENCE_URL env variable to the ngrok URL from the Colab notebook.
# Leave unset to use local backend/hctg_net_model.h5 instead.
COLAB_INFERENCE_URL: Optional[str] = os.getenv("COLAB_INFERENCE_URL", "").strip().rstrip("/") or None
if COLAB_INFERENCE_URL:
    logger.info(f"☁️  Colab inference bridge active: {COLAB_INFERENCE_URL}")
else:
    logger.info("💻 Local HCTG-Net mode (place hctg_net_model.h5 in backend/ for real inference).")

class PatientSession(BaseModel):
    patient_id: str
    name: str
    age: int

active_patient: Optional[PatientSession] = None

# In-memory buffer — 5 seconds at configured sample rate
ecg_buffer: list[float] = []
BUFFER_SIZE = FS * 5  # 2500 samples @ 500 Hz

eval_counter = 0
EVAL_EVERY   = FS   # run inference every 1 second of new data

latest_prediction: Optional[dict] = None
latest_diagnostic: Optional[dict] = None
leads_off: bool = False

# WebSocket manager for active frontend clients
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
        """Thread-safe broadcast called from the MQTT sync callback thread."""
        loop = self._loop
        if loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)

manager = ConnectionManager()

def on_mqtt_connect(client, userdata, flags, rc):
    logger.info(f"MQTT connected to {MQTT_BROKER} (rc={rc})")
    client.subscribe(MQTT_TOPIC)

def on_mqtt_message(client, userdata, msg):
    global ecg_buffer, latest_prediction, latest_diagnostic, leads_off, eval_counter
    try:
        payload = msg.payload.decode().strip()

        if payload == "LEADS_OFF":
            leads_off = True
            manager.broadcast_from_thread(json.dumps({"type": "leads_off"}))
            return

        leads_off = False
        val = float(payload)
        ecg_buffer.append(val)

        if len(ecg_buffer) > BUFFER_SIZE:
            ecg_buffer = ecg_buffer[-BUFFER_SIZE:]

        eval_counter += 1

        if eval_counter >= EVAL_EVERY and len(ecg_buffer) >= SEGMENT_LEN:
            eval_counter = 0
            pid = active_patient.patient_id if active_patient else "patient-unknown"

            cleaned    = process_ecg(ecg_buffer)
            window     = extract_beat_window(cleaned)
            prediction = predict_arrhythmia(window)
            latest_prediction = prediction

            broadcast_payload: dict = {
                "type": "prediction",
                "patient_id": pid,
                **prediction,
                "ecg_snapshot": list(ecg_buffer[-100:])
            }

            if prediction["is_arrhythmia"]:
                logger.warning(
                    f"⚠️  {prediction['classification']} | confidence={prediction['confidence']}"
                )
                fhir = generate_fhir_diagnostic_report(
                    patient_id=pid,
                    classification=prediction["classification"],
                    confidence=prediction.get("confidence", 0.90),
                    explainability_map=prediction.get("explainability_map")
                )
                latest_diagnostic = fhir
                broadcast_payload["fhir_report"] = fhir

            manager.broadcast_from_thread(json.dumps(broadcast_payload))

    except (ValueError, TypeError):
        pass
    except Exception as exc:
        logger.error(f"MQTT handler error: {exc}")

try:
    mqtt_client = mqtt.Client(
        client_id="PulseAI-Backend-v2",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1
    )
except AttributeError:
    mqtt_client = mqtt.Client(client_id="PulseAI-Backend-v2")

mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

@app.on_event("startup")
async def startup_event():
    manager._loop = asyncio.get_running_loop()
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        logger.info("MQTT listener started.")
    except Exception as exc:
        logger.error(f"MQTT connection failed: {exc}. Running without live hardware feed.")

    # Start the internal data simulator
    asyncio.create_task(simulate_ecg_background())

async def simulate_ecg_background():
    """Background task to simulate ECG data if no real hardware is connected."""
    global ecg_buffer, eval_counter
    import math, random
    t = 0
    freq = 500
    logger.info("🎬 Internal ECG simulator started (running alongside MQTT)")
    while True:
        # Only simulate if buffer is low (means MQTT isn't feeding it)
        # Increased limit to 600 to allow SEGMENT_LEN (250) and EVAL_EVERY (500) to trigger
        if len(ecg_buffer) < 600:
            is_anomaly = random.random() < 0.05
            hr = 60 if not is_anomaly else 140
            
            p_wave = 0.1 * math.exp(-((t % (freq * 60 / hr) - 50)**2) / 100)
            qrs = 1.2 * math.exp(-((t % (freq * 60 / hr) - 100)**2) / 8)
            t_wave = 0.3 * math.exp(-((t % (freq * 60 / hr) - 200)**2) / 400)
            
            val = (p_wave + qrs + t_wave + (random.random() * 0.05)) * 100
            ecg_buffer.append(val)
            if len(ecg_buffer) > BUFFER_SIZE: 
                ecg_buffer.pop(0)
            
            eval_counter += 1
            if eval_counter >= EVAL_EVERY:
                eval_counter = 0
                try:
                    # Capture the data snapshot to process
                    current_data = list(ecg_buffer)
                    cleaned = process_ecg(current_data)
                    if len(cleaned) >= SEGMENT_LEN:
                        window = extract_beat_window(cleaned)
                        # We use create_task to avoid blocking the simulator pulse
                        asyncio.create_task(predict_api(window))
                except Exception as e:
                    logger.debug(f"Simulation inference throttle: {e}")
            t += 1
        await asyncio.sleep(1/freq)

async def predict_api(window: list[float]):
    """Wrapper to handle inference and broadcast results."""
    global latest_prediction, latest_diagnostic
    pid = active_patient.patient_id if active_patient else "patient-sim"
    res = await get_inference(window, pid)
    latest_prediction = res
    if res.get("fhir_report"):
        latest_diagnostic = res["fhir_report"]
        
    manager.broadcast_from_thread(json.dumps({
        "type": "prediction",
        "patient_id": pid,
        **res,
        "ecg_snapshot": list(ecg_buffer[-100:])
    }))
    return res

@app.on_event("shutdown")
async def shutdown_event():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

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
    return {
        "status": "ok",
        "version": "2.0.0",
        "colab_bridge": COLAB_INFERENCE_URL or "disabled (local model)",
        "mqtt_connected": mqtt_client.is_connected(),
        "leads_off": leads_off,
        "buffer_samples": len(ecg_buffer),
        "active_patient": active_patient.patient_id if active_patient else None
    }

@app.post("/api/patient")
async def register_patient(patient: PatientSession):
    global active_patient
    active_patient = patient
    logger.info(f"Patient registered: {patient.patient_id} — {patient.name}, age {patient.age}")
    return {"status": "registered", "patient_id": patient.patient_id}

@app.get("/api/ecg")
async def get_ecg():
    """Return last 100 ECG samples for dashboard chart."""
    buffer_len = len(ecg_buffer)
    start_idx = max(0, buffer_len - 100)
    data_slice = ecg_buffer[start_idx:buffer_len]
    return {"data": list(data_slice), "leads_off": leads_off, "buffer_size": buffer_len}

@app.get("/api/diagnostic")
async def get_latest_diagnostic():
    """Return the latest FHIR DiagnosticReport or last prediction."""
    if latest_diagnostic:
        return latest_diagnostic
    if latest_prediction:
        return {"status": "monitoring", "last_prediction": latest_prediction}
    return {"status": "No data yet — waiting for ECG stream from device."}

@app.post("/api/predict")
async def predict_ecg_window(payload: dict):
    """
    Direct inference endpoint — accepts JSON body with 'ecg_window' (list of floats).
    Routes to Colab cloud GPU if COLAB_INFERENCE_URL is set, otherwise local model.

    Body: { "ecg_window": [0.12, 0.34, ...], "patient_id": "optional-id" }
    """
    ecg_window = payload.get("ecg_window")
    if not ecg_window or len(ecg_window) < 10:
        raise HTTPException(status_code=400, detail="'ecg_window' must have at least 10 samples.")

    pid     = str(payload.get("patient_id", "api-test"))
    cleaned = process_ecg(ecg_window)
    window  = extract_beat_window(cleaned)

async def get_inference(window: list[float], pid: str) -> dict:
    """Core inference logic: Routes to Colab GPU if active, else local models."""
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
                result = dict(resp.json())
        except Exception as exc:
            logger.warning(f"Colab bridge failed ({exc}), using local model.")
            result = predict_arrhythmia(window)
    else:
        result = predict_arrhythmia(window)

    inference_result = dict(result)
    if inference_result.get("is_arrhythmia"):
        inference_result["fhir_report"] = generate_fhir_diagnostic_report(
            patient_id=pid,
            classification=str(inference_result.get("classification", "Unknown")),
            confidence=float(inference_result.get("confidence", 0.90)),
            explainability_map=inference_result.get("explainability_map")
        )
    return inference_result
