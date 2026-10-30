# 04 — Đấu dây và nạp cấu hình hai bo

## Bo ngực: ESP32-CAM AI Thinker

**Chỉ dùng pinout này nếu bo đúng AI Thinker ESP32-CAM với OV2640/PSRAM.** Người dùng chưa xác nhận chính xác model nên đây là giả định thiết kế, không phải nhận diện bo từ xa. Đối chiếu nhãn/ảnh pinout chính thức trước khi đấu. Bản ESP32-CAM-MB là bo đế USB cho camera; phải kiểm tra khả năng tháo đường UART khi dùng GPIO1/3 làm nút.

Không dùng SD; tháo thẻ microSD. Không nối các GPIO camera, GPIO16 dành cho PSRAM, hoặc GPIO12. Cụm ngực có **nút tìm gậy vật lý tại GPIO4**; chân này cũng điều khiển đèn flash trên AI Thinker, nên firmware dành GPIO4 cho nút và không dùng đèn flash. Không gắn OLED hay HC-SR04 thứ hai vào sơ đồ này.

### Cấp nguồn và cảm biến

- Chân **5V** bo ngực → nguồn 5 V ổn định đủ dòng; GND → GND nguồn.
- VCC HC-SR04 → 5 V; GND → GND chung.
- TRIG HC-SR04 → **GPIO13**.
- ECHO → chia áp **2 kΩ phía ECHO / 3 kΩ phía GND** → **GPIO14**, y như sơ đồ file 02. Dùng năm điện trở 1 kΩ nếu không có sẵn 2 kΩ và 3 kΩ.
- Camera OV2640 cắm đúng chiều cáp và khóa socket. Không rút/cắm camera khi đang cấp nguồn.

### Nút tìm gậy trên ngực

- Một chân nút nhấn → **GPIO4**, chân còn lại → **GND**. Không cần điện trở ngoài; firmware dùng INPUT_PULLUP.
- Khi nhấn, chest yêu cầu API tạo lệnh tìm gậy; ESP32 ở gậy nhận lệnh và bật còi tối đa 30 giây. Cần Wi-Fi, máy chủ đang chạy, `PROJECT_MODE=final`, và bo gậy đang kết nối. Đây là lệnh qua máy chủ, không phải liên lạc trực tiếp giữa hai bo; khi mất mạng nút ngực không thể làm gậy kêu.
- GPIO4 cũng nối với LED flash tích hợp và giao tiếp microSD trên một số bản AI Thinker. Không lắp thẻ SD, không dùng flash LED. Kiểm tra đúng model bo trước khi đấu.

### Motor và còi

- Motor PWM → **GPIO15**, qua gate resistor 220 Ω của MOSFET. Gate → **2 kΩ xuống GND** ở bo ngực, khác bản test 10 kΩ. Có thể dùng hai điện trở 1 kΩ nối tiếp.
- Lý do kéo xuống mạnh hơn: GPIO15 có pull-up lúc khởi động; motor không được tự chạy do gate lơ lửng. Kéo GPIO15 thấp có thể tắt log ROM UART, không phải chọn flash 1,8 V; chân liên quan flash voltage cần tránh là GPIO12.
- Chọn MOSFET có RDS(on) tại gate 2,5 V vì điện trở gate/kéo xuống làm điện áp HIGH thực tế thấp hơn 3,3 V một chút. Diode, nguồn motor và GND chung như file 02.
- Buzzer **active** → driver tại **GPIO2**, gate pulldown 10 kΩ. GPIO2 phải LOW khi vào chế độ nạp, nên không gắn module có pull-up kéo chân này lên lúc boot. Bản ngực không dùng buzzer passive.

### Nút và xung đột UART phải hiểu rõ

- Nút **SOS**: GPIO3/U0R → điện trở **1 kΩ** → nút → GND.
- Nút **PRIVACY**: GPIO1/U0T → điện trở **1 kΩ** → nút → GND.
- Nút **TÌM GẬY**: GPIO4 → nút → GND, như phần trên.
- Firmware gọi `Serial.end()` rồi đặt hai chân thành INPUT_PULLUP. Chọn **Core Debug Level: None**. Không thêm `Serial.print()` trong code bo ngực.
- Khi **nạp chương trình**, tháo hai nhánh nút trên GPIO1/3, nối UART theo bước dưới. Nút tìm gậy GPIO4 có thể để nguyên, nhưng nên nhả nút khi khởi động.
- Khi **chạy sử dụng**, tháo dây TX/RX của USB–UART; chỉ giữ nguồn/GND nếu phù hợp. Nếu bo đế CAM-MB vẫn nối cứng UART, cần tháo camera khỏi đế hoặc ngắt jumper/đường UART theo thiết kế đế. Không đồng thời để UART driver và nút điều khiển chân.
- Điện trở 1 kΩ hạn chế dòng nếu đang boot mà nút bị nhấn; không phải lý do để bỏ qua việc tháo UART.

Nếu nhóm muốn đấu đơn giản hơn, có thể dùng điện thoại điều khiển lịch ảnh và bỏ nút privacy ngực, nhưng như vậy mất quyền điều khiển vật lý đã thiết kế. Giữ sơ đồ trên hoặc thiết kế lại với expander; đừng tự đổi sang GPIO12 hay GPIO16.

### Nạp ESP32-CAM

1. Tắt nguồn, tháo dây nút GPIO1/3; giữ motor/còi có pulldown đúng hoặc tháo nguồn tải trong lúc nạp.
2. USB–UART TX logic 3,3 V → GPIO3/U0R; RX → GPIO1/U0T; GND → GND. Nguồn bo vào 5V, không dùng chân 3V3 yếu của adapter để cấp camera. Nếu dùng nguồn 5 V riêng, không nối song song hai nguồn 5 V; chỉ nối GND chung và tín hiệu.
3. Nối GPIO0 → GND, nhấn RESET/EN hoặc cấp nguồn lại để vào chế độ nạp.
4. Arduino IDE: core **esp32 3.3.0**, thư viện **ArduinoJson 7.3.1**, board **AI Thinker ESP32-CAM**, tốc độ 115200, PSRAM bật (board này thường mặc định bật), debug None.
5. Mở `firmware/chest_cam/chest_cam.ino`; sửa config.h bằng **CHEST_TOKEN**, Wi-Fi và API_BASE đúng.
6. Upload; khi hoàn thành, tắt nguồn, **tháo nối GPIO0–GND**, tháo UART TX/RX, nối lại nút GPIO1/3, rồi cấp nguồn/reset lại.
7. Nếu cameraReady=false: kiểm tra model/pinout, PSRAM, cáp camera, nguồn; chưa dùng bản này làm demo ảnh thật cho đến khi sửa được. Firmware tự thử khởi động lại camera mỗi 15 giây; bo không có PSRAM vẫn chụp được ở QVGA.
8. Nạp gậy và chuyển server sang `final`; nhấn nút GPIO4 trên ngực. Còi gậy phải kêu khi cả hai bo và API trực tuyến. Nếu đang ở `test`, server từ chối yêu cầu từ chest để tránh nhầm gậy thật với bo thử.

Pin camera nội bộ được mã hóa theo [ví dụ Espressif](https://raw.githubusercontent.com/espressif/arduino-esp32/master/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h): PWDN32, RESET−1, XCLK0, SDA26, SCL27, dữ liệu D0…D7 = 5,18,19,21,36,39,34,35, VSYNC25, HREF23, PCLK22. Không đấu phần ngoài vào các chân này.

## Bo gậy: ESP32 development

Tắt nguồn, tháo các dây bản test không dùng nữa. Nạp `firmware/cane/cane.ino`, sửa config.h dùng **CANE_TOKEN**. Board ESP32 Dev Module, core/thư viện như bản test.

- Buzzer active riêng tại gậy → driver GPIO13; nguồn đúng định mức, GND chung tại gậy.
- Nút SOS → GPIO27 và GND.
- Nút STOP/tắt còi khi nhặt được gậy → GPIO32 và GND.
- Nút DROP thử nghiệm → GPIO33 và GND. Đây là nút tùy chọn để demo có gắn nhãn giả lập.
- MPU6050 SDA → GPIO21; SCL → GPIO22; GND → GND; AD0 → GND để địa chỉ 0x68; INT không dùng.
- Nguồn MPU6050: mua **breakout được tài liệu xác nhận dùng nguồn 3,3 V và pull-up I²C về 3,3 V**, cấp VCC/3V3 theo đúng breakout. GY-521 clone có thể có regulator khác nhau; không cấp 5 V nếu pull-up SDA/SCL sẽ lên 5 V. Nếu không rõ sơ đồ module, kiểm tra trước hoặc dùng breakout có tài liệu. Chip trần không được cấp 5 V.

Mặc định `ENABLE_IMU=1`. Nếu chưa có MPU6050, đặt **0** và dùng nút DROP, ghi rõ trong báo cáo là giả lập. Nếu đặt 1 nhưng không đọc đúng WHO_AM_I 0x68, firmware báo `imu_ready=false`, không bịa ra rơi gậy. Các tính năng SOS/tìm gậy vẫn chạy. AD0 kéo cao tạo địa chỉ 0x69 chưa được code mặc định hỗ trợ.

Không gắn HC-SR04 lên gậy trong cấu hình này vì mục tiêu bạn nêu là tìm gậy và SOS. ESP32 gậy và ESP32-CAM **không nối dây tín hiệu với nhau**. Mỗi bên có nguồn riêng; cùng truy cập API qua Wi-Fi. Tài liệu 05 giải thích phụ thuộc mạng của liên lạc hai bo.

## Chuyển máy chủ và kiểm tra toàn hệ thống

1. Dừng máy chủ bằng Ctrl+C. Sửa `.env`: `PROJECT_MODE=final`; có thể đặt `DATA_DIR=data-final` để tách dữ liệu khỏi buổi thử một bo.
2. Khởi động lại máy chủ. Ngắt/kết nối lại web để đọc chế độ mới; không để tab điện thoại giữ cấu hình test cũ.
3. Nạp cả hai bo với các khóa khác nhau. Web phải có heartbeat `chest` và `cane`; `camera_ready=true` tại chest, `imu_ready=true` tại cane nếu gắn IMU.
4. Điện thoại chỉ chia sẻ GPS. Bấm SOS ngực, kiểm tra ảnh từ chest; bấm SOS gậy, kiểm tra sự kiện source=cane nhưng ảnh được chest chụp.
5. Tắt riêng tư trên ngực: ảnh định kỳ dừng sau khi trạng thái đồng bộ; SOS vẫn yêu cầu ảnh. Thử mất Wi-Fi: còi tại chỗ vẫn hoạt động.
6. Thử rơi trên gậy giả có đệm, không ném thiết bị, không để người dùng ngã để test. Bắt đầu bằng nút DROP, sau đó hiệu chỉnh IMU.
