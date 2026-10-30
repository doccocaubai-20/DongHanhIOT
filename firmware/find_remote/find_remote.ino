// Nút tìm gậy cầm tay, tùy chọn (chuyển từ smart_cane/firmware/find_remote_c3).
// ESP32-C3 Mini, nút từ GPIO3 xuống GND. Không dùng nút BOOT. Cần REMOTE_TOKEN trong .env của máy chủ.
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "config.h"

constexpr int BUTTON_PIN = 3;
constexpr uint32_t REQUEST_TTL_MS = 10000; // quá thời gian này coi như không còn cần tìm gậy
bool raw = HIGH, stable = HIGH, pending = false;
uint32_t changedAt = 0, pressedAt = 0, lastAttempt = 0, lastWifi = 0;

int requestFind() {
  String url = String(API_BASE) + "/api/v1/find-cane";
  WiFiClient plain; WiFiClientSecure secure; HTTPClient http;
  bool ok = false;
  if (url.startsWith("https://")) { if (strlen(ROOT_CA) < 100) return -2; secure.setCACert(ROOT_CA); ok = http.begin(secure, url); }
  else if (url.startsWith("http://") && ALLOW_HTTP_LAN) ok = http.begin(plain, url);
  if (!ok) return -3;
  http.setConnectTimeout(1200); http.setTimeout(1500);
  http.addHeader("Authorization", String("Bearer ") + DEVICE_TOKEN);
  int status = http.POST("");
  http.end();
  return status;
}

void setup() {
  Serial.begin(115200); pinMode(BUTTON_PIN, INPUT_PULLUP);
  WiFi.mode(WIFI_STA); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Find remote: GPIO3 button to GND. Requires server and cane on Wi-Fi.");
}

void loop() {
  uint32_t now = millis();
  bool value = digitalRead(BUTTON_PIN);
  if (value != raw) { raw = value; changedAt = now; }
  if (now - changedAt >= 30 && stable != raw) {
    stable = raw;
    if (stable == LOW) { pending = true; pressedAt = now; }
  }
  if (pending && now - pressedAt > REQUEST_TTL_MS) { pending = false; Serial.println("Find request expired: no server acknowledgement."); }
  if (WiFi.status() != WL_CONNECTED) {
    if (now - lastWifi > 10000) { lastWifi = now; WiFi.reconnect(); }
  } else if (pending && now - lastAttempt > 1000) {
    lastAttempt = now;
    int status = requestFind();
    // 401/403 = sai khóa hoặc máy chủ chưa bật REMOTE_TOKEN: thử lại không giúp được.
    if (status == 200 || status == 401 || status == 403) pending = false;
    Serial.printf("Find request HTTP=%d\n", status);
  }
  delay(5);
}
