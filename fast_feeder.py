import httpx
import math
import time

print("Feeding ECG data to localhost:8000...")
try:
    for i in range(500):
        # Create a rough ECG-like shape (mostly flat, some spikes)
        v = math.sin(i / 5.0) * 0.5
        if i % 50 == 0: v += 1.5 # R-peak
        elif i % 50 == 10: v -= 0.5 # S-wave
        
        try:
            httpx.post(f"http://127.0.0.1:8000/api/ingest?value={v}", timeout=1.0)
        except Exception as e:
            pass
        
        time.sleep(0.04) # 25Hz feed rate
except KeyboardInterrupt:
    pass
print("Finished feeding.")
