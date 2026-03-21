@echo off
echo Starting PULSEAI Backend Server...
cd /d "g:\My Drive\PULSEAI\backend"
set COLAB_INFERENCE_URL=https://unfagged-emerie-swampy.ngrok-free.dev
start "PulseAI Backend" cmd /c "C:\Users\gokul\anaconda3\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload & pause"

echo Starting PULSEAI Frontend Server...
cd /d "g:\My Drive\PULSEAI\frontend"
start "PulseAI Frontend" cmd /c "npm run dev & pause"

echo Both servers have been launched in new windows!
echo Please open your browser to your frontend URL (usually http://localhost:5173 or 57089)
echo The 5-minute simulation will begin immediately.
