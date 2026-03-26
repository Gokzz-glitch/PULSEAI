import logging
import asyncio
import json
import time
import math
import random
import serial
import serial.tools.list_ports
from typing import Callable, Optional, List
from paho.mqtt import client as mqtt
try:
    import bleak
except ImportError:
    bleak = None


logger = logging.getLogger(__name__)

class DataIngestor:
    """
    Unified ingestion engine for PulseAI.
    Subscribes to multiple sources and emits a unified stream of ECG samples.
    """
    def __init__(self, on_data_callback: Callable[[float], None], on_status_callback: Optional[Callable[[bool], None]] = None):
        self.on_data = on_data_callback
        self.on_status = on_status_callback # True = leads on, False = leads off
        self.active_source = "SIMULATION" 
        
        # Sources Config
        self.mqtt_broker = "broker.hivemq.com"
        self.mqtt_topic = "pulseai/ecg/data"
        self.serial_port = "COM4"
        self.serial_baud = 115200
        
        # Socket Config (Wireless Stream)
        self.socket_remote_host = "192.168.1.10" # IP of the Friend's laptop (Server)
        self.socket_remote_port = 5555
        
        # State
        self.is_running = False
        self._tasks: List[asyncio.Task] = []
        self._mqtt_client: Optional[mqtt.Client] = None
        self._serial_conn: Optional[serial.Serial] = None

    def set_source(self, source: str):
        """Set the active data source (SIMULATION, MQTT, SERIAL, BLUETOOTH, HTTP)."""
        logger.info(f"🔄 Switching data source to: {source}")
        self.active_source = source.upper()

    async def start(self):
        """Initialize all ingestion tasks."""
        self.is_running = True
        
        # Launch Simulation Task
        self._tasks.append(asyncio.create_task(self._run_simulation()))
        
        # Launch MQTT Task
        self._tasks.append(asyncio.create_task(self._run_mqtt()))
        
        # Launch Serial Task
        self._tasks.append(asyncio.create_task(self._run_serial()))
        
        # Launch Socket Task
        self._tasks.append(asyncio.create_task(self._run_socket()))

    async def stop(self):
        self.is_running = False
        for t in self._tasks:
            t.cancel()
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
        if self._serial_conn:
            self._serial_conn.close()

    async def ingest_http(self, value: float):
        """Manual ingestion via HTTP POST."""
        if self.active_source == "HTTP" or self.active_source == "REMOTE":
            self.on_data(value)

    # --- Private Implementation ---

    async def _run_simulation(self):
        """Clinical ECG simulator."""
        t = 0
        freq = 500
        while self.is_running:
            if self.active_source == "SIMULATION":
                if self.on_status: self.on_status(True)
                # Basic QRS/P/T generation
                hr = 72 + 5 * math.sin(t / 2000)
                qrs_pos = (t % (freq * 60 / hr))
                qrs = 1.3 * math.exp(-((qrs_pos - 100)**2) / 10)
                p_wave = 0.15 * math.exp(-((qrs_pos - 60)**2) / 50)
                t_wave = 0.35 * math.exp(-((qrs_pos - 180)**2) / 200)
                noise = random.uniform(-0.02, 0.02)
                
                val = (p_wave + qrs + t_wave + noise) * 100
                self.on_data(val)
                t += 1
            await asyncio.sleep(1/freq)

    async def _run_mqtt(self):
        """Bridge MQTT data to local stream."""
        def on_connect(client, userdata, flags, rc):
            client.subscribe(self.mqtt_topic)
            logger.info(f"✅ Ingestor MQTT Connected: {self.mqtt_topic}")

        def on_message(client, userdata, msg):
            if self.active_source == "MQTT":
                try:
                    payload = msg.payload.decode().strip()
                    if payload == "LEADS_OFF":
                        if self.on_status: self.on_status(False)
                    else:
                        if self.on_status: self.on_status(True)
                        self.on_data(float(payload))
                except Exception:
                    pass

        try:
            self._mqtt_client = mqtt.Client(client_id=f"PulseAI-Ingestor-{random.randint(0,1000)}")
            self._mqtt_client.on_connect = on_connect
            self._mqtt_client.on_message = on_message
            self._mqtt_client.connect_async(self.mqtt_broker, 1883)
            self._mqtt_client.loop_start()
        except Exception as e:
            logger.error(f"MQTT Ingestion Error: {e}")

    async def _run_serial(self):
        """Read from direct USB connection."""
        while self.is_running:
            if self.active_source == "SERIAL":
                try:
                    if not self._serial_conn:
                        ports = [p.device for p in serial.tools.list_ports.comports()]
                        target_port = None
                        
                        # Try preferred port first
                        if self.serial_port in ports:
                            target_port = self.serial_port
                        elif ports:
                            target_port = ports[0]
                            
                        if not target_port:
                            await asyncio.sleep(2)
                            continue
                            
                        self._serial_conn = serial.Serial(target_port, self.serial_baud, timeout=0.1)
                        logger.info(f"🔌 Serial connected on {target_port}")

                    if self._serial_conn.in_waiting > 0:
                        line = self._serial_conn.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            if line == "LEADS_OFF":
                                if self.on_status: self.on_status(False)
                            else:
                                try:
                                    val = float(line)
                                    if self.on_status: self.on_status(True)
                                    self.on_data(val)
                                except ValueError:
                                    pass
                except Exception as e:
                    logger.warning(f"Serial Ingestion Error: {e}")
                    self._serial_conn = None
            await asyncio.sleep(0.01)

    async def _run_socket(self):
        """Connect to a remote data stream (Wireless Bridge)."""
        while self.is_running:
            if self.active_source == "SOCKET" or self.active_source == "WIRELESS":
                try:
                    logger.info(f"📡 Attempting connection to Wireless Bridge at {self.socket_remote_host}:{self.socket_remote_port}...")
                    reader, writer = await asyncio.open_connection(
                        self.socket_remote_host, self.socket_remote_port
                    )
                    
                    logger.info(f"🤝 Wireless connection established with {self.socket_remote_host}")
                    
                    while self.is_running and self.active_source in ["SOCKET", "WIRELESS"]:
                        data = await reader.readline()
                        if not data:
                            break
                        line = data.decode().strip()
                        if line:
                            if line == "LEADS_OFF":
                                if self.on_status: self.on_status(False)
                            else:
                                try:
                                    val = float(line)
                                    if self.on_status: self.on_status(True)
                                    self.on_data(val)
                                except ValueError:
                                    pass
                    
                    writer.close()
                    await writer.wait_closed()
                    logger.info("👋 Wireless connection closed.")
                    
                except Exception as e:
                    logger.warning(f"Socket Connection Error: {e}. Retrying in 5s...")
                    await asyncio.sleep(5)
            else:
                await asyncio.sleep(1.0)

    async def _run_bluetooth(self):
        """Placeholder for BLE ingestion (requires bleak)."""
        # FUTURE: Implement scanning and characteristic reading
        pass
