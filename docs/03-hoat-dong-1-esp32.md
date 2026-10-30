# 03 — Cách hoạt động khi test với một ESP32

## Vai trò từng thành phần

ESP32 development đóng vai thiết bị cảnh báo tổng hợp. HC-SR04 là phép đo thật; LED GPIO25 thay rung nếu chưa có motor. Hai buzzer, nút SOS và nút riêng tư là đầu vào/đầu ra thật nếu đã lắp đủ driver. Nút DROP **chỉ mô phỏng gậy rơi**. Điện thoại thay camera ngực và cung cấp GPS; laptop chạy máy chủ và AI nếu có mô hình.

Luồng chính:

```text
HC-SR04 -> ESP32 -> LED/motor + nhịp còi tại chỗ
                    |
                    +-- Wi-Fi -> API -> SQLite -> web người nhà
Nút SOS ------------+               |
                                     +-> lệnh chụp -> web điện thoại
                                                           |
                                              JPEG + giờ chụp
                                                           v
                                              API -> worker AI -> web
GPS điện thoại -----------------------------------> API -> web
```

## Khi cấp nguồn

Bo khởi tạo chân, đọc trạng thái ảnh định kỳ đã lưu trong NVS, rồi bắt đầu đo và thử kết nối Wi-Fi. Không chờ Wi-Fi để dùng nút/còi. Nút đang bị giữ lúc khởi động không tạo SOS cho đến khi đã thả rồi nhấn lại. NTP chạy khi có mạng; nếu chưa đồng bộ, sự kiện không tự bịa thời gian xảy ra.

Cứ khoảng 80 ms bo kích HC-SR04 một lần, trigger 12 µs. Ngắt cạnh ECHO đo độ rộng xung; hết 30 ms không có echo thì phép đo không hợp lệ. Ba số đo hợp lệ gần nhất được lọc trung vị. Nếu lỗi, bỏ mẫu cũ, hiện không xác định; ba xung cảnh báo ngắn mỗi 5 giây báo lỗi đo. Khi có phép đo trở lại, nhịp khoảng cách hoạt động bình thường.

Khoảng 3 giây gửi trạng thái lên máy chủ; web làm mới khoảng 2,5 giây. Giá trị cm trên web có thể chậm hơn cảnh báo tại chỗ. Không dùng độ trễ web để đánh giá độ phản ứng motor.

## Khoảng cách và cảnh báo

Từ 120 cm trở lên không có nhịp vật cản theo cấu hình, nhưng điều đó không có nghĩa mọi hướng đều an toàn. Từ 120 xuống 40 cm, nhịp tăng dần, PWM motor tăng dần. Dưới 40 cm giữ mức cảnh báo gần nhất. Vật gần dưới cự ly tối thiểu HC-SR04 cũng có thể tạo đo lỗi.

Thứ tự ưu tiên (bản hợp nhất): **rung luôn báo vật cản trước**, kể cả khi đang SOS/rơi/tìm gậy. Bo thử có hai nguồn âm: còi GPIO13 cho SOS/rơi/tìm gậy, piezo GPIO26 cho vật cản → phản hồi nút riêng tư → cảnh báo AI (nếu bật) → lỗi đo; hai luồng không che nhau. Bo chỉ có một còi: vật cản ≤ ALERT_NEAR_CM → báo động → phản hồi nút → vật cản → AI → lỗi đo. Ngưỡng xa có vùng trễ `ALERT_HYSTERESIS_CM` (5 cm). SOS cần **giữ nút 1,5 giây**, phát kiểu 300 ms kêu / 150 ms nghỉ, tự dừng sau 60 giây hoặc giữ SOS lần nữa/STOP. Rơi gậy giả lập kêu hai bíp mỗi giây tối đa 60 giây. Tìm gậy từ web tối đa 30 giây. STOP không đánh dấu SOS đã được người thân xem.

## Bấm SOS

1. ESP32 bật cảnh báo cục bộ và tạo ID sự kiện duy nhất theo phiên khởi động + số thứ tự.
2. Sự kiện được chuyển vào hàng đợi, lưu NVS ở tác vụ mạng rồi gửi đến API bằng TEST_TOKEN.
3. API lưu sự kiện `sos` trước khi yêu cầu chụp. Web người nhà đã có thể thấy SOS dù ảnh chưa đến.
4. Máy chủ giao lệnh chụp cho điện thoại qua polling; chỉ tab đang dùng PHONE_TOKEN và có camera bật mới chụp được.
5. Điện thoại lấy khung hình mới, gửi JPEG kèm thời gian chụp. Máy chủ gắn ảnh vào đúng event_id và lưu giờ nhận ảnh riêng.
6. Worker phân tích: chưa có model thì trả `not_configured/unknown`; có model thì trả nhãn và nhận xét thận trọng. Web cập nhật.
7. Người nhà bấm “Tôi đã xem SOS”. Đây chỉ là xác nhận đã xem, không chứng minh trợ giúp đã tới, không tự tắt còi tại thiết bị.

Camera chưa bật hoặc điện thoại rời trang: SOS vẫn có, ảnh ghi `camera_unavailable` hoặc hết thời hạn. Không dùng ảnh của sự kiện trước để làm như vừa chụp. Lệnh ảnh SOS có hạn 90 giây; nếu đã muộn, không tiếp tục chụp theo lệnh cũ.

## Ảnh định kỳ và riêng tư

Máy chủ chỉ lên lịch khi cài đặt người nhà bật **và** trạng thái riêng tư của ESP32 bật, đồng thời ESP32 có heartbeat trong 20 giây. Khoảng chụp mặc định 60 giây; web cho chỉnh 15–3600 giây qua API, các lựa chọn nhanh có trên giao diện. Điện thoại vẫn phải mở camera.

Nhấn nút PRIVACY đổi trạng thái lưu trong NVS; trạng thái được gửi ở heartbeat kế tiếp. Hai bíp/rung ngắn xác nhận bật, một bíp/rung dài xác nhận tắt; phản hồi này nhường ưu tiên cho SOS/rơi/tìm gậy. Người nhà không thể ghi đè trạng thái tắt tại thiết bị. SOS là ngoại lệ: chủ động nhấn SOS vẫn yêu cầu ảnh, kể cả định kỳ đang tắt. Ảnh “Chụp ảnh ngay” do người nhà yêu cầu tuân theo cùng quy tắc riêng tư như ảnh định kỳ. Tắt camera trên điện thoại chặn cả chụp định kỳ lẫn SOS từ nguồn đó.

## Mất mạng và có mạng lại

Rung/còi và nút vẫn hoạt động. Tối đa 16 sự kiện được giữ trong hàng đợi NVS của tác vụ mạng; tầng truyền từ vòng chính sang tác vụ mạng cũng có 16 phần tử. Khi đầy, sự kiện không phải SOS được ưu tiên loại trước khi thêm SOS; nếu toàn bộ là SOS thì có thể mất sự kiện mới, bộ đếm `queue_dropped` tăng. Không quảng cáo lưu vô hạn.

NVS được ghi sau khi tác vụ mạng nhận sự kiện; mất điện ngay trong khe thời gian đó vẫn có thể mất sự kiện. Hệ thống thử kết nối lại Wi-Fi, gửi sự kiện cũ cùng ID. API chống trùng ID, nên retry không tạo nhiều SOS. Nếu chưa có NTP khi bấm, web chỉ có giờ nhận; nếu NTP đã có, web phân biệt giờ xảy ra và giờ nhận.

**Ảnh sau khi có mạng lại là ảnh lúc chụp sau đó**, không phải ảnh tại thời điểm SOS khi đang offline. Không có bộ đệm ảnh lịch sử trong firmware. Đây là giới hạn cần nói rõ trong báo cáo.

## Những gì bản một bo chưa chứng minh

Chưa có camera ESP32 thật, chưa có hai thiết bị độc lập đeo ngực/gậy, chưa phát hiện gậy rơi bằng IMU, chưa có motor nếu đang dùng LED, chưa có AI thật khi chưa cài model. Bản này kiểm tra được chuỗi chức năng và giao thức bằng phần cứng hiện có, với các phần thay thế được ghi nhãn rõ ràng.
