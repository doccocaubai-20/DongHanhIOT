#pragma once
// Copy file này thành config.h trong cùng thư mục. Không đưa config.h lên Git.
const char* WIFI_SSID = "YOUR_WIFI_2_4_GHZ";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
// Không thêm dấu / cuối.
const char* API_BASE = "http://192.168.1.10:8000";
// REMOTE_TOKEN từ .env của máy chủ (không dùng khóa của bo khác).
const char* DEVICE_TOKEN = "PASTE_REMOTE_TOKEN_HERE";
constexpr bool ALLOW_HTTP_LAN = true;
// Nếu API_BASE là HTTPS: dán CA gốc phù hợp vào đây. KHÔNG dùng setInsecure().
const char* ROOT_CA = R"PEM(
)PEM";
