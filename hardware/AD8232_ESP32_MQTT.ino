#include <WiFi.h>
#include <PubSubClient.h>
#include <BluetoothSerial.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT Broker details
const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic = "pulseai/ecg/data";

// AD8232 Pins
const int pinLOPlus = 34; // LO+
const int pinLOMinus = 35; // LO-
const int pinOutput = 32; // OUTPUT

WiFiClient espClient;
PubSubClient client(espClient);
BluetoothSerial SerialBT;

unsigned long lastSendTime = 0;
const int sampleIntervalMs = 2; // 500 Hz

void setup_wifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  delay(10);
  Serial.println("Connecting WiFi...");
  WiFi.begin(ssid, password);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    Serial.print(".");
    retry++;
  }
}

void reconnect_mqtt() {
  while (!client.connected() && WiFi.status() == WL_CONNECTED) {
    Serial.print("MQTT connecting...");
    String clientId = "PulseAI-ESP32-";
    clientId += String(random(0, 1000));
    if (client.connect(clientId.c_str())) {
      Serial.println("MQTT connected");
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  SerialBT.begin("PulseAI_Device"); 
  Serial.println("PulseAI: Bluetooth and Serial Ready");

  pinMode(pinLOPlus, INPUT);
  pinMode(pinLOMinus, INPUT);
  pinMode(pinOutput, INPUT);

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  // Handle MQTT connectivity if WiFi is connected
  if (WiFi.status() == WL_CONNECTED) {
    if (!client.connected()) reconnect_mqtt();
    client.loop();
  }

  unsigned long currentMillis = millis();
  
  if (currentMillis - lastSendTime >= sampleIntervalMs) {
    lastSendTime = currentMillis;

    String payload;
    if ((digitalRead(pinLOPlus) == 1) || (digitalRead(pinLOMinus) == 1)) {
      payload = "LEADS_OFF";
    } else {
      payload = String(analogRead(pinOutput));
    }

    // 1. Send via USB Serial (Direct Connection)
    Serial.println(payload);

    // 2. Send via Bluetooth Serial
    if (SerialBT.hasClient()) {
      SerialBT.println(payload);
    }

    // 3. Send via MQTT (Wi-Fi)
    if (client.connected()) {
      client.publish(mqtt_topic, payload.c_str());
    }
  }
}
