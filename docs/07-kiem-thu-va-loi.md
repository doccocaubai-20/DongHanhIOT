# 07 — Kiểm thử, nghiệm thu đồ án và xử lý lỗi

## Trước khi cấp điện

Đối chiếu model bo, số GPIO, nguồn đúng điện áp, chiều diode và G/D/S MOSFET. Kiểm tra 5 V không đi trực tiếp vào ECHO input; GND chung trong từng thiết bị. Ngắt nguồn khi thay dây. Cổng USB nhiều khi chỉ có dây sạc, cần cáp dữ liệu khi nạp. Không ghép song song nguồn USB và nguồn ngoài 5 V nếu không có thiết kế chống cấp ngược.

## Kịch bản demo một ESP32

1. **Web minh họa:** mở trang, nhấn thử SOS, xem chi tiết/đánh dấu đã xem, lọc nhật ký. Phải thấy chữ MINH HỌA.
2. **Kết nối thật:** nhập CAREGIVER_TOKEN; lúc chưa có bo danh sách phải rỗng, không tự tạo ảnh/vị trí thật. Nhập sai token phải bị từ chối.
3. **Khoảng cách:** vật phẳng tại 150, 100, 70, 40, 20 cm; ghi số đọc và nhịp. Dùng thước đo đối chiếu, không gọi độ phân giải quảng cáo là độ chính xác đo được.
4. **Lỗi cảm biến:** ngắt nguồn HC-SR04 hoặc che/đổi hướng khiến không có echo; phải hiện không xác định, không giữ số cũ và tuyên bố an toàn.
5. **SOS có ảnh:** điện thoại bật camera. Bấm nút vật lý; còi tại chỗ, web hiện SOS, sau đó ảnh gắn đúng sự kiện; giờ nhận và giờ chụp có thể khác nhau.
6. **SOS thiếu ảnh:** tắt camera điện thoại rồi bấm SOS; vẫn phải thấy SOS và trạng thái thiếu ảnh. Không hiển thị ảnh trước như ảnh SOS mới trong chi tiết.
7. **Riêng tư:** tắt nút trên ESP32; đợi trạng thái lên web, ảnh định kỳ dừng. Cài đặt web bật không vượt quyền tắt này. SOS vẫn yêu cầu ảnh. Tắt/bật nguồn rồi kiểm tra trạng thái được nhớ.
8. **Mất mạng:** tắt Wi-Fi/router hoặc tạm dừng API; khoảng cách/SOS cục bộ vẫn chạy. Khi mạng lại, sự kiện được gửi lại cùng ID, không nhân đôi.
9. **Tìm gậy:** bấm web/điện thoại, còi bo thử kêu tối đa 30 giây; STOP tắt được. Khi bo offline lâu hơn TTL20s, lệnh tìm cũ không được chạy khi nối lại.
10. **GPS:** bật quyền vị trí, kiểm tra tọa độ + sai số + tuổi dữ liệu. Dừng chia sẻ và chờ: vị trí phải chuyển nhãn cũ, không tự nhảy theo dữ liệu giả.
11. **AI:** chưa cài model phải ghi chưa cấu hình; không được có kết luận model thật. Sau cài model, gửi ảnh mới và kiểm tra có tên model/nhãn.

## Kịch bản bổ sung cho hai bo

- Bấm SOS ngực: source=chest, camera ngực gửi ảnh. Bấm SOS gậy: source=cane, ảnh vẫn từ camera ngực.
- Bấm nút TÌM GẬY GPIO4 trên ngực khi server ở `final`: còi ESP32 gậy phát tối đa 30 giây. Lặp lại ở mode `test` phải không tạo lệnh gậy; tắt Wi-Fi/API thì nút không thể làm gậy kêu.
- Ngắt mạng của gậy: còi SOS tại gậy vẫn kêu; ảnh ngực không được hứa nếu máy chủ chưa nhận yêu cầu.
- Tháo camera hoặc PSRAM lỗi: `camera_ready=false`, SOS vẫn ghi; không treo vòng đo.
- Rơi gậy mô phỏng trên đệm với người giám sát; ghi nhầm/bỏ sót cho các độ cao/tư thế. Gõ, quét, đặt nhẹ gậy để kiểm tra báo nhầm. Không dùng thử người bị ngã.
- Khởi động ESP32-CAM nhiều lần: motor không tự chạy lúc boot; GPIO0 đã tháo khỏi GND; nút GPIO1/3 không xung đột UART.
- Chạy camera + còi + motor đồng thời, đo điện áp và theo dõi reset/brownout. Không tắt brownout detector để che nguồn yếu.
- Đo thời gian phản ứng riêng cho phần cục bộ và phần mạng/AI. Không hứa ảnh/AI thời gian thực chỉ dựa vào chu kỳ poll.

## Kiểm tra phần mềm tự động

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests dùng cơ sở dữ liệu tạm, không dùng dữ liệu gia đình. Kiểm tra quyền truy cập, quyền riêng tư hai lớp, SOS không phụ thuộc lịch ảnh, lệnh giao lại, chống trùng, upload ảnh, vị trí, chế độ hai bo và AI chưa cấu hình. Nếu hệ thống hạn chế thư mục Temp, đặt biến `TEST_TEMP_DIR` tới thư mục thử nghiệm có quyền ghi trước khi chạy.

## Khi không chạy được

- **Không nạp DevKit:** chọn đúng COM, cáp dữ liệu, giữ BOOT khi connecting, giảm upload speed, kiểm tra driver USB-UART theo chip của bo.
- **ESP32-CAM không nạp:** tháo hai nhánh nút GPIO1/3, nối chéo UART TX/RX 3,3 V, GPIO0–GND lúc reset để nạp. Sau nạp phải tháo GPIO0–GND, tháo TX/RX adapter và reset.
- **Camera init failed/PSRAM:** sai model/pinout, cáp lỏng, nguồn không đủ, PSRAM chưa bật. Bộ mã chỉ chuẩn bị cho AI Thinker OV2640; không tự thay pin ngẫu nhiên.
- **Web chỉ có cảnh vẽ:** bạn đang xem demo, chưa nhập CAREGIVER_TOKEN hoặc chưa có ảnh thật. Nhãn minh họa là có chủ ý.
- **Web báo 401:** khóa sai; dùng đúng khóa cho role, khởi động lại backend sau sửa .env. Không dùng cùng một khóa cho các role.
- **403 khi gửi sự kiện:** dùng sketch/role không khớp PROJECT_MODE, ví dụ test_one gửi vào final. Đổi đúng mode và token.
- **Không thấy thiết bị:** kiểm tra cùng mạng 2,4 GHz, API_BASE phải là IPv4 laptop/domain API, port/firewall/client isolation. Đèn Wi-Fi sáng không đồng nghĩa token/API đúng.
- **Nút tìm gậy trên ngực không làm còi gậy kêu:** dùng firmware chest/cane đúng role và token, server phải là `final`, cả hai bo phải có heartbeat, cùng truy cập được API; lệnh chỉ sống 20 giây trước khi gậy nhận.
- **Điện thoại không có camera/GPS:** phải HTTPS và quyền trình duyệt; không dùng HTTP IPv4 LAN. Trình duyệt nhúng có thể chặn; mở trình duyệt hệ thống. Rời trang làm camera tự tắt.
- **CORS/mixed content:** ưu tiên web/API cùng origin. Web HTTPS không nên gọi API HTTP; dùng API HTTPS và khai báo ALLOWED_ORIGINS chính xác khi tách frontend.
- **Cm nhảy hoặc luôn không xác định:** kiểm tra chia áp, GND, nguồn HC-SR04, chân 18/19 test hoặc 13/14 chest, vật phản xạ, nhiễu motor. Không kích hai cảm biến đồng thời.
- **Motor yếu/không khởi động:** điện áp/dòng, MOSFET không dẫn ở 3,3 V, pin G/D/S sai, mức PWM thấp hơn ngưỡng khởi động. Hiệu chỉnh `duty` sau khi đo; không tăng điện áp quá định mức motor.
- **Rung/camera làm reset:** nguồn sụt, dây dài, thiếu diode/tụ, motor cấp từ GPIO/3V3; sửa nguồn và dây. Không vô hiệu hóa bảo vệ brownout.
- **MPU không đọc:** địa chỉ 0x68, AD0 về GND, SDA21/SCL22, nguồn/pull-up 3,3 V đúng module. Firmware không tự khởi tạo lại IMU sau lỗi I²C; sửa kết nối rồi reset bo.
- **AI rất chậm:** CPU/model, ảnh độ phân giải lớn, thiếu RAM. SegFormer chạy phía server; đừng chặn vòng cảm biến để chờ AI. Chưa có phép đo hiệu năng AI thật trong gói.
- **SOS đến muộn:** event giữ khi offline. Xem giờ xảy ra/giờ nhận; ảnh khi reconnect là ảnh sau đó. Hàng đợi hữu hạn, kiểm tra `queue_dropped` nếu bấm liên tục.

## Các thông số nên ghi trong báo cáo

Model bo/cảm biến thật, sơ đồ nguồn, khoảng đo thực tế, sai số và tỷ lệ timeout theo vật liệu; độ trễ local/SOS/ảnh/AI; số lần báo nhầm rơi gậy; thời lượng pin có đo thật; cấu hình model và tách dữ liệu; những chức năng còn mô phỏng. Không ghi “đã thử phần cứng” chỉ vì chương trình biên dịch thành công.
