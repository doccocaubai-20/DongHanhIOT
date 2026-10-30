"""Gói giao diện minh họa thành HTML mở trực tiếp, không khởi động API."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=(root/'web/index.html').read_text(encoding='utf-8')
css=(root/'web/style.css').read_text(encoding='utf-8')
js=(root/'web/app.js').read_text(encoding='utf-8')
source=source.replace('<link rel="stylesheet" href="style.css">','<style>'+css+'</style>')
source=source.replace('<script src="app.js" defer></script>','')
source=source.replace('</body>','<script>'+js+'</script></body>')
(root/'XEM-THU-WEB.html').write_text(source,encoding='utf-8')
print('Built XEM-THU-WEB.html')
