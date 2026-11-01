#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp_now.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "qrcode.h"
#include "config.h"

// Thời gian chờ tối đa mỗi request HTTP (kết nối + đọc).
constexpr uint16_t HTTP_TIMEOUT_MS = 3000;
constexpr uint32_t ALARM_DURATION_MS = 25000;

// Trạng thái báo động
volatile bool alarmArmed = false;
volatile uint32_t alarmUntil = 0;
volatile uint32_t shortBeepUntil = 0; // Tiếng bíp phản hồi nút bấm tức thì (0ms trễ)
volatile bool wifiOnline = false;
volatile uint8_t espNowEvent = 0;

uint32_t lastPoll = 0;
uint32_t lastState = 0;
uint32_t lastWifiCheck = 0;
uint32_t lastDisplayUpdate = 0;
uint32_t pageSwitchTime = 0;

// ==========================================
// MÀN HÌNH OLED 0.96 inch (SSD1306 I2C 128x64)
// ==========================================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
bool oledReady = false;

// Đối tượng QR Code lưu sẵn trong bộ nhớ RAM
QRCode qrCodeObj;
uint8_t qrDataBuffer[64];
bool qrInitialized = false;

// Quản lý trang màn hình:
// 0 = Mã QR Cứu Hộ (Mặc định)
// 1 = Trạng thái kết nối Wi-Fi & Thiết bị gậy
// 2 = Danh bạ SĐT SOS người nhà
int displayPage = 0;
const int TOTAL_PAGES = 3;

// Cấu trúc gói tin nhận trực tiếp qua ESP-NOW
typedef struct {
  char cmd[16];
} DirectMsg;

void startAlarm(uint32_t durationMs) {
  alarmUntil = millis() + durationMs;
  alarmArmed = true;
}

void stopAlarm() {
  alarmArmed = false;
}

bool alarmActive(uint32_t now) {
  return alarmArmed && (int32_t)(alarmUntil - now) > 0;
}

// Kích hoạt tiếng bíp phản hồi nút bấm NGAY LẬP TỨC (chạy trong buzzerTask, 0ms trễ)
void triggerInstantBeep(uint32_t durationMs = 70) {
  shortBeepUntil = millis() + durationMs;
}

// Điều khiển còi trong buzzerTask
void setBuzzer(bool on) {
  static bool current = false;
  if (current == on) return;
  current = on;
#if PASSIVE_BUZZER
  if (on) {
    for (int i = 0; i < NUM_BUZZER_PINS; i++) tone(BUZZER_PINS[i], 2700);
  } else {
    for (int i = 0; i < NUM_BUZZER_PINS; i++) { noTone(BUZZER_PINS[i]); digitalWrite(BUZZER_PINS[i], LOW); }
  }
#else
  for (int i = 0; i < NUM_BUZZER_PINS; i++) {
    digitalWrite(BUZZER_PINS[i], on ? HIGH : LOW);
  }
#endif
}

// Cờ báo nút bấm chuyển trang từ buzzerTask sang loop()
volatile bool btnPageSwitchReq = false;

// Task riêng chạy mỗi 10 ms: xử lý nút bấm, phản hồi tiếng bíp tức thì, còi báo động
void buzzerTask(void*) {
  uint32_t lastBlink = 0;
  uint32_t lastPress = 0;
  bool ledState = false;

  for (;;) {
    uint32_t now = millis();

    // 1. Kiểm tra bấm nút NGAY LẬP TỨC (Nút rời ngoài GPIO 10 HOẶC Nút BOOT GPIO 9)
    bool btnPressed = (digitalRead(STOP_BUTTON_PIN) == LOW || digitalRead(PIN_BUTTON_EXT) == LOW);
    if (btnPressed && (now - lastPress >= 250)) {
      lastPress = now;

      // Nếu còi đang kêu -> Tắt còi tại chỗ ngay lập tức!
      if (alarmActive(now)) {
        stopAlarm();
        Serial.println("[NUT BAM] Da an nut tat coi tai cho!");
      }
      // Nếu còi không kêu -> KÊU BÍP PHẢN HỒI NGAY & BÁO ĐỔI TRANG MÀN HÌNH TỨC THÌ
      else {
        triggerInstantBeep(70);   // Kêu bíp ngay lập tức (không cần đợi mạng)
        btnPageSwitchReq = true;  // Báo loop() đổi trang màn hình
      }
    }

    // 2. Ưu tiên âm thanh: Tiếng bíp phản hồi nút bấm (0ms trễ)
    if (now < shortBeepUntil) {
      setBuzzer(true);
    }
    // 3. Âm thanh báo động SOS / Tìm gậy (nhịp đôi)
    else if (alarmActive(now)) {
      uint32_t cycle = now % 1000;
      bool beep = (cycle < 150) || (cycle >= 230 && cycle < 380);
      setBuzzer(beep);
      digitalWrite(LED_BOARD, beep ? LOW : HIGH);
    }
    // 4. Còi tắt, quản lý LED trạng thái bo
    else {
      alarmArmed = false;
      setBuzzer(false);
      if (wifiOnline) {
        digitalWrite(LED_BOARD, HIGH); // Tắt LED: mạng đã sẵn sàng
      } else if (now - lastBlink >= 300) {
        lastBlink = now;
        ledState = !ledState;
        digitalWrite(LED_BOARD, ledState ? LOW : HIGH);
      }
    }

    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

// ==========================================
// CÁC HÀM HIỂN THỊ MÀN HÌNH OLED
// ==========================================

// TRANG 0: MÃ QR CỨU HỘ TO, NÉT CĂNG (100% TRONG DẢI XANH, KHÔNG DÍNH VÀNG)
void renderQRCodePage() {
  display.clearDisplay();

  // 1. DẢI MÀU VÀNG PHÍA TRÊN (Y = 0 đến 15)
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(10, 4);
  display.print(F("QUET MA CUU HO SOS"));

  // 2. DẢI MÀU XANH PHÍA DƯỚI (Y = 16 đến 63)
  int scale = 2;
  int qrWidth = qrCodeObj.size * scale;      // 42 px
  int startX = (SCREEN_WIDTH - qrWidth) / 2; // 43 (Căn giữa ngang)
  int startY = 19;                           // Căn giữa dọc dải màu xanh
  int border = 2;

  // Viền trắng Quiet Zone (46x46 px, từ Y=17 đến 62 -> 100% trong dải xanh!)
  display.fillRect(startX - border, startY - border, qrWidth + border * 2, qrWidth + border * 2, SSD1306_WHITE);

  // Vẽ các module đen của mã QR
  if (qrInitialized) {
    for (uint8_t y = 0; y < qrCodeObj.size; y++) {
      for (uint8_t x = 0; x < qrCodeObj.size; x++) {
        if (qrcode_getModule(&qrCodeObj, x, y)) {
          display.fillRect(startX + x * scale, startY + y * scale, scale, scale, SSD1306_BLACK);
        }
      }
    }
  }

  // Điều hướng trực quan ở 2 bên mã QR
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(6, 23);  display.print(F("GOI"));
  display.setCursor(6, 35);  display.print(F("SOS"));
  display.setCursor(6, 47);  display.print(F(">>>"));

  display.setCursor(94, 23); display.print(F("SDT"));
  display.setCursor(94, 35); display.print(F("NHA"));
  display.setCursor(94, 47); display.print(F("<<<"));

  display.display();
}

// TRANG 1: TRẠNG THÁI KẾT NỐI WI-FI & HỆ THỐNG GẬY
void renderStatusPage() {
  display.clearDisplay();

  // Dải màu vàng phía trên
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(8, 4);
  display.print(F("TRANG THAI KET NOI"));

  // Dải màu xanh phía dưới
  display.setCursor(2, 18);
  display.print(F("Wi-Fi : "));
  if (wifiOnline) {
    display.print(WIFI_SSID);
  } else {
    display.print(F("Dang ket noi..."));
  }

  display.setCursor(2, 29);
  display.print(F("IP C3 : "));
  if (wifiOnline) {
    display.print(WiFi.localIP().toString());
  } else {
    display.print(F("--.--.--.--"));
  }

  display.setCursor(2, 40);
  display.print(F("Server: iot.chongziapp"));

  display.setCursor(2, 52);
  display.print(F("Coi(5): "));
  display.print(alarmActive(millis()) ? F("[DANG KEU]") : F("SAN SANG"));

  display.display();
}

// TRANG 2: DANH BẠ SỐ ĐIỆN THOẠI NGƯỜI NHÀ (SOS TOÀN MÀN HÌNH)
void renderContactPage() {
  display.clearDisplay();

  // Dải màu vàng phía trên
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 4);
  display.print(F("SO GOI NGUOI NHA (SOS)"));

  // Dải màu xanh phía dưới
  display.setCursor(2, 18);
  display.print(F("Nguoi dung: "));
  display.print(EMERGENCY_NAME);

  display.setCursor(2, 30);
  display.print(F("SDT chinh : "));
  display.print(EMERGENCY_PHONE1);

  display.setCursor(2, 42);
  display.print(F("SDT phu   : "));
  display.print(EMERGENCY_PHONE2);

  display.drawLine(2, 53, 126, 53, SSD1306_WHITE);
  display.setCursor(2, 55);
  display.print(F("* Xin nho goi giup!"));

  display.display();
}

// MÀN HÌNH KHẨN CẤP: HIỂN THỊ KHI CÒI BÁO ĐỘNG ĐANG KÊU
void renderAlarmScreen() {
  display.clearDisplay();

  // Dải vàng nhấp nháy
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 4);
  display.print(F("!!! CANH BAO SOS !!!"));

  // Dải xanh
  display.setCursor(14, 20);
  display.setTextSize(1);
  display.print(F("[ COI DANG KEU ]"));

  display.setCursor(6, 34);
  display.print(F("BAM NUT DE TAT COI"));

  display.setCursor(6, 48);
  display.print(F("HOAC GOI NGUOI NHA:"));
  display.setCursor(20, 56);
  display.print(EMERGENCY_PHONE1);

  display.display();
}

void updateOledDisplay() {
  if (!oledReady) return;

  // Nếu đang có báo động -> Ưu tiên hiện màn hình báo động
  if (alarmActive(millis())) {
    renderAlarmScreen();
    return;
  }

  // Hiển thị theo trang người dùng chọn
  if (displayPage == 0) {
    renderQRCodePage();
  } else if (displayPage == 1) {
    renderStatusPage();
  } else {
    renderContactPage();
  }
}

// ==========================================
// CÁC HÀM GIAO TIẾP SERVER & ESP-NOW
// ==========================================
bool beginApi(HTTPClient& http, WiFiClient& client, const char* path) {
  if (!http.begin(client, String(API_BASE) + path)) return false;
  http.setConnectTimeout(HTTP_TIMEOUT_MS);
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.addHeader("Authorization", String("Bearer ") + DEVICE_TOKEN);
  return true;
}

void ackCommand(const char* cid) {
  if (WiFi.status() != WL_CONNECTED || !*cid) return;
  WiFiClient client;
  HTTPClient http;
  String path = String("/api/v1/commands/") + cid + "/ack";
  if (beginApi(http, client, path.c_str())) {
    http.addHeader("Content-Type", "application/json");
    http.POST("{\"result\":\"done\"}");
    http.end();
  }
}

void pollCommands() {
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClient client;
  HTTPClient http;

  if (beginApi(http, client, "/api/v1/commands")) {
    int code = http.GET();
    if (code == 200) {
      String payload = http.getString();
      JsonDocument doc;
      DeserializationError err = deserializeJson(doc, payload);
      if (!err) {
        JsonArray commands = doc["commands"].as<JsonArray>();
        for (JsonObject cmd : commands) {
          const char* kind = cmd["kind"] | "";
          const char* cid = cmd["id"] | "";
          if (strcmp(kind, "find") == 0 || strcmp(kind, "sos") == 0) {
            Serial.printf(">>> [LENH] Nhan lenh %s tu Server! Bat coi 25 giay...\n", kind);
            startAlarm(ALARM_DURATION_MS);
            ackCommand(cid);
          } else if (strcmp(kind, "stop") == 0) {
            Serial.println(">>> [LENH] Nhan lenh STOP tu Server! Tat coi ngay lap tuc!");
            stopAlarm();
            ackCommand(cid);
          }
        }
      }
    }
    http.end();
  }
}

void sendState() {
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClient client;
  HTTPClient http;

  if (beginApi(http, client, "/api/v1/state")) {
    http.addHeader("Content-Type", "application/json");

    JsonDocument doc;
    doc["uptime_s"] = millis() / 1000;
    doc["drop_alarm"] = false;
    doc["sos_alarm"] = alarmActive(millis());
    doc["sensor_valid"] = true;
    doc["distance_cm"] = nullptr;

    String body;
    serializeJson(doc, body);
    http.POST(body);
    http.end();
  }
}

#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onDataRecv(const esp_now_recv_info_t*, const uint8_t* data, int len) {
#else
void onDataRecv(const uint8_t*, const uint8_t* data, int len) {
#endif
  if (len <= 0) return;
  char cmd[sizeof(DirectMsg::cmd) + 1] = {0};
  memcpy(cmd, data, min(len, (int)sizeof(DirectMsg::cmd)));
  if (strcmp(cmd, "FIND") == 0 || strcmp(cmd, "SOS") == 0) {
    startAlarm(ALARM_DURATION_MS);
    espNowEvent = 1;
  } else if (strcmp(cmd, "STOP") == 0) {
    stopAlarm();
    espNowEvent = 2;
  }
}

bool espNowStarted = false;
void startEspNow() {
  if (!espNowStarted && esp_now_init() == ESP_OK) {
    esp_now_register_recv_cb(onDataRecv);
    espNowStarted = true;
    Serial.println("[ESP-NOW] San sang nhan lenh truc tiep!");
  }
}

// Task riêng cho Wi-Fi và giao tiếp mạng Server: chạy ngầm hoàn toàn,
// không làm chặn hay lag nút bấm và màn hình OLED!
void networkTask(void*) {
  for (;;) {
    uint32_t now = millis();

    // 1. Quản lý trạng thái kết nối Wi-Fi
    if (WiFi.status() == WL_CONNECTED) {
      if (!wifiOnline) {
        wifiOnline = true;
        Serial.printf("[Wi-Fi] KET NOI THANH CONG! IP: %s\n", WiFi.localIP().toString().c_str());
        startEspNow();
      }
    } else {
      if (wifiOnline) {
        wifiOnline = false;
        lastWifiCheck = now;
      }
      if (now - lastWifiCheck >= 30000) {
        lastWifiCheck = now;
        Serial.println(F("[Wi-Fi] Thu ket noi lai..."));
        WiFi.reconnect();
      }
    }

    // 2. Định kỳ 1 giây hỏi lệnh từ server (chạy ngầm)
    if (wifiOnline && (now - lastPoll >= 1000)) {
      lastPoll = now;
      pollCommands();
    }

    // 3. Định kỳ 3 giây gửi trạng thái lên server (chạy ngầm)
    if (wifiOnline && (now - lastState >= 3000)) {
      lastState = now;
      sendState();
    }

    vTaskDelay(pdMS_TO_TICKS(50));
  }
}

// ==========================================
// SETUP & LOOP
// ==========================================
void setup() {
  // 1. Cấu hình chân còi và nút bấm
  for (int i = 0; i < NUM_BUZZER_PINS; i++) {
    pinMode(BUZZER_PINS[i], OUTPUT);
    digitalWrite(BUZZER_PINS[i], LOW);
  }
  pinMode(LED_BOARD, OUTPUT);
  digitalWrite(LED_BOARD, HIGH); // Tắt LED bo

  pinMode(STOP_BUTTON_PIN, INPUT_PULLUP);
  pinMode(PIN_BUTTON_EXT, INPUT_PULLUP);

  Serial.begin(115200);
  delay(300);

  Serial.println("\n=======================================================");
  Serial.println("  ESP32-C3 SUPER MINI: BO PHAT COI CANH BAO + OLED QR");
  Serial.println("=======================================================");

  // 2. Khởi động I2C cho Màn hình OLED trên GPIO 6 & 7
  Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);

  // 3. Khởi tạo mã QR cứu hộ vào bộ nhớ RAM
  int8_t qrStatus = qrcode_initText(&qrCodeObj, qrDataBuffer, 1, ECC_LOW, QR_LINK);
  if (qrStatus == 0) {
    qrInitialized = true;
    Serial.printf("[OK] Ma QR tao thanh cong! Link: %s\n", QR_LINK);
  } else {
    qrInitialized = false;
    Serial.printf("[LOI] Tao ma QR that bai (ma loi: %d)\n", qrStatus);
  }

  // 4. Khởi động OLED (0x3C)
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("[LOI] Khong tim thay OLED! Kiem tra SDA(6), SCL(7)."));
    oledReady = false;
  } else {
    Serial.println(F("[OK] Màn hình OLED khởi động thành công!"));
    oledReady = true;
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(16, 4);
    display.println(F("THIET BI DONG HANH"));
    display.setCursor(20, 26);
    display.println(F("BO COI & OLED SOS"));
    display.setCursor(18, 44);
    display.println(F("Dang khoi tao..."));
    display.display();
    delay(500);
  }

  // Mặc định hiển thị Màn hình QR Code cứu hộ
  displayPage = 0;
  updateOledDisplay();

  // Khởi chạy buzzerTask (ưu tiên 3) chuyên còi & nút bấm tức thì (0ms lag)
  xTaskCreate(buzzerTask, "buzzer", 3072, nullptr, 3, nullptr);

  // 5. Cấu hình Wi-Fi & ESP-NOW
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  startEspNow();

  WiFi.onEvent([](WiFiEvent_t event, WiFiEventInfo_t info) {
    switch (event) {
      case ARDUINO_EVENT_WIFI_STA_GOT_IP:
        Serial.printf("[WiFi-EVT] DA NHAN IP: %s\n", IPAddress(info.got_ip.ip_info.ip.addr).toString().c_str());
        break;
      case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
        Serial.printf("[WiFi-EVT] Mat ket noi (ly do: %d)\n", info.wifi_sta_disconnected.reason);
        break;
      default:
        break;
    }
  });

  Serial.printf("[WiFi] Dang ket noi toi '%s'...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Khởi chạy networkTask (ưu tiên 1) chuyên HTTP & kết nối mạng ngầm
  xTaskCreate(networkTask, "network", 4096, nullptr, 1, nullptr);

  triggerInstantBeep(80);
}

void loop() {
  uint32_t now = millis();

  // 1. Xử lý yêu cầu đổi trang màn hình từ nút bấm NGAY TỨC THÌ (Độ trễ < 15ms)
  if (btnPageSwitchReq) {
    btnPageSwitchReq = false;
    displayPage = (displayPage + 1) % TOTAL_PAGES;
    pageSwitchTime = now;
    updateOledDisplay(); // Chuyển trang màn hình ngay lập tức!
  }

  // 2. Tự động quay về Màn hình QR Code Cứu Hộ sau 15 giây không bấm nút
  if (displayPage != 0 && (now - pageSwitchTime >= 15000)) {
    displayPage = 0;
    updateOledDisplay();
    Serial.println(F("[OLED] Tu dong quay ve Man hinh QR Code!"));
  }

  // 3. Cập nhật màn hình OLED định kỳ mỗi 500ms
  if (oledReady && (now - lastDisplayUpdate >= 500)) {
    lastDisplayUpdate = now;
    updateOledDisplay();
  }

  // 4. Cập nhật OLED khi có sự kiện ESP-NOW khẩn cấp
  uint8_t evt = espNowEvent;
  if (evt) {
    espNowEvent = 0;
    Serial.println(evt == 1 ? ">>> [ESP-NOW] Kich hoat coi!" : ">>> [ESP-NOW] Tat coi!");
    updateOledDisplay();
  }

  delay(10);
}
