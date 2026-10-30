#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "config.h"

// Thời gian còi sẽ kêu đến thời điểm nào (ms)
uint32_t buzzerUntil = 0;
uint32_t lastPoll = 0;
uint32_t lastState = 0;
uint32_t lastWifiCheck = 0;
uint32_t lastBlink = 0;
bool ledState = false;

// Cấu trúc gói tin nhận trực tiếp qua ESP-NOW
typedef struct {
  char cmd[16];
} DirectMsg;

// Trạng thái còi hiện tại: -1: chưa khởi tạo, 0: tắt, 1: bật
static int currentBuzzerState = -1;

void setBuzzer(bool on) {
  int target = on ? 1 : 0;
  if (currentBuzzerState == target) return;
  currentBuzzerState = target;

  if (on) {
    for (int i = 0; i < NUM_BUZZER_PINS; i++) {
      pinMode(BUZZER_PINS[i], OUTPUT);
      digitalWrite(BUZZER_PINS[i], HIGH); // Xuất DC 3.3V (Kêu to)
    }
    digitalWrite(LED_BOARD, LOW); // Bật LED báo
  } else {
    for (int i = 0; i < NUM_BUZZER_PINS; i++) {
      pinMode(BUZZER_PINS[i], OUTPUT);
      digitalWrite(BUZZER_PINS[i], LOW);  // Dập 0V (Tắt hoàn toàn)
    }
    digitalWrite(LED_BOARD, HIGH); // Tắt LED báo
  }
}

// Hàm xác nhận với server rằng đã nhận lệnh (ACK)
void ackCommand(const char* cid) {
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClient client;
  HTTPClient http;
  String url = String(API_BASE) + "/api/v1/commands/" + cid + "/ack";
  if (http.begin(client, url)) {
    http.addHeader("Authorization", String("Bearer ") + DEVICE_TOKEN);
    http.addHeader("Content-Type", "application/json");
    http.POST("{\"status\":\"done\"}");
    http.end();
  }
}

// Hàm kiểm tra lệnh từ server (/api/v1/commands)
void pollCommands() {
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClient client;
  HTTPClient http;
  String url = String(API_BASE) + "/api/v1/commands";
  
  if (http.begin(client, url)) {
    http.setTimeout(1200);
    http.addHeader("Authorization", String("Bearer ") + DEVICE_TOKEN);
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
            buzzerUntil = millis() + 25000; // Kêu còi trong 25 giây
            ackCommand(cid);
          } else if (strcmp(kind, "stop") == 0) {
            Serial.println(">>> [LENH] Nhan lenh STOP tu Server! Tat coi ngay lap tuc!");
            buzzerUntil = 0;
            setBuzzer(false);
            ackCommand(cid);
          }
        }
      }
    }
    http.end();
  }
}

// Hàm gửi trạng thái lên server (/api/v1/state)
void sendState() {
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClient client;
  HTTPClient http;
  String url = String(API_BASE) + "/api/v1/state";
  
  if (http.begin(client, url)) {
    http.setTimeout(1200);
    http.addHeader("Authorization", String("Bearer ") + DEVICE_TOKEN);
    http.addHeader("Content-Type", "application/json");
    
    JsonDocument doc;
    doc["uptime_s"] = millis() / 1000;
    doc["drop_alarm"] = false;
    doc["sos_alarm"] = (buzzerUntil > millis());
    doc["sensor_valid"] = true;
    doc["distance_cm"] = nullptr;
    
    String body;
    serializeJson(doc, body);
    http.POST(body);
    http.end();
  }
}

// Callback khi nhận gói tin ESP-NOW trực tiếp từ bo ngực
void onDataRecv(const uint8_t *mac, const uint8_t *data, int len) {
  if (len >= (int)sizeof(DirectMsg)) {
    DirectMsg msg;
    memcpy(&msg, data, sizeof(msg));
    Serial.printf("[ESP-NOW] Nhan goi tin truc tiep: %s\n", msg.cmd);
    if (strcmp(msg.cmd, "FIND") == 0 || strcmp(msg.cmd, "SOS") == 0) {
      Serial.println(">>> [ESP-NOW] Kich hoat coi ngay lap tuc!");
      buzzerUntil = millis() + 25000;
    } else if (strcmp(msg.cmd, "STOP") == 0) {
      Serial.println(">>> [ESP-NOW] Nhan lenh STOP truc tiep! Tat coi ngay!");
      buzzerUntil = 0;
      setBuzzer(false);
    }
  }
}

bool espNowStarted = false;

void startEspNow() {
  if (!espNowStarted && esp_now_init() == ESP_OK) {
    esp_now_register_recv_cb(esp_now_recv_cb_t(onDataRecv));
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
  currentBuzzerState = 0; // Đánh dấu đã tắt còi

  Serial.begin(115200);
  delay(300);

  Serial.println("\n=======================================================");
  Serial.println("  ESP32-C3 SUPER MINI: BO PHAT COI CANH BAO (GAY)");
  Serial.println("=======================================================");
  Serial.printf("Chân còi: GPIO %d | Chân nút tắt còi: GPIO %d\n", BUZZER_PIN, STOP_BUTTON_PIN);

  // Chớp đèn LED 2 lần báo hiệu bo đã bật nguồn (giữ im lặng còi lúc khởi động)
  for (int i = 0; i < 2; i++) {
    digitalWrite(LED_BOARD, LOW);
    delay(80);
    digitalWrite(LED_BOARD, HIGH);
    delay(80);
  }

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  // Hạ công suất phát sóng xuống 8.5dBm để chống sụt áp nguồn và chống méo sóng RF gây lỗi AUTH_EXPIRE (Reason 2)
  WiFi.setTxPower(WIFI_POWER_8_5dBm);

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
  
  uint8_t bestBssid[6] = {0};
  int bestRssi = -100;
  bool foundBssid = false;

  for (int i = 0; i < n; ++i) {
    if (WiFi.SSID(i) == WIFI_SSID) {
      Serial.printf("  -> TIM THAY AP '%s' | BSSID: %s | RSSI: %d dBm | Ch: %d\n",
        WiFi.SSID(i).c_str(), WiFi.BSSIDstr(i).c_str(), WiFi.RSSI(i), WiFi.channel(i));
      if (WiFi.RSSI(i) > bestRssi) {
        bestRssi = WiFi.RSSI(i);
        memcpy(bestBssid, WiFi.BSSID(i), 6);
        foundBssid = true;
      }
    }
  }

  Serial.printf("\n[WiFi] Bat dau ket noi toi '%s' (TX=8.5dBm)...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void loop() {
  uint32_t now = millis();

  // 1. Kiểm tra nút bấm BOOT (GPIO9) trên bo C3 để tắt còi tại chỗ
  if (digitalRead(STOP_BUTTON_PIN) == LOW) {
    if (buzzerUntil > now) {
      Serial.println("[NUT BAM BOOT] Da an nut tat coi tai cho!");
      buzzerUntil = 0;
      setBuzzer(false);
      delay(300); // Chống dội phím
    }
  }

  // 2. Quản lý trạng thái kết nối Wi-Fi & đèn LED báo
  static bool wasOnline = false;
  if (WiFi.status() == WL_CONNECTED) {
    if (!wasOnline) {
      wasOnline = true;
      Serial.printf("[Wi-Fi] DA KET NOI THANH CONG! IP C3: %s | Server: %s\n", WiFi.localIP().toString().c_str(), API_BASE);
      startEspNow();
    }
    // Nếu còi không kêu: Đèn LED tắt báo mạng đã sẵn sàng
    if (buzzerUntil <= now) {
      digitalWrite(LED_BOARD, HIGH); // Tắt LED
    }
  } else {
    wasOnline = false;
    // Đang mất kết nối: Nhấp nháy đèn LED mỗi 300ms
    if (now - lastBlink >= 300) {
      lastBlink = now;
      ledState = !ledState;
      digitalWrite(LED_BOARD, ledState ? LOW : HIGH);
    }
    // Chỉ thử kết nối lại nếu bị ngắt sau 20 giây
    if (now - lastWifiCheck >= 20000) {
      lastWifiCheck = now;
      if (WiFi.status() != WL_CONNECTED) {
        Serial.printf("[Wi-Fi] Thu ket noi lai (status=%d)...\n", WiFi.status());
        WiFi.reconnect();
      }
    }
  }

  // 3. Xử lý âm thanh còi khi có báo động (nhịp tít tít 2 tiếng mỗi giây)
  if (buzzerUntil > now) {
    uint32_t cycle = now % 1000;
    // Nhịp đôi: Kêu 0-150ms, Nghỉ 150-230ms, Kêu 230-380ms, Nghỉ 380-1000ms
    bool beep = (cycle < 150) || (cycle >= 230 && cycle < 380);
    setBuzzer(beep);
  } else {
    setBuzzer(false);
  }

  // 4. Định kỳ 1 giây hỏi lệnh từ server
  if (now - lastPoll >= 1000) {
    lastPoll = now;
    pollCommands();
  }

  // 5. Định kỳ 3 giây gửi trạng thái lên server
  if (now - lastState >= 3000) {
    lastState = now;
    sendState();
  }

  delay(10);
}
