# 05 — Cách hoạt động dự án khi dùng hai ESP32

## Phân công

**Ngực — ESP32-CAM:** HC-SR04 đo ngang phía trước, rung/còi cảnh báo, camera chụp JPEG, nút SOS, nút bật/tắt ảnh định kỳ và **nút tìm gậy vật lý**. Bo tự đo và cảnh báo, không cần đợi AI hoặc Internet.

**Gậy — ESP32 development:** MPU6050 thử nhận biết gậy rơi, còi giúp tìm gậy, nút SOS, nút STOP. Không có camera/GPS trên gậy.

**Điện thoại:** cung cấp Internet qua hotspot nếu phù hợp và chia sẻ tọa độ bằng trang HTTPS. Hai vai trò này khác nhau: bật hotspot không tự gửi GPS; vẫn phải mở trang và cấp quyền vị trí.

**Máy chủ:** nhận dữ liệu của một gia đình, lưu ảnh/sự kiện, phân tích AI và trung chuyển lệnh. **Web người nhà:** xem thông tin, xem/ack SOS, gửi lệnh tìm gậy, điều chỉnh lịch ảnh.

```text
Ngực: HC-SR04 -> vòng cảnh báo -> motor / active buzzer
                     |
                  ESP32-CAM <---- lệnh chụp ---- Máy chủ <---- SOS ---- ESP32 gậy
                     |                            |                     ^
                  JPEG + giờ                      |                  MPU6050
                     +----------------------------+                     |
                                                  +--> AI / web     còi tìm gậy
Điện thoại GPS ---------------------------------->+
Nút tìm gậy ở ngực ------------------------------>+-- poll --> ESP32 gậy
Web / điện thoại -- lệnh tìm gậy ---------------->+
```

## SOS ở ngực và SOS ở gậy

SOS ngực bật còi/rung tại ngực, rồi đưa sự kiện vào hàng đợi mạng. Máy chủ tạo yêu cầu ảnh cho chính chest. Camera lấy frame mới, gửi ảnh gắn với sự kiện; AI chạy trên máy chủ, web cập nhật. Nhấn SOS thêm lần nữa khi đang kêu để tắt còi tại ngực; sự kiện đã gửi vẫn lưu.

SOS gậy bật còi ở **gậy**, gửi source=cane lên máy chủ. Máy chủ giao yêu cầu chụp cho **chest**; ảnh từ camera ngực gắn với event_id của SOS gậy. Bản hiện tại không tự bật còi ngực khi SOS từ gậy: còi tại gậy đã phát ngay. Có thể mở rộng lệnh báo từ xa sau khi cần, nhưng không nên nhầm với chức năng đang có.

Điện thoại cũng có nút SOS trên web, nhưng nút này cần Internet và không phát còi vật lý qua API trong phiên bản này. Nút vật lý trên mỗi bo là cách phát cảnh báo tại chỗ độc lập mạng.

## Vì sao chưa dùng ESP-NOW/Bluetooth giữa hai bo?

Để nhóm dễ triển khai, cả hai bo dùng HTTP đến cùng máy chủ; không phải cấu hình MAC, kênh Wi-Fi ESP-NOW hay thêm gateway. Lệnh có thời hạn và xác nhận, không kéo lệnh cũ vô hạn.

Đổi lại, **SOS gậy yêu cầu ảnh ngực cần cả hai bo truy cập được máy chủ**. Mất Internet nhưng vẫn có laptop/server trong LAN thì phần LAN còn hoạt động; nếu API nằm ngoài Internet và mất đường truyền thì ảnh từ ngực không được yêu cầu qua gậy. Còi SOS/rơi ở gậy và cảnh báo khoảng cách ở ngực vẫn chạy cục bộ.

Nếu yêu cầu phiên bản sau là “mất Internet nhưng SOS gậy vẫn phải làm camera ngực chụp”, cần thêm ESP-NOW hoặc giao tiếp LAN trực tiếp và bộ đệm ảnh; bộ mã hiện tại chưa có đường truyền dự phòng đó. Không mô tả trong báo cáo rằng hai bo có liên lạc trực tiếp ngoại tuyến.

## Rơi gậy và tìm gậy

IMU được đọc khoảng 50 Hz, ±8 g; firmware tìm chuỗi:

1. Gia tốc tổng <0,55 g ít nhất khoảng 80 ms.
2. Va chạm >2,5 g trong 800 ms tiếp theo.
3. Sau đó gia tốc gần 1 g, tốc độ góc nhỏ, đứng yên khoảng 1 giây trong cửa sổ 4 giây.

Đạt chuỗi thì kêu hai bíp mỗi giây tối đa 60 giây và gửi sự kiện `drop`. Nhấn STOP để tắt. Có thể dùng web/điện thoại gửi “Phát còi tìm gậy”; lệnh có hiệu lực 20 giây, bo nhận hợp lệ thì kêu tối đa 30 giây.

Đây là heuristic cần hiệu chỉnh: gõ mạnh, quét nhanh, đặt gậy, rơi thấp/rơi lên đệm có thể gây báo nhầm hoặc bỏ sót. Đặc biệt cú rơi không có pha freefall đủ lâu sẽ không được nhận ra. Cảm biến không phát hiện người bị ngã. Báo rơi không tự chụp ảnh, vì bạn chỉ yêu cầu còi tìm gậy; SOS trên gậy mới yêu cầu camera ngực.

Nút **TÌM GẬY trên ngực (GPIO4)** cũng tạo cùng lệnh như nút trên web/điện thoại. Máy chủ chuyển lệnh tới ESP32 gậy, còi phát tối đa 30 giây. Nút GPIO4 cần nối xuống GND, và đèn flash tích hợp không dùng được khi chân này dành cho nút. Chức năng tìm gậy này cần cả hai bo truy cập được API; nếu mất mạng, nút không thể kích còi ở bo kia. Cấu hình thử một bo không có gậy riêng để tìm, nên nút này chỉ có trên firmware chest của cấu hình final.

## Ảnh định kỳ

Máy chủ tạo lệnh chụp khi đủ khoảng thời gian, không có yêu cầu capture đang chờ, công tắc máy chủ bật và công tắc người đeo bật, chest có heartbeat mới. Mặc định 60 giây, tùy chỉnh từ web. Không tích lũy hàng trăm ảnh định kỳ khi mất mạng; sau khi nối lại chỉ tiếp tục lịch mới.

Người đeo nhấn PRIVACY để tắt/bật; trạng thái được lưu khi khởi động lại. Hai bíp/rung ngắn xác nhận bật, một bíp/rung dài xác nhận tắt, nếu không có cảnh báo ưu tiên cao hơn. Tắt ảnh định kỳ không tắt đo khoảng cách và không cấm ảnh SOS. Người nhà có thể tắt lịch thêm một lớp nhưng không thể bật vượt công tắc người đeo.

## Camera, AI và thời gian

Ảnh VGA JPEG khi có PSRAM, QVGA khi không có (camera tự thử lại mỗi 15 giây nếu khởi động lỗi). Camera không phát livestream liên tục; trước khi chụp có bỏ frame cũ trong bộ đệm. Còi/motor dùng timer PWM khác camera. Mạng/camera nằm trong tác vụ riêng để vòng cảm biến không đợi HTTP.

Sự kiện lưu ba thời điểm nếu có: xảy ra SOS, chụp ảnh, máy chủ nhận; ảnh còn có giờ nhận riêng. Đồng hồ thiết bị chưa đồng bộ thì để trống giờ nguồn. Ảnh chụp sau khi mạng trở lại không được gọi là ảnh đúng lúc sự cố. GPS điện thoại cũng có giờ lấy vị trí, giờ nhận và độ chính xác.

AI hiện ở web, **chưa có lời nói hoặc cảnh báo AI phát về người đeo**. Model không phải bộ phận trong vòng cảnh báo khoảng cách. Nhận diện “road” chỉ nói có bề mặt giống lòng đường, không kết luận lúc nào được sang đường. “Water” không suy ra khoảng cách/mức sâu. “Unknown” là kết quả hợp lệ, không ép model chọn một nhãn chắc chắn.

## Giới hạn của bản hoàn thiện đồ án

Hai bo hoạt động theo thiết kế nguyên mẫu, chưa có chứng nhận, thử độ bền, chịu mưa, pin chạy lâu, tối ưu công thái học hay đảm bảo độ tin cậy ngoài đường. Chưa có app native chạy nền, push khi đóng trang, giọng nói, modem độc lập, điều hướng, phát hiện ổ gà hoặc nhận dạng tín hiệu giao thông. Không dùng như sản phẩm an toàn đã hoàn chỉnh; trình bày đây là cấu hình hoàn thiện **trong phạm vi bài tập**.
