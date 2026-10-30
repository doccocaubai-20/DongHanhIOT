"""Khởi tạo cục bộ; không in token ra màn hình, không ghi đè khóa cũ."""
from pathlib import Path
import secrets
import sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    print('.env đã tồn tại; giữ nguyên.')
else:
    content = (root / '.env.example').read_text(encoding='utf-8')
    for name in ('CAREGIVER', 'PHONE', 'TEST', 'CHEST', 'CANE', 'REMOTE'):
        content = content.replace(f'{name}_TOKEN=CHANGE_ME', f'{name}_TOKEN={secrets.token_urlsafe(32)}')
    target.write_text(content, encoding='utf-8')
    print('Đã tạo .env. Mở file này trên máy của bạn để lấy khóa cần dùng.')

