import psutil
import time
from datetime import datetime
import winsound

def check_hardware():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    
    msg = f"[{datetime.now().isoformat()}] CPU: {cpu}%, RAM: {ram}%"
    print(msg, end='\r')
    
    if cpu > 65 or ram > 65:
        warning = f"\n[{datetime.now().isoformat()}] WARNING: CPU/RAM usage exceeded 65% (CPU: {cpu}%, RAM: {ram}%). Please ensure tasks are offloaded to Colab.\n"
        print(warning)
        with open('hardware_log.txt', 'a') as f:
            f.write(warning)
        # Beep to alert user
        winsound.Beep(1000, 500)

print("Starting hardware monitor (limit 60% CPU)...")
while True:
    check_hardware()
    time.sleep(2)
