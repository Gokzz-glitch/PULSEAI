# 🫀 PULSEAI: Edge-Cloud Arrhythmia Platform
**Master Setup & Onboarding Guide**

Welcome to the PulseAI repository. This document serves as the absolute source of truth for understanding, cloning, and running the PulseAI platform in **under 5 minutes**.

PulseAI is a real-time ECG monitoring platform that ingests raw telemetry (from ESP32 or simulated sources), filters it (0.5Hz / 50Hz notch), and passes it through an incredibly fast, highly accurate (>85%) Deep Learning model (**HCTG-Net**) to detect Arrhythmias and generate FHIR Diagnostic Reports in real time.

---

## 📂 Repository Structure

When you clone this project, here is exactly what you are looking at:

### 1. The Brain (`/backend`)
*   `main.py`: The FastAPI server. This is the heart of the system that hosts all REST endpoints and WebSockets.
*   `ml_model.py`: The **ArrhythmiaEngine**. It automatically loads the trained AI model weights and performs live inferences.
*   `signal_processing.py`: Clinical-grade digital filters (baseline wander removal, powerline noise removal, Z-Score normalization) used to clean the raw ECG array before it reaches the AI.
*   `ingestion.py`: Handles incoming data from Serial/USB (COM Ports), MQTT, or HTTP.
*   `hctg_net_model.h5`: The **golden compiled model file**. This is the state-of-the-art Hybrid CNN-Transformer weights exported from Google Colab.

### 2. The Face (`/vanilla_demo.html` & `/frontend`)
*   `vanilla_demo.html`: **[Recommended for instantly viewing]** A zero-dependency, lightning-fast static HTML file. Double-click it to instantly connect to the backend WebSocket and visualize the live heartbeat data and AI predictions.
*   `/frontend`: The primary React/Vite 3D dashboard. (Requires Node.js/NPM to run).
*   `/frontend_runtime`: A backup copy of the frontend.

### 3. The Simulators & Testing
*   `fast_feeder.py`: A very lightweight script that pumps a perfect sine-wave into the backend via HTTP. Great for rapid local UI testing.
*   `test_10cases_age_variety.py`: A robust test suite running 10 unique clinical scenarios through the AI engine to generate CSV/PNG accuracy reports.
*   `realtime_detection_monitor.py`: A terminal UI script simulating live data streaming and printing FHIR Diagnostic reports to your console.

---

## 🚀 5-Minute Quickstart

If you just cloned this repo and want to see the AI running immediately, follow these 3 exact steps:

### Step 1: Start the AI Backend Server
You need Python installed (v3.10+ recommended).
Open a terminal, navigate to the `backend/` folder, and start the FastAPI server:
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
*(You will see a message saying `ArrhythmiaEngine initialized` and that it loaded the Keras `hctg_net_model.h5` model).*

### Step 2: Open the Dashboard
You don't need any complex web servers. Simply locate `vanilla_demo.html` in the root folder and double-click it to open it in Chrome or Edge. It will instantly say:
**`LIVE • connected to ArrhythmiaEngine`**

### Step 3: Stream Live Heartbeat Data
Open a *second* terminal window in the root directory and start feeding the engine realistic heartbeat data using the built-in HTTP simulator:
```bash
python fast_feeder.py
```
*(As soon as this script is running, instantly check your browser! You will see the ECG graph dancing and the HCTG-Net classifying the rhythm live).*

---

## 📡 Hardware Integration (ESP32)
If you are connecting an actual ESP32 sensor:
1. Ensure the ESP32 is plugged in (typically `COM4` on Windows).
2. The `ingestion.py` module handles the Serial baud rate (115200). 
3. Run `python backend/serial_test.py` to confirm raw data is arriving cleanly before connecting the AI engine!

## 🎓 Model Re-Training
To train a new model from scratch, locate the Colab Notebooks saved in your Google Drive (e.g., `Untitled-1.ipynb` or `PulseAI_HCTG_Net_Colab.ipynb`). These scripts automatically download the MIT-BIH Arrhythmia Dataset, build the Deep Learning model, train it to >85% accuracy, and export a new `.h5` file which you can drop back into this `backend/` folder!

---

## 🤖 AI Agent Boot Protocol
**Attention AI Assistants (Gemini/Claude/ChatGPT, etc):**
If the user tells you to "check MASTER.md and start my project", execute the following tasks sequentially:
1. Verify `requirements.txt` is installed in the local environment. If not, run `pip install -r backend/requirements.txt`.
2. Launch the `fastapi` backend server by running `python -m uvicorn main:app --host 0.0.0.0 --port 8000` from the `backend/` directory in a background process.
3. Once the server is live and the ArrhythmiaEngine model is loaded, launch the `vanilla_demo.html` in the user's default browser by running `Start-Process "vanilla_demo.html"` (on Windows) or equivalent.
4. Launch the local heartbeat simulation by running `python fast_feeder.py` in the background so data is flowing into the UI automatically.
5. Notify the user the system is fully alive!
