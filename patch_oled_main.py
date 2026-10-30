path = r'c:\Users\admin\Downloads\dong-hanh-hop-nhat\dong-hanh-hop-nhat\firmware\test_one\runtime.h'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Add headers
if 'Adafruit_SSD1306.h' not in c:
    c = c.replace('#include <esp_now.h>', '#include <esp_now.h>\n#include <Adafruit_GFX.h>\n#include <Adafruit_SSD1306.h>')

# 2. Release D13 (BUZZER) and D26 (PIEZO) for OLED
old_pins = 'constexpr int TRIG=32,ECHO=35,MOTOR=25,PIEZO=SINGLE_BUZZER?-1:26,BUZZER=13,SOS=27,PRIVACY=14,DROP=-1,STOP=12,FIND=33,POT=34,STATUS_LED=2;'
new_pins = 'constexpr int TRIG=32,ECHO=35,MOTOR=25,PIEZO=-1,BUZZER=-1,SOS=27,PRIVACY=14,DROP=-1,STOP=12,FIND=33,POT=34,STATUS_LED=2;\nconstexpr int OLED_SDA=26, OLED_SCL=13;'
c = c.replace(old_pins, new_pins)

# 3. Add OLED functions
oled_code = '''
// Man hinh OLED 0.96 inch I2C (SDA=D26, SCL=D13)
static Adafruit_SSD1306 oled(128, 64, &Wire, -1);
static bool oledReady = false;
static uint32_t lastOledTick = 0;

void initOled() {
  Wire.begin(OLED_SDA, OLED_SCL);
  if (oled.begin(SSD1306_SWITCHCAPVCC, 0x3C) || oled.begin(SSD1306_SWITCHCAPVCC, 0x3D)) {
    oledReady = true;
    oled.clearDisplay();
    oled.setTextSize(1);
    oled.setTextColor(SSD1306_WHITE);
    oled.setCursor(18, 12);
    oled.println("DONG HANH IoT");
    oled.setCursor(20, 32);
    oled.println("Dang khoi dong...");
    oled.display();
    LOGF("[oled] Khoi tao OLED thanh cong!\\n");
  } else {
    LOGF("[oled] Khong tim thay OLED!\\n");
  }
}

void oledTick(uint32_t now, const Snapshot& s, bool sosActive, bool findActive, bool dropActive) {
  if (!oledReady || now - lastOledTick < 180) return;
  lastOledTick = now;

  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setTextColor(SSD1306_WHITE);

  // Thanh Tieu de & WiFi
  oled.setCursor(2, 2);
  oled.print("DONG HANH");
  oled.setCursor(74, 2);
  if (WiFi.status() == WL_CONNECTED) {
    oled.print("[WiFi:OK]");
  } else {
    oled.print("[No-WiFi]");
  }
  oled.drawLine(0, 11, 127, 11, SSD1306_WHITE);

  // Dong 2: Khoang cach vat can
  oled.setCursor(2, 15);
  if (s.sensorValid && s.distance >= 0) {
    oled.printf("Vat can: %d cm", (int)round(s.distance));
    if (s.distance < 40) {
      oled.setCursor(90, 15);
      oled.print("!CANH!");
    }
  } else {
    oled.print("Vat can: Dang do...");
  }

  // Dong 3: Trang thai Bao dong / Lenh
  oled.setCursor(2, 27);
  if (sosActive) {
    oled.print(">> SOS BAO DONG! <<");
  } else if (findActive) {
    oled.print(">> TIM GAY (BEEP) <<");
  } else if (dropActive) {
    oled.print(">> CANH BAO ROI <<");
  } else {
    oled.print("Trang thai: San sang");
  }

  oled.drawLine(0, 38, 127, 38, SSD1306_WHITE);

  // Dong 4: IP hoac ESP-NOW
  oled.setCursor(2, 42);
  if (WiFi.status() == WL_CONNECTED) {
    oled.printf("IP: %s", WiFi.localIP().toString().c_str());
  } else {
    oled.print("Song: ESP-NOW san sang");
  }

  // Dong 5: Uptime & Quyen rieng tu
  oled.setCursor(2, 53);
  oled.printf("Up: %us | Anh: %s", (unsigned)s.uptime, s.periodic ? "BAT" : "TAT");

  oled.display();
}
'''

if 'initOled' not in c:
    c = c.replace('void sendEspNowDirect(const char* cmd) {', oled_code + '\nvoid sendEspNowDirect(const char* cmd) {')

# 4. In setup(): call initOled()
if 'initOled();' not in c:
    c = c.replace('bootNonce=esp_random();', 'bootNonce=esp_random();initOled();')

# 5. In loop(): call oledTick(...)
if 'oledTick(' not in c:
    target_loop = 'if(STATUS_LED>=0)digitalWrite(STATUS_LED,(WiFi.status()==WL_CONNECTED)?HIGH:now%1000<100);'
    c = c.replace(target_loop, target_loop + '\n  oledTick(now, s, sosActive, findActive, dropActive);')

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print('SUCCESS_OLED_PATCH')
