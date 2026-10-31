#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include "qrcode.h"

// ==========================================
// CẤU HÌNH ĐƯỜNG DẪN CỨU HỘ SOS & THÔNG TIN
// ==========================================
// Link bắt đầu bằng HTTP:// để camera điện thoại nhận diện là LIÊN KẾT WEB (không vào thanh tìm kiếm)
// Chuẩn Alphanumeric 23 ký tự -> Vừa khít Version 1 (42x42 px), 100% trong dải màu xanh
const char* QR_LINK          = "HTTP://161.118.211.25/S";

// Thông tin người thân (hiển thị khi bấm nút xem trang liên hệ)
const char* EMERGENCY_NAME   = "NGUYEN VAN A";
const char* EMERGENCY_PHONE1 = "0988 123 456";
const char* EMERGENCY_PHONE2 = "0912 345 678";

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

// 6. NÚT BẤM CHUYỂN TRANG
constexpr int PIN_BUTTON_EXT  = 10; // Nút bấm rời to từ bộ kit -> GPIO 10 (nối chân còn lại với GND)
constexpr int PIN_BUTTON_BOOT = 9;  // Nút BOOT nhỏ tích hợp sẵn trên bo mạch -> GPIO 9 (dự phòng)

// ==========================================
// BIẾN TOÀN CỤC & QUẢN LÝ DỮ LIỆU
// ==========================================
float temperature = 0.0;
float humidity = 0.0;
int ldrRaw = 0;
int lightPercent = 0;
String lightStatus = "Binh thuong";
uint32_t lastSensorRead = 0;
uint32_t lastDisplayUpdate = 0;
uint32_t pageSwitchTime = 0;

// Chế độ hiển thị:
// 0 = Màn hình QR Code Cứu Hộ (MẶC ĐỊNH, KHÔNG TỰ ĐỔI ĐỂ NGƯỜI ĐI ĐƯỜNG QUÉT DỄ DÀNG)
// 1 = Màn hình Cảm biến Môi trường (Bấm nút BOOT để xem)
// 2 = Màn hình Danh bạ SĐT SOS (Bấm nút BOOT tiếp để xem)
int displayPage = 0;
const int TOTAL_PAGES = 3;
bool oledReady = false;

// Đối tượng QR Code lưu sẵn trong bộ nhớ RAM
QRCode qrCodeObj;
uint8_t qrDataBuffer[64]; // Vừa vặn cho Version 1 (56 bytes)
bool qrInitialized = false;

// 7 màu sắc pha được của LED RGB
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

// Đọc thông số cảm biến môi trường
void readSensors() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (!isnan(t) && !isnan(h) && t > 0) {
    temperature = t;
    humidity = h;
  }

  // Đọc quang trở: ADC cao = tối (0%), ADC thấp = sáng (100%)
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

// ==========================================
// CÁC HÀM HIỂN THỊ MÀN HÌNH OLED
// ==========================================

// TRANG 0: MÃ QR CỨU HỘ TO, NÉT CĂNG (100% MÀU XANH, KHÔNG DÍNH VÀNG)
void renderQRCodePage() {
  display.clearDisplay();

  // 1. DẢI MÀU VÀNG PHÍA TRÊN (Y = 0 đến 15)
  // Bỏ hoàn toàn chữ "DONG HANH" theo đúng yêu cầu
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(10, 4);
  display.print(F("QUET MA CUU HO SOS"));

  // 2. DẢI MÀU XANH PHÍA DƯỚI (Y = 16 đến 63 - Cao đúng 48 pixel)
  // QR Version 1 (21x21 modules), phóng to 2x2 px = 42x42 px
  int scale = 2;
  int qrWidth = qrCodeObj.size * scale; // 42 px
  int startX = (SCREEN_WIDTH - qrWidth) / 2; // = 43 (Căn chính giữa màn hình)
  int startY = 19; // Từ Y = 19 đến 60 (Cao 42 px, căn chính giữa dải màu xanh 16-63)
  int border = 2;

  // Vẽ khung trắng Quiet Zone xung quanh (46x46 px, từ Y = 17 đến 62 -> 100% trong dải xanh!)
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

  // Chữ điều hướng ở 2 bên mã QR trong dải màu xanh
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  
  // Bên trái mã QR
  display.setCursor(6, 23);
  display.print(F("GOI"));
  display.setCursor(6, 35);
  display.print(F("SOS"));
  display.setCursor(6, 47);
  display.print(F(">>>"));

  // Bên phải mã QR
  display.setCursor(94, 23);
  display.print(F("SDT"));
  display.setCursor(94, 35);
  display.print(F("NHA"));
  display.setCursor(94, 47);
  display.print(F("<<<"));

  display.display();
}

// TRANG 1: HIỂN THỊ CÁC THÔNG SỐ CẢM BIẾN MÔI TRƯỜNG
void renderSensorPage() {
  display.clearDisplay();

  // Dải màu vàng phía trên
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 4);
  display.print(F("THONG SO MOI TRUONG"));

  if (lightPercent < 25) {
    display.setCursor(110, 4);
    display.print(F("[*]"));
  }

  // Dải màu xanh phía dưới
  display.setCursor(2, 18);
  display.print(F("Nhiet do: "));
  if (temperature > 0) display.printf("%.1f C", temperature);
  else display.print(F("--.- C"));

  display.setCursor(2, 29);
  display.print(F("Do am   : "));
  if (humidity > 0) display.printf("%.0f %%", humidity);
  else display.print(F("-- %"));

  display.setCursor(2, 40);
  display.print(F("Anh sang: "));
  display.printf("%d %% (%s)", lightPercent, lightPercent < 25 ? "Toi" : "Sang");

  // Thanh đo độ sáng
  display.drawRect(2, 52, 124, 8, SSD1306_WHITE);
  int barWidth = map(lightPercent, 0, 100, 0, 120);
  if (barWidth > 0) {
    display.fillRect(4, 54, barWidth, 4, SSD1306_WHITE);
  }

  display.display();
}

// TRANG 2: HIỂN THỊ DANH BẠ SỐ ĐIỆN THOẠI NGƯỜI NHÀ
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

// Điều khiển LED RGB theo môi trường
void updateRgb(uint32_t now) {
  static uint32_t lastRainbowChange = 0;
  static int colorIndex = 0;

  // Quá nhiệt (>= 36°C): Nháy ĐỎ cảnh báo
  if (temperature >= 36.0) {
    bool blink = (now / 300) % 2;
    setRgbColor(blink, false, false);
    return;
  }

  // KHI TRỜI TỐI (< 25%): Đổi tất cả các màu sắc cầu vồng liên tục
  if (lightPercent < 25) {
    if (now - lastRainbowChange >= 400) {
      lastRainbowChange = now;
      colorIndex = (colorIndex + 1) % TOTAL_COLORS;
      setRgbColor(ALL_COLORS[colorIndex].r, ALL_COLORS[colorIndex].g, ALL_COLORS[colorIndex].b);
    }
  }
  // KHI TRỜI SÁNG: Giữ màu XANH LÁ an toàn
  else {
    setRgbColor(false, true, false);
  }
}

// ==========================================
// SETUP & LOOP
// ==========================================
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
  pinMode(PIN_BUTTON_EXT, INPUT_PULLUP);

  // Khởi động I2C cho OLED trên GPIO 6 & 7
  Wire.begin(PIN_SDA, PIN_SCL);

  Serial.println("\n=======================================================");
  Serial.println("  ESP32-C3: OLED QR CUU HO (100% KHONG NHIEM VANG)");
  Serial.println("=======================================================");

  // Khởi tạo mã QR một lần duy nhất vào bộ nhớ RAM
  int8_t qrStatus = qrcode_initText(&qrCodeObj, qrDataBuffer, 1, ECC_LOW, QR_LINK);
  if (qrStatus == 0) {
    qrInitialized = true;
    Serial.printf("[OK] Ma QR tao thanh cong! Link: %s (Kich thuoc: %d modules)\n", QR_LINK, qrCodeObj.size);
  } else {
    qrInitialized = false;
    Serial.printf("[LOI] Tao ma QR that bai (ma loi: %d)\n", qrStatus);
  }

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

  // Đọc cảm biến lần đầu
  readSensors();

  // Mặc định hiển thị ngay màn hình QR Code cứu hộ
  displayPage = 0;
  if (oledReady) {
    renderQRCodePage();
  }

  beep(80);
}

void loop() {
  uint32_t now = millis();

  // Đọc cảm biến mỗi 1.5 giây
  if (now - lastSensorRead >= 1500) {
    lastSensorRead = now;
    readSensors();
  }

  // Cập nhật màn hình OLED định kỳ mỗi 500ms (tránh I2C spam liên tục)
  if (oledReady && (now - lastDisplayUpdate >= 500)) {
    lastDisplayUpdate = now;
    if (displayPage == 0) {
      renderQRCodePage();
    } else if (displayPage == 1) {
      renderSensorPage();
    } else {
      renderContactPage();
    }
  }

  // Nếu người dùng đang xem trang cảm biến hoặc danh bạ SĐT,
  // sau 15 giây không bấm nút sẽ TỰ ĐỘNG QUAY VỀ MÀN HÌNH QR CODE CỨU HỘ!
  if (displayPage != 0 && (now - pageSwitchTime >= 15000)) {
    displayPage = 0;
    if (oledReady) renderQRCodePage();
    Serial.println(F("[OLED] Tu dong quay ve Man hinh QR Code Cuu Ho!"));
  }

  // Đổi màu LED RGB liên tục
  updateRgb(now);

  // Bấm nút chuyển trang thủ công: Hỗ trợ cả Nút Rời Ngoài (GPIO 10) HOẶC Nút BOOT (GPIO 9)
  if (digitalRead(PIN_BUTTON_EXT) == LOW || digitalRead(PIN_BUTTON_BOOT) == LOW) {
    displayPage = (displayPage + 1) % TOTAL_PAGES;
    pageSwitchTime = now;
    beep(80);
    if (oledReady) {
      if (displayPage == 0) renderQRCodePage();
      else if (displayPage == 1) renderSensorPage();
      else renderContactPage();
    }
    delay(300);
  }
}
