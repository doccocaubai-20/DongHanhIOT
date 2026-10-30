#include <Arduino.h>

constexpr int BUZZER = 13;
constexpr int LED_BOARD = 2; // LED xanh tren bo ESP32 DevKit

void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(BUZZER, OUTPUT);
  pinMode(LED_BOARD, OUTPUT);
  digitalWrite(BUZZER, LOW);
  digitalWrite(LED_BOARD, LOW);

  Serial.println("\n=======================================================");
  Serial.println("  CHUONG TRINH CHAN DOAN COI CHI TIET (GPIO 13)");
  Serial.println("=======================================================");
}

void loop() {
  Serial.println("\n--- BAT DAU CHU KY KIEM TRA COI TREN CHAN D13 ---");

  // TEST 1: Nguon DC 3.3V (Cho coi Active)
  Serial.println("1. [Active Buzzer] Cap dien DC lien tuc 1 giay vao D13...");
  digitalWrite(LED_BOARD, HIGH);
  digitalWrite(BUZZER, HIGH);
  delay(1000);
  digitalWrite(BUZZER, LOW);
  digitalWrite(LED_BOARD, LOW);
  delay(600);

  // TEST 2: Ham tone() Arduino 2.000 Hz (Cho coi Passive)
  Serial.println("2. [Passive Buzzer - tone()] Phat am thanh 2.000 Hz 1 giay...");
  digitalWrite(LED_BOARD, HIGH);
  tone(BUZZER, 2000);
  delay(1000);
  noTone(BUZZER);
  digitalWrite(LED_BOARD, LOW);
  delay(600);

  // TEST 3: Bam xung thu cong 2.400 Hz (Khong phu thuoc thu vien)
  Serial.println("3. [Passive Buzzer - Xung 2.400 Hz thu cong] 1 giay...");
  digitalWrite(LED_BOARD, HIGH);
  uint32_t tEnd = millis() + 1000;
  while (millis() < tEnd) {
    digitalWrite(BUZZER, HIGH);
    delayMicroseconds(208);
    digitalWrite(BUZZER, LOW);
    delayMicroseconds(208);
  }
  digitalWrite(LED_BOARD, LOW);
  delay(600);

  // TEST 4: Bam xung thu cong 1.000 Hz (Am tram, rung manh hon)
  Serial.println("4. [Passive Buzzer - Xung 1.000 Hz am tram] 1 giay...");
  digitalWrite(LED_BOARD, HIGH);
  tEnd = millis() + 1000;
  while (millis() < tEnd) {
    digitalWrite(BUZZER, HIGH);
    delayMicroseconds(500);
    digitalWrite(BUZZER, LOW);
    delayMicroseconds(500);
  }
  digitalWrite(LED_BOARD, LOW);
  delay(1500);
}
