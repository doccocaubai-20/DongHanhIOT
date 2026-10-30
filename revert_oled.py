path = r'c:\Users\admin\Downloads\dong-hanh-hop-nhat\dong-hanh-hop-nhat\firmware\test_one\runtime.h'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Remove Adafruit headers
c = c.replace('#include <Adafruit_GFX.h>\n', '')
c = c.replace('#include <Adafruit_SSD1306.h>\n', '')

# 2. Revert pins: BUZZER back to 13
old_pins = '''constexpr int TRIG=32,ECHO=35,MOTOR=25,PIEZO=-1,BUZZER=-1,SOS=27,PRIVACY=14,DROP=-1,STOP=12,FIND=33,POT=34,STATUS_LED=2;
constexpr int OLED_SDA=26, OLED_SCL=13;'''
new_pins = 'constexpr int TRIG=32,ECHO=35,MOTOR=25,PIEZO=SINGLE_BUZZER?-1:26,BUZZER=13,SOS=27,PRIVACY=14,DROP=-1,STOP=12,FIND=33,POT=34,STATUS_LED=2;'
c = c.replace(old_pins, new_pins)

# 3. Remove initOled() call in setup
c = c.replace('bootNonce=esp_random();initOled();', 'bootNonce=esp_random();')

# 4. Remove oledTick call in loop
c = c.replace('  oledTick(now, s, sosActive, findActive, dropActive);\n', '')

# 5. Remove OLED functions block
start_str = '// Man hinh OLED 0.96 inch I2C (SDA=D26, SCL=D13)'
end_str = 'void sendEspNowDirect(const char* cmd) {'
idx1 = c.find(start_str)
idx2 = c.find(end_str)
if idx1 != -1 and idx2 != -1:
    c = c[:idx1] + c[idx2:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print('REVERT_SUCCESS')
