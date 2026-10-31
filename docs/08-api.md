# 08 — Giao thức API và cấu trúc mã

Base path `/api/v1`. Trừ `/health` và file giao diện tĩnh, API cần `Authorization: Bearer <token>`. Không đưa token vào query string. Payload JSON UTF-8; ảnh dùng JPEG thô. Một instance cho một gia đình, chưa có tenant/account nhiều gia đình.

## Các endpoint

- `GET /health`: kiểm tra tiến trình máy chủ; trả `{"ok":true}`. Không chứng minh bo/camera hoạt động.
- `GET /api/v1/session`: mọi role hợp lệ; trả role, mode, camera_source, server_time.
- `POST /api/v1/state`: test/chest/cane/phone; heartbeat với distance_cm hoặc null, sensor_valid, periodic_enabled, drop_alarm, sos_alarm, simulated, camera_ready, imu_ready, queue_dropped, uptime_s. Role xác định từ token, không tin device_id do client gửi.
- `POST /api/v1/events`: test/chest/cane/phone theo mode/quyền; `event_id`, `kind`, `occurred_at` hoặc null, `clock_synced`, `message`. Kind phía bo: sos/drop/privacy/test; phone chỉ sos. Nguồn được gửi theo mode: test/duo → bo `test`; final → `chest`, `cane`. ID giống role+kind được chống trùng. Sự kiện periodic chỉ do máy chủ tạo.
- `GET /api/v1/commands`: thiết bị/phone lấy lệnh của chính role. Có thêm `road_alert_ms` (0–20000): chỉ khác 0 với test/chest khi `WEARER_AI_ALERT=1` và ảnh mới nhất (chụp < 20 s) có `risk` là possible_road/possible_water. Lease12s, tối đa4 lệnh/lần; retry khi chưa ACK và chưa hết hạn. Capture SOS TTL90s; manual TTL60s; periodic TTL30s; tìm gậy TTL20s.
- `POST /api/v1/commands/{id}/ack`: cùng role đích; `result=done|failed|privacy_off|camera_unavailable`. Capture chưa upload ảnh không được ACK done.
- `POST /api/v1/events/{id}/image`: nguồn camera đúng mode, `Content-Type:image/jpeg`, header `X-Captured-At` Unix seconds nếu đồng hồ đã đồng bộ; body là JPEG thô. Cần yêu cầu chụp còn hiệu lực. Retry cùng event_id không ghi đè ảnh đã nhận.
- `GET /api/v1/events/{id}/image`: caregiver; JPEG riêng tư. Giao diện fetch bằng header rồi tạo blob URL, không lộ khóa trong URL ảnh.
- `GET /api/v1/dashboard`: caregiver; 100 sự kiện mới nhất, trạng thái thiết bị, settings, vị trí mới nhất, giờ server, `ai_provider`, `push_enabled`, `unread_messages`, `wearer_ai_alert`. Mỗi SOS có `context` (vị trí + khoảng cách lúc nhận) và `notifications` (tin nhắn của sự kiện: stage, trạng thái đẩy, đã đọc).
- `GET /api/v1/messages`: caregiver; 100 tin mới nhất (`sos`, `image`, `drop`) và số chưa đọc.
- `POST /api/v1/messages/read`: caregiver; `{"ids":[...]}` đánh dấu từng tin, `{}` đánh dấu tất cả. Đọc tin **không** thay cho xác nhận đã xem SOS.
- `GET /api/v1/push/config`: caregiver; khóa công khai VAPID cho trình duyệt.
- `POST /api/v1/push/subscriptions` / `POST /api/v1/push/unsubscribe`: caregiver; đăng ký/hủy nhận thông báo đẩy. Chỉ nhận endpoint HTTPS của dịch vụ push trình duyệt (Google, Mozilla, Apple, Microsoft); tối đa 20 thiết bị.
- `PUT /api/v1/settings`: caregiver; `periodic_enabled` boolean, `interval_s` 15–3600. Không thay được trạng thái riêng tư cục bộ của chest/test.
- `POST /api/v1/events/{id}/ack`: caregiver, xác nhận đã xem SOS; không có nghĩa cứu trợ đã xong, không điều khiển còi.
- `POST /api/v1/capture`: caregiver; người nhà yêu cầu chụp ngay (kind `manual`). Trả 409 nếu người đeo đang tắt ảnh hoặc thiết bị điều khiển mất heartbeat; nếu camera đang có yêu cầu chụp thì trả lại yêu cầu đó với `duplicate=true`. TTL 60 s.
- `POST /api/v1/find-cane`: caregiver, phone hoặc remote (nút cầm tay, khi `REMOTE_TOKEN` được đặt); xếp lệnh tìm cho test trong mode test, cane trong mode final. Token chest cũng được phép gọi endpoint này khi `PROJECT_MODE=final`; đây là luồng nút tìm gậy vật lý trên ngực. Chest bị từ chối ở mode test.
- `POST /api/v1/location`: phone; latitude, longitude, accuracy mét, captured_at. Không chấp nhận tọa độ ngoài miền; bản tin cũ hơn không thay tọa độ mới hơn.

## Ví dụ sự kiện và lệnh

```json
{
  "event_id": "cane-a12b34c5-00000001",
  "kind": "sos",
  "occurred_at": null,
  "clock_synced": false,
  "message": "Physical SOS button pressed."
}
```

```json
{
  "commands": [{
    "id": "server-generated-uuid",
    "kind": "capture",
    "event_id": "cane-a12b34c5-00000001",
    "expires_at": 1790000090,
    "reason": "sos"
  }],
  "settings": {"periodic_enabled": true, "interval_s": 60}
}
```

Các số thời gian trong ví dụ chỉ minh họa định dạng, không dùng làm dữ liệu test thật. Lúc chưa đồng bộ giờ, firmware dùng null, không suy ra giờ từ uptime. Máy chủ luôn có giờ nhận riêng.

## Mã nằm ở đâu?

`server/app.py` chứa API, schema dữ liệu, hàng đợi lệnh và worker nền. `server/ai_adapter.py` là điểm thay mô hình (chọn provider), `server/gemini.py` gọi Gemini, `server/notify.py` soạn tin nhắn và gửi Web Push. `web/app.js` xử lý giao diện, phone camera/GPS và xác thực. `firmware/runtime.h` chứa mã dùng chung; APP_ROLE=0/1/2 chọn test/chest/cane, `CAMERA_ONLY 1` (sketch `camera`) cho ESP32-CAM chỉ chụp ở mode duo. Mỗi thư mục sketch có bản sao runtime.h để mở trực tiếp trong Arduino IDE.

`firmware/find_remote` là sketch riêng cho ESP32-C3, không dùng runtime.h. Nếu sửa runtime dùng chung, chạy `python scripts/prepare_firmware.py` để đồng bộ vào cả ba sketch, rồi biên dịch lại. Script không thay config.h đã có, vì đó là cấu hình riêng từng bo. Không chỉ sửa một bản sao mà quên hai bản còn lại khi sửa giao thức chung.

## Bền vững và vận hành

SQLite WAL, mỗi kết nối được đóng sau giao dịch; dữ liệu lưu trong DATA_DIR. Một luồng AI xử lý tuần tự để không tải model nhiều lần. Sau restart, ảnh đang analyzing được đưa về uploaded để thử lại. Lỗi AI không làm mất sự kiện. Lệnh hết hạn không được giao tiếp; ảnh pending không tới được đổi thành missing.

Hệ thống chưa có audit đa tài khoản, rate limiting phân tán, queue cloud, push nền hoặc giới hạn quota lưu trữ theo hộ. Khi triển khai lâu dài cần bổ sung các phần này và theo dõi dung lượng/backup. Không công bố endpoint không có TLS, không tắt xác minh chứng chỉ để “chạy nhanh”.
