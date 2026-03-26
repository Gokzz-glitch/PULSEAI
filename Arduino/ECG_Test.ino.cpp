#line 1 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
#include <Arduino.h>
#include <WiFi.h>
#include <Firebase_ESP_Client.h>

#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"

// 1. Wi-Fi Details
#define WIFI_SSID "TP-Link_F5BC"
#define WIFI_PASSWORD "13047337"

// 2. PulseAI Firebase Credentials
#define API_KEY "AIzaSyCHA1jwX7EuxjbMrquxZYMAao1J6RHSajw"
#define DATABASE_URL "https://pulseasi-default-rtdb.asia-southeast1.firebasedatabase.app/"
#define USER_EMAIL "esp32@pulseai.com" 
#define USER_PASSWORD "pulseai_secure"

FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

// 3. ECG Variables (From your old code)
#define ECG_PIN 34
const int SAMPLE_RATE = 250;
const int SAMPLE_PERIOD = 1000000 / SAMPLE_RATE;
unsigned long lastSample = 0;

float filtered = 0;
float prevFiltered = 0;
float prevRaw = 0;
float alpha = 0.95;

int threshold = 150;
unsigned long lastBeat = 0;
int currentBPM = 0; // We store the BPM here to send to cloud later

unsigned long sendDataPrevMillis = 0;

#line 39 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void setup();
#line 62 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void loop();
#line 39 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void setup() {
  Serial.begin(115200);

  // WARNING: We removed WiFi.mode(WIFI_OFF) because we need the cloud!
  
  // Connect to Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(300);
  }
  Serial.println("\nConnected to Wi-Fi!");

  // Initialize Firebase
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  auth.user.email = USER_EMAIL;
  auth.user.password = USER_PASSWORD;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
}

void loop() {
  // --- TASK 1: FAST ECG SAMPLING ---
  if (micros() - lastSample >= SAMPLE_PERIOD) {
    lastSample = micros();
    int raw = analogRead(ECG_PIN);

    filtered = alpha * (prevFiltered + raw - prevRaw);
    prevFiltered = filtered;
    prevRaw = raw;

    // Calculate BPM
    if(filtered > threshold && millis() - lastBeat > 300) {
      unsigned long now = millis();
      currentBPM = 60000 / (now - lastBeat);
      lastBeat = now;
      
      // Print locally so your friend can see it's working
      Serial.print("Local BPM: ");
      Serial.println(currentBPM);
    }
  }

  // --- TASK 2: SLOW FIREBASE UPLOAD ---
  // Push the latest BPM to PulseAI every 5 seconds
  if (Firebase.ready() && (millis() - sendDataPrevMillis > 5000 || sendDataPrevMillis == 0)) {
    sendDataPrevMillis = millis();
    
    // Only send if we have a valid heart rate
    if (currentBPM > 0) {
      Serial.printf("Pushing BPM to PulseAI: %d... ", currentBPM);
      
      if (Firebase.RTDB.setInt(&fbdo, "sensors/esp32/bpm", currentBPM)) {
        Serial.println("Mass! Cloud update success.");
      } else {
        Serial.println("Failed. Reason: " + fbdo.errorReason());
      }
    }
  }
}
