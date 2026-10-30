#pragma once
#include <Arduino.h>

// ==========================================
// CẤU HÌNH KẾT NỐI WI-FI & SERVER (Dành cho Fallback HTTP)
// ==========================================
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Địa chỉ Server (hoặc Domain HTTPS khi triển khai Cloud)
const char* API_BASE = "https://iot.yourdomain.com";

// CANE_TOKEN từ file .env (được sinh ngẫu nhiên khi chạy scripts/setup.py)
const char* DEVICE_TOKEN = "YOUR_CANE_TOKEN_HERE";

// ==========================================
// CẤU HÌNH PHẦN CỨNG ESP32-C3 SUPER MINI:
// ==========================================
// Chân còi chính: GPIO 5 (chân góc dưới bên phải)
constexpr int BUZZER_PIN = 5;

// Các chân xuất tín hiệu còi đồng thời (tăng cường âm lượng hoặc tương thích nhiều chân):
const int BUZZER_PINS[] = {5, 21, 3, 4};
const int NUM_BUZZER_PINS = sizeof(BUZZER_PINS) / sizeof(BUZZER_PINS[0]);

// Đèn LED trạng thái trên bo ESP32-C3 Super Mini (GPIO 8)
constexpr int LED_BOARD = 8;

// Nút bấm BOOT trên bo ESP32-C3 Super Mini (GPIO 9: bấm để tắt còi tại chỗ)
constexpr int STOP_BUTTON_PIN = 9;

// Loại còi: 0 = Còi Active (cấp điện áp HIGH 3.3V là kêu)
#define PASSIVE_BUZZER 0
#define BUZZER_ACTIVE_LEVEL HIGH
