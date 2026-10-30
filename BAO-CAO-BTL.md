# BÁO CÁO BÀI TẬP LỚN / ĐỒ ÁN MÔN HỌC

**ĐỀ TÀI:**  
### HỆ THỐNG HỖ TRỢ NGƯỜI KHIẾM THỊ DI CHUYỂN AN TOÀN "ĐỒNG HÀNH"
*(Smart Assistive IoT System for the Visually Impaired)*

---

## MỤC LỤC
1. [TỔNG QUAN VÀ TÍNH CẤP THIẾT](#1-tổng-quan-và-tính-cấp-thiết)
2. [KIẾN TRÚC HỆ THỐNG IOT CHUẨN MỰC](#2-kiến-trúc-hệ-thống-iot-chuẩn-mực)
3. [THIẾT KẾ PHẦN CỨNG (HARDWARE DESIGN)](#3-thiết-kế-phần-cứng-hardware-design)
4. [GIAO THỨC TRUYỀN THÔNG VÀ BẢO MẬT (NETWORKING)](#4-giao-thức-truyền-thông-và-bảo-mật-networking)
5. [HỆ THỐNG PHẦN MỀM VÀ CLOUD (BACKEND & DASHBOARD)](#5-hệ-thống-phần-mềm-và-cloud-backend--dashboard)
6. [TÍCH HỢP TRÍ TUỆ NHÂN TẠO (AI INTEGRATION)](#6-tích-hợp-trí-tuệ-nhân-tạo-ai-integration)
7. [KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN](#7-kết-luận-và-hướng-phát-triển)

---

## 1. TỔNG QUAN VÀ TÍNH CẤP THIẾT

### 1.1. Đặt vấn đề
Người khiếm thị gặp vô vàn rào cản và nguy cơ tai nạn khi tham gia giao thông hoặc sinh hoạt hàng ngày:
* Gậy truyền thống (White Cane) chỉ quét được vật cản ở tầm thấp (mặt đất), hoàn toàn bỏ sót các chướng ngại vật tầm cao ngang ngực/đầu (gương xe tải, cành cây chìa ra, biển quảng cáo, dây điện chùng).
* Khi gặp sự cố nguy hiểm (vấp ngã, lạc đường, tai nạn), người khiếm thị không thể thao tác điện thoại màn hình cảm ứng để gọi cứu trợ kịp thời.
* Người nhà / người giám hộ ở xa luôn ở trong trạng thái lo lắng do thiếu công cụ giám sát lộ trình và tình trạng an toàn theo thời gian thực.

### 1.2. Mục tiêu của đề tài
Xây dựng một hệ sinh thái thiết bị hỗ trợ đeo người (Wearable IoT Assistive Ecosystem) bao gồm:
1. **Khối thiết bị đeo ngực (Chest Unit):** Gồm vi điều khiển trung tâm ESP32 DevKit phát hiện vật cản tầm trung - cao, cảnh báo xúc giác (rung), âm thanh (còi), các nút bấm khẩn cấp SOS; kết hợp cùng **Module camera ESP32-CAM** thu thập hình ảnh quang học phía trước người khiếm thị phục vụ phân tích AI.
2. **Khối gậy thông minh (Cane Unit):** Phát còi định vị tìm gậy hai chiều, tích hợp cảm biến phát hiện rơi ngã.
3. **Mạng truyền thông song công (Dual Communication):** Kết hợp sóng vô tuyến tầm ngắn **ESP-NOW** (an toàn sinh mạng nội bộ, hoạt động 100% không cần Internet) và mạng viễn thông đám mây **RESTful HTTPS** qua Wi-Fi / 4G Hotspot.
4. **Trung tâm giám sát đám mây (Cloud Dashboard PWA):** Dành cho người thân theo dõi vị trí, lịch sử cảnh báo, pin và điều khiển tìm gậy từ xa.
5. **Trí tuệ nhân tạo (Edge/Cloud AI):** Tích hợp thị giác máy tính nhận diện lòng đường, mặt nước, biển báo nguy hiểm.

---

## 2. KIẾN TRÚC HỆ THỐNG IOT CHUẨN MỰC

### 2.1. Phân loại theo thang đo Arshdeep Bahga & Vijay Madisetti
Hệ thống **Đồng Hành** đáp ứng đầy đủ tiêu chí của **Hệ thống IoT Cấp 5 (Level 5 IoT System)**:
* **Hệ thống đa nút (Multiple Nodes):** Gồm các vi điều khiển chuyên trách hoạt động phối hợp: **ESP32 DevKit** (điều phối trung tâm khối ngực), **ESP32-CAM** (thu nhận thị giác máy tính ở ngực) và **ESP32-C3 Super Mini** (định vị và cảnh báo ở gậy).
* **Điều phối cục bộ (Local Coordinator):** Sử dụng giao thức không dây trực tiếp **ESP-NOW** điều phối giữa các nút biên với độ trễ < 5ms mà không cần Router hay Gateway trung gian.
* **Đám mây hóa và Phân tích tập trung (Cloud Analytics & Storage):** Dữ liệu đo đạc (telemetry) được đẩy lên Cloud Server (FastAPI + SQLite), hỗ trợ phân tích AI (SegFormer / Gemini Vision).
* **Ứng dụng điều khiển người dùng:** Web App Dashboard PWA cho phép người thân giám sát và tương tác hai chiều từ bất kỳ đâu trên thế giới.

### 2.2. Sơ đồ khối kiến trúc hệ thống
```
                     +---------------------------------------+
                     |        NGƯỜI THÂN / GIÁM HỘ           |
                     |  (Web Dashboard PWA / Smart Phone)    |
                     +-------------------+-------------------+
                                         | HTTPS (Bearer Token)
                                         v
                     +---------------------------------------+
                     |          CLOUD SERVER (FastAPI)       |
                     |  • Domain: https://iot.chongziapp.id.vn|
                     |  • Nginx Reverse Proxy + Let's Encrypt |
                     |  • SQLite + AI Vision Adapter         |
                     +-------------------+-------------------+
                                         ^
                                         | RESTful HTTPS
                     +-------------------+-------------------+
                     |           NGƯỜI KHIẾM THỊ             |
                     |       (Smartphone 4G Hotspot)         |
                     +---------------------------------------+
                                         ^
                                         | Wi-Fi Hotspot (802.11 b/g/n)
         +-------------------------------+-------------------------------+
         |                                                               |
+--------+------------------------------------+         +------------------------+-------+
|        THIẾT BỊ ĐEO NGỰC (CHEST UNIT)       |         |       THIẾT BỊ GẬY (CANE)      |
| 1. ESP32 DevKit V1 (Bo điều khiển chính):   | ESP-NOW | • ESP32-C3 Super Mini (RISC-V) |
|    • Cảm biến siêu âm HC-SR04 (quét cự ly)  |<------->| • Active Buzzer đa kênh (5,21) |
|    • Motor rung xúc giác + Còi D13          | (Direct)| • Nút bấm dừng còi (GPIO 9)    |
|    • 4 Nút: SOS / Privacy / Stop / Find     | < 5ms   | • Nguồn sạc nhỏ gọn            |
| 2. ESP32-CAM AI Thinker (Module thị giác):  |         |                                |
|    • Camera OV2640 chụp ảnh JPEG gửi AI     |         |                                |
+---------------------------------------------+         +--------------------------------+
```

---

## 3. THIẾT KẾ PHẦN CỨNG (HARDWARE DESIGN)

### 3.1. Danh mục linh kiện phần cứng

| Tên linh kiện | Vai trò trong hệ thống | Giao tiếp / Chân kết nối |
| :--- | :--- | :--- |
| **ESP32 DevKit V1 (30 chân)** | Vi điều khiển điều phối trung tâm khối đeo ngực | Wi-Fi 2.4GHz, ESP-NOW, GPIOs |
| **ESP32-CAM (AI Thinker + OV2640)** | Module camera thị giác gắn ngực chụp ảnh gửi AI | Wi-Fi, Cảm biến ảnh OV2640 2MP |
| **ESP32-C3 Super Mini** | Vi điều khiển khối gậy cầm tay (siêu nhỏ) | RISC-V 160MHz, ESP-NOW, GPIOs |
| **Cảm biến siêu âm HC-SR04** | Đo khoảng cách vật cản phía trước (2 - 400 cm) | D32 (TRIG), D35 (ECHO) |
| **Motor rung DC Mini (Coin Motor)** | Cảnh báo xúc giác phân cấp cho người khiếm thị | D25 (Transistor NPN / Opto) |
| **Active/Passive Buzzer** | Phát âm thanh cảnh báo cự ly gần & báo động SOS | D13 (Áo) và GPIO 5, 21, 3, 4 (Gậy) |
| **Nút nhấn công tắc (4 nút)** | Nút SOS (D27), Privacy (D14), Stop (D12), Find (D33) | Input Pullup |
| **Nguồn cấp di động** | Cấp nguồn 5V ổn định cho ESP32 và cảm biến | Pin sạc dự phòng Mini 5V qua cổng Type-C / MicroUSB |

### 3.2. Sơ đồ nối chân vi điều khiển (Pinout Map)

#### A. Trên ESP32 DevKit V1 (Khối Áo):
* `GPIO 32`: Chân **TRIG** cảm biến HC-SR04 (phát xung siêu âm 10µs).
* `GPIO 35`: Chân **ECHO** cảm biến HC-SR04 (nhận phản xạ xung - Input only).
* `GPIO 25`: Chân điều khiển **Motor Rung** (băm xung PWM tăng dần theo độ gần).
* `GPIO 13`: Chân điều khiển **Buzzer** trên áo (phát bíp cảnh báo cự ly gần và SOS).
* `GPIO 27`: Nút bấm **SOS** (nhấn giữ 1.5s để kích hoạt báo động khẩn cấp).
* `GPIO 14`: Nút bấm **Privacy** (tạm ngắt truyền dữ liệu hình ảnh/vị trí).
* `GPIO 12`: Nút bấm **Stop Alarm** (tắt còi khẩn cấp tại chỗ).
* `GPIO 33`: Nút bấm **Find Cane** (gửi sóng ESP-NOW kích hoạt còi trên gậy).

#### B. Trên ESP32-C3 Super Mini (Khối Gậy):
* `GPIO 5, 21, 3, 4`: Mảng chân xuất xung kích còi **Buzzer** trên gậy (kết nối song song/đa chân để tối đa hóa cường độ âm thanh ngoài đường phố).
* `GPIO 8`: Đèn LED xanh báo trạng thái bo mạch.
* `GPIO 9`: Nút nhấn vật lý BOOT trên bo (dùng làm nút **Tắt Còi** khi người dùng đã tìm thấy gậy).

### 3.3. Tính toán năng lượng (Power Budget)
* Khi ESP32 phát Wi-Fi truyền tin: dòng đỉnh điểm $I_{peak} \approx 250 - 380\text{ mA}$.
* Khi chạy cảm biến và phát ESP-NOW thông thường: $I_{avg} \approx 80 - 120\text{ mA}$.
* **Kết luận chọn nguồn:** Sử dụng pin sạc dự phòng mini chuẩn 5V (dung lượng 2.000 – 5.000 mAh) đảm bảo hệ thống hoạt động liên tục từ 12 đến 24 tiếng mà không gặp hiện tượng sụt áp (Brownout Reset).

---

## 4. GIAO THỨC TRUYỀN THÔNG VÀ BẢO MẬT (NETWORKING)

### 4.1. Cơ chế an toàn song công (Dual Communication Strategy)
1. **Tầng an toàn sinh mạng (Local Safety Layer - ESP-NOW):**
   * Sử dụng chuẩn sóng MAC Layer 2.4 GHz độc quyền của Espressif.
   * Không cần thông qua Access Point (AP), không cần mật khẩu Wi-Fi, không cần IP mạng.
   * Độ trễ truyền tín hiệu cực thấp: **$\le 5\text{ ms}$**.
   * Khi người khiếm thị đi vào vùng mất sóng điện thoại, hết dung lượng 4G, hoặc máy tính server ở nhà bị tắt: **Cảnh báo vật cản, nút SOS, và tính năng bấm tìm gậy vẫn hoạt động 100% bình thường**.

2. **Tầng giám sát viễn thông đám mây (Cloud Telemetry Layer - RESTful HTTPS):**
   * Thiết bị kết nối qua điểm phát sóng di động (4G Hotspot) của điện thoại người đeo.
   * Định kỳ gửi gói tin trạng thái (Telemetry JSON) lên Cloud Server.
   * Người thân ở xa có thể theo dõi vị trí và bấm nút *"Tìm gậy"* từ giao diện web ở bất kỳ đâu trên thế giới.

### 4.2. So sánh lựa chọn giao thức: RESTful HTTP/JSON vs. MQTT

| Tiêu chí | RESTful HTTP/JSON (Hệ thống đang dùng) | MQTT (Broker truyền thống) |
| :--- | :--- | :--- |
| **Kiến trúc** | Client-Server qua giao thức chuẩn Web (Port 443) | Publish-Subscribe qua MQTT Broker (Port 1883/8883) |
| **Tường lửa & Nhà mạng 4G** | Dễ dàng đi qua mọi loại mạng di động (Viettel, Vina, Mobi) không bị chặn cổng | Thường bị chặn ở mạng công cộng, cần cấu hình phức tạp qua WebSocket |
| **Bảo mật xác thực** | Chuẩn **Bearer Token (RFC 6750)** phân quyền theo vai trò (Role-Based Access Control) | Phụ thuộc vào ACL của Broker hoặc TLS Client Cert |
| **Khả năng tích hợp Web** | Dashboard PWA gọi trực tiếp API `fetch()` không cần thư viện trung gian | Cần chạy thêm thư viện MQTT.js qua WebSocket |
| **Độ tin cậy** | Bản chất Stateless, có cơ chế xác thực từng gói tin (HTTP 200 OK) | Khó xử lý khi thiết bị di động chập chờn mạng nhảy IP liên tục |

👉 **Kết luận:** Lựa chọn RESTful HTTP/JSON kết hợp Bearer Token là giải pháp tối ưu cho hệ thống IoT di động ngoài trời, dễ dàng bảo vệ an toàn qua Cloudflare CDN và tường lửa Nginx.

---

## 5. HỆ THỐNG PHẦN MỀM VÀ CLOUD (BACKEND & DASHBOARD)

### 5.1. Máy chủ dịch vụ (Backend Server)
* **Framework:** FastAPI (Python 3.12) - hiệu năng xử lý bất đồng bộ (Asynchronous I/O) cao, chuẩn OpenAPI/Swagger tự động.
* **Cơ sở dữ liệu:** SQLite kết hợp WAL Mode (Write-Ahead Logging), lưu trữ lịch sử sự kiện, nhật ký rung/còi, và ảnh chụp từ camera.
* **Phân quyền truy cập theo vai trò (RBAC):**
  * `caregiver`: Người nhà (xem Dashboard, bấm tìm gậy, tắt còi, nhận thông báo đẩy).
  * `chest`: Thiết bị đeo ngực (gửi khoảng cách, kích hoạt SOS, nhận lệnh còi).
  * `cane`: Thiết bị gậy (lắng nghe lệnh còi tìm gậy, báo trạng thái pin).
  * `phone`: Ứng dụng điện thoại người mù (gửi vị trí GPS, hỗ trợ chụp ảnh).

### 5.2. Hạ tầng triển khai đám mây (Cloud Deployment)
* **Máy chủ ảo:** Oracle Cloud VPS (Ubuntu 24.04 LTS, 2 vCPU AMD EPYC, 1GB RAM vật lý, 3GB Swap).
* **Reverse Proxy:** Nginx xử lý cân bằng tải và bảo mật cổng 443.
* **Tên miền & SSL:** Tên miền chính thức `https://iot.chongziapp.id.vn`, tự động gia hạn chứng chỉ mã hóa **Let's Encrypt TLS 1.3**.
* **Định tuyến toàn cầu:** Quản lý DNS qua Cloudflare Proxy giúp tăng tốc độ tải và ngăn chặn tấn công DDoS.

### 5.3. Giao diện Web Dashboard (PWA)
* Thiết kế chuẩn **Progressive Web App (PWA)**: Có thể cài đặt trực tiếp lên màn hình chính của iPhone và Android như ứng dụng bản địa (Native App).
* **Cảnh báo đa giác quan:**
  * Hiển thị bảng đồ thị cự ly vật cản theo thời gian thực.
  * Tích hợp **Web Speech API**: Tự động phát âm thanh giọng nói tiếng Việt qua loa/tai nghe khi có cảnh báo khẩn cấp: *"Cảnh báo vật cản nguy hiểm"*, *"Người thân đã bấm nút SOS"*.
  * Các nút điều khiển tác vụ nhanh: **"Phát còi tìm gậy"** và **"⏹ Tắt còi ngay"**.

---

## 6. TÍCH HỢP TRÍ TUỆ NHÂN TẠO (AI INTEGRATION)

### 6.1. Kiến trúc phân tích thị giác kép (Dual-Engine Vision AI)
Hệ thống hỗ trợ 2 cơ chế trí tuệ nhân tạo nhận diện nguy cơ:

1. **Mô hình Semantic Segmentation (SegFormer B0):**
   * Sử dụng mạng Transformer gọn nhẹ dành cho thiết bị biên (Edge/CPU inference).
   * Phân đoạn ngữ nghĩa điểm ảnh, nhận diện các vùng rủi ro cao:
     * `possible_road`: Nhận diện lòng đường giao thông, cảnh báo nguy cơ xe cộ.
     * `possible_water`: Nhận diện vũng nước, ao hồ tránh ngã ngập.
2. **Google Gemini Vision Multimodal API:**
   * Gửi ảnh lên đám mây phân tích ngữ cảnh nâng cao bằng tiếng Việt.
   * Đọc biển báo giao thông, cảnh báo công trường, nhận diện loại phương tiện đang tiến lại gần.

## 7. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

### 7.1. Kết quả đạt được
1. Chế tạo thành công mô hình phần cứng hoạt động ổn định gồm khối ngực (ESP32) và khối gậy (ESP32-C3).
2. Xây dựng cơ chế an toàn kép: **ESP-NOW nội bộ (Offline)** kết hợp **RESTful HTTPS Cloud (Online)**.
3. Triển khai hoàn chỉnh hệ thống Backend FastAPI và Web Dashboard PWA trên máy chủ đám mây Oracle Cloud với tên miền riêng và chứng chỉ SSL bảo mật.
4. Tích hợp thử nghiệm thành công mô hình trí tuệ nhân tạo SegFormer và Gemini Vision.

### 7.2. Hướng phát triển trong tương lai
* Tích hợp thêm cảm biến định vị **GPS NEO-6M** độc lập trên gậy để không phụ thuộc vào GPS điện thoại.
* Bổ sung module phát âm thanh phần cứng **DFPlayer Mini + Loa nhỏ** gắn trực tiếp lên cổ áo, giúp phát giọng nói tiếng Việt trực tiếp mà không cần qua tai nghe điện thoại.
* Tối ưu hóa mô hình AI sang định dạng **TensorRT** hoặc **ONNX** để chạy trực tiếp trên các vi xử lý biên tiết kiệm năng lượng.
