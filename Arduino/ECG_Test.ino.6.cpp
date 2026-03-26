#include <Arduino.h>
#line 1 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
int ecgPin = 34;

#line 3 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void setup();
#line 7 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void loop();
#line 3 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void setup() {
  Serial.begin(115200);
}

void loop() {
  int ecgValue = analogRead(ecgPin);
  Serial.println(ecgValue);
  delay(5);
}
