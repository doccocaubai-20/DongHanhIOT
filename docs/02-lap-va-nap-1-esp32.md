# 02 — Đấu dây và nạp bản thử trên một ESP32

## Phạm vi bo

Từ 26/10/2026 mọi chân của bản thử nằm trên **một dãy** của DevKit (VIN, GND, D13, D12, D14, D27, D26, D25, D33, D32, D35, D34) vì bo rộng chỉ chừa một cột trống trên breadboard 830. Bố trí lỗ chi tiết: [tài liệu 12](12-lap-dat-tung-buoc.md).

Sơ đồ này cho **ESP32-WROOM-32 / ESP32 DevKit** có các chân GPIO nêu dưới đây. Không áp dụng cho ESP32-C3/S3 hay ESP32-CAM. Dùng **số GPIO**, không đếm vị trí chân hay dùng số D tùy tiện. Tắt nguồn trước mỗi lần sửa dây.

Mở thêm [sơ đồ chia áp và driver](mach-dien.svg). Sơ đồ là đường nối điện; thứ tự chân transistor/MOSFET phải theo linh kiện thực tế.

## Bước 1: HC-SR04 đo thật

- VCC HC-SR04 → đường **5 V** đã kiểm tra của nguồn/bo.
- GND HC-SR04 → GND ESP32.
- TRIG → GPIO32.
- ECHO → **hai điện trở 1 kΩ nối tiếp** → nút A.
- Nút A → GPIO35 (chân chỉ đọc vào, đủ cho ECHO).
- Nút A → **ba điện trở 1 kΩ nối tiếp** → GND.

Chuỗi ECHO đến GND gồm năm điện trở 1 kΩ, lấy tín hiệu ở nút sau điện trở thứ hai kể từ ECHO. Công thức `5 V × 3 kΩ / (2 kΩ + 3 kΩ) = 3,0 V`. Kiểm tra điện trở bằng đồng hồ trước khi lắp; không lấy nhầm 220 Ω. Không nối ECHO 5 V trực tiếp vào ESP32.

HC-SR04 đã cần 5 điện trở 1 kΩ. Kiểm tra bộ 30 điện trở có đủ số 1 kΩ cần dùng; nếu thiếu mua thêm. Thử một cảm biến trước, để chiếc thứ hai dự phòng. Đặt vật cứng/phẳng cách 20–150 cm; không dùng người đứng sát cảm biến khi vừa cấp nguồn.

## Bước 2: Nút bấm và LED

Các nút nối giữa GPIO tương ứng và GND, firmware dùng `INPUT_PULLUP`; nhấn là LOW. Nút bốn chân có hai chân cùng phía nối sẵn: dùng đồng hồ để chọn hai chân chỉ nối khi nhấn.

- SOS → GPIO27. **Giữ 1,5 giây** khi chưa báo SOS: phát cảnh báo + gửi sự kiện; giữ lại khi đang báo: tắt còi SOS tại chỗ. Đổi thời gian giữ bằng `SOS_HOLD_MS` trong config.h (0 = nhấn là gửi).
- Bật/tắt ảnh định kỳ → GPIO14.
- DROP giả lập rơi gậy → GPIO33.
- STOP tắt còi SOS/rơi/tìm → GPIO12.
- LED thay motor: GPIO25 → điện trở 220 Ω → anode LED → cathode GND. LED càng sáng/mau hơn khi vật gần. Khi gắn driver motor thì tháo LED hoặc giữ như chỉ báo với mạch phù hợp.
- LED onboard GPIO2 hiển thị Wi-Fi: sáng liên tục khi đã vào Wi-Fi, nháy khi chưa kết nối. Có bo clone không gắn LED tại GPIO2; xem web để kiểm tra. Đây là trạng thái Wi-Fi, không chứng minh API đã nhận dữ liệu.

## Bước 3: Còi

- GPIO26 → driver của **buzzer passive**: dùng cho nhịp khoảng cách ở tần số 2,2 kHz.
- GPIO13 → driver của **buzzer active**: dùng cho SOS/rơi/tìm gậy.

Với còi hai chân: nguồn đúng điện áp định mức → cực + còi; cực − → drain MOSFET; source → GND; gate nhận GPIO qua 220 Ω, gate xuống GND qua 10 kΩ. Nếu là buzzer điện từ, cần diode dập ngược phù hợp; piezo không phải tải motor nhưng vẫn cần kiểm tra driver/định mức. Module 3 chân có driver dùng theo sơ đồ hãng, chỉ khi nhận mức điều khiển 3,3 V.

Nếu chưa có driver và không biết dòng còi, **thử bằng LED trước**, không nối tải không rõ dòng vào GPIO. Tiếng SOS “to” phụ thuộc còi đã chọn, công suất nguồn và hộp; code không biến buzzer nhỏ thành còi công suất lớn.

## Bước 4: Motor sau khi mua

- GPIO25 → 220 Ω → gate MOSFET; gate → 10 kΩ → GND.
- Source MOSFET → GND; drain → cực − motor.
- Cực + motor → nguồn đúng điện áp motor, ví dụ 3 V ổn áp riêng cho motor 3 V.
- Diode song song motor: **đầu có vạch (cathode) về motor+**, anode về motor−/drain.
- GND nguồn motor nối GND ESP32. Tụ 100 nF gần motor và tụ bulk 470 µF trên đường cấp tải; kiểm tra cực tụ hóa.

Chọn MOSFET dẫn tốt ở gate 3,3 V theo datasheet. Không dùng relay 5 V để tạo PWM rung. Không cấp motor từ chân 3V3 của bo nếu chưa kiểm tra dòng và khả năng nguồn; hướng dẫn này ưu tiên nguồn motor riêng.

## Chế độ chưa nối HC-SR04

Nối biến trở 10 kΩ: hai chân ngoài → 3V3/GND, chân giữa → GPIO34. Đặt `TEST_DISTANCE_SIMULATION 1` trong `config.h`. Xoay biến trở giả lập 5–200 cm, web hiển thị rõ “giả lập”. Đây không phải phép đo. Khi dùng HC-SR04, để giá trị **0**; đó là mặc định đã chuẩn bị.

## Nạp chương trình

1. Cài Arduino IDE 2. Thêm URL board manager chính thức:

```text
https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

2. Cài **esp32 by Espressif Systems 3.3.0**; cài thư viện **ArduinoJson 7.3.1**. Mã không cần thư viện HC-SR04 hoặc MPU6050 bên ngoài.
3. Mở `firmware/test_one/test_one.ino`. Các file `runtime.h` và `config.h` phải ở cùng thư mục. Nếu bị thiếu, chạy `python scripts/prepare_firmware.py` tại thư mục gốc để tạo lại; script không ghi đè `config.h` đã có.
4. Sửa `config.h`: SSID/mật khẩu Wi-Fi 2,4 GHz, API_BASE, **TEST_TOKEN** từ `.env`. Không dùng CAREGIVER_TOKEN ở bo.
5. Chọn board **ESP32 Dev Module**, port COM đúng; tốc độ nạp 115200 nếu cáp/USB không ổn định. Bấm Upload; có thể cần giữ BOOT khi IDE đang “Connecting…”, rồi thả khi bắt đầu ghi.
6. Máy chủ để `PROJECT_MODE=test`, chạy theo tài liệu 01. Web người nhà kết nối bằng CAREGIVER_TOKEN; điện thoại kết nối PHONE_TOKEN, bật camera/GPS qua HTTPS.
7. Đưa vật cản gần dần: web hiện cm thật, LED/motor và nhịp còi đổi. Nhấn SOS: còi báo tại chỗ ngay; web hiện SOS, điện thoại chụp ảnh và gắn vào đúng sự kiện.

Code dùng tác vụ riêng cho mạng, nên máy chủ chậm không chặn vòng đo/cảnh báo. Không cần nạp vào ESP32-CAM trong bước này. Xem cách hoạt động chi tiết ở file 03.
