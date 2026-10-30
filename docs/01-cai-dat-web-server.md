# 01 — Cài web, máy chủ và điện thoại

## Kiến trúc chạy thật

Laptop hoặc VPS chạy **FastAPI + SQLite + thư mục JPEG + worker AI**. Web được phục vụ từ chính máy chủ này. ESP32 gọi API; điện thoại cung cấp GPS, và cung cấp camera khi `PROJECT_MODE=test`. Người nhà mở web và nhập khóa người thân. Không cần MQTT broker hay dịch vụ AI trả phí để bắt đầu.

Không có mô hình: web vẫn nhận ảnh và SOS, AI hiển thị “Chưa cài mô hình”. Không có phần cứng: web vẫn có bản minh họa để xem giao diện, dữ liệu minh họa không đi vào máy chủ.

## Cài trên Windows

1. Cài Python 3.12 từ python.org. Giải nén cả gói, không chỉ lấy file HTML. Mở terminal tại thư mục chứa `README.md`.
2. Chạy:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/setup.py
```

3. Mở `.env`. Công cụ đã tạo **năm khóa ngẫu nhiên khác nhau** cùng `REMOTE_TOKEN` tùy chọn cho nút tìm gậy cầm tay (để trống nếu không dùng). Không sửa về chuỗi dễ đoán. `PROJECT_MODE=test` cho một ESP32 + camera điện thoại; `duo` cho ESP32 + ESP32-CAM chỉ chụp (xem [tài liệu 12](12-lap-dat-tung-buoc.md)); `final` cho cấu hình hai bo đeo. Mặc định đã bật SegFormer-B0 (`AI_PROVIDER=segformer`, `AI_MODEL_DIR=ai/model-baseline`); cần cài `ai/requirements-ai.txt`. Gemini và cảnh báo AI cho người đeo: xem [tài liệu hợp nhất](11-hop-nhat.md).
4. Chạy:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 1
```

5. Mở `http://localhost:8000`. Bấm “Kết nối máy chủ”, để trống địa chỉ API, nhập `CAREGIVER_TOKEN`. Nếu chỉ mở trang mà chưa nhập khóa, bạn vẫn đang xem **MINH HỌA**.
6. Windows có thể hỏi firewall: chỉ cho phép máy chủ trên mạng riêng dùng cho demo. Các thiết bị cùng Wi-Fi phải truy cập được máy laptop. Không tắt toàn bộ firewall.
7. Xem IPv4 Wi-Fi của laptop trong cài đặt mạng hoặc `ipconfig`, ví dụ `192.168.1.10`. Ghi `http://192.168.1.10:8000` vào `API_BASE` của ESP32. `localhost` trên ESP32 không phải laptop.

Linux/macOS tương tự, dùng `python3 -m venv .venv`, `source .venv/bin/activate`, rồi các lệnh `python ...`. Có thể dùng Docker: tạo `.env` bằng script trước, sau đó `docker compose up --build -d`. Docker chưa được kiểm tra trong môi trường soạn gói này; xem báo cáo kiểm thử.

## Mỗi khóa dùng ở đâu?

- `CAREGIVER_TOKEN`: web người nhà; xem ảnh/vị trí, đánh dấu đã xem SOS, chỉnh khoảng chụp, tìm gậy.
- `PHONE_TOKEN`: trang điện thoại; gửi GPS, nhận yêu cầu chụp ở test, gửi SOS, tìm gậy. Không xem toàn bộ ảnh trong API.
- `TEST_TOKEN`: `firmware/test_one/config.h`.
- `CHEST_TOKEN`: `firmware/chest_cam/config.h`.
- `CANE_TOKEN`: `firmware/cane/config.h`.

Khóa là mật khẩu của nguyên mẫu một gia đình; không phải hệ thống tài khoản nhiều hộ. Web giữ khóa trong `sessionStorage` của tab. Ngắt kết nối hoặc đóng phiên để xóa. Không đưa `.env`, `config.h` đã sửa hoặc dữ liệu ảnh vào Git. Đổi khóa trong `.env` và nạp lại bo liên quan nếu bị lộ.

## HTTPS để dùng camera/GPS điện thoại

Trình duyệt điện thoại cần **HTTPS + quyền camera/vị trí**. `http://localhost` chỉ hữu ích khi trình duyệt chạy ngay trên máy chủ. `http://192.168…` trên điện thoại thường không được dùng camera/GPS. [Quyền và secure context của getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

Một cách demo tạm thời: cài `cloudflared` từ Cloudflare, rồi mở terminal thứ hai:

```text
cloudflared tunnel --url http://localhost:8000
```

Công cụ in địa chỉ HTTPS ngẫu nhiên. Mở **địa chỉ đó trên điện thoại và máy người nhà**, nhập đúng khóa. Quick Tunnel chỉ phục vụ thử nghiệm, URL thay đổi khi khởi động lại; không hứa uptime. Không bật Uvicorn `--reload` trong cấu hình tunnel. [Hướng dẫn Quick Tunnel chính thức](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/).

Trong cách này ESP32 vẫn có thể gửi HTTP đến IPv4 laptop trong cùng LAN tin cậy; điện thoại/web nhận HTTPS thông qua tunnel vào **cùng tiến trình máy chủ**. Không cần hai máy chủ hay sao chép dữ liệu. Tắt tunnel sau demo. Dù URL bên ngoài mở được, API/ảnh thật vẫn cần token. Không dùng token trên HTTP qua Internet.

Nếu nhóm dùng hotspot điện thoại, kiểm tra hotspot có cho các thiết bị truy cập nhau không. Một số máy/router cách ly client; dùng router Wi-Fi chung nếu ESP32 không gọi được laptop. ESP32 cần Wi-Fi 2,4 GHz. Laptop phải còn mạng ra Internet để tunnel hoạt động.

## Trang điện thoại

1. Mở URL HTTPS, nhập `PHONE_TOKEN`; giao diện chuyển sang “Điện thoại đồng hành”.
2. Trong bản test, bấm **Bật camera**, cấp quyền, hướng camera phía trước. Không xin micro. Bấm **Chia sẻ vị trí**, cấp quyền GPS.
3. Giữ điện thoại mở, trang ở phía trước. Khi rời trang, mã chủ động tắt camera; quay lại phải bật lại. Trình duyệt có thể dừng GPS khi khóa màn hình. Web người nhà vẫn ghi tuổi vị trí cũ.
4. Ở cấu hình final, trang không dùng camera điện thoại; chỉ bật GPS. Camera ngực chụp qua ESP32-CAM.
5. Nút SOS trên điện thoại gửi được khi có mạng; không phát còi trên ESP32 trong bản này. Các nút SOS vật lý mới điều khiển còi cục bộ ngay tại bo.

## Xem từ xa / triển khai lâu hơn

Đưa backend lên VPS hoặc nền tảng hỗ trợ Python và ổ đĩa bền vững; dùng tên miền HTTPS hợp lệ, reverse proxy Caddy/Nginx. Giữ một worker Uvicorn cho nguyên mẫu SQLite/AI này. Sao lưu thư mục dữ liệu; thiết lập quyền đọc riêng tư. Token không thay cho hệ thống tài khoản hoàn chỉnh nếu mở rộng cho nhiều gia đình.

Nếu ESP32 gọi HTTPS trực tiếp, dán **CA gốc đúng của máy chủ** vào `ROOT_CA`, đổi `API_BASE=https://...`, đặt `ALLOW_HTTP_LAN=false`. Đồng hồ NTP phải đúng để xác minh chứng chỉ. Không dùng `setInsecure()` để bỏ xác minh. Mỗi lần đổi domain/certificate chain, kiểm tra lại CA.

Giao diện tĩnh trên Sites, nếu xuất bản được, chỉ là frontend. Nó **không tự chứa máy chủ Python, SQLite hay mô hình AI**. Cần API HTTPS riêng và đặt `ALLOWED_ORIGINS` trong `.env` bằng origin chính xác của frontend. Cách đơn giản nhất cho bài tập là dùng web và API cùng máy chủ như hướng dẫn trên.

## Dữ liệu và quyền riêng tư

Ảnh JPEG được kiểm tra định dạng/kích thước, tái mã hóa để loại metadata EXIF; tối đa 2 MB đầu vào, tối đa 8 triệu pixel, thu về cạnh dài tối đa 1280. Không có đường dẫn ảnh công khai không cần khóa. Mặc định xóa sự kiện/ảnh và vị trí quá 7 ngày, kiểm tra dọn theo giờ; dữ liệu demo trong trình duyệt không được lưu máy chủ. Web hiện tối đa 100 sự kiện gần nhất.

Nút trên người đeo tắt ảnh **định kỳ**; SOS vẫn yêu cầu ảnh. Ảnh đã gửi trước đó không bị xóa khi tắt định kỳ. Một ảnh đang truyền đúng lúc tắt có thể đã đến máy chủ trước khi trạng thái riêng tư mới được đồng bộ; không quảng cáo đây là công tắc ngắt nguồn camera. Cần ngắt nguồn vật lý nếu muốn chặn toàn bộ chụp ngay lập tức.
