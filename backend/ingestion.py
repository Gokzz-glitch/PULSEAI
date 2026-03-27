import logging
import asyncio
import sys
import json
import time
import math
import random
import serial # pyre-ignore[21]
import serial.tools.list_ports # pyre-ignore[21]
from typing import Callable, Optional, List, Any
from paho.mqtt import client as mqtt # pyre-ignore[21]
try:
    import bleak # pyre-ignore[21]
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
        self._mqtt_client: Optional[Any] = None
        self._serial_conn: Optional[serial.Serial] = None
        self.simulation_mode = "1"


    def _update_status(self, leads_on: bool):
        cb = self.on_status
        if cb is not None:
            cb(leads_on)

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
        if self._mqtt_client is not None:
            try:
                self._mqtt_client.loop_stop()  # type: ignore
                self._mqtt_client.disconnect()  # type: ignore
            except Exception:
                pass
        conn = self._serial_conn
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    async def ingest_http(self, value: float):
        """Manual ingestion via HTTP POST."""
        if self.active_source == "HTTP" or self.active_source == "REMOTE":
            self.on_data(value)

    # --- Private Implementation ---

    async def _run_simulation(self):
        """Clinical ECG simulator capable of dynamic disease states."""
        sim_time = 0.0
        freq = 500.0
        dt = 1.0 / freq
        chunk_size = 50
        time_since_last_beat = 0.0
        current_rr = 0.8

        while self.is_running:
            if self.active_source == "SIMULATION":
                mode = self.simulation_mode
                if mode == "0":
                    self._update_status(False)
                else:
                    self._update_status(True)

                for _ in range(chunk_size):
                    v = 0.0
                    if mode == "0":
                        v = random.uniform(-0.02, 0.02)
                        time_since_last_beat += dt  # type: ignore
                    elif mode == "5":
                        v = 2.0 * math.sin(sim_time * 15.0) + 1.2 * math.cos(sim_time * 25.0) + random.uniform(-0.5, 0.5)  # type: ignore
                        time_since_last_beat += dt  # type: ignore
                    else:
                        if mode == "1": hr, target_rr = 75.0, 60.0 / 75.0
                        elif mode == "3": hr, target_rr = 150.0, 60.0 / 150.0
                        elif mode == "4": hr, target_rr = 180.0, 60.0 / 180.0
                        elif mode == "6": hr, target_rr = 40.0, 60.0 / 40.0
                        else: target_rr = current_rr  # AFib

                        if time_since_last_beat >= target_rr:
                            time_since_last_beat = 0.0
                            if mode == "2":
                                current_rr = random.uniform(0.4, 1.2)

                        qrs_pos = time_since_last_beat * freq
                        noise = random.uniform(-0.02, 0.02)

                        if mode == "4":
                            qrs = 2.5 * math.exp(-((qrs_pos - 50.0)**2.0) / 40.0)
                            t_wave = -0.8 * math.exp(-((qrs_pos - 100.0)**2.0) / 20.0)
                            v = qrs + t_wave + noise
                        else:
                            qrs = 1.5 * math.exp(-((qrs_pos - 100.0)**2.0) / 10.0)
                            t_wave = 0.35 * math.exp(-((qrs_pos - 200.0)**2.0) / 200.0)

                            if mode == "3":
                                f_wave = 0.3 * math.sin(sim_time * 80.0)
                                v = qrs + t_wave + f_wave + noise
                            elif mode == "2":
                                v = qrs + t_wave + 0.1 * math.sin(sim_time * 40.0) + noise
                            else:
                                p_wave = 0.15 * math.exp(-((qrs_pos - 50.0)**2.0) / 50.0)
                                v = p_wave + qrs + t_wave + noise

                    self.on_data(v)
                    sim_time += dt
                    
                    # Print live numerical feed on the same terminal line for the "hacker" visual!
                    if int(sim_time * freq) % 15 == 0:
                        sys.stdout.write(f"\r🫀 Live ECG Telemetry [Mode {mode}]: {v:+.5f} mV    ")
                        sys.stdout.flush()

                await asyncio.sleep(chunk_size / freq)
            else:
                await asyncio.sleep(1.0)

    async def _run_mqtt(self):
        """Bridge MQTT data to local stream."""
        def on_connect(client, userdata, flags, rc):
            client.subscribe(self.mqtt_topic)  # type: ignore
            logger.info(f"✅ Ingestor MQTT Connected: {self.mqtt_topic}")

        def on_message(client, userdata, msg):
            if self.active_source == "MQTT":
                try:
                    payload = msg.payload.decode().strip()
                    if payload == "LEADS_OFF":
                        self._update_status(False)
                    else:
                        self._update_status(True)
                        self.on_data(float(payload))
                except Exception:
                    pass

        try:
            client = mqtt.Client(client_id=f"PulseAI-Ingestor-{random.randint(0,1000)}")  # type: ignore
            client.on_connect = on_connect  # type: ignore
            client.on_message = on_message  # type: ignore
            client.connect_async(self.mqtt_broker, 1883)  # type: ignore
            client.loop_start()  # type: ignore
            self._mqtt_client = client
        except Exception as e:
            logger.error(f"MQTT Ingestion Error: {e}")

    async def _run_serial(self):
        """Read from direct USB connection."""
        count = 0
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

                    conn = self._serial_conn
                    if conn is not None and conn.in_waiting > 0:
                        line = conn.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            if line == "LEADS_OFF":
                                self._update_status(False)
                            else:
                                try:
                                    val = float(line)
                                    self._update_status(True)
                                    self.on_data(val)
                                    count += 1
                                    if count % 15 == 0:
                                        sys.stdout.write(f"\r🔌 [HW SENSOR LIVE] Telemetry: {val:+.5f} mV   ")
                                        sys.stdout.flush()
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
                                self._update_status(False)
                            else:
                                try:
                                    val = float(line)
                                    self._update_status(True)
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
