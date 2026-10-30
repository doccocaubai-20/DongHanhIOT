#pragma once
// Copy file này vào thư mục sketch đang dùng, đổi tên thành config.h.
// Không đưa config.h đã chứa khóa lên Git hoặc chụp vào báo cáo.
const char* WIFI_SSID = "YOUR_WIFI_2_4_GHZ";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
// Không thêm dấu / cuối. LAN chỉ dùng trong buổi thử trên mạng tin cậy.
const char* API_BASE = "http://192.168.1.10:8000";
// test_one -> TEST_TOKEN, chest_cam -> CHEST_TOKEN, cane -> CANE_TOKEN từ .env
const char* DEVICE_TOKEN = "PASTE_CORRECT_DEVICE_TOKEN_HERE";
constexpr bool ALLOW_HTTP_LAN = true;
// Nếu API_BASE là HTTPS: dán CA gốc phù hợp vào đây. KHÔNG dùng setInsecure().
const char* ROOT_CA = R"PEM(
)PEM";
// 0 = HC-SR04 thật. 1 = giả lập khoảng cách bằng biến trở ở sketch test_one.
#define TEST_DISTANCE_SIMULATION 0
// Chỉ có tác dụng ở cane: 1 dùng MPU6050; nếu chưa có cảm biến đặt 0 và dùng nút DROP.
#define ENABLE_IMU 1
// Giới hạn thử nghiệm; cần hiệu chỉnh với người sử dụng.
constexpr float ALERT_FAR_CM = 120.0f;
constexpr float ALERT_NEAR_CM = 40.0f;
// Tùy chọn (có thể bỏ trống, runtime.h có giá trị mặc định):
// Thời gian giữ nút SOS trước khi gửi, ms. 0 = nhấn là gửi như dong-hanh-iot cũ.
#define SOS_HOLD_MS 1500
// Vùng trễ khi rời ngưỡng ALERT_FAR_CM, cm.
#define ALERT_HYSTERESIS_CM 5.0f
// Chỉ ESP32-CAM: lật ảnh nếu camera gắn ngược/xoay (0 hoặc 1).
#define CAMERA_VFLIP 0
#define CAMERA_HMIRROR 0

