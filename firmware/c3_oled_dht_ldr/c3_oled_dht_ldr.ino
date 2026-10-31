#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include "qrcode.h"

// ==========================================
// CẤU HÌNH THÔNG TIN LIÊN HỆ NGƯỜI NHÀ (SOS)
// ==========================================
// Bạn có thể sửa tên và số điện thoại người nhà ở đây:
const char* EMERGENCY_NAME   = "NGUYEN VAN A";     // Tên người dùng gậy
const char* EMERGENCY_PHONE1 = "0988 123 456";     // SĐT người thân chính (Bố/Mẹ/Vợ/Con)
const char* EMERGENCY_PHONE2 = "0912 345 678";     // SĐT người thân phụ / dự phòng

// Đường link cứu hộ công cộng (không vào trang dashboard có ảnh riêng tư)
// Link chuẩn Alphanumeric để mã QR nằm gọn trong 42x42 px dải màu xanh
const char* QR_LINK          = "IOT.CHONGZIAPP.ID.VN/SOS";

// ==========================================
// CẤU HÌNH PHẦN CỨNG ESP32-C3 SUPER MINI
// ==========================================

// 1. MÀN HÌNH OLED 0.96 inch (SSD1306 I2C 128x64)
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
constexpr int PIN_SDA = 6;    // OLED SDA -> GPIO 6
constexpr int PIN_SCL = 7;    // OLED SCL -> GPIO 7

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// 2. CẢM BIẾN NHIỆT ĐỘ & ĐỘ ẨM DHT11
constexpr int PIN_DHT = 2;    // DHT11 Data -> GPIO 2
#define DHTTYPE DHT11
DHT dht(PIN_DHT, DHTTYPE);

// 3. CẢM BIẾN ÁNH SÁNG QUANG TRỞ (LDR)
constexpr int PIN_LDR = 0;    // Quang trở A0 -> GPIO 0 (ADC1_CH0)

// 4. CÒI BÁO (BUZZER)
constexpr int PIN_BUZZER = 5; // Còi (+) -> GPIO 5

// 5. ĐÈN LED RGB (4 CHÂN)
constexpr int PIN_RGB_R = 1;  // Đỏ (Red) -> GPIO 1 (qua trở)
constexpr int PIN_RGB_G = 3;  // Xanh lá (Green) -> GPIO 3 (qua trở)
constexpr int PIN_RGB_B = 4;  // Xanh dương (Blue) -> GPIO 4 (qua trở)

// 6. NÚT BẤM BOOT TRÊN BO
constexpr int PIN_BUTTON_BOOT = 9;

// Biến lưu trữ dữ liệu
float temperature = 0.0;
float humidity = 0.0;
int ldrRaw = 0;
int lightPercent = 0;
String lightStatus = "Binh thuong";
uint32_t lastSensorRead = 0;
uint32_t lastPageSwitch = 0;
int displayPage = 0; // 0 = Cảm biến, 1 = SĐT Người nhà, 2 = Mã QR Code (Dải xanh)
const int TOTAL_PAGES = 3;
bool oledReady = false;

// 7 màu sắc có thể pha được của LED RGB
struct RgbColor {
  bool r, g, b;
  const char* name;
};

const RgbColor ALL_COLORS[] = {
  {true,  false, false, "Do"},
  {true,  true,  false, "Vang"},
  {false, true,  false, "Xanh la"},
  {false, true,  true,  "Xanh lo"},
  {false, false, true,  "Xanh duong"},
  {true,  false, true,  "Tim"},
  {true,  true,  true,  "Trang"}
};
const int TOTAL_COLORS = sizeof(ALL_COLORS) / sizeof(ALL_COLORS[0]);

// Điều khiển màu LED RGB (Cathode chung: HIGH = Sáng, LOW = Tắt)
void setRgbColor(bool r, bool g, bool b) {
  digitalWrite(PIN_RGB_R, r ? HIGH : LOW);
  digitalWrite(PIN_RGB_G, g ? HIGH : LOW);
  digitalWrite(PIN_RGB_B, b ? HIGH : LOW);
}

void beep(int ms) {
  digitalWrite(PIN_BUZZER, HIGH);
  delay(ms);
  digitalWrite(PIN_BUZZER, LOW);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  pinMode(PIN_RGB_R, OUTPUT);
  pinMode(PIN_RGB_G, OUTPUT);
  pinMode(PIN_RGB_B, OUTPUT);
  setRgbColor(false, false, false);

  pinMode(PIN_LDR, INPUT);
  pinMode(PIN_BUTTON_BOOT, INPUT_PULLUP);

  // Khởi động I2C cho OLED trên GPIO 6 & 7
  Wire.begin(PIN_SDA, PIN_SCL);

  Serial.println("\n=======================================================");
  Serial.println("  ESP32-C3: OLED (KHONG NHIEM VANG) + ROUTER SOS + RGB");
  Serial.println("=======================================================");

  // Khởi động OLED (0x3C)
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("[LOI] Khong tim thay OLED! Kiem tra day SDA(6), SCL(7)."));
    oledReady = false;
  } else {
    Serial.println(F("[OK] Man hinh OLED khoi dong thanh cong!"));
    oledReady = true;
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(18, 4);
    display.println(F("THIET BI CUU HO"));
    display.setCursor(22, 26);
    display.println(F("C3 SUPER MINI"));
    display.setCursor(14, 44);
    display.println(F("Dang khoi tao..."));
    display.display();
    delay(1000);
  }

  // Khởi động DHT11
  dht.begin();
  Serial.println(F("[OK] DHT11 da san sang tren GPIO 2!"));

  beep(80);
}

void readSensors() {
  // 1. Đọc DHT11
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t) && !isnan(h)) {
    temperature = t;
    humidity = h;
  }

  // 2. Đọc Quang trở (Đảo chiều: ADC cao = tối 0%, ADC thấp = sáng 100%)
  ldrRaw = analogRead(PIN_LDR);
  lightPercent = map(ldrRaw, 3700, 400, 0, 100);
  lightPercent = constrain(lightPercent, 0, 100);

  if (lightPercent < 25) {
    lightStatus = "Troi toi";
  } else if (lightPercent < 60) {
    lightStatus = "Vua phai";
  } else {
    lightStatus = "Sang ro";
  }

  Serial.printf("[DO] Nhiet do: %.1f C | Do am: %.0f %% | Sang: %d %% (ADC: %d) -> %s\n",
                temperature, humidity, lightPercent, ldrRaw, lightStatus.c_str());
}

// TRANG 1: HIỂN THỊ CÁC THÔNG SỐ CẢM BIẾN MÔI TRƯỜNG
void renderSensorPage() {
  display.clearDisplay();

  // Dải màu vàng ở trên (Y = 0 đến 15) - Bỏ chữ Dong Hanh
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 3);
  display.print(F("THONG SO MOI TRUONG"));

  if (lightPercent < 25) {
    display.setCursor(110, 3);
    display.print(F("[*]"));
  }

  // Dải màu xanh ở dưới (Y = 16 đến 63)
  // Dòng 1: Nhiệt độ
  display.setCursor(2, 17);
  display.print(F("Nhiet do: "));
  if (temperature > 0) display.printf("%.1f C", temperature);
  else display.print(F("--.- C"));

  // Dòng 2: Độ ẩm
  display.setCursor(2, 28);
  display.print(F("Do am   : "));
  if (humidity > 0) display.printf("%.0f %%", humidity);
  else display.print(F("-- %"));

  // Dòng 3: Ánh sáng
  display.setCursor(2, 39);
  display.print(F("Anh sang: "));
  display.printf("%d %% (%s)", lightPercent, lightPercent < 25 ? "Toi" : "Sang");

  // Thanh đo độ sáng (Progress Bar)
  display.drawRect(2, 51, 124, 8, SSD1306_WHITE);
  int barWidth = map(lightPercent, 0, 100, 0, 120);
  if (barWidth > 0) {
    display.fillRect(4, 53, barWidth, 4, SSD1306_WHITE);
  }

  display.display();
}

// TRANG 2: HIỂN THỊ THÔNG TIN SỐ ĐIỆN THOẠI NGƯỜI NHÀ (SOS TOÀN MÀN HÌNH)
void renderContactPage() {
  display.clearDisplay();

  // Dải màu vàng ở trên (Y = 0 đến 15)
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 3);
  display.print(F("SO GOI NGUOI NHA (SOS)"));

  // Dải màu xanh ở dưới (Y = 16 đến 63)
  display.setCursor(2, 17);
  display.print(F("Ten: "));
  display.print(EMERGENCY_NAME);

  display.setCursor(2, 29);
  display.print(F("SDT: "));
  display.print(EMERGENCY_PHONE1);

  display.setCursor(2, 41);
  display.print(F("Phu: "));
  display.print(EMERGENCY_PHONE2);

  display.drawLine(2, 52, 126, 52, SSD1306_WHITE);
  display.setCursor(2, 55);
  display.print(F("* Xin nho goi giup!"));

  display.display();
}

// TRANG 3: HIỂN THỊ MÃ QR CODE (100% NẰM TRONG DẢI MÀU XANH, KHÔNG DÍNH VÀNG)
void renderQRCodePage() {
  QRCode qrcode;
  uint8_t qrcodeData[qrcode_getBufferSize(1)];
  // Tạo mã QR Version 1 (21x21 modules): vừa vặn chiều cao 48px của dải màu xanh
  qrcode_initText(&qrcode, qrcodeData, 1, ECC_LOW, QR_LINK);

  display.clearDisplay();

  // Dải màu vàng ở trên (Y = 0 đến 15): Tiêu đề ngắn gọn, BỎ chữ "DONG HANH"
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 3);
  display.print(F("QUET MA HOAC GOI SOS"));

  // Dải màu xanh ở dưới (Y = 16 đến 63):
  // QR code kích thước 21x21 module, mỗi module to 2x2 px = 42x42 px
  // Bắt đầu từ Y = 17 -> kết thúc ở Y = 61 (100% màu xanh, không chạm 1 pixel vàng nào!)
  int startX = 4;
  int startY = 17;
  int qrPixSize = 2;

  // Viền trắng Quiet Zone (46x46 px)
  display.fillRect(startX - 2, startY - 2, qrcode.size * qrPixSize + 4, qrcode.size * qrPixSize + 4, SSD1306_WHITE);

  // Vẽ các module đen của QR code
  for (uint8_t y = 0; y < qrcode.size; y++) {
    for (uint8_t x = 0; x < qrcode.size; x++) {
      if (qrcode_getModule(&qrcode, x, y)) {
        display.fillRect(startX + x * qrPixSize, startY + y * qrPixSize, qrPixSize, qrPixSize, SSD1306_BLACK);
      }
    }
  }

  // Nửa bên phải dải màu xanh (X từ 54 đến 127): Hiển thị trực tiếp SĐT người nhà
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(54, 17);
  display.print(F("SDT CHINH:"));
  display.setCursor(54, 27);
  display.print(EMERGENCY_PHONE1);

  display.setCursor(54, 39);
  display.print(F("SDT PHU:"));
  display.setCursor(54, 49);
  display.print(EMERGENCY_PHONE2);

  display.display();
}

// Điều khiển LED RGB theo môi trường
void updateRgb(uint32_t now) {
  static uint32_t lastRainbowChange = 0;
  static int colorIndex = 0;

  // 1. Quá nhiệt (>= 36°C): Nháy ĐỎ cảnh báo
  if (temperature >= 36.0) {
    bool blink = (now / 300) % 2;
    setRgbColor(blink, false, false);
    return;
  }

  // 2. KHI TRỜI TỐI (< 25%): Đổi tất cả các màu sắc cầu vồng liên tục
  if (lightPercent < 25) {
    if (now - lastRainbowChange >= 400) {
      lastRainbowChange = now;
      colorIndex = (colorIndex + 1) % TOTAL_COLORS;
      setRgbColor(ALL_COLORS[colorIndex].r, ALL_COLORS[colorIndex].g, ALL_COLORS[colorIndex].b);
    }
  }
  // 3. KHI TRỜI SÁNG: Giữ màu XANH LÁ an toàn, ổn định
  else {
    setRgbColor(false, true, false);
  }
}

void loop() {
  uint32_t now = millis();

  // Đọc cảm biến mỗi 1.5 giây
  if (now - lastSensorRead >= 1500) {
    lastSensorRead = now;
    readSensors();
  }

  // Tự động chuyển trang màn hình mỗi 5 giây (Cảm biến -> SĐT Người nhà -> Mã QR sạch)
  if (now - lastPageSwitch >= 5000) {
    lastPageSwitch = now;
    displayPage = (displayPage + 1) % TOTAL_PAGES;
  }

  // Cập nhật màn hình OLED theo trang hiện tại
  if (oledReady) {
    if (displayPage == 0) {
      renderSensorPage();
    } else if (displayPage == 1) {
      renderContactPage();
    } else {
      renderQRCodePage();
    }
  }

  // Đổi màu LED RGB liên tục
  updateRgb(now);

  // Bấm nút BOOT (GPIO 9) để đổi trang ngay lập tức + kêu bíp
  if (digitalRead(PIN_BUTTON_BOOT) == LOW) {
    displayPage = (displayPage + 1) % TOTAL_PAGES;
    beep(80);
    delay(300);
  }
}
