#include <WiFi.h>
#include <PubSubClient.h>

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

unsigned long lastSendTime = 0;
// Sample at 500 Hz -> 2ms interval
const int sampleIntervalMs = 2; 

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "ESP32Client-PULSEAI-";
    clientId += String(random(0, 10000));
    
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(pinLOPlus, INPUT);
  pinMode(pinLOMinus, INPUT);
  pinMode(pinOutput, INPUT);

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long currentMillis = millis();
  
  // Sample at 500 Hz
  if (currentMillis - lastSendTime >= sampleIntervalMs) {
    lastSendTime = currentMillis;

    // Check if leads are off
    if ((digitalRead(pinLOPlus) == 1) || (digitalRead(pinLOMinus) == 1)) {
      // Leads off anomaly value or 0
      client.publish(mqtt_topic, "LEADS_OFF");
    } else {
      // Read ADC value
      int ecgValue = analogRead(pinOutput);
      
      // Publish Data via MQTT payload
      char msg[10];
      snprintf(msg, sizeof(msg), "%d", ecgValue);
      client.publish(mqtt_topic, msg);
    }
  }
}
