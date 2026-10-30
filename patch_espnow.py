import sys

path = r'c:\Users\admin\Downloads\dong-hanh-hop-nhat\dong-hanh-hop-nhat\firmware\test_one\runtime.h'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add #include <esp_now.h>
if '#include <esp_now.h>' not in content:
    content = content.replace('#include "config.h"', '#include <esp_now.h>\n#include "config.h"')

# 2. Add DirectMsg and ESP-NOW sender functions
esp_now_code = '''
// Truyen tin khong day truc tiep ESP-NOW giua nguc va gay (do tre < 10ms)
typedef struct {
  char cmd[16];
} DirectMsg;

static const uint8_t espNowBroadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
static bool espNowSenderReady = false;

void initEspNowSender() {
  if (espNowSenderReady) return;
  if (esp_now_init() != ESP_OK) {
    LOGF("[esp_now] khoi tao that bai\\n");
    return;
  }
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, espNowBroadcastMac, 6);
  peerInfo.channel = 0; // 0 = kenh Wi-Fi hien tai
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) == ESP_OK) {
    espNowSenderReady = true;
    LOGF("[esp_now] sender broadcast san sang!\\n");
  } else {
    LOGF("[esp_now] them peer broadcast that bai\\n");
  }
}

void sendEspNowDirect(const char* cmd) {
  if (!espNowSenderReady) {
    initEspNowSender();
  }
  if (espNowSenderReady) {
    DirectMsg msg;
    memset(&msg, 0, sizeof(msg));
    strncpy(msg.cmd, cmd, sizeof(msg.cmd) - 1);
    esp_err_t res = esp_now_send(espNowBroadcastMac, (const uint8_t*)&msg, sizeof(msg));
    LOGF("[esp_now] ban lenh '%s' -> %s\\n", cmd, res == ESP_OK ? "OK (tuc thi)" : "LOI");
  }
}
'''

if 'sendEspNowDirect' not in content:
    target = 'struct LocalCommand {uint8_t type;uint32_t value;};'
    content = content.replace(target, target + '\n' + esp_now_code)

# 3. Call initEspNowSender() in networkTask
target_wifi = 'WiFi.mode(WIFI_STA);WiFi.setSleep(false);WiFi.begin(WIFI_SSID,WIFI_PASSWORD);'
if 'initEspNowSender();' not in content:
    content = content.replace(target_wifi, target_wifi + 'initEspNowSender();')

# 4. In loop(): call sendEspNowDirect on findButton and stopButton
find_btn_old = 'if(findButton.pressed(now)){emitEvent("find","Physical find-cane button pressed.");LOGF("[nut] FIND\\n");}'
find_btn_new = 'if(findButton.pressed(now)){sendEspNowDirect("FIND");emitEvent("find","Physical find-cane button pressed.");LOGF("[nut] FIND\\n");}'
content = content.replace(find_btn_old, find_btn_new)

stop_btn_old = 'if(stopButton.pressed(now)){sosUntil=0;dropUntil=0;findUntil=0;roadUntil=0;emitEvent("stop","Physical STOP button pressed.");LOGF("[nut] STOP: tat coi\\n");}'
stop_btn_new = 'if(stopButton.pressed(now)){sosUntil=0;dropUntil=0;findUntil=0;roadUntil=0;sendEspNowDirect("STOP");emitEvent("stop","Physical STOP button pressed.");LOGF("[nut] STOP: tat coi\\n");}'
content = content.replace(stop_btn_old, stop_btn_new)

# 5. In loop(): call sendEspNowDirect on SOS
sos_btn_old = 'else{sosUntil=now+60000;emitEvent("sos","Physical SOS button held.");LOGF("[nut] SOS: gui su kien\\n");}'
sos_btn_new = 'else{sosUntil=now+60000;sendEspNowDirect("SOS");emitEvent("sos","Physical SOS button held.");LOGF("[nut] SOS: gui su kien\\n");}'
content = content.replace(sos_btn_old, sos_btn_new)

# 6. Also forward find/stop when server sends command
poll_find_old = 'if(lastFind!=id){LocalCommand cmd{1,0};if(xQueueSend(commandQueue,&cmd,0)!=pdTRUE)continue;lastFind=id;}'
poll_find_new = 'if(lastFind!=id){LocalCommand cmd{1,0};if(xQueueSend(commandQueue,&cmd,0)!=pdTRUE)continue;lastFind=id;sendEspNowDirect("FIND");}'
content = content.replace(poll_find_old, poll_find_new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('SUCCESS')
