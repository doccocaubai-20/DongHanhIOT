# Đồng Hành — Hệ thống IoT hỗ trợ người khiếm thị di chuyển an toàn

> 📚 **Tài liệu Báo cáo BTL / Đồ án:** Đã biên soạn đầy đủ cấu trúc học thuật, sơ đồ khối, kiến trúc 5 lớp IoT Level 5, bảng chân nối, so sánh giao thức REST vs MQTT và ma trận kiểm thử tại [**BAO-CAO-BTL.md**](BAO-CAO-BTL.md).

Bản này lấy `dong-hanh-iot` làm nền và đưa vào các phần tốt của `IOT/smart_cane`: Gemini, chụp ảnh theo yêu cầu, vị trí lúc SOS, giữ nút SOS, cảnh báo AI tùy chọn cho người đeo, nút tìm gậy ESP32-C3, camera không PSRAM. Chi tiết thay đổi và lý do: [docs/11-hop-nhat.md](docs/11-hop-nhat.md).

**Bắt đầu nhanh với 1 ESP32 trên breadboard + 1 ESP32-CAM trên đế MB:** làm theo [docs/12-lap-dat-tung-buoc.md](docs/12-lap-dat-tung-buoc.md) (chế độ `PROJECT_MODE=duo`, SegFormer-B0 chạy trên máy chủ, tin nhắn cho người nhà qua web/app, LED thay mô-tơ rung).

Gói này đã điều chỉnh theo đồ bạn xác nhận: **ESP32 development board, 2 HC-SR04, 1 ESP32-CAM**, bộ linh kiện ban đầu; mô-tơ rung sẽ mua sau. ESP32 development được giả định là **ESP32-WROOM-32 / DevKit thông thường**; ESP32-CAM được giả định là **AI Thinker + OV2640 + PSRAM**. Hãy đối chiếu tên bo/chân in trên bo trước khi cắm nguồn. Nếu khác loại, không dùng nguyên sơ đồ chân.

**Trạng thái kiểm tra (26/10/2026):** 41 test máy chủ và 21 khẳng định giao diện đạt; cả bốn sketch biên dịch được với core esp32 3.3.12. Chưa nạp hay thử trên bo thật; xem [báo cáo đầy đủ](docs/09-ket-qua-kiem-tra.md). Không coi bộ mã này là thiết bị đã được thử trên bo thật.

Mở `XEM-THU-WEB.html` để xem giao diện minh họa, hoặc `HUONG-DAN-DONG-HANH.html` để đọc toàn bộ hướng dẫn trong một file có nút In/Lưu PDF. Các file này không thay cho việc khởi động backend khi cần dữ liệu thật.

## Bạn nhận được gì?

- `web/`: web tiếng Việt cho người nhà, nhật ký ảnh, SOS, thời gian chụp/nhận, vị trí điện thoại, kết quả AI, điều khiển tìm gậy và trang điện thoại.
- `server/`: API FastAPI + SQLite + lưu JPEG, phân quyền năm loại khóa (+ khóa nút cầm tay tùy chọn), hàng đợi lệnh có thời hạn, gửi lại có chống trùng, tác vụ AI riêng (SegFormer hoặc Gemini), tin nhắn cho người nhà trên web kèm thông báo đẩy (Web Push) có thử lại, chụp ảnh theo yêu cầu.
- `firmware/test_one/`: nạp **một ESP32 development** để đo thật, cảnh báo, SOS, bật/tắt ảnh định kỳ, giả lập rơi gậy. Camera/GPS từ điện thoại.
- `firmware/chest_cam/`: nạp **ESP32-CAM AI Thinker** ở ngực: camera, HC-SR04, rung, còi, nút SOS, nút riêng tư và nút GPIO4 tìm gậy (gửi lệnh qua máy chủ).
- `firmware/cane/`: nạp **ESP32 development** ở gậy: SOS, còi tìm gậy, phát hiện rơi thử nghiệm bằng MPU6050; có nút giả lập khi chưa mua MPU6050.
- `firmware/camera/`: nạp **ESP32-CAM AI Thinker** chỉ để chụp ảnh khi `PROJECT_MODE=duo` (ESP32 giữ cảm biến, nút, còi).
- `firmware/find_remote/`: tùy chọn, **ESP32-C3 Mini** làm nút tìm gậy cầm tay (cần `REMOTE_TOKEN`).
- `ai/`: chỗ tích hợp model SegFormer, mã fine-tune tùy chọn; **không kèm mô hình đã huấn luyện hoặc dữ liệu**.
- `docs/`: hướng dẫn đấu dây, cài đặt, mô tả hoạt động tách riêng cho cả hai cấu hình, kịch bản kiểm thử, nguồn tham khảo.

## Mở và làm theo thứ tự

1. [Chọn linh kiện, rung/còi và GPS](docs/00-thiet-ke-va-linh-kien.md).
2. [Cài máy chủ, web và điện thoại](docs/01-cai-dat-web-server.md).
3. [Đấu dây và nạp một ESP32](docs/02-lap-va-nap-1-esp32.md).
4. [Cách hoạt động khi thử một ESP32](docs/03-hoat-dong-1-esp32.md).
5. [Đấu dây và nạp hai bo](docs/04-lap-va-nap-2-esp32.md).
6. [Cách hoạt động của bản hoàn thiện](docs/05-hoat-dong-hoan-thien.md).
7. [AI: tích hợp, dữ liệu và fine-tune](docs/06-ai-va-fine-tune.md).
8. [Kiểm thử và xử lý lỗi](docs/07-kiem-thu-va-loi.md), [API](docs/08-api.md), [kết quả kiểm tra phần mềm](docs/09-ket-qua-kiem-tra.md).
9. [Bản hợp nhất: thay đổi, cấu hình Gemini, nâng cấp từ bản cũ](docs/11-hop-nhat.md).
10. [**Hướng dẫn từng bước: 1 ESP32 + 1 ESP32-CAM trên breadboard 830 lỗ**](docs/12-lap-dat-tung-buoc.md).

## Chạy nhanh trên Windows

Cài Python 3.12 và mở `start-windows.cmd`. Lần đầu cần Internet để cài thư viện. Hoặc mở PowerShell tại thư mục này:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/setup.py
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 1
```

Mở **http://localhost:8000**. Ban đầu web hiện **dữ liệu minh họa**. Chọn “Kết nối máy chủ”, để trống địa chỉ và nhập `CAREGIVER_TOKEN` trong `.env` để xem dữ liệu thật. Mở một tab/điện thoại khác, dùng `PHONE_TOKEN` cho camera/GPS. Không dùng khóa thiết bị trên giao diện web.

**Ảnh/GPS trên điện thoại cần HTTPS**, không phải `http://192.168…`. Xem hướng dẫn máy chủ để tạo địa chỉ HTTPS cho buổi thử. ESP32 có thể gọi API HTTP trên LAN tin cậy trong buổi demo, còn điện thoại/người nhà gọi HTTPS đến cùng máy chủ.

## Điểm đã làm và giới hạn

Mã xử lý đầy đủ luồng của nguyên mẫu: đo khoảng cách → rung/bíp; SOS → máy chủ → yêu cầu ảnh → web/AI; nút riêng tư; GPS điện thoại; tìm gậy; rơi gậy thử nghiệm; gửi lại sự kiện khi có mạng. Đây **không phải thiết bị dẫn đường đã được xác nhận an toàn**. Không dùng độc lập khi đi gần xe cộ, ao hồ hoặc cầu thang. Chỉ thử có người quan sát ở môi trường kiểm soát.

Web không phải ứng dụng Android/iOS chạy nền. Tin nhắn SOS/rơi gậy có trong trang “Tin nhắn”; khi mở web bằng HTTPS và bật thông báo, tin được đẩy tới điện thoại/máy tính kể cả khi đóng trình duyệt (Web Push, cài được như ứng dụng). Không có SMS/cuộc gọi tự động. Phiên bản này không truyền AI về người đeo bằng giọng nói; có thể bật rung/bíp khi AI thấy lòng đường/mặt nước bằng `WEARER_AI_ALERT=1` (mặc định tắt). Cảnh báo cảm biến chạy cục bộ; AI được hiển thị cho người nhà như yêu cầu.

**Đã biên dịch không có nghĩa đã thử trên bo thật.** Xem báo cáo kiểm tra để biết chính xác phần đã kiểm tra bằng công cụ và phần nhóm cần kiểm tra thực tế.
