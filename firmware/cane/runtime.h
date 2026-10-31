#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <Wire.h>
#include <driver/ledc.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include <esp_random.h>
#include <time.h>
#include <esp_task_wdt.h>
#include "config.h"
#if APP_ROLE == 1
#include "esp_camera.h"
#endif
// Giá trị mặc định cho config.h cũ của dong-hanh-iot (không cần sửa config.h đã có).
#ifndef SOS_HOLD_MS
#define SOS_HOLD_MS 1500 // giữ nút SOS 1,5 s như smart_cane để tránh SOS nhầm; 0 = nhấn là gửi
#endif
#ifndef ALERT_HYSTERESIS_CM
#define ALERT_HYSTERESIS_CM 5.0f // vùng trễ khi rời ngưỡng xa, tránh bật/tắt liên tục ở biên
#endif
#ifndef SINGLE_BUZZER
#define SINGLE_BUZZER 0 // 1 = test_one chỉ có một còi ở GPIO13 (không có piezo GPIO26)
#endif
#ifndef BUZZER_ACTIVE_LOW
#define BUZZER_ACTIVE_LOW 0 // 1 = module còi kêu khi chân I/O ở mức LOW (loại dùng transistor PNP)
#endif
#ifndef CAMERA_ONLY
#define CAMERA_ONLY 0 // 1 = ESP32-CAM chỉ chụp ảnh (PROJECT_MODE=duo); không nút, không cảm biến
#endif
#ifndef CAMERA_VFLIP
#define CAMERA_VFLIP 0 // 1 = lật ảnh trên-dưới (camera gắn ngược)
#endif
#ifndef CAMERA_HMIRROR
#define CAMERA_HMIRROR 0 // 1 = lật ảnh trái-phải
#endif
#ifndef LOG_SERIAL
#define LOG_SERIAL 1 // in trạng thái ra Serial Monitor 115200 để dò lỗi khi lắp
#endif
#ifndef NETWORK_WDT_S
#define NETWORK_WDT_S 60 // tác vụ mạng/camera treo quá 60 s (chụp ảnh, HTTP kẹt) thì tự khởi động lại; 0 = tắt
#endif
#ifndef OFFLINE_RESTART_MIN
#define OFFLINE_RESTART_MIN (CAMERA_ONLY?10:0) // ESP32-CAM chỉ chụp: 10 phút không gọi được server thì khởi động lại; 0 = tắt
#endif
#ifndef POLL_INTERVAL_MS
#define POLL_INTERVAL_MS (CAMERA_ONLY?1000:2000) // camera-only hỏi lệnh nhanh hơn để chụp ngay khi người nhà bấm
#endif
#ifndef STATE_INTERVAL_MS
#define STATE_INTERVAL_MS (CAMERA_ONLY?5000:3000) // camera-only không là bo điều khiển, gửi trạng thái thưa hơn để bớt chặn hàng request
#endif
#ifndef CAMERA_XCLK_HZ
#define CAMERA_XCLK_HZ 10000000 // 10 MHz thay 20 MHz: bớt nhiễu Wi-Fi và bớt tràn bộ đệm khung (FB-OVF) trên ESP32-CAM
#endif
#ifndef INVALID_AFTER_MISSES
#define INVALID_AFTER_MISSES 6 // chỉ báo "không đo được" sau 6 lần đo hỏng liên tiếp (~0,5 s); 1 = báo ngay như cũ
#endif
#ifndef DISTANCE_DEBUG
#define DISTANCE_DEBUG 0 // 1 = in từng lần đo thô của HC-SR04 (độ rộng xung, hết giờ, ECHO kẹt mức cao) để dò lỗi cảm biến
#endif
#ifndef NO_ECHO_US
#define NO_ECHO_US 19000 // HC-SR04 phổ biến trả xung ~20 ms (~343 cm) khi không nhận được tiếng vọng
#endif
#ifndef NEAR_HOLD_CM
#define NEAR_HOLD_CM 20 // vật sát hơn ~4 cm hoặc che kín cảm biến làm mất tiếng vọng: nếu lần đo trước đã gần thì giữ số gần
#endif
#ifndef NEAR_RELEASE_PULSES
#define NEAR_RELEASE_PULSES 25 // 25 xung ~20 ms liên tiếp (~2 s) = vật gần đã đi, phía trước trống: thôi giữ số gần
#endif
#ifndef NEAR_HOLD_MS
#define NEAR_HOLD_MS 10000 // giữ số gần tối đa 10 s, quá thì coi như cảm biến lỗi
#endif
#ifndef HTTP_CONNECT_MS
#define HTTP_CONNECT_MS 5000 // server qua Cloudflare có lúc mất >2 s mới kết nối; 2,5 s cũ làm hụt nhiều nhịp trạng thái liền nhau
#endif
#ifndef HTTP_READ_MS
#define HTTP_READ_MS 5000
#endif
#ifndef HTTP_IMAGE_MS
#define HTTP_IMAGE_MS 10000
#endif
// chest_cam đầy đủ dùng GPIO1/3 (UART) làm nút nên không thể in log.
#define UART_IS_BUTTONS (APP_ROLE == 1 && !CAMERA_ONLY)
#define LOGF(...) do{if(LOG_SERIAL&&!UART_IS_BUTTONS)Serial.printf(__VA_ARGS__);}while(0)

// Core Arduino-ESP32 3.3.0. Camera LEDC timer0/channel0 được giữ riêng.
#if APP_ROLE == 0
// MOTOR=25 có thể nối LED + 220 Ω thay mô-tơ rung: độ sáng/nhịp đổi theo khoảng cách.
// Mọi chân nằm trên CÙNG MỘT dãy (dãy có VIN/5V, GND, D13…D32, D34, D35): bo ESP32 rộng chỉ chừa
// một cột trống trên breadboard 830. ECHO dùng GPIO35 (chỉ vào, ngắt OK); STOP dùng GPIO12 (nút kéo xuống GND = an toàn lúc khởi động).
constexpr int TRIG=32,ECHO=35,MOTOR=25,PIEZO=SINGLE_BUZZER?-1:26,BUZZER=13,SOS=27,PRIVACY=14,DROP=33,STOP=12,FIND=-1,POT=34,STATUS_LED=2;
const char* ROLE="test";
#elif APP_ROLE == 1 && CAMERA_ONLY
constexpr int TRIG=-1,ECHO=-1,MOTOR=-1,PIEZO=-1,BUZZER=-1,SOS=-1,PRIVACY=-1,DROP=-1,STOP=-1,FIND=-1,POT=-1,STATUS_LED=-1;
constexpr int FLASH_LED=4; // đèn flash trên bo AI Thinker: giữ tắt
const char* ROLE="chest";
#elif APP_ROLE == 1
constexpr int TRIG=13,ECHO=14,MOTOR=15,PIEZO=-1,BUZZER=2,SOS=3,PRIVACY=1,DROP=-1,STOP=-1,FIND=4,POT=-1,STATUS_LED=-1;
const char* ROLE="chest";
#else
constexpr int TRIG=-1,ECHO=-1,MOTOR=-1,PIEZO=-1,BUZZER=13,SOS=27,PRIVACY=-1,DROP=33,STOP=32,FIND=-1,POT=-1,STATUS_LED=2;
const char* ROLE="cane";
#endif

struct Snapshot {
  float distance=-1;
  bool sensorValid=false,periodic=true,dropAlarm=false,sosAlarm=false,cameraReady=false,imuReady=false;
  uint32_t queueDropped=0,uptime=0;
};
Snapshot shared;
portMUX_TYPE stateMux=portMUX_INITIALIZER_UNLOCKED;
QueueHandle_t eventQueue;
QueueHandle_t commandQueue;
Preferences prefs;
struct LocalEvent {char id[64];char kind[12];char message[160];uint32_t epoch;};
struct LocalCommand {uint8_t type;uint32_t value;}; // 1 = tìm gậy, 2 = cảnh báo AI (value = ms còn lại)
Snapshot snapshot(){portENTER_CRITICAL(&stateMux);Snapshot s=shared;portEXIT_CRITICAL(&stateMux);return s;}
void countDropped(){portENTER_CRITICAL(&stateMux);shared.queueDropped++;portEXIT_CRITICAL(&stateMux);}
uint32_t validEpoch(){time_t n=time(nullptr);return n>1700000000 ? (uint32_t)n : 0;}
uint32_t bootNonce;
uint32_t eventSequence=0;
void emitEvent(const char* kind,const char* message){
  LocalEvent e{};
  snprintf(e.id,sizeof(e.id),"%s-%08lx-%08lx",ROLE,(unsigned long)bootNonce,(unsigned long)++eventSequence);
  strlcpy(e.kind,kind,sizeof(e.kind));strlcpy(e.message,message,sizeof(e.message));e.epoch=validEpoch();
  if(xQueueSend(eventQueue,&e,0)!=pdTRUE)countDropped();
}

class Button {
 public:
  int pin;bool raw=true,stable=true,armed=false,fired=true;uint32_t changed=0,downAt=0;
  explicit Button(int p):pin(p){}
  void begin(){if(pin>=0){pinMode(pin,INPUT_PULLUP);raw=stable=digitalRead(pin);}}
  // Trả true một lần khi nút được giữ đủ holdMs (0 = ngay khi nhấn). Gọi đúng một lần mỗi vòng loop.
  bool pressed(uint32_t now,uint32_t holdMs=0){
    if(pin<0)return false;
    bool value=digitalRead(pin);
    if(value!=raw){raw=value;changed=now;}
    if(now-changed>=40 && stable!=raw){stable=raw;if(!stable){downAt=now;fired=!armed;armed=false;}}
    if(stable)armed=true; // phải thả nút ít nhất một lần sau khởi động
    if(!stable&&!fired&&now-downAt>=holdMs){fired=true;return true;}
    return false;
  }
};
Button sosButton(SOS),privacyButton(PRIVACY),dropButton(DROP),stopButton(STOP),findButton(FIND);
bool localPrivacy=true;
uint32_t sosUntil=0,dropUntil=0,findUntil=0,roadUntil=0;
uint32_t privacyFeedbackUntil=0;
bool activeUntil(uint32_t deadline,uint32_t now){return deadline!=0&&(int32_t)(deadline-now)>0;}

void pwmSetup(){
  if(MOTOR>=0){
    ledc_timer_config_t timer{};timer.speed_mode=LEDC_LOW_SPEED_MODE;timer.duty_resolution=LEDC_TIMER_8_BIT;
    timer.timer_num=LEDC_TIMER_1;timer.freq_hz=200;timer.clk_cfg=LEDC_AUTO_CLK;ledc_timer_config(&timer);
    ledc_channel_config_t channel{};channel.gpio_num=MOTOR;channel.speed_mode=LEDC_LOW_SPEED_MODE;
    channel.channel=LEDC_CHANNEL_2;channel.intr_type=LEDC_INTR_DISABLE;channel.timer_sel=LEDC_TIMER_1;channel.duty=0;ledc_channel_config(&channel);
  }
  if(PIEZO>=0){
    ledc_timer_config_t timer{};timer.speed_mode=LEDC_LOW_SPEED_MODE;timer.duty_resolution=LEDC_TIMER_8_BIT;
    timer.timer_num=LEDC_TIMER_2;timer.freq_hz=2200;timer.clk_cfg=LEDC_AUTO_CLK;ledc_timer_config(&timer);
    ledc_channel_config_t channel{};channel.gpio_num=PIEZO;channel.speed_mode=LEDC_LOW_SPEED_MODE;
    channel.channel=LEDC_CHANNEL_4;channel.intr_type=LEDC_INTR_DISABLE;channel.timer_sel=LEDC_TIMER_2;channel.duty=0;ledc_channel_config(&channel);
  }
}
void buzzer(bool on){if(BUZZER>=0)digitalWrite(BUZZER,(on!=(bool)BUZZER_ACTIVE_LOW)?HIGH:LOW);}
void motorDuty(uint8_t duty){if(MOTOR>=0){ledc_set_duty(LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_2,duty);ledc_update_duty(LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_2);}}
void piezo(bool on){if(PIEZO>=0){ledc_set_duty(LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_4,on?128:0);ledc_update_duty(LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_4);}}

volatile uint32_t echoRise=0,echoWidth=0;
volatile bool echoDone=false,echoListening=false;
portMUX_TYPE echoMux=portMUX_INITIALIZER_UNLOCKED;
void ARDUINO_ISR_ATTR echoISR(){
  bool high=digitalRead(ECHO);uint32_t now=micros();
  portENTER_CRITICAL_ISR(&echoMux);
  if(echoListening){if(high)echoRise=now;else if(echoRise){echoWidth=now-echoRise;echoDone=true;echoListening=false;}}
  portEXIT_CRITICAL_ISR(&echoMux);
}
float readings[3]={-1,-1,-1};int readingIndex=0,readingCount=0;
uint32_t lastMeasure=0,triggerAt=0;bool waitingEcho=false;
// Số lần đo hỏng liên tiếp: một lần mất echo/nhiễu lẻ tẻ không làm mất số đo trên còi, rung và dashboard.
uint8_t missCount=0;
// Lần đo thật hợp lệ gần nhất (trước lọc trung vị), để nhận ra vật quá sát làm mất tiếng vọng.
float lastGood=-1;uint32_t lastGoodAt=0;uint8_t noEchoRun=0;
void publishDistance(float value){
  bool valid=value>=2&&value<=400;
  // Mất tiếng vọng ngay sau khi đo được vật gần = vật quá sát/che cảm biến: báo gần, không nhảy ra xa hay "không đo được".
  if(!valid&&lastGood>0&&lastGood<NEAR_HOLD_CM&&millis()-lastGoodAt<NEAR_HOLD_MS){value=lastGood;valid=true;}
  else if(valid){lastGood=value;lastGoodAt=millis();}
  if(valid){readings[readingIndex]=value;readingIndex=(readingIndex+1)%3;readingCount=min(readingCount+1,3);float sorted[3];for(int i=0;i<readingCount;i++)sorted[i]=readings[i];for(int i=0;i<readingCount;i++)for(int j=i+1;j<readingCount;j++)if(sorted[j]<sorted[i]){float t=sorted[i];sorted[i]=sorted[j];sorted[j]=t;}value=sorted[readingCount/2];}
  else{
    if(missCount<255)missCount++;
    // Chưa đủ số lần hỏng liên tiếp: giữ nguyên số đo hợp lệ gần nhất.
    if(missCount<INVALID_AFTER_MISSES)return;
    readingCount=0;readingIndex=0;lastGood=-1;
  }
  if(valid)missCount=0;
  portENTER_CRITICAL(&stateMux);shared.distance=valid?value:-1;shared.sensorValid=valid;portEXIT_CRITICAL(&stateMux);
}
void distanceTick(uint32_t now){
  if(TRIG<0)return;
#if APP_ROLE == 0 && TEST_DISTANCE_SIMULATION
  if(now-lastMeasure>=80){lastMeasure=now;publishDistance(5+analogRead(POT)*(195.0f/4095.0f));}
#else
  if(waitingEcho){
    portENTER_CRITICAL(&echoMux);bool done=echoDone;uint32_t width=echoWidth;portEXIT_CRITICAL(&echoMux);
    if(done){waitingEcho=false;if(DISTANCE_DEBUG)LOGF("[raw] %lu us -> %.1f cm\n",(unsigned long)width,width*.0343f/2.0f);
      // Xung ~20 ms = không có tiếng vọng: xa ngoài tầm (giữ như số đo xa), trừ khi vừa đo được vật gần (publishDistance giữ số gần).
      // Vật gần lẫn tay nghiêng hay xen vài xung 20 ms; nhiều xung liền nhau thì đúng là phía trước đã trống.
      if(width>=NO_ECHO_US){if(noEchoRun<255)noEchoRun++;}else noEchoRun=0;
      bool noEcho=width>=NO_ECHO_US&&noEchoRun<NEAR_RELEASE_PULSES&&lastGood>0&&lastGood<NEAR_HOLD_CM;
      publishDistance(noEcho?-1:width*.0343f/2.0f);}
    else if((uint32_t)(micros()-triggerAt)>30000){
      waitingEcho=false;portENTER_CRITICAL(&echoMux);bool rose=echoRise!=0;echoListening=false;portEXIT_CRITICAL(&echoMux);
      if(DISTANCE_DEBUG)LOGF("[raw] het gio 30ms (%s)\n",rose?"ECHO len nhung khong xuong":"khong thay ECHO len");
      publishDistance(-1);
    }
  }
  if(!waitingEcho&&now-lastMeasure>=80){
    lastMeasure=now;
    if(digitalRead(ECHO)){if(DISTANCE_DEBUG)LOGF("[raw] ECHO van HIGH truoc khi phat\n");publishDistance(-1);return;}
    portENTER_CRITICAL(&echoMux);echoRise=0;echoWidth=0;echoDone=false;echoListening=true;portEXIT_CRITICAL(&echoMux);
    triggerAt=micros();waitingEcho=true;digitalWrite(TRIG,HIGH);delayMicroseconds(12);digitalWrite(TRIG,LOW);
  }
#endif
}

#if APP_ROLE == 2
bool imuReady=false,wireStarted=false;uint32_t lastImu=0,lastImuRetry=0,freefallSince=0,phaseAt=0,stillSince=0;int dropPhase=0;
bool writeMpu(uint8_t reg,uint8_t value){Wire.beginTransmission(0x68);Wire.write(reg);Wire.write(value);return Wire.endTransmission()==0;}
bool startImu(){
#if ENABLE_IMU
  if(!wireStarted){Wire.begin(21,22);Wire.setTimeOut(10);wireStarted=true;}
  Wire.beginTransmission(0x68);Wire.write(0x75);if(Wire.endTransmission(false)!=0)return false;
  if(Wire.requestFrom(0x68,1)!=1||Wire.read()!=0x68)return false;
  return writeMpu(0x6B,0)&&writeMpu(0x1C,0x10)&&writeMpu(0x1B,0x08)&&writeMpu(0x1A,3);
#else
  return false;
#endif
}
void imuTick(uint32_t now){
#if ENABLE_IMU
  // Lỗi I2C thoáng qua (dây lỏng, nhiễu) không tắt phát hiện rơi vĩnh viễn: thử lại mỗi 10 s.
  if(!imuReady&&now-lastImuRetry>=10000){
    lastImuRetry=now;imuReady=startImu();dropPhase=0;freefallSince=0;
    portENTER_CRITICAL(&stateMux);shared.imuReady=imuReady;portEXIT_CRITICAL(&stateMux);
  }
#endif
  if(!imuReady||now-lastImu<20)return;lastImu=now;
  Wire.beginTransmission(0x68);Wire.write(0x3B);
  if(Wire.endTransmission(false)!=0||Wire.requestFrom(0x68,14)!=14){imuReady=false;portENTER_CRITICAL(&stateMux);shared.imuReady=false;portEXIT_CRITICAL(&stateMux);return;}
  int16_t v[7];for(int i=0;i<7;i++){uint16_t hi=Wire.read(),lo=Wire.read();v[i]=(int16_t)((hi<<8)|lo);}
  float a=sqrtf((float)v[0]*v[0]+(float)v[1]*v[1]+(float)v[2]*v[2])/4096.0f;
  float g=sqrtf((float)v[4]*v[4]+(float)v[5]*v[5]+(float)v[6]*v[6])/65.5f;
  if(dropPhase==0){if(a<.55f){if(!freefallSince)freefallSince=now;if(now-freefallSince>=80){dropPhase=1;phaseAt=now;}}else freefallSince=0;}
  else if(dropPhase==1){if(a>2.5f){dropPhase=2;phaseAt=now;stillSince=0;}else if(now-phaseAt>800){dropPhase=0;freefallSince=0;}}
  else if(dropPhase==2){
    if(fabsf(a-1)<.18f&&g<35){if(!stillSince)stillSince=now;if(now-stillSince>=1000){if(!activeUntil(dropUntil,now)){dropUntil=now+60000;emitEvent("drop","MPU6050: freefall + impact + stillness (experimental).");}dropPhase=0;freefallSince=0;}}
    else stillSince=0;
    if(now-phaseAt>4000){dropPhase=0;freefallSince=0;}
  }
}
#endif

bool cameraStart(){
#if APP_ROLE == 1
  camera_config_t c{};
  c.ledc_channel=LEDC_CHANNEL_0;c.ledc_timer=LEDC_TIMER_0;
  c.pin_d0=5;c.pin_d1=18;c.pin_d2=19;c.pin_d3=21;c.pin_d4=36;c.pin_d5=39;c.pin_d6=34;c.pin_d7=35;
  c.pin_xclk=0;c.pin_pclk=22;c.pin_vsync=25;c.pin_href=23;c.pin_sccb_sda=26;c.pin_sccb_scl=27;c.pin_pwdn=32;c.pin_reset=-1;
  c.xclk_freq_hz=CAMERA_XCLK_HZ;c.pixel_format=PIXFORMAT_JPEG;
  // Bo không có PSRAM vẫn chụp được ở QVGA trong DRAM (từ smart_cane) thay vì tắt camera hẳn.
  bool psram=psramFound();
  c.frame_size=psram?FRAMESIZE_VGA:FRAMESIZE_QVGA;c.jpeg_quality=14;c.fb_count=1;
  c.fb_location=psram?CAMERA_FB_IN_PSRAM:CAMERA_FB_IN_DRAM;c.grab_mode=CAMERA_GRAB_WHEN_EMPTY;
  if(esp_camera_init(&c)!=ESP_OK)return false; // init lỗi tự giải phóng phần đã cấp phát; có thể gọi lại
  sensor_t* sensor=esp_camera_sensor_get();
  if(sensor){sensor->set_vflip(sensor,CAMERA_VFLIP);sensor->set_hmirror(sensor,CAMERA_HMIRROR);}
  return true;
#else
  return false;
#endif
}

// Lần cuối server trả lời (bất kỳ mã HTTP nào), để phát hiện Wi-Fi/TCP kẹt khi vẫn báo đã kết nối.
uint32_t lastServerOk=0;
// HTTP chỉ ở tác vụ mạng. Vòng đo và cảnh báo cục bộ không đợi máy chủ.
int requestHttp(const String& method,const String& route,const uint8_t* bytes,size_t length,String& response,const char* type="application/json",uint32_t captured=0){
  if(WiFi.status()!=WL_CONNECTED)return -1;
  String url=String(API_BASE)+route;
  WiFiClient plain;WiFiClientSecure secure;HTTPClient http;
  bool ok=false;
  if(url.startsWith("https://")){if(strlen(ROOT_CA)<100)return -2;secure.setCACert(ROOT_CA);ok=http.begin(secure,url);}
  else if(url.startsWith("http://")&&ALLOW_HTTP_LAN)ok=http.begin(plain,url);
  if(!ok)return -3;
  http.setConnectTimeout(HTTP_CONNECT_MS);http.setTimeout(strcmp(type,"image/jpeg")==0?HTTP_IMAGE_MS:HTTP_READ_MS);
  http.addHeader("Authorization",String("Bearer ")+DEVICE_TOKEN);
  http.addHeader("Content-Type",type);
  if(captured)http.addHeader("X-Captured-At",String(captured));
  int status=method=="GET"?http.GET():http.sendRequest(method.c_str(),const_cast<uint8_t*>(bytes),length);
  if(status>0){int len=http.getSize();if(len<0||len<=16384)response=http.getString();}
  http.end();if(status>0)lastServerOk=millis();return status;
}
int jsonRequest(const String& method,const String& route,JsonDocument& doc,String& response){String payload;serializeJson(doc,payload);return requestHttp(method,route,(const uint8_t*)payload.c_str(),payload.length(),response);}
void ack(const char* id,const char* result){JsonDocument doc;doc["result"]=result;String response;jsonRequest("POST",String("/api/v1/commands/")+id+"/ack",doc,response);}

constexpr int PENDING_MAX=16;
LocalEvent pending[PENDING_MAX];int pendingCount=0;
void savePending(){
  JsonDocument doc;JsonArray array=doc.to<JsonArray>();
  for(int i=0;i<pendingCount;i++){JsonObject o=array.add<JsonObject>();o["id"]=pending[i].id;o["kind"]=pending[i].kind;o["message"]=pending[i].message;o["epoch"]=pending[i].epoch;}
  String value;serializeJson(doc,value);prefs.putString("pending",value);
}
void loadPending(){
  JsonDocument doc;if(deserializeJson(doc,prefs.getString("pending","[]")))return;
  for(JsonObject o:doc.as<JsonArray>()){if(pendingCount>=PENDING_MAX)break;auto& e=pending[pendingCount++];strlcpy(e.id,o["id"]|"",sizeof(e.id));strlcpy(e.kind,o["kind"]|"test",sizeof(e.kind));strlcpy(e.message,o["message"]|"",sizeof(e.message));e.epoch=o["epoch"]|0;}
}
bool addPending(LocalEvent& event){
  if(pendingCount>=PENDING_MAX){
    // Ưu tiên SOS khi đầy; loại sự kiện không phải SOS cũ nhất nếu có.
    int removable=-1;if(strcmp(event.kind,"sos")==0)for(int i=0;i<pendingCount;i++)if(strcmp(pending[i].kind,"sos")!=0){removable=i;break;}
    countDropped();if(removable<0)return false;
    for(int i=removable;i<pendingCount-1;i++)pending[i]=pending[i+1];pendingCount--;
  }
  pending[pendingCount++]=event;return true;
}

void sendState(){
  Snapshot s=snapshot();JsonDocument doc;
  if(s.sensorValid)doc["distance_cm"]=s.distance;else doc["distance_cm"]=nullptr;
  doc["sensor_valid"]=s.sensorValid;doc["periodic_enabled"]=s.periodic;
  doc["drop_alarm"]=s.dropAlarm;doc["sos_alarm"]=s.sosAlarm;doc["camera_ready"]=s.cameraReady;doc["imu_ready"]=s.imuReady;
  doc["queue_dropped"]=s.queueDropped;doc["uptime_s"]=s.uptime;
  doc["simulated"]=(APP_ROLE==0&&TEST_DISTANCE_SIMULATION);
  String response;int status=jsonRequest("POST","/api/v1/state",doc,response);
  // Chỉ in khi mã trả về đổi, để Serial Monitor không bị tràn.
  static int lastStatus=0;
  if(status!=lastStatus){lastStatus=status;LOGF("[state] HTTP %d%s\n",status,status==401?" (sai DEVICE_TOKEN)":status==403?" (sai role/PROJECT_MODE)":status<0?" (chua ket noi duoc API_BASE)":"");}
}
void pollCommands(){
  String response;int code=requestHttp("GET","/api/v1/commands",nullptr,0,response);if(code!=200)return;
  JsonDocument doc;if(deserializeJson(doc,response))return;
  // Cảnh báo AI cho người đeo (server chỉ gửi khi WEARER_AI_ALERT=1). 0 = hủy cảnh báo đang chạy.
  LocalCommand road{2,min<uint32_t>(doc["road_alert_ms"]|0u,20000u)};xQueueSend(commandQueue,&road,0);
  for(JsonObject command:doc["commands"].as<JsonArray>()){
    const char* id=command["id"]|"";const char* kind=command["kind"]|"";
    if(strcmp(kind,"find")==0){
      // RAM chống chạy lặp khi ACK bị mất. TTL server chặn lệnh cũ.
      static String lastFind;
      if(lastFind!=id){LocalCommand cmd{1,0};if(xQueueSend(commandQueue,&cmd,0)!=pdTRUE)continue;lastFind=id;}
      ack(id,"done");
    }
#if APP_ROLE == 1
    else if(strcmp(kind,"capture")==0){
      // Mọi ảnh không phải SOS (định kỳ, người nhà yêu cầu) đều cần quyền riêng tư cục bộ.
      bool periodic=strcmp(command["reason"]|"","sos")!=0;
      if(periodic&&!snapshot().periodic){ack(id,"privacy_off");continue;}
      if(!snapshot().cameraReady){ack(id,"camera_unavailable");continue;}
      // Bỏ frame cũ đang nằm trong bộ đệm, chụp frame kế tiếp cho yêu cầu hiện tại.
      camera_fb_t* old=esp_camera_fb_get();if(old)esp_camera_fb_return(old);
      camera_fb_t* frame=esp_camera_fb_get();if(!frame)continue;
      uint32_t captured=validEpoch();
      if(periodic&&!snapshot().periodic){esp_camera_fb_return(frame);ack(id,"privacy_off");continue;}
      const char* eid=command["event_id"]|"";String result;
      uint32_t sendStart=millis();int status=requestHttp("POST",String("/api/v1/events/")+eid+"/image",frame->buf,frame->len,result,"image/jpeg",captured);
      // In thời gian gửi và RSSI: gửi chậm + RSSI dưới khoảng -75 dBm là do sóng Wi-Fi yếu.
      LOGF("[camera] %s %u bytes -> HTTP %d (%lu ms, RSSI %d dBm)\n",command["reason"]|"?",(unsigned)frame->len,status,(unsigned long)(millis()-sendStart),(int)WiFi.RSSI());
      esp_camera_fb_return(frame);
      if(status>=200&&status<300)ack(id,"done");
      else if(status==409)ack(id,"privacy_off");
      // Lỗi tạm thời: không ACK để server giao lại. Ảnh đã nhận không bị ghi đè.
    }
#endif
  }
}
void networkTask(void*){
  loadPending();
  uint32_t reconnectAt=0,stateAt=0,pollAt=0,retryAt=0;
  [[maybe_unused]] uint32_t findAt=0,findRetryAt=0; // chỉ chest_cam dùng
  bool savedPrivacy=snapshot().periodic;[[maybe_unused]] bool findRequestPending=false;
  // Nhà có nhiều điểm phát cùng tên (mesh): mặc định ESP32 vào điểm phát tìm thấy đầu tiên, có thể rất yếu.
  // Quét hết các kênh và chọn điểm phát mạnh nhất.
  WiFi.mode(WIFI_STA);WiFi.setSleep(false);
  WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);WiFi.setSortMethod(WIFI_CONNECT_AP_BY_SIGNAL);
  WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
  // SNTP dùng IP, không dùng tên miền: core 3.3.x có lỗi hostByName() xóa cache DNS không khóa TCPIP,
  // làm callback DNS đang chờ của SNTP chạy sai luồng và assert "Required to lock TCPIP core" (crash ngay sau khi có Wi-Fi).
  configTime(0,0,"162.159.200.1","216.239.35.0"); // time.cloudflare.com, time.google.com
#if NETWORK_WDT_S
  // Watchdog cho tác vụ mạng: mỗi vòng phải quay lại trong NETWORK_WDT_S giây, nếu không chip tự khởi động lại.
  esp_task_wdt_config_t wdt{};wdt.timeout_ms=NETWORK_WDT_S*1000;wdt.idle_core_mask=1;wdt.trigger_panic=true;
  if(esp_task_wdt_reconfigure(&wdt)!=ESP_OK)esp_task_wdt_init(&wdt);
  esp_task_wdt_add(nullptr);
#endif
  for(;;){
#if NETWORK_WDT_S
    esp_task_wdt_reset();
#endif
    LocalEvent e;bool dirty=false;while(xQueueReceive(eventQueue,&e,0)==pdTRUE){
#if APP_ROLE == 1
      // Tìm gậy là lệnh tạm thời, không lưu ngoại tuyến để tránh còi chạy muộn.
      if(strcmp(e.kind,"find")==0){findRequestPending=true;findAt=millis();}
      else if(addPending(e))dirty=true;
#else
      if(addPending(e))dirty=true;
#endif
    }
    if(dirty)savePending();
    bool periodic=snapshot().periodic;if(periodic!=savedPrivacy){prefs.putBool("periodic",periodic);savedPrivacy=periodic;}
    uint32_t now=millis();
#if OFFLINE_RESTART_MIN
    // Sự kiện chờ gửi đã lưu trong prefs nên khởi động lại không mất SOS.
    if(now-lastServerOk>OFFLINE_RESTART_MIN*60000UL){LOGF("[wdt] %d phut khong goi duoc server, khoi dong lai\n",(int)OFFLINE_RESTART_MIN);delay(200);ESP.restart();}
#endif
#if APP_ROLE == 1
    if(findRequestPending&&now-findAt>20000)findRequestPending=false;
    // Camera lỗi lúc khởi động (cáp, nguồn yếu) được thử lại mỗi 15 s thay vì tắt đến khi reset.
    static uint32_t cameraRetryAt=0;
    if(!snapshot().cameraReady&&now-cameraRetryAt>=15000){
      cameraRetryAt=now;bool ready=cameraStart();
      LOGF("[camera] khoi dong lai: %s\n",ready?"OK":"LOI (kiem tra cap camera, nguon 5V)");
      portENTER_CRITICAL(&stateMux);shared.cameraReady=ready;portEXIT_CRITICAL(&stateMux);
    }
#endif
    static bool wasOnline=false;
    if(WiFi.status()!=WL_CONNECTED){
      if(wasOnline){wasOnline=false;LOGF("[wifi] mat ket noi\n");}
      if(now-reconnectAt>5000){reconnectAt=now;WiFi.reconnect();LOGF("[wifi] dang ket noi '%s'...\n",WIFI_SSID);}
      vTaskDelay(pdMS_TO_TICKS(50));continue;
    }
    if(!wasOnline){wasOnline=true;LOGF("[wifi] OK, IP %s, AP %s, RSSI %d dBm, API_BASE %s\n",WiFi.localIP().toString().c_str(),WiFi.BSSIDstr().c_str(),(int)WiFi.RSSI(),API_BASE);}
#if APP_ROLE == 1
    if(findRequestPending&&now-findRetryAt>=1000){
      findRetryAt=now;String response;
      int status=requestHttp("POST","/api/v1/find-cane",(const uint8_t*)"",0,response);
      if((status>=200&&status<300)||status==401||status==403)findRequestPending=false;
    }
#endif
    if(pendingCount&&now-retryAt>1500){
      retryAt=now;
      int next=0;
      for(int i=0;i<pendingCount;i++)if(strcmp(pending[i].kind,"sos")==0){next=i;break;}
      const auto& event=pending[next];JsonDocument doc;
      doc["event_id"]=event.id;doc["kind"]=event.kind;doc["message"]=event.message;doc["clock_synced"]=event.epoch>0;
      if(event.epoch)doc["occurred_at"]=event.epoch;else doc["occurred_at"]=nullptr;
      String response;int status=jsonRequest("POST","/api/v1/events",doc,response);
      LOGF("[event] %s %s -> HTTP %d\n",event.kind,event.id,status);
      bool isSos=strcmp(event.kind,"sos")==0;
      // 400/422 = nội dung sai, gửi lại cũng không được: bỏ sự kiện thường, KHÔNG bỏ SOS.
      bool rejected=!isSos&&(status==400||status==422);
      if((status>=200&&status<300)||status==409||rejected){
        if(rejected)countDropped();
        for(int i=next+1;i<pendingCount;i++)pending[i-1]=pending[i];pendingCount--;savePending();
      }
      else if(status==400||status==401||status==403||status==422){
        // Lỗi cấu hình (token/PROJECT_MODE) hoặc SOS bị từ chối: giữ sự kiện nhưng chuyển xuống cuối,
        // để một sự kiện bị từ chối không chặn mãi các sự kiện phía sau.
        LocalEvent held=pending[next];for(int i=next+1;i<pendingCount;i++)pending[i-1]=pending[i];pending[pendingCount-1]=held;
      }
      // Lỗi mạng/5xx: giữ nguyên thứ tự và thử lại sau 1,5 s.
    }
    // Hỏi lệnh trước gửi trạng thái: lệnh chụp không phải xếp sau một request trạng thái chậm.
    if(now-pollAt>=POLL_INTERVAL_MS){pollAt=now;pollCommands();}
    if(now-stateAt>=STATE_INTERVAL_MS){stateAt=now;sendState();}
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

void setup(){
#if !UART_IS_BUTTONS
  Serial.begin(115200);
#endif
  LOGF("\n[boot] Dong Hanh role=%s%s\n",ROLE,CAMERA_ONLY?" (camera only)":"");
  // 1=bat nguon, 3=ESP.restart, 4=panic, 6=watchdog task, 9=sut ap: biết lần trước vì sao bo khởi động lại.
  LOGF("[boot] ly do reset truoc: %d\n",(int)esp_reset_reason());
  // In số chân thật đang dùng để đối chiếu với dây trên breadboard (biết ngay có nạp nhầm bản cũ không).
  if(TRIG>=0||SOS>=0)LOGF("[boot] chan: TRIG=%d ECHO=%d | SOS=%d (giu %ums) PRIVACY=%d DROP=%d STOP=%d | LED=%d COI1=%d COI2=%d\n",TRIG,ECHO,SOS,(unsigned)SOS_HOLD_MS,PRIVACY,DROP,STOP,MOTOR,BUZZER,PIEZO);
  bootNonce=esp_random();
  if(BUZZER>=0){pinMode(BUZZER,OUTPUT);buzzer(false);}
#if APP_ROLE == 1 && CAMERA_ONLY
  pinMode(FLASH_LED,OUTPUT);digitalWrite(FLASH_LED,LOW);
#endif
  if(MOTOR>=0){pinMode(MOTOR,OUTPUT);digitalWrite(MOTOR,LOW);}
  if(STATUS_LED>=0){pinMode(STATUS_LED,OUTPUT);digitalWrite(STATUS_LED,LOW);}
  eventQueue=xQueueCreate(16,sizeof(LocalEvent));commandQueue=xQueueCreate(4,sizeof(LocalCommand));
  if(!eventQueue||!commandQueue){LOGF("[boot] het RAM\n");while(true){buzzer(true);delay(100);buzzer(false);delay(900);}}
  prefs.begin(ROLE,false);localPrivacy=prefs.getBool("periodic",true);shared.periodic=localPrivacy;
  shared.cameraReady=cameraStart();pwmSetup();
#if APP_ROLE == 1
  LOGF("[camera] %s, PSRAM %s\n",shared.cameraReady?"OK":"LOI",psramFound()?"co":"khong");
#endif
#if UART_IS_BUTTONS
  // GPIO1/3 thành nút. UART adapter phải tháo. Core Debug Level = None.
  Serial.end();
#endif
  sosButton.begin();privacyButton.begin();dropButton.begin();stopButton.begin();findButton.begin();
  if(TRIG>=0){pinMode(TRIG,OUTPUT);digitalWrite(TRIG,LOW);pinMode(ECHO,INPUT);attachInterrupt(digitalPinToInterrupt(ECHO),echoISR,CHANGE);}
#if APP_ROLE == 0 && TEST_DISTANCE_SIMULATION
  analogReadResolution(12);pinMode(POT,INPUT);
#endif
#if APP_ROLE == 2
  imuReady=startImu();shared.imuReady=imuReady;LOGF("[imu] MPU6050 %s\n",imuReady?"OK":"khong thay");
#endif
  xTaskCreatePinnedToCore(networkTask,"network",14336,nullptr,1,nullptr,0);
}
bool obstacleActive=false; // trạng thái có trễ của vùng cảnh báo xa
void loop(){
  uint32_t now=millis();
  if(sosButton.pressed(now,SOS_HOLD_MS)){
    // Giữ lần nữa khi đang báo động = tắt còi tại chỗ; SOS đã gửi vẫn giữ trên máy chủ.
    if(activeUntil(sosUntil,now)){sosUntil=0;LOGF("[nut] SOS: tat coi tai cho\n");}
    else{sosUntil=now+60000;emitEvent("sos","Physical SOS button held.");LOGF("[nut] SOS: gui su kien\n");}
  }
  if(privacyButton.pressed(now)){localPrivacy=!localPrivacy;privacyFeedbackUntil=now+550;emitEvent("privacy",localPrivacy?"Periodic images enabled locally.":"Periodic images disabled locally.");LOGF("[nut] PRIVACY: anh dinh ky %s\n",localPrivacy?"BAT":"TAT");}
  if(findButton.pressed(now)){emitEvent("find","Physical find-cane button pressed.");LOGF("[nut] FIND\n");}
  if(dropButton.pressed(now)){dropUntil=now+60000;emitEvent("drop","SIMULATED drop: test button pressed.");LOGF("[nut] DROP: coi 60 s\n");}
  if(stopButton.pressed(now)){sosUntil=0;dropUntil=0;findUntil=0;roadUntil=0;LOGF("[nut] STOP: tat coi\n");}
  LocalCommand cmd;while(xQueueReceive(commandQueue,&cmd,0)==pdTRUE){
    if(cmd.type==1)findUntil=now+30000;
    else if(cmd.type==2)roadUntil=cmd.value?now+cmd.value:0;
  }
  distanceTick(now);
#if APP_ROLE == 2
  imuTick(now);
#endif
  bool sosActive=activeUntil(sosUntil,now),dropActive=activeUntil(dropUntil,now),findActive=activeUntil(findUntil,now);
  bool alarm=sosActive||dropActive||findActive;
  Snapshot s=snapshot();
  // Cảnh báo báo động (còi). SOS: nhịp dồn; rơi/tìm gậy: hai tiếng bíp mỗi giây.
  bool alarmBeep=sosActive?now%450<300:(now%1000<170||((now%1000)>300&&(now%1000)<470));
  // Vật cản: nhịp nhanh dần khi lại gần. Có trễ ở ngưỡng xa để không chập chờn ở biên.
  if(TRIG<0||!s.sensorValid)obstacleActive=false;
  else if(s.distance<ALERT_FAR_CM)obstacleActive=true;
  else if(s.distance>=ALERT_FAR_CM+ALERT_HYSTERESIS_CM)obstacleActive=false;
  float closeness=obstacleActive?constrain((ALERT_FAR_CM-s.distance)/(ALERT_FAR_CM-ALERT_NEAR_CM),0.0f,1.0f):0;
  bool obstacleBeep=obstacleActive&&now%(uint32_t)(900-700*closeness)<100;
  uint8_t obstacleDuty=obstacleBeep?(uint8_t)(150+105*closeness):0;
  bool danger=obstacleActive&&s.distance<=ALERT_NEAR_CM;
  bool feedback=activeUntil(privacyFeedbackUntil,now),feedbackBeep=false;
  if(feedback){uint32_t elapsed=550-(privacyFeedbackUntil-now);feedbackBeep=localPrivacy?(elapsed<100||(elapsed>=250&&elapsed<350)):elapsed<350;}
  uint32_t roadPhase=now%2000;
  bool road=activeUntil(roadUntil,now),roadBeep=road&&(roadPhase<120||(roadPhase>=280&&roadPhase<400));
  // Ba xung ngắn mỗi 5 giây = mất phép đo, không phải đường trống.
  uint32_t phase=now%5000;
  bool invalid=TRIG>=0&&!s.sensorValid,invalidBeep=invalid&&(phase<50||(phase>=150&&phase<200)||(phase>=300&&phase<350));
  // Rung: cảnh báo vật cản luôn được ưu tiên (là tín hiệu dẫn đường), kể cả khi đang SOS/tìm gậy.
  uint8_t duty=obstacleActive?obstacleDuty:sosActive?(alarmBeep?255:0):feedback?(feedbackBeep?180:0):road?(roadBeep?180:0):invalidBeep?150:0;
  motorDuty(duty);
  if(PIEZO>=0){
    // Bo thử có hai nguồn âm: còi cho báo động, piezo cho dẫn đường; hai luồng không che nhau.
    buzzer(alarm&&alarmBeep);
    piezo(obstacleActive?obstacleBeep:feedback?feedbackBeep:road?roadBeep:invalidBeep);
  } else {
    // Một còi: vật cản rất gần > báo động > phản hồi nút > vật cản > AI > mất phép đo.
    bool beep=danger?obstacleBeep:alarm?alarmBeep:feedback?feedbackBeep:obstacleActive?obstacleBeep:road?roadBeep:invalidBeep;
    buzzer(beep);
  }
  static uint32_t lastLog=0;
  if(TRIG>=0&&now-lastLog>=1000){lastLog=now;if(s.sensorValid)LOGF("[do] %.0f cm\n",s.distance);else LOGF("[do] khong do duoc (kiem tra TRIG/ECHO, chia ap)\n");}
  if(STATUS_LED>=0)digitalWrite(STATUS_LED,(WiFi.status()==WL_CONNECTED)?HIGH:now%1000<100);
  portENTER_CRITICAL(&stateMux);shared.periodic=localPrivacy;shared.sosAlarm=sosActive;shared.dropAlarm=dropActive;shared.uptime=now/1000;portEXIT_CRITICAL(&stateMux);
  delay(5);
}
