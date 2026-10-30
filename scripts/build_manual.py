"""Ghép tài liệu Markdown thành một HTML đọc/print được, không cần thư viện ngoài."""
from pathlib import Path
import html
import re
root=Path(__file__).resolve().parents[1]
docs=root/'docs'

def inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)
    def link(m):
        label,target=m.groups()
        if target.endswith('.md'):
            target='#'+Path(target).stem
        elif target=='mach-dien.svg':target='#wiring'
        elif target=='breadboard-duo.svg':target='#breadboard'
        elif target=='breadboard-duo-1coi.svg':target='#breadboard-1coi'
        return f'<a href="{target}">{label}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)

def render(source):
    lines=source.splitlines();out=[];code=[];paragraph=[];in_code=False;listing=None
    def flush():
        if paragraph:out.append('<p>'+inline(' '.join(paragraph))+'</p>');paragraph.clear()
    def close_list():
        nonlocal listing
        if listing:out.append('</'+listing+'>');listing=None
    for line in lines:
        if line.startswith('```'):
            flush();close_list()
            if in_code:out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>');code=[]
            in_code=not in_code;continue
        if in_code:code.append(line);continue
        if not line.strip():flush();close_list();continue
        heading=re.match(r'^(#{1,6})\s+(.*)',line)
        if heading:
            flush();close_list();n=len(heading[1]);out.append(f'<h{n}>{inline(heading[2])}</h{n}>');continue
        item=re.match(r'^(- |\d+\. )(.*)',line)
        if item:
            flush();tag='ul' if item[1]=='- ' else 'ol'
            if listing!=tag:
                close_list();listing=tag
                start=' start="'+item[1].split('.')[0]+'"' if tag=='ol' else ''
                out.append('<'+tag+start+'>')
            out.append('<li>'+inline(item[2])+'</li>');continue
        close_list();paragraph.append(line)
    flush();close_list();return '\n'.join(out)

files=[root/'README.md']+sorted(docs.glob('[0-9][0-9]-*.md'))
nav=[];sections=[]
for file in files:
    source=file.read_text(encoding='utf-8');title=source.splitlines()[0].lstrip('# ')
    nav.append(f'<a href="#{file.stem}">{html.escape(title)}</a>')
    sections.append(f'<section id="{file.stem}">{render(source)}</section>')
sections.insert(3,'<section id="wiring"><h1>Sơ đồ mạch bổ trợ</h1>'+ (docs/'mach-dien.svg').read_text(encoding='utf-8')+'</section>')
sections.append('<section id="breadboard"><h1>Sơ đồ breadboard: ESP32 + ESP32-CAM (duo)</h1>'+(docs/'breadboard-duo.svg').read_text(encoding='utf-8')+'</section>')
sections.append('<section id="breadboard-1coi"><h1>Sơ đồ breadboard: 1 còi active, không transistor</h1>'+(docs/'breadboard-duo-1coi.svg').read_text(encoding='utf-8')+'</section>')
style='''body{font:15px/1.8 system-ui,Arial,sans-serif;color:#203d35;background:#f6f8f2;margin:0}aside{position:fixed;inset:0 auto 0 0;width:270px;padding:25px;background:#153f38;color:#eaf3dd;overflow:auto}aside a{display:block;color:#dbe9cc;font-size:12px;padding:7px 0;text-decoration:none}aside strong{font-size:24px}main{margin-left:320px;max-width:960px;padding:40px 35px}section{background:white;padding:35px;border:1px solid #dae3d2;border-radius:12px;margin-bottom:28px;scroll-margin-top:20px}h1{font-size:27px;line-height:1.4;color:#205b49}h2{font-size:21px;margin-top:30px}h3{font-size:17px}a{color:#276d58}pre{overflow:auto;background:#f0f4e9;padding:18px;border-radius:6px;font-size:12px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere}code{font-size:.9em;background:#edf2e7;padding:2px 4px;border-radius:3px}pre code{padding:0}li{margin:7px 0}svg{width:100%;height:auto}button{border:1px solid #afc98a;background:#e2eecb;border-radius:6px;padding:9px 14px;margin:20px 0;cursor:pointer}small{display:block;font-size:11px;color:#bdcdb3}@media(max-width:900px){aside{position:static;width:auto}main{margin:0;padding:15px}section{padding:20px}}@media print{body{background:white;font-size:11px}aside{display:none}main{margin:0;padding:0;max-width:none}section{border:0;padding:0;page-break-before:always}section:first-child{page-break-before:auto}h1,h2,h3{break-after:avoid}pre,svg{break-inside:avoid}a{color:inherit}}'''
document='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Đồng Hành — Toàn bộ hướng dẫn</title><style>'+style+'</style><aside><strong>đồng hành</strong><small>TOÀN BỘ HƯỚNG DẪN · 1 BO VÀ 2 BO</small><button onclick="print()">In / Lưu PDF</button>'+''.join(nav)+'<a href="#wiring">Sơ đồ mạch bổ trợ</a><a href="#breadboard">Sơ đồ breadboard duo</a><a href="#breadboard-1coi">Sơ đồ 1 còi, không transistor</a></aside><main>'+''.join(sections)+'</main></html>'
(root/'HUONG-DAN-DONG-HANH.html').write_text(document,encoding='utf-8')
print('Built HUONG-DAN-DONG-HANH.html')
