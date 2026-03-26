#include <Arduino.h>
#line 1 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
int ecgPin = 34;
int LOplus = 32;
int LOminus = 33;

#line 5 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void setup();
#line 11 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void loop();
#line 5 "C:\\Users\\JEYAKANISH\\Documents\\Arduino\\ECG_Test\\ECG_Test.ino"
void setup() {
  Serial.begin(115200);
  pinMode(LOplus, INPUT);
  pinMode(LOminus, INPUT);
}

void loop() {

  if(digitalRead(LOplus)==1 || digitalRead(LOminus)==1){
    Serial.println(0);
  }
  else{
    int ecgValue = analogRead(ecgPin);

    static float filtered = 0;
    filtered = 0.95 * filtered + 0.05 * ecgValue;

    Serial.println(filtered);
  }

  delay(5);
}
