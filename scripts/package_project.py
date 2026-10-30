"""Create a distributable ZIP and never package local secrets or runtime data."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os
import sys
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parents[1]
target=root.parent/'dong-hanh-hop-nhat.zip'
skip_dirs={'.venv','data','data-final','node_modules','build-checks','__pycache__','.git'}
files=[]
for path in sorted(root.rglob('*')):
    rel=path.relative_to(root)
    if any(part in skip_dirs for part in rel.parts):continue
    if path.is_dir():continue
    if path.name=='.env' or path.suffix in {'.pyc','.log'}:continue
    # config.h contains device credentials in a real setup: bundle the safe template instead.
    if path.name=='config.h':continue
    files.append(path)
manifest=['ĐỒNG HÀNH / Gói mã nguồn và hướng dẫn','Không kèm .env, config.h riêng, ảnh, cơ sở dữ liệu, node_modules hoặc model đã tải.','']
manifest.extend(f'{p.relative_to(root).as_posix()}  ({p.stat().st_size} bytes)' for p in files)
temporary=target.with_suffix('.zip.tmp')
with ZipFile(temporary,'w',ZIP_DEFLATED,compresslevel=7) as archive:
    for path in files:archive.write(path,'dong-hanh-hop-nhat/'+path.relative_to(root).as_posix())
    archive.writestr('dong-hanh-hop-nhat/PACKAGE-CONTENTS.txt','\n'.join(manifest)+'\n')
    for name in ('test_one','chest_cam','cane','camera','find_remote'):
        template=root/'firmware'/name/'config.example.h'
        if template.exists():archive.write(template,'dong-hanh-hop-nhat/firmware/'+name+'/config.h')
os.replace(temporary,target)
print(f'Created {target.name}: {target.stat().st_size:,} bytes; {len(files)+6} entries.')
