"""Biên dịch cả sáu sketch trên máy có Arduino CLI; không tự nạp bo.
python scripts/check_firmware.py --cli arduino-cli
Cài core/thư viện đúng phiên bản theo tài liệu trước khi chạy.
"""
import argparse
from pathlib import Path
import subprocess
import sys
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--cli',default='arduino-cli')
parser.add_argument('--config-file')
args=parser.parse_args()
prefix=[args.cli]+(['--config-file',args.config_file] if args.config_file else [])
output=root/'build-checks';output.mkdir(exist_ok=True)
failed=[]
for name,board in [('test_one','esp32:esp32:esp32'),('chest_cam','esp32:esp32:esp32cam'),('cane','esp32:esp32:esp32'),('camera','esp32:esp32:esp32cam'),('find_remote','esp32:esp32:esp32c3'),('kiem_tra','esp32:esp32:esp32')]:
    command=prefix+['compile','--fqbn',board,'--warnings','all','--build-path',str(output/name),str(root/'firmware'/name)]
    try:
        result=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        text=result.stdout.decode('utf-8',errors='replace')
        (output/(name+'.log')).write_text(text,encoding='utf-8')
        print(name+(': PASS' if result.returncode==0 else ': FAILED'))
        if result.returncode:failed.append(name);print(text[-2500:])
    except OSError as error:
        failed.append(name);print(name+': '+str(error))
if failed:
    print('Chưa xác nhận biên dịch: '+', '.join(failed));sys.exit(1)
print('Cả sáu sketch biên dịch thành công. Vẫn cần thử phần cứng thực tế.')
