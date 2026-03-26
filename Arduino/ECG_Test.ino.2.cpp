#include <Arduino.h>
#line 1 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
#include <WiFi.h>
#define ECG_PIN 34

const int SAMPLE_RATE = 250;
const int SAMPLE_PERIOD = 1000000 / SAMPLE_RATE;

unsigned long lastSample = 0;

#line 9 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void setup();
#line 16 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void loop();
#line 9 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void setup() {
  Serial.begin(115200);

  WiFi.mode(WIFI_OFF);
  btStop();
}

void loop() {

  if (micros() - lastSample >= SAMPLE_PERIOD) {
    lastSample = micros();

    int raw = analogRead(ECG_PIN);
    Serial.println(raw);
  }
}
