#include <Arduino.h>

// ===================================================================
// FILE TEST TOÀN DIỆN CHO ESP32-C3 SUPER MINI
// HỖ TRỢ TỰ ĐỘNG CẢ CÒI ACTIVE LẪN PASSIVE TRÊN MỌI CHÂN GPIO
// ===================================================================

// Danh sách tất cả các chân GPIO hàng bên trái có thể cắm còi:
const int TEST_PINS[] = {3, 4, 2, 1, 0};
const int NUM_PINS = sizeof(TEST_PINS) / sizeof(TEST_PINS[0]);

constexpr int LED_PIN = 8;        // LED xanh có sẵn trên bo C3
constexpr int BOOT_BTN_PIN = 9;   // Nút bấm BOOT trên bo C3

// Chế độ test:
// 0 = TẮT CÒI (Im lặng hoàn toàn)
// 1 = CÒI ACTIVE (Kích điện áp DC 3.3V, nhịp tít... tít...)
// 2 = CÒI PASSIVE (Phát xung tần số 2.400 Hz)
int testMode = 0;

int lastBtnReading = HIGH;
int stableBtnState = HIGH;
uint32_t lastDebounce = 0;

void setAllPins(int level) {
  for (int i = 0; i < NUM_PINS; i++) {
    digitalWrite(TEST_PINS[i], level);
  }
}

void setup() {
  // 1. Khởi tạo tất cả chân còi là OUTPUT và dập về mức 0V ngay lập tức
  for (int i = 0; i < NUM_PINS; i++) {
    pinMode(TEST_PINS[i], OUTPUT);
    digitalWrite(TEST_PINS[i], LOW);
  }

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH); // Tắt LED

  pinMode(BOOT_BTN_PIN, INPUT_PULLUP);

  Serial.begin(115200);
  delay(300);

  Serial.println("\n=======================================================");
  Serial.println("  ESP32-C3 SUPER MINI: CHUONG TRINH TEST TOAN DIEN COI");
  Serial.println("=======================================================");
  Serial.println("Bam nut BOOT de chuyen qua 3 che do:");
  Serial.println("  [LẦN 1] -> Chế độ 1: CÒI ACTIVE (Điện áp DC 3.3V)");
  Serial.println("  [LẦN 2] -> Chế độ 2: CÒI PASSIVE (Phát xung 2.400 Hz)");
  Serial.println("  [LẦN 3] -> Chế độ 0: TẮT HOÀN TOÀN (Im lặng)");
  Serial.println("-------------------------------------------------------");
  Serial.println("Xuat tin hieu dong thoi ra cac chan: GPIO 3, 4, 2, 1, 0");
  Serial.println("=======================================================\n");
  Serial.println(">>> [KHOI DONG] CHE DO 0: TAT COI (Im lang)");
}

void loop() {
  // 1. Đọc nút bấm BOOT (chống dội phím)
  int reading = digitalRead(BOOT_BTN_PIN);
  if (reading != lastBtnReading) {
    lastDebounce = millis();
  }

  if ((millis() - lastDebounce) > 50) {
    if (reading != stableBtnState) {
      stableBtnState = reading;
      if (stableBtnState == LOW) { // Nhấn nút BOOT
        testMode = (testMode + 1) % 3; // Chuyển vòng 0 -> 1 -> 2 -> 0

        if (testMode == 0) {
          setAllPins(LOW);
          digitalWrite(LED_PIN, HIGH);
          Serial.println("\n>>> [CHE DO 0] TẮT CÒI HOÀN TOÀN (LED Tắt)");
        } else if (testMode == 1) {
          Serial.println("\n>>> [CHE DO 1] THỬ CÒI ACTIVE (DC 3.3V) - Nhịp tít tít");
        } else if (testMode == 2) {
          Serial.println("\n>>> [CHE DO 2] THỬ CÒI PASSIVE (Xung 2.400 Hz) - Nhịp tít tít");
        }
      }
    }
  }
  lastBtnReading = reading;

  // 2. Thực thi theo chế độ hiện tại
  if (testMode == 0) {
    setAllPins(LOW);
    digitalWrite(LED_PIN, HIGH);
    delay(10);
  }
  else if (testMode == 1) {
    // Chế độ 1: Còi Active (cấp DC 3.3V)
    // Nhịp: Kêu 250ms, Nghỉ 250ms
    uint32_t phase = millis() % 500;
    if (phase < 250) {
      setAllPins(HIGH);
      digitalWrite(LED_PIN, LOW); // LED sáng
    } else {
      setAllPins(LOW);
      digitalWrite(LED_PIN, HIGH); // LED tắt
    }
    delay(5);
  }
  else if (testMode == 2) {
    // Chế độ 2: Còi Passive (phát xung 2.400 Hz)
    // Nhịp: Kêu 250ms, Nghỉ 250ms
    uint32_t phase = millis() % 500;
    if (phase < 250) {
      digitalWrite(LED_PIN, LOW);
      // Phát sóng vuông 2.400 Hz (chu kỳ 416 us: 208 us HIGH, 208 us LOW)
      setAllPins(HIGH);
      delayMicroseconds(208);
      setAllPins(LOW);
      delayMicroseconds(208);
    } else {
      setAllPins(LOW);
      digitalWrite(LED_PIN, HIGH);
      delay(5);
    }
  }
}
