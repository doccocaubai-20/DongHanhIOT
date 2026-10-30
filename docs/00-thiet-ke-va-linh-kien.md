# 00 — Thiết kế và linh kiện

## Chốt phạm vi phù hợp đồ án

Nhóm đã có đủ hai vi điều khiển: ESP32 development và ESP32-CAM. Không cần mua thêm ESP32 nếu ESP32-CAM hoạt động và đúng loại hỗ trợ. Giai đoạn đầu chỉ dùng development để giảm số yếu tố cần kiểm tra. Giai đoạn sau chuyển development sang gậy, ESP32-CAM lên ngực.

Một HC-SR04 hướng phía trước dùng đo khoảng cách. Cái còn lại làm dự phòng. Không gắn cả hai cùng hướng rồi kích đồng thời vì có thể nhiễu chéo. Nếu mở rộng cảm biến nhìn xuống, cần thêm chân/phần cứng và thuật toán riêng; bộ mã này chưa thực hiện phát hiện mép hố.

Mô-đun tránh chướng ngại vật IR trong bộ chỉ phù hợp thử có/không. PIR phát hiện thay đổi bức xạ hồng ngoại, không thay HC-SR04. DHT11, quang trở, relay và OLED không cần cho phiên bản tối thiểu. Không cần cố sử dụng mọi linh kiện để đủ tính năng.

## Càng gần thì rung/còi như thế nào?

Đã lập trình ngưỡng mặc định: từ 120 cm trở vào bắt đầu cảnh báo; từ 40 cm trở vào dùng mức gần nhất. Nhịp bíp thay đổi khoảng 0,9 giây → 0,2 giây; mỗi bíp dài 0,1 giây. Rung tăng duty PWM từ 150/255 đến 255/255 trong xung. Cần hiệu chỉnh ngưỡng khởi động của motor thật.

Độ lớn âm thanh không tăng tuyến tính chỉ vì tăng PWM. Còi active có mạch dao động bên trong, phù hợp bật/tắt theo nhịp. Còi passive cho phép phát tần số; độ to vẫn phụ thuộc cộng hưởng, nguồn và kiểu còi. Bản test dùng passive cho khoảng cách, active cho SOS/tìm gậy. Bản ESP32-CAM tiết kiệm chân, dùng một còi active cho tất cả kiểu nhịp.

Muốn **điều khiển âm lượng rõ ràng**, cần loa + bộ khuếch đại có điều khiển gain hoặc DAC/I²S, và bổ sung chân/bo phù hợp. Với bài tập hiện tại, tăng lực rung + nhịp bíp là phương án đơn giản, dễ phân biệt hơn; không cam kết “càng gần càng to” với buzzer đang có. [TDK về các loại buzzer](https://product.tdk.com/en/products/selectionguide/piezo-buzzer.html).

## Những thứ nên mua/bổ sung

Ưu tiên cho bản thử:

- 1 mô-tơ rung đúng điện áp, ví dụ motor coin 3 V; đọc dòng chạy và dòng kẹt của mẫu mua.
- Mạch nguồn 3 V đủ dòng cho motor 3 V. Không cấp thẳng 5 V vào motor 3 V, không lấy dòng motor từ GPIO.
- MOSFET logic-level loại có RDS(on) được công bố ở VGS 2,5 V hoặc thấp hơn, ví dụ AO3400A trên breakout dễ cắm; mua đủ cho motor và các còi cần driver. Kiểm tra chân G/D/S của đúng linh kiện, không suy theo hình minh họa chung.
- Diode dập xung cho motor, ví dụ 1N5819; điện trở gate 220 Ω, điện trở kéo xuống; tụ 100 nF tại motor và tụ 470 µF trên đường nguồn tải. Các giá trị là điểm bắt đầu cho thử nghiệm, cần đo nhiễu thực tế.
- Nếu còi là module 3 chân có driver nhận 3,3 V, có thể dùng module đó theo datasheet. Nếu còi 2 chân, dùng driver; không mặc định GPIO đủ dòng.
- Nguồn USB/power bank tốt, dây nguồn ngắn. Nguồn 5 V 2 A là mức khởi đầu hợp lý cho mô hình trên bàn, nhưng phải đo sụt áp khi camera phát Wi-Fi và còi/motor chạy cùng lúc. Hai thiết bị đeo thực tế cần hai nguồn riêng.

Cho bản hai bo:

- 1 MPU6050/GY-521 để thử phát hiện **gậy bị rơi**. Đây không phải cảm biến xác định người bị ngã. Nếu chưa mua, vẫn demo bằng nút DROP, được ghi rõ là giả lập.
- 1 còi active thứ hai: kit hiện chỉ có một active; cần một ở ngực, một ở gậy. Có thể thay loại ở gậy bằng phần cứng khác nhưng phải chỉnh code/driver tương ứng.
- Mạch nạp USB–UART logic 3,3 V hoặc đế ESP32-CAM-MB nếu ESP32-CAM chưa có USB. Nguồn cấp bo là 5 V theo sơ đồ, **tín hiệu UART vẫn 3,3 V**.
- Dây đeo, hộp cách điện, đầu nối chống tuột; chỉ đeo lên người sau khi nguồn và nhiệt độ ổn định. Không đưa breadboard lỏng ra ngoài đường.

## Định vị riêng có đắt không?

Dùng GPS điện thoại là lựa chọn ưu tiên: không mua thêm GNSS và tận dụng Internet điện thoại. Web cần được cấp quyền vị trí và giữ ở phía trước. Nếu muốn chạy nền khi khóa máy, bước sau nên viết app Android với foreground service và FCM, không cố hứa khả năng đó bằng một trang web.

Để tham khảo quy mô chi phí, trang Nshop đang niêm yết module NEO-6M 7N APM2.5 **220.000 đồng** tại lần tra cứu 16/10/2026; giá có thể thay đổi, chưa phải báo giá cho toàn bộ hệ thống. [Trang sản phẩm Nshop](https://nshopvn.com/product/module-dinh-vi-gps-neo-6m-7n-apm2-5/).

Module GPS/GNSS chỉ tạo tọa độ, **không tự gửi tọa độ về nhà**. Muốn độc lập điện thoại phải thêm đường truyền mạng, nguồn, anten, SIM/gói dữ liệu nếu dùng modem di động. GPS gắn ở gậy còn có nhược điểm: gậy rơi một chỗ thì vị trí đó không còn chắc là vị trí người dùng.

## Hạn chế cần đưa vào báo cáo

HC-SR04 đo echo âm, có thể bỏ sót vật mềm, nhỏ, nghiêng, hấp thụ âm; không chống nước mặc định. Camera một ảnh có thể nhầm phản chiếu, bóng tối, mặt đường ướt, không biết chắc độ sâu hay thời điểm an toàn để sang đường. Không echo phải hiện “không xác định”, không phải “không có vật cản”. Giới hạn danh định 2–400 cm từ [datasheet HC-SR04](https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf) không bảo đảm hiệu năng trong mọi điều kiện.

Ưu tiên đánh giá trên vật cản giả, bậc mô phỏng và ảnh ghi sẵn, có người giám sát. Dự án nên được giới thiệu là **hỗ trợ kết nối và cảnh báo thử nghiệm**, không thay gậy trắng, kỹ năng định hướng hay hỗ trợ của con người.
