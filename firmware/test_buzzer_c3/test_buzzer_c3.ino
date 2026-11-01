#include <Arduino.h>

// Chân còi thử nghiệm theo yêu cầu: GPIO 3
constexpr int BUZZER_PIN = 3;

// Đèn LED tích hợp trên bo ESP32-C3 Super Mini (GPIO 8: mức LOW là sáng, HIGH là tắt)
constexpr int LED_BOARD = 8;

// Nút bấm BOOT tích hợp trên bo ESP32-C3 Super Mini (GPIO 9)
constexpr int BUTTON_BOOT = 9;

void setup() {
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  pinMode(LED_BOARD, OUTPUT);
  digitalWrite(LED_BOARD, HIGH); // Tắt LED ban đầu

  pinMode(BUTTON_BOOT, INPUT_PULLUP);

  Serial.begin(115200);
  delay(1000);

  Serial.println("\n=======================================================");
  Serial.println("   KIEM TRA COI BUZZER - CHAN GPIO 3 (ESP32-C3)");
  Serial.println("=======================================================");
  Serial.println("- CUC DUONG (+) hoac chan tin hieu S cua coi: noi GPIO 3");
  Serial.println("- CUC AM (-) cua coi: noi GND");
  Serial.println("- Neu coi co 3 chan (VCC, GND, I/O):");
  Serial.println("    + VCC -> 3V3 hoac 5V");
  Serial.println("    + GND -> GND");
  Serial.println("    + I/O (hoac S) -> GPIO 3");
  Serial.println("- Code se test ca 2 che do: COI CHU DONG (DC HIGH) va COI THU DONG (Tan so tone)");
  Serial.println("=======================================================\n");
}

// 1. Kêu bằng xung tần số (dành cho còi thụ động - Passive buzzer)
void beepTone(int freq, int durationMs, int pauseMs = 150) {
  Serial.printf("[TONE THU DONG] GPIO 3 phat tan so %d Hz (%d ms)...\n", freq, durationMs);
  digitalWrite(LED_BOARD, LOW); // Sang LED
  tone(BUZZER_PIN, freq, durationMs);
  delay(durationMs);
  noTone(BUZZER_PIN);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_BOARD, HIGH); // Tat LED
  delay(pauseMs);
}

// 2. Kêu bằng mức điện áp DC HIGH (dành cho còi chủ động - Active buzzer)
void beepDirect(int durationMs, int pauseMs = 150) {
  Serial.printf("[DC CHU DONG] GPIO 3 xuat HIGH 3.3V (%d ms)...\n", durationMs);
  digitalWrite(LED_BOARD, LOW); // Sang LED
  digitalWrite(BUZZER_PIN, HIGH);
  delay(durationMs);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_BOARD, HIGH); // Tat LED
  delay(pauseMs);
}

void loop() {
  // Kiểm tra nút bấm BOOT (GPIO 9)
  if (digitalRead(BUTTON_BOOT) == LOW) {
    Serial.println(">>> NUT BOOT DUOC BAM: Phat am thanh khan cap!");
    for (int i = 0; i < 3; i++) {
      beepTone(2700, 150, 80);
      beepDirect(150, 80);
    }
    delay(500);
    return;
  }

  // --- PHAN 1: TEST COI THU DONG (Bang tone PWM 2000Hz - 3000Hz) ---
  Serial.println("\n--- [1] Test che do TONE (Neu la coi thu dong 3 chan hoac coi den se keu o day) ---");
  beepTone(2000, 200, 100);
  beepTone(2500, 200, 100);
  beepTone(3000, 300, 800);

  // --- PHAN 2: TEST COI CHU DONG (Bang xuat dien ap DC HIGH 3.3V) ---
  Serial.println("--- [2] Test che do DC HIGH (Neu la coi chu dong co mach tao dao dong se keu o day) ---");
  beepDirect(200, 100);
  beepDirect(200, 100);
  beepDirect(500, 1500);

  // Doc lenh tu Serial Monitor neu co
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '1' || c == 'b' || c == 'B') {
      Serial.println(">>> Lenh Serial: Phat coi ca 2 kieu");
      beepTone(2700, 500, 100);
      beepDirect(500, 100);
    }
  }
}
