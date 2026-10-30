#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

#define OLED_SDA 26
#define OLED_SCL 13

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[OLED] Bat dau khoi tao man hinh...");

  // Khoi tao I2C voi chan SDA=26, SCL=13
  Wire.begin(OLED_SDA, OLED_SCL);

  // Quet dia chi I2C
  byte error, address;
  int nDevices = 0;
  byte foundAddr = 0x3C;
  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    if (error == 0) {
      Serial.printf("[I2C] Tim thay thiet bi tai dia chi: 0x%02X\n", address);
      foundAddr = address;
      nDevices++;
    }
  }

  // Khoi tao SSD1306
  if (!display.begin(SSD1306_SWITCHCAPVCC, foundAddr)) {
    Serial.println("[OLED] Khoi tao SSD1306 that bai! Thu lai voi 0x3D...");
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3D)) {
      Serial.println("[OLED] Khong tim thay man hinh OLED!");
      return;
    }
  }

  Serial.println("[OLED] Khoi tao thanh cong!");
  display.clearDisplay();

  // Khung vien
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);

  // Tieu de
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(18, 6);
  display.println("DONG HANH IoT");

  display.drawLine(4, 18, 124, 18, SSD1306_WHITE);

  display.setCursor(10, 24);
  display.println("OLED 0.96 inch OK!");

  display.setCursor(10, 38);
  display.println("SDA: D26 | SCL: D13");

  display.setCursor(10, 50);
  display.println("Chao mung ban!");

  display.display();
}

int count = 0;
void loop() {
  count++;
  // Hien thi so giay hoat dong
  display.fillRect(10, 50, 108, 10, SSD1306_BLACK);
  display.setCursor(10, 50);
  display.printf("Uptime: %d s", count);
  display.display();
  delay(1000);
}
