"""Tạo các sketch độc lập từ runtime đã kiểm tra; chỉ thêm config.h nếu chưa tồn tại."""
from pathlib import Path
import sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[1]
firmware = root / 'firmware'
# (thư mục, APP_ROLE, define thêm). camera = ESP32-CAM chỉ chụp ảnh cho PROJECT_MODE=duo.
SKETCHES = [('test_one', 0, ''), ('chest_cam', 1, ''), ('cane', 2, ''), ('camera', 1, '#define CAMERA_ONLY 1\n')]
for name, role, extra in SKETCHES:
    folder = firmware / name
    folder.mkdir(exist_ok=True)
    (folder / f'{name}.ino').write_text(f'#define APP_ROLE {role}\n{extra}#include "runtime.h"\n', encoding='utf-8')
    (folder / 'runtime.h').write_bytes((firmware / 'runtime.h').read_bytes())
    config = folder / 'config.h'
    if not config.exists():
        config.write_bytes((firmware / 'config.example.h').read_bytes())
    (folder / 'config.example.h').write_bytes((firmware / 'config.example.h').read_bytes())
print('Đã chuẩn bị ' + ', '.join(n for n, _, _ in SKETCHES) + '. Sửa config.h trong từng thư mục trước khi nạp.')
