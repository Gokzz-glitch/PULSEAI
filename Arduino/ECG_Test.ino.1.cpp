#include <Arduino.h>
#line 1 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
#include <WiFi.h>     

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

void setup() {
  Serial.begin(115200);

  WiFi.mode(WIFI_OFF);
  btStop();
}

void loop() {

  if (micros() - lastSample >= SAMPLE_PERIOD) {
    lastSample = micros();

    int raw = analogRead(ECG_PIN);

    filtered = alpha * (prevFiltered + raw - prevRaw);
    prevFiltered = filtered;
    prevRaw = raw;



























































    Serial.println(filtered);

    if(filtered > threshold && millis() - lastBeat > 300) {
      unsigned long now = millis();
      int bpm = 60000 / (now - lastBeat);
      lastBeat = now;

      Serial.print("BPM:");
      Serial.println(bpm);
    }
  }
}
