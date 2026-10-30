"""Tin nhắn cho người nhà qua web/app (thay Telegram).

Mỗi tin nằm trong hộp tin của web (luôn có) và được đẩy tới các trình duyệt/app đã bật
thông báo (Web Push, cần HTTPS). Khóa VAPID tự sinh trong DATA_DIR lần chạy đầu.
Soạn nội dung SOS giữ logic event_text của smart_cane.
"""
import base64
import json
from pathlib import Path
from urllib.parse import urlsplit

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from pywebpush import webpush, WebPushException
    PUSH_AVAILABLE = True
except ImportError:  # thiếu thư viện: hộp tin trong web vẫn chạy, chỉ không đẩy được
    PUSH_AVAILABLE = False

SOURCES = {'test': 'thiết bị ESP32', 'chest': 'thiết bị ở ngực', 'cane': 'thiết bị ở gậy', 'phone': 'điện thoại'}
# Chỉ gửi tới máy chủ push của trình duyệt, không gọi URL tùy ý do client đưa lên.
PUSH_HOSTS = ('fcm.googleapis.com', 'updates.push.services.mozilla.com', 'push.services.mozilla.com',
              'web.push.apple.com', 'push.apple.com', 'notify.windows.com')


def push_host_allowed(endpoint: str) -> bool:
    parts = urlsplit(endpoint)
    host = (parts.hostname or '').lower()
    return parts.scheme == 'https' and not parts.username and any(host == h or host.endswith('.' + h) for h in PUSH_HOSTS)


def event_text(event: dict) -> str:
    text = f"Từ {SOURCES.get(event['source'], event['source'])}. Chưa xác minh nguyên nhân; hãy liên hệ trực tiếp với người dùng."
    if not event.get('clock_synced'):
        text += ' Thiết bị chưa đồng bộ giờ; lúc nhấn nút có thể sớm hơn giờ máy chủ nhận.'
    elif event.get('occurred_at') and event['received_at'] - event['occurred_at'] > 5:
        text += f" Sự kiện đến muộn khoảng {int(event['received_at'] - event['occurred_at'])} giây."
    context = json.loads(event['context']) if event.get('context') else {}
    location = context.get('location')
    if location:
        text += (f" Vị trí điện thoại ±{location['accuracy']:.0f} m: "
                 f"https://www.google.com/maps?q={location['latitude']},{location['longitude']}")
    else:
        text += ' Chưa có vị trí đủ mới tại thời điểm sự kiện.'
    if context.get('distance_cm') is not None:
        text += f" Khoảng cách đo lúc nhận SOS: {context['distance_cm']:.0f} cm."
    return text


def compose(event: dict, stage: str, ai: dict | None = None):
    """Trả (level, title, body) cho một tin nhắn."""
    if stage == 'sos':
        return 'sos', 'SOS: người thân cần hỗ trợ', event_text(event)
    if stage == 'image':
        if event.get('image_path'):
            return 'sos', 'Ảnh SOS đã có', ((ai or {}).get('summary') or 'Đã nhận ảnh; chưa có kết quả AI.') + ' Mở web để xem ảnh.'
        return 'sos', 'SOS: không nhận được ảnh', 'Camera không gửi ảnh kịp cho SOS này. Hãy liên hệ trực tiếp với người dùng.'
    if stage == 'drop':
        return 'warn', 'Gậy có thể bị rơi', f"Từ {SOURCES.get(event['source'], event['source'])}. {event.get('details') or ''}".strip()
    raise ValueError('stage không hợp lệ')


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


class Push:
    """Khóa VAPID và gửi Web Push. Không ghi endpoint hay khóa vào log."""

    def __init__(self, folder: Path, subject: str):
        self.key_path = Path(folder) / 'vapid_private.pem'
        self.subject = subject
        self.public_key = ''
        if not PUSH_AVAILABLE:
            return
        if not self.key_path.exists():
            key = ec.generate_private_key(ec.SECP256R1())
            self.key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                        serialization.NoEncryption()))
        key = serialization.load_pem_private_key(self.key_path.read_bytes(), password=None)
        self.public_key = _b64(key.public_key().public_bytes(serialization.Encoding.X962,
                                                              serialization.PublicFormat.UncompressedPoint))

    @property
    def enabled(self) -> bool:
        return PUSH_AVAILABLE and bool(self.public_key)

    def send(self, subscription: dict, payload: dict, urgent: bool) -> int:
        """Trả mã HTTP của máy chủ push; 0 nếu lỗi mạng."""
        try:
            response = webpush(subscription_info=subscription, data=json.dumps(payload, ensure_ascii=False),
                               vapid_private_key=str(self.key_path), vapid_claims={'sub': self.subject},
                               ttl=3600, headers={'Urgency': 'high' if urgent else 'normal'}, timeout=10)
            return response.status_code
        except WebPushException as exc:
            return exc.response.status_code if exc.response is not None else 0
        except Exception:
            return 0
