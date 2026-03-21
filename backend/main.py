import logging
import json
import os
import asyncio
import time
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import paho.mqtt.client as mqtt
from signal_processing import process_ecg, extract_beat_window, FS, SEGMENT_LEN
from ml_model import predict_arrhythmia, get_model_status
from fhir_generator import generate_fhir_diagnostic_report
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PulseAI Edge-Cloud Platform", version="2.0.0")

cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
allow_origins = [o.strip() for o in cors_origins.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT   = 1883
MQTT_TOPIC  = "pulseai/ecg/data"

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

active_patient: Optional[PatientSession] = None

# In-memory buffer — 5 seconds at configured sample rate
ecg_buffer: List[float] = []
BUFFER_SIZE = FS * 5  # 2500 samples @ 500 Hz

_eval_counter = 0
EVAL_EVERY    = FS   # run inference every 1 second of new data

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

        # Push latest snapshot immediately to improve first paint UX.
        initial_state = {
            "type": "snapshot",
            "leads_off": leads_off,
            "ecg_snapshot": ecg_buffer[-100:],
            "prediction": latest_prediction,
            "diagnostic": latest_diagnostic,
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
        """Thread-safe broadcast called from the MQTT sync callback thread."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)

manager = ConnectionManager()

def on_mqtt_connect(client, userdata, flags, rc):
    logger.info(f"MQTT connected to {MQTT_BROKER} (rc={rc})")
    client.subscribe(MQTT_TOPIC)

def on_mqtt_message(client, userdata, msg):
    global ecg_buffer, latest_prediction, latest_diagnostic, leads_off, _eval_counter
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

        _eval_counter += 1

        if _eval_counter >= EVAL_EVERY and len(ecg_buffer) >= SEGMENT_LEN:
            _eval_counter = 0
            pid = active_patient.patient_id if active_patient else "patient-unknown"

            cleaned    = process_ecg(ecg_buffer)
            window     = extract_beat_window(cleaned)
            prediction = predict_arrhythmia(window)
            latest_prediction = prediction

            broadcast_payload: dict = {
                "type": "prediction",
                "patient_id": pid,
                **prediction,
                "timestamp": time.time(),
                "ecg_snapshot": ecg_buffer[-100:]
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
    manager.set_loop(asyncio.get_running_loop())
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        logger.info("MQTT listener started.")
    except Exception as exc:
        logger.error(f"MQTT connection failed: {exc}. Running without live hardware feed.")
    
    # Internal Simulator to ensure dashboard is NEVER blank (even without hardware)
    asyncio.create_task(simulate_ecg_background())

async def simulate_ecg_background():
    """Rotating multi-case simulator for clinical testing."""
    global ecg_buffer, _eval_counter
    import math, random
    t = 0
    freq = 500
    
    # Simulation Phase Timing: 75 seconds per case = 5 minutes total
    PHASE_DURATION = 75 
    
    while True:
        elapsed = (t / freq)
        phase = int(elapsed / PHASE_DURATION) % 4
        
        # Always simulate for presentation mode
        if True:
            # Case Logic
            if phase == 0: # CASE 1: HEAVY WORKOUT
                hr = 145 + random.uniform(-2, 2)
                mode = "Workout (Tachycardia)"
                is_arrhythmia = False
            elif phase == 1: # CASE 2: SLEEPING POST-GYM
                hr = 62 + random.uniform(-1, 1)
                mode = "Deep Sleep"
                is_arrhythmia = False
            elif phase == 2: # CASE 3: ELDERLY ATTACK (AFIB)
                hr = 155 + random.uniform(-20, 20) # High variability for AFib
                mode = "Critical Event (AFib)"
                is_arrhythmia = True
            else: # CASE 4: ELDERLY CLIMBING HILL
                hr = 115 + random.uniform(-3, 3)
                mode = "Elderly Activity"
                is_arrhythmia = False

            # Waveform Generation
            # QRS complex
            qrs_pos = (t % (freq * 60 / hr))
            qrs = 1.3 * math.exp(-((qrs_pos - 100)**2) / 10)
            
            # P and T waves
            p_wave = 0.15 * math.exp(-((qrs_pos - 60)**2) / 50)
            t_wave = 0.35 * math.exp(-((qrs_pos - 180)**2) / 200)
            
            # Add AFib noise/irregularity in Phase 2
            noise = random.uniform(-0.05, 0.05)
            if phase == 2:
                noise += random.uniform(-0.2, 0.2) # Baseline wander/f-waves
            
            val = (p_wave + qrs + t_wave + noise) * 100
            ecg_buffer.append(val)
            
            if len(ecg_buffer) > BUFFER_SIZE: 
                ecg_buffer.pop(0)
            
            _eval_counter += 1
            if _eval_counter >= EVAL_EVERY:
                _eval_counter = 0
                logger.info(f"🧪 Simulation Phase {phase+1}: {mode} | HR: {int(hr)}")
                asyncio.create_task(run_inference_cycle())
            
            t += 1
        await asyncio.sleep(1/freq)

async def run_inference_cycle():
    """Trigger AI processing and broadcast results."""
    global latest_prediction, latest_diagnostic
    if len(ecg_buffer) < SEGMENT_LEN: return
    
    pid = active_patient.patient_id if active_patient else "pulseai-sim"
    cleaned = process_ecg(ecg_buffer)
    window = extract_beat_window(cleaned)
    
    # Prediction via Bridge or Local
    res = await predict_logic(window, pid)
    latest_prediction = res
    if res.get("fhir_report"):
        latest_diagnostic = res["fhir_report"]
    
    manager.broadcast_from_thread(json.dumps({
        "type": "prediction",
        "patient_id": pid,
        **res,
        "ecg_snapshot": list(ecg_buffer[-100:])
    }))

async def predict_logic(window: list, pid: str) -> dict:
    if COLAB_INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{COLAB_INFERENCE_URL}/predict",
                    json={"ecg_window": window, "patient_id": pid},
                    headers={"bypass-tunnel-reminder": "true"}
                )
                resp.raise_for_status()
                result = resp.json()
        except Exception:
            result = predict_arrhythmia(window)
    else:
        result = predict_arrhythmia(window)

    if result.get("is_arrhythmia"):
        result["fhir_report"] = generate_fhir_diagnostic_report(
            patient_id=pid,
            classification=result["classification"],
            confidence=result.get("confidence", 0.90),
            explainability_map=result.get("explainability_map")
        )
    return result

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
    model_status = get_model_status()
    return {
        "status": "ok",
        "version": "2.0.0",
        "colab_bridge": COLAB_INFERENCE_URL or "disabled (local model)",
        "cors_allow_origins": allow_origins,
        "mqtt_connected": mqtt_client.is_connected(),
        "leads_off": leads_off,
        "buffer_samples": len(ecg_buffer),
        "active_patient": active_patient.patient_id if active_patient else None,
        **model_status,
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
    return {"data": ecg_buffer[-100:], "leads_off": leads_off, "buffer_size": len(ecg_buffer)}

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

    if COLAB_INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{COLAB_INFERENCE_URL}/predict",
                    json={"ecg_window": window, "patient_id": pid}
                )
                resp.raise_for_status()
                result = resp.json()
        except Exception as exc:
            logger.warning(f"Colab bridge failed ({exc}), using local model.")
            result = predict_arrhythmia(window)
    else:
        result = predict_arrhythmia(window)

    if result.get("is_arrhythmia"):
        result["fhir_report"] = generate_fhir_diagnostic_report(
            patient_id=pid,
            classification=result["classification"],
            confidence=result.get("confidence", 0.90),
            explainability_map=result.get("explainability_map")
        )
    return result
