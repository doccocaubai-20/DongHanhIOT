# 09 — Kết quả kiểm tra và những phần chưa xác nhận

Ngày tổng hợp: **20/10/2026**, cập nhật cho bản hợp nhất **26/10/2026**. Ghi nhận cho mã nguồn trong gói này; không phải chứng nhận phần cứng hay thiết bị y tế/an toàn.

## Cập nhật: tin nhắn web/app, SegFormer, chế độ duo (26/10/2026)

- **48/48 bài kiểm tra Python đạt, không bỏ qua bài nào** (venv dự án: Python 3.12.7, FastAPI 0.139.0, pywebpush 2.5.0, torch 2.14.1+cpu, torchvision 0.29.1+cpu, transformers 5.20.2). Các bài mới: tạo tin nhắn SOS/ảnh/rơi gậy, hàng đợi đẩy (không có máy, thử lại, bỏ sau 8 lần, đăng ký hết hạn 410), API hộp tin, kiểm tra endpoint push (chặn host lạ/HTTP/IP nội bộ), sinh khóa VAPID thật, chế độ duo, **SegFormer-B0 chạy thật** trên ảnh.
- Bài SegFormer thật phát hiện transformers 5.x cần `torchvision`; đã thêm vào `ai/requirements-ai.txt` và `start-windows.cmd`.
- **29 khẳng định DOM đạt** (trang Tin nhắn, đọc tin, nút bật thông báo, kết nối duo, nhãn AI).
- **Năm sketch biên dịch thành công, 0 cảnh báo** (core esp32 3.3.12, ArduinoJson 7.4.3): test_one 82%, chest_cam 36%, cane 81%, camera 36%, find_remote 82%.
- Chạy thật máy chủ ở `PROJECT_MODE=duo` qua HTTP: ESP32 giả lập gửi SOS → lệnh chụp tới ESP32-CAM → tải ảnh → SegFormer phân tích → 2 tin nhắn; ESP32-CAM gửi sự kiện bị 403; tìm gậy tới ESP32; manifest/sw.js/icon phục vụ đúng kiểu.
- Sau khi chuyển ESP32-CAM sang đế ESP32-CAM-MB (ngoài breadboard) và thêm CAMERA_VFLIP/CAMERA_HMIRROR: năm sketch biên dịch lại thành công, 0 cảnh báo.
- Đổi chân test_one sang một dãy của DevKit (TRIG GPIO32, ECHO GPIO35, STOP GPIO12) cho bo rộng chỉ chừa một cột trống: năm sketch biên dịch lại thành công, 0 cảnh báo.
- **Chưa kiểm tra:** gửi Web Push tới trình duyệt thật (cần HTTPS và một trình duyệt đăng ký), cài PWA trên điện thoại, nạp và chạy trên bo thật, lắp breadboard thực tế, Docker.

## Bản hợp nhất (26/10/2026)

- **41/41 bài kiểm tra Python đạt** (Python 3.12.7, FastAPI 0.139.0): 21 bài cũ không sửa nội dung + 20 bài mới cho outbox Telegram, ngữ cảnh SOS, chụp theo yêu cầu, role remote, cảnh báo AI cho người đeo, phân tích Gemini (giả lập HTTP, không gọi mạng thật), nâng cấp CSDL cũ, ảnh bị xóa, mất ACK.
- **21 khẳng định DOM (jsdom 26.1.0) đạt**, không có lỗi JavaScript.
- **Cả bốn sketch biên dịch thành công** trên Windows bằng arduino-cli 1.5.1, core esp32 **3.3.12**, ArduinoJson **7.4.3**, `--warnings all`, không có cảnh báo trong mã dự án: test_one 82% flash, chest_cam 36%, cane 81%, find_remote (ESP32-C3) 82%. Lỗi toolchain ghi bên dưới không còn xuất hiện trên máy này.
- Chạy thử server thật (uvicorn) qua HTTP: health, web tĩnh, heartbeat, GPS, SOS kèm vị trí/khoảng cách, lệnh capture, tải ảnh, worker AI, tải ảnh riêng tư, find-cane bằng role remote, remote bị chặn dashboard.
- **Chưa kiểm tra:** nạp và chạy trên bo thật, gọi Gemini/Telegram thật, model SegFormer thật, Docker.

Phần dưới là kết quả của bản dong-hanh-iot ngày 20/10, giữ để đối chiếu.

## Đã kiểm tra thành công

- **21/21 bài kiểm tra API đã qua trên máy nhóm ngày 20/10/2026**, gồm kiểm tra nút tìm gậy từ ESP32-CAM chỉ được chấp nhận ở mode `final` và máy chủ gửi lệnh tới ESP32 ở gậy. Đây là kiểm tra API; chưa xác nhận biên dịch firmware hay hoạt động phần cứng thực tế.
- **18 khẳng định về trạng thái giao diện trong môi trường DOM giả lập jsdom**, và kiểm tra không có lỗi JavaScript được ghi nhận: trang minh họa, SOS/chi tiết/đã xem, lọc và tìm nhật ký, tắt định kỳ, hộp kết nối, dữ liệu thật rỗng không giữ hình minh họa, ngắt kết nối. Đây **không phải kiểm tra ảnh chụp màn hình/trình duyệt thật**.
- Kiểm tra cú pháp JavaScript và Python cho máy chủ, script hỗ trợ và script train.
- Đối chiếu các API chính với header của Arduino-ESP32 3.3.0 đã tải: HTTPClient, Wire, camera/PWM; rà soát sơ đồ chân và nguồn theo tài liệu dẫn ở các file hướng dẫn.

Môi trường kiểm tra API: Python 3.14, FastAPI 0.139.0, Uvicorn 0.49.0, HTTPX 0.28.1, Pillow 12.3.0. Hướng dẫn người dùng ưu tiên Python 3.12 để tương thích bộ thư viện AI đã chọn. Bộ tests có cảnh báo deprecation về HTTPX của Starlette nhưng không có bài kiểm tra thất bại sau khi sửa việc đóng kết nối SQLite.

## Chưa xác nhận biên dịch ESP32

Đã cài core **esp32 3.3.0**, thư viện **ArduinoJson 7.3.1** và thử biên dịch cả ba mục tiêu:

- test_one → `esp32:esp32:esp32`.
- chest_cam → `esp32:esp32:esp32cam`.
- cane → `esp32:esp32:esp32`.

Cả ba dừng **trước khi trình biên dịch xử lý mã** vì chương trình `xtensa-esp32-elf-g++.exe` không khởi động được. Kiểm tra gọi riêng `g++ --version` cũng gặp lỗi hệ thống:

```text
Illegal System DLL Relocation
The system DLL was relocated in memory.
```

Đã xác nhận công cụ tải về là bản Windows x64, không phải nhầm 32-bit/64-bit. Vì thế **không có kết luận “sketch đã biên dịch thành công” và không cung cấp firmware .bin đã xác nhận**. Vẫn có thể còn lỗi chỉ được phát hiện khi biên dịch thật; nhóm cần chạy Verify trước khi nạp. Mã là bộ triển khai đầy đủ cho nguyên mẫu, chưa phải bản đã kiểm thử trên bo của bạn.

Trên máy có Arduino IDE/CLI hoạt động bình thường, cài đúng core/thư viện rồi Verify từng sketch. Có thể chạy:

```text
python scripts/check_firmware.py --cli arduino-cli
```

Script ghi log và trả lỗi nếu bất kỳ sketch nào chưa biên dịch được. Không tự nạp hoặc thay đổi phần cứng. Không tắt các bảo vệ Windows hoặc brownout của ESP32 để che lỗi công cụ/nguồn.

## Chưa kiểm tra thực tế

Chưa có kết nối đến bo của người dùng để nạp/chạy, đo mức điện áp, thử camera thật, độ to còi, lực rung, nguồn khi phát Wi-Fi, độ chính xác HC-SR04, phát hiện rơi MPU6050, GPS ngoài thực địa, thời lượng pin hoặc độ trễ mạng thực. Người dùng chưa xác nhận chính xác model ESP32-CAM; pinout AI Thinker là giả định cần đối chiếu.

Chưa tải/huấn luyện/evaluate mô hình AI thật. Script train được kiểm tra cú pháp; không có số mIoU/recall/độ trễ AI thực nghiệm trong gói. Chưa kiểm tra Docker image và môi trường Python 3.12 riêng.

## Trạng thái web trực tuyến

Đã chuẩn bị mã frontend tĩnh cho Sites và người dùng đã đồng ý xuất bản **riêng tư**. Tuy nhiên công cụ đồng bộ nguồn tiếp tục bị cơ chế phê duyệt của môi trường từ chối ở thao tác cấp đầu vào, với thông báo yêu cầu quyền `sandbox_approval` đang bị vô hiệu hóa. Đã cấp quyền ghi thư mục Git theo phạm vi cần thiết nhưng thao tác vẫn bị chặn. Vì vậy **chưa có bản web được xác nhận xuất bản và chưa có URL trực tuyến để bàn giao**.

Thử xem trước HTTP cục bộ không truy cập được giữa môi trường thực thi và trình duyệt của công cụ; truy cập file HTML qua công cụ trình duyệt bị chặn vì chỉ cho HTTP/HTTPS. Không thực hiện cách vòng qua giới hạn này. Kiểm tra trực quan responsive trên trình duyệt thật còn cần nhóm thực hiện.

File `XEM-THU-WEB.html` mở trực tiếp để xem minh họa; file `HUONG-DAN-DONG-HANH.html` là tài liệu tổng hợp có thể in. Để chạy dữ liệu thật, dùng server theo tài liệu 01. Bản tĩnh Sites dù được xuất bản sau này cũng cần backend HTTPS riêng để nhận dữ liệu ESP32.

## Chạy lại các kiểm tra trên máy nhóm

```text
python -m unittest discover -s tests -v
npm install
npm run test:ui
python scripts/check_firmware.py
```

Node/npm chỉ dùng cho tests giao diện, không bắt buộc để chạy web/backend. Sau khi phần mềm kiểm tra xong, tiếp tục checklist phần cứng ở tài liệu 07 trước khi đeo thử.

