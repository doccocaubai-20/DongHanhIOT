# 11 — Bản hợp nhất dong-hanh-iot + IOT/smart_cane

Bản này lấy **dong-hanh-iot** làm nền: FastAPI, API `/api/v1`, phân quyền theo role, lệnh có lease/TTL, quyền riêng tư cục bộ, web tiếng Việt, ba vai trò firmware dùng chung `runtime.h`. Các phần tốt của **IOT/smart_cane** được đưa vào, nhưng không giữ hai hệ thống song song: firmware và API cũ của smart_cane (`/api/telemetry`, `/api/sos`, form-urlencoded) **không** còn được hỗ trợ.

## Giữ lại từ mỗi bản

| Từ dong-hanh-iot (nền) | Từ smart_cane (đưa vào) |
|---|---|
| FastAPI + Pydantic, SQLite WAL, 5 role token | Gemini phân tích ảnh (`server/gemini.py`) |
| Lệnh capture/find có lease, TTL, ACK | Hàng đợi thông báo có thử lại (nay gửi qua web/app thay Telegram, `server/notify.py`) |
| Quyền riêng tư cục bộ cho ảnh định kỳ | Chụp ảnh theo yêu cầu người nhà (`POST /api/v1/capture`) |
| HC-SR04 đo bằng ngắt + lọc trung vị | Vị trí + khoảng cách gắn vào SOS (chỉ khi khớp thời điểm) |
| Hàng đợi SOS ngoại tuyến ưu tiên SOS | SOS phải **giữ nút** (mặc định 1,5 s) |
| HTTPS với CA, MPU6050, chế độ test/duo/final | Vùng trễ ở ngưỡng cảnh báo |
| Web, GPS điện thoại, jsdom test | Cảnh báo AI cho người đeo (`road_ms`), **mặc định tắt** |
| | Camera không PSRAM chạy QVGA, tự thử khởi động lại |
| | Nút tìm gậy cầm tay ESP32-C3 (`firmware/find_remote`) |

Bỏ khỏi smart_cane: server Flask, giao thức text, worker benchmark SegFormer song song với Gemini (tốn CPU, không phục vụ người dùng), các bảng đo thời gian chi tiết. Model SegFormer Cityscapes của smart_cane không chép sang; dùng model ADE20K có sẵn ở `ai/model-baseline` (có nhãn road/water).

## Thay đổi hành vi cần biết

- **SOS:** giữ nút 1,5 giây mới gửi (`SOS_HOLD_MS`, 0 = nhấn là gửi như bản cũ). Giữ lại khi đang báo động = tắt còi tại chỗ.
- **Ưu tiên cảnh báo (sửa lỗi an toàn):** bản cũ tắt cảnh báo vật cản 30–60 giây khi đang SOS/rơi/tìm gậy. Nay rung luôn báo vật cản trước; bo một còi thì vật cản ≤ `ALERT_NEAR_CM` đứng trên cả báo động.
- **Ảnh theo yêu cầu** tuân theo nút riêng tư như ảnh định kỳ. Chỉ SOS được chụp khi người đeo đã tắt ảnh.
- **Vị trí lúc SOS** chỉ được gắn khi thiết bị đã đồng bộ giờ, SOS đến trong 120 giây và bản tin GPS nằm trong khoảng [−60 s, +5 s] quanh lúc bấm. SOS gửi muộn sau khi mất mạng sẽ không bị gắn nhầm vị trí hiện tại.

## Cấu hình mới trong `.env`

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `REMOTE_TOKEN` | trống | Bật role `remote` cho nút tìm gậy cầm tay; ≥ 24 ký tự, khác 5 khóa kia |
| `AI_PROVIDER` | trống | `none`, `segformer`, `gemini`. Trống = segformer nếu có `AI_MODEL_DIR` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | trống, `gemini-3.5-flash-lite` | Chỉ đặt trên máy chủ |
| `WEARER_AI_ALERT` | `0` | `1` = rung/bíp 2 nhịp mỗi 2 s khi ảnh mới nhất (< 20 s) có thể là lòng đường/mặt nước |
| `VAPID_SUBJECT` | `mailto:admin@example.com` | Email liên hệ gửi kèm thông báo đẩy; khóa VAPID tự sinh trong `DATA_DIR` |

Gemini và thông báo đẩy cần máy chủ có Internet. Gemini gửi ảnh lên Google; thông báo đẩy chỉ gửi tiêu đề/nội dung tin (không gửi ảnh) qua dịch vụ push của trình duyệt.

## Cập nhật 26/10/2026: tin nhắn web/app thay Telegram, chế độ duo

- **Bỏ Telegram.** Mỗi SOS tạo tin “SOS” rồi tin “ảnh SOS” (hoặc “không nhận được ảnh”); sự kiện rơi gậy tạo tin cảnh báo. Tin nằm trong trang **Tin nhắn** (đếm chưa đọc), và được **đẩy** tới mọi trình duyệt/app đã bật thông báo (Web Push, khóa VAPID tự sinh). Lỗi mạng thì thử lại tăng dần tối đa 8 lần; đăng ký bị trình duyệt hủy (404/410) tự xóa. Khi trang đang mở, SOS chưa xem phát âm báo lặp lại.
- **Cài như ứng dụng (PWA):** `manifest.json`, `sw.js`, icon. Có tùy chọn “Ghi nhớ trên thiết bị này” để mở từ thông báo mà không nhập lại khóa.
- **`PROJECT_MODE=duo`:** ESP32 (`firmware/test_one`) giữ cảm biến, nút, còi, LED; ESP32-CAM (`firmware/camera`, `CAMERA_ONLY 1`) chỉ chụp. Không dùng GPIO1/3/4 của ESP32-CAM làm nút nên còn xem được log Serial.
- **Firmware:** log Serial (`LOG_SERIAL`), `SINGLE_BUZZER` (chỉ một còi), `BUZZER_ACTIVE_LOW` (module còi kích mức thấp).
- **AI:** SegFormer-B0 ADE20K bật mặc định; đường dẫn model tương đối tính từ gốc dự án; transformers 5.x cần thêm `torchvision`.

## Nâng cấp từ dong-hanh-iot

1. Sao chép `.env` cũ, thêm các biến ở bảng trên nếu cần. Chạy lại `python scripts/setup.py` không ghi đè `.env` đã có.
2. CSDL cũ dùng tiếp được: server tự thêm cột `context` và bảng `outbox`.
3. `config.h` cũ của từng bo dùng tiếp được (tên biến không đổi; tùy chọn mới có giá trị mặc định).
4. Biên dịch lại và nạp cả ba bo, vì firmware và server phải cùng phiên bản để có `road_alert_ms` và lệnh `manual`.

Từ smart_cane: phải đấu lại theo sơ đồ chân của dong-hanh (docs 02/04) và nạp firmware mới. Token và API cũ không dùng được.

## Lỗi đã sửa

Lỗi có sẵn trong dong-hanh-iot:
- Cảnh báo vật cản bị tắt khi SOS/rơi/tìm gậy hoặc khi có phản hồi nút riêng tư.
- Sau khi nhận ảnh, lệnh chụp vẫn ở `leased` đến khi thiết bị ACK. Mất ACK thì lệnh bị giao lại và chặn ảnh mới đến hết TTL.
- Một sự kiện bị 400/401/403/422 nằm ở đầu hàng đợi chặn mãi các sự kiện phía sau.
- MPU6050 lỗi một lần là tắt phát hiện rơi đến khi reset; camera cũng vậy, và thiếu PSRAM thì tắt hẳn.
- Ảnh trong CSDL nhưng file bị xóa thì trả 500 thay vì 404.
- Bản tin outbox không bị dọn cùng sự kiện hết hạn lưu trữ.
- Giá trị `.env` có dấu nháy bị đọc cả dấu nháy; nhãn ADE20K có khoảng trắng thừa (`'bed '`).

Lỗi có sẵn trong smart_cane (không mang sang): `pulseIn` chặn vòng lặp, chỉ dùng HTTP thường, chụp định kỳ không tắt được.
