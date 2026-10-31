#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp_now.h>
#include "config.h"

// Thời gian chờ tối đa mỗi request HTTP (kết nối + đọc). Server qua Cloudflare có lúc mất >1 giây,
// cộng TX 8.5dBm nên cần dư; còi chạy ở task riêng nên chờ lâu không làm còi bị kẹt.
constexpr uint16_t HTTP_TIMEOUT_MS = 4000;
constexpr uint32_t ALARM_DURATION_MS = 25000;

// Trạng thái báo động: chỉ ghi qua startAlarm()/stopAlarm() (an toàn từ mọi task),
// chỉ buzzerTask điều khiển chân còi và LED nên HTTP chậm không làm còi bị kẹt.
volatile bool alarmArmed = false;
volatile uint32_t alarmUntil = 0;
volatile bool wifiOnline = false;
// Lệnh ESP-NOW vừa nhận (0: không có, 1: bật còi, 2: tắt còi), in log ở loop() thay vì trong callback Wi-Fi
volatile uint8_t espNowEvent = 0;

uint32_t lastPoll = 0;
uint32_t lastState = 0;
uint32_t lastWifiCheck = 0;

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

// So sánh có dấu để không lỗi khi millis() tràn số (sau ~49 ngày)
bool alarmActive(uint32_t now) {
  return alarmArmed && (int32_t)(alarmUntil - now) > 0;
}

// Chỉ gọi từ buzzerTask. pinMode đã đặt một lần trong setup().
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

// Task riêng chạy mỗi 10 ms: nhịp còi, nút BOOT tắt còi, LED trạng thái
void buzzerTask(void*) {
  uint32_t lastBlink = 0;
  uint32_t lastPress = 0;
  bool ledState = false;
  for (;;) {
    uint32_t now = millis();

    // Nút BOOT (GPIO9): tắt còi tại chỗ, chống dội phím 300 ms mà không chặn task
    if (digitalRead(STOP_BUTTON_PIN) == LOW && now - lastPress >= 300) {
      lastPress = now;
      if (alarmActive(now)) {
        stopAlarm();
        Serial.println("[NUT BAM BOOT] Da an nut tat coi tai cho!");
      }
    }

    if (alarmActive(now)) {
      // Nhịp đôi: Kêu 0-150ms, Nghỉ 150-230ms, Kêu 230-380ms, Nghỉ 380-1000ms
      uint32_t cycle = now % 1000;
      bool beep = (cycle < 150) || (cycle >= 230 && cycle < 380);
      setBuzzer(beep);
      digitalWrite(LED_BOARD, beep ? LOW : HIGH); // LED nháy theo còi
    } else {
      alarmArmed = false;
      setBuzzer(false);
      if (wifiOnline) {
        digitalWrite(LED_BOARD, HIGH); // Tắt LED: mạng đã sẵn sàng
      } else if (now - lastBlink >= 300) {
        // Đang mất kết nối: nhấp nháy LED mỗi 300ms
        lastBlink = now;
        ledState = !ledState;
        digitalWrite(LED_BOARD, ledState ? LOW : HIGH);
      }
    }

    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

bool beginApi(HTTPClient& http, WiFiClient& client, const char* path) {
  if (!http.begin(client, String(API_BASE) + path)) return false;
  http.setConnectTimeout(HTTP_TIMEOUT_MS);
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.addHeader("Authorization", String("Bearer ") + DEVICE_TOKEN);
  return true;
}

// Hàm xác nhận với server rằng đã nhận lệnh (ACK)
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

// Hàm kiểm tra lệnh từ server (/api/v1/commands)
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
    } else if (code < 0) {
      Serial.printf("[HTTP] Hoi lenh loi: %s\n", http.errorToString(code).c_str());
    }
    http.end();
  }
}

// Hàm gửi trạng thái lên server (/api/v1/state)
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

// Callback khi nhận gói tin ESP-NOW trực tiếp từ bo ngực. Chạy trong task Wi-Fi:
// chỉ đặt trạng thái, không in log hay điều khiển chân ở đây.
#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onDataRecv(const esp_now_recv_info_t*, const uint8_t* data, int len) {
#else
void onDataRecv(const uint8_t*, const uint8_t* data, int len) {
#endif
  if (len <= 0) return;
  // Chép có giới hạn và luôn kết thúc bằng '\0' để strcmp không đọc tràn
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

void setup() {
  // 1. ÉP TẮT CÒI TRÊN TẤT CẢ CÁC CHÂN NGAY LẬP TỨC
  for (int i = 0; i < NUM_BUZZER_PINS; i++) {
    pinMode(BUZZER_PINS[i], OUTPUT);
    digitalWrite(BUZZER_PINS[i], LOW);
  }
  pinMode(LED_BOARD, OUTPUT);
  digitalWrite(LED_BOARD, HIGH); // Tắt LED
  pinMode(STOP_BUTTON_PIN, INPUT_PULLUP);

  Serial.begin(115200);
  delay(300);

  Serial.println("\n=======================================================");
  Serial.println("  ESP32-C3 SUPER MINI: BO PHAT COI CANH BAO (GAY)");
  Serial.println("=======================================================");
  Serial.print("Chân còi: GPIO");
  for (int i = 0; i < NUM_BUZZER_PINS; i++) Serial.printf(" %d", BUZZER_PINS[i]);
  Serial.printf(" | Chân nút tắt còi: GPIO %d\n", STOP_BUTTON_PIN);
#if !ARDUINO_USB_CDC_ON_BOOT
  // GPIO20/21 là RX/TX của UART0: khi tắt "USB CDC On Boot", Serial chạy trên UART0 nên dùng 2 chân này làm còi sẽ làm hỏng log
  for (int i = 0; i < NUM_BUZZER_PINS; i++) {
    if (BUZZER_PINS[i] == 20 || BUZZER_PINS[i] == 21) {
      Serial.printf("[CANH BAO] GPIO%d trung chan UART0 cua Serial! Bat 'USB CDC On Boot' hoac bo chan nay khoi BUZZER_PINS.\n", BUZZER_PINS[i]);
    }
  }
#endif

  // Chớp đèn LED 2 lần báo hiệu bo đã bật nguồn (giữ im lặng còi lúc khởi động)
  for (int i = 0; i < 2; i++) {
    digitalWrite(LED_BOARD, LOW);
    delay(80);
    digitalWrite(LED_BOARD, HIGH);
    delay(80);
  }

  // Còi chạy độc lập với Wi-Fi/HTTP, ưu tiên cao hơn loop() (ưu tiên 1)
  xTaskCreate(buzzerTask, "buzzer", 3072, nullptr, 3, nullptr);

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  // Hạ công suất phát sóng xuống 8.5dBm để chống sụt áp nguồn và chống méo sóng RF gây lỗi AUTH_EXPIRE (Reason 2)
  WiFi.setTxPower(WIFI_POWER_8_5dBm);

  // Kích hoạt ESP-NOW ngay lập tức để nhận lệnh trực tiếp (hoạt động 100% offline không cần Wi-Fi)
  startEspNow();

  WiFi.onEvent([](WiFiEvent_t event, WiFiEventInfo_t info) {
    switch (event) {
      case ARDUINO_EVENT_WIFI_STA_START:
        Serial.println("[WiFi-EVT] STA khoi dong");
        break;
      case ARDUINO_EVENT_WIFI_STA_CONNECTED:
        Serial.println("[WiFi-EVT] Da ket noi toi AP!");
        break;
      case ARDUINO_EVENT_WIFI_STA_GOT_IP:
        Serial.printf("[WiFi-EVT] DA NHAN IP THANH CONG: %s\n", IPAddress(info.got_ip.ip_info.ip.addr).toString().c_str());
        break;
      case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
        Serial.printf("[WiFi-EVT] Mat ket noi! Ly do: %d | BSSID: %02X:%02X:%02X:%02X:%02X:%02X\n",
          info.wifi_sta_disconnected.reason,
          info.wifi_sta_disconnected.bssid[0], info.wifi_sta_disconnected.bssid[1],
          info.wifi_sta_disconnected.bssid[2], info.wifi_sta_disconnected.bssid[3],
          info.wifi_sta_disconnected.bssid[4], info.wifi_sta_disconnected.bssid[5]);
        break;
      default:
        break;
    }
  });

  Serial.println("[WiFi] Dang quet cac mang xung quanh...");
  int n = WiFi.scanNetworks(false, true);
  Serial.printf("[WiFi] Tim thay %d AP:\n", n);

  int bestRssi = -100;
  int bestChannel = 0;

  for (int i = 0; i < n; ++i) {
    if (WiFi.SSID(i) == WIFI_SSID) {
      Serial.printf("  -> TIM THAY AP '%s' | BSSID: %s | RSSI: %d dBm | Ch: %d\n",
        WiFi.SSID(i).c_str(), WiFi.BSSIDstr(i).c_str(), (int)WiFi.RSSI(i), (int)WiFi.channel(i));
      if (WiFi.RSSI(i) > bestRssi) {
        bestRssi = WiFi.RSSI(i);
        bestChannel = WiFi.channel(i);
      }
    }
  }
  WiFi.scanDelete();

  // Khóa đúng kênh của AP: kết nối nhanh hơn, và ESP-NOW nghe cùng kênh với bo ngực (bo ngực phát trên kênh AP) ngay cả khi chưa có IP
  Serial.printf("\n[WiFi] Bat dau ket noi toi '%s' (TX=8.5dBm, kenh %d)...\n", WIFI_SSID, bestChannel);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD, bestChannel);
}

void loop() {
  uint32_t now = millis();

  // 1. Log lệnh ESP-NOW vừa nhận (callback không được in log)
  uint8_t evt = espNowEvent;
  if (evt) {
    espNowEvent = 0;
    Serial.println(evt == 1 ? ">>> [ESP-NOW] Kich hoat coi ngay lap tuc!" : ">>> [ESP-NOW] Nhan lenh STOP truc tiep! Tat coi ngay!");
  }

  // 2. Quản lý trạng thái kết nối Wi-Fi (LED do buzzerTask xử lý)
  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiOnline) {
      wifiOnline = true;
      Serial.printf("[Wi-Fi] DA KET NOI THANH CONG! IP C3: %s | Kenh: %d | Server: %s\n",
        WiFi.localIP().toString().c_str(), (int)WiFi.channel(), API_BASE);
      startEspNow();
    }
  } else {
    if (wifiOnline) {
      wifiOnline = false;
      lastWifiCheck = now; // Cho tự kết nối lại trước, không cắt ngang ngay khi vừa rớt
    }
    // Chỉ ép kết nối lại nếu vẫn mất mạng sau 30 giây
    if (now - lastWifiCheck >= 30000) {
      lastWifiCheck = now;
      Serial.printf("[Wi-Fi] Thu ket noi lai (status=%d)...\n", WiFi.status());
      WiFi.reconnect();
    }
  }

  // 3. Định kỳ 1 giây hỏi lệnh từ server
  if (now - lastPoll >= 1000) {
    lastPoll = now;
    pollCommands();
  }

  // 4. Định kỳ 3 giây gửi trạng thái lên server
  if (now - lastState >= 3000) {
    lastState = now;
    sendState();
  }

  delay(10);
}
