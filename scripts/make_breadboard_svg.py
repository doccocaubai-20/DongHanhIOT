"""Vẽ sơ đồ lắp breadboard 830 lỗ cho PROJECT_MODE=duo (docs/breadboard-duo.svg).
HC-SR04 và 2 còi 2 chân nằm NGOÀI bảng, nối rời bằng dây đực–cái; còi đi qua transistor S8050.

ESP32 DevKit bản rộng (1 inch): chỉ còn MỘT cột trống, nên mọi dây đi từ dãy chân phía cột a
(VIN, GND, D13, D12, D14, D27, D26, D25, D33, D32, D35, D34). ESP32-CAM ở trên đế MB, ngoài breadboard.
Vị trí lỗ trùng với bảng trong docs/12-lap-dat-tung-buoc.md; sửa ở đây thì sửa cả bảng.
"""
from pathlib import Path
import html
import subprocess
import sys

# --single: biến thể 1 còi active nối thẳng D13, không transistor (docs/breadboard-duo-1coi.svg)
SINGLE = '--single' in sys.argv

P = 15
X0 = 70
Y = {'J+': 156, 'J-': 171}
for i, c in enumerate('jihgf'): Y[c] = 205 + i * P
for i, c in enumerate('edcba'): Y[c] = 205 + 5 * P + 24 + i * P
Y['A-'] = Y['a'] + 34; Y['A+'] = Y['A-'] + P
W = X0 + 64 * P + 40
out = []
RED, BLACK = '#d64545', '#222'

def x(row): return X0 + (row - 1) * P
def pt(spec):
    """'a14' -> lỗ; 'A-:14' -> ray tại hàng 14."""
    if ':' in spec:
        rail, row = spec.split(':'); return x(int(row)), Y[rail]
    return x(int(spec[1:])), Y[spec[0]]
def text(px, py, s, size=10, anchor='middle', color='#203d35', weight='normal'):
    out.append(f'<text x="{px}" y="{py}" font-size="{size}" text-anchor="{anchor}" fill="{color}" font-weight="{weight}">{html.escape(s)}</text>')
def dot(px, py, color='#f2c94c', r=3.4): out.append(f'<circle cx="{px}" cy="{py}" r="{r}" fill="{color}"/>')
def wire(a, b, color):
    (x1, y1), (x2, y2) = pt(a), pt(b)
    cx = (x1 + x2) / 2
    if y1 == y2:  # cùng một cột: cong ra phía mép gần nhất để các dây không chồng lên nhau
        up = y1 <= Y['f'] or a[0] == 'J'
        cy = y1 + (-1 if up else 1) * (12 + abs(x2 - x1) * 0.13)
    else:
        cy = (y1 + y2) / 2
    out.append(f'<path d="M{x1},{y1} Q{cx},{cy} {x2},{y2}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" opacity=".9"/>')
    dot(x1, y1, color, 3.5); dot(x2, y2, color, 3.5)
def resistor(a, b, label):
    (x1, y1), (x2, y2) = pt(a), pt(b)
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#8a7a5a" stroke-width="2"/>')
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    horiz = abs(x2 - x1) >= abs(y2 - y1)
    w, h = (18, 8) if horiz else (8, 18)
    out.append(f'<rect x="{mx-w/2}" y="{my-h/2}" width="{w}" height="{h}" rx="2" fill="#e8d3a8" stroke="#8a7a5a"/>')
    text(mx, my - 8 if horiz else my + 3, label, 8, 'middle' if horiz else 'start', '#6b5a35')
def line(x1, y1, x2, y2, color, w=3): out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>')
def label(px, py, s, color='#203d35'): text(px, py, s, 11, 'start', color)

# Nền, ray, lỗ
out.append(f'<rect x="20" y="{Y["J+"]-26}" width="{W-40}" height="{Y["A+"]-Y["J+"]+44}" rx="10" fill="#f7f6f0" stroke="#cfcab8"/>')
for rail, color in (('J+', RED), ('J-', '#2b6cb0'), ('A-', '#2b6cb0'), ('A+', RED)):
    out.append(f'<line x1="{x(1)-10}" y1="{Y[rail]-7}" x2="{x(63)+10}" y2="{Y[rail]-7}" stroke="{color}" stroke-width="1.5"/>')
    text(x(1) - 22, Y[rail] + 4, rail.replace('-', '−'), 11, 'end', color, 'bold')
    for r in range(1, 64):
        if r % 6: dot(x(r), Y[rail], '#b9b5a6', 2.3)
for c in 'jihgfedcba':
    text(x(1) - 22, Y[c] + 4, c, 11, 'end')
    for r in range(1, 64): dot(x(r), Y[c], '#b9b5a6', 2.3)
for r in (1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 63):
    text(x(r), Y['f'] + 20, str(r), 9, color='#8a8678')
text(W / 2, 16, 'Mặt trên breadboard 830 lỗ · hàng 1–63 · cột a–j · ray A (phía cột a) và ray J (phía cột j)', 11, color='#5a6a5a')
text(40, 66, 'BIẾN THỂ: 1 CÒI ACTIVE NỐI THẲNG, KHÔNG TRANSISTOR' if SINGLE else 'BẢN ĐẦY ĐỦ: 2 CÒI QUA TRANSISTOR S8050', 13, 'start', '#1f3b57', 'bold')
text(W / 2, 32, 'ESP32 30 chân, USB quay ra ngoài: VIN ở b1 … EN ở b15 (chừa lỗ cột a); dãy kia ở cột j (bị che, không dùng)', 11, color='#a32020', weight='bold')

# ESP32 DevKit V1 30 chân: dãy dùng ở cột b (lỗ trống cột a), dãy còn lại ở cột j
# Cổng USB quay ra ngoài mép (phía hàng 1): VIN ở hàng 1, EN ở hàng 15.
left = ['VIN','GND','D13','D12','D14','D27','D26','D25','D33','D32','D35','D34','VN','VP','EN']
right = ['3V3','GND','D15','D2','D4','RX2','TX2','D5','D18','D19','D21','RX0','TX0','D22','D23']
out.append(f'<rect x="{x(1)-9}" y="{Y["j"]-10}" width="{14*P+18}" height="{Y["b"]-Y["j"]+20}" rx="5" fill="#1f3b57" opacity=".93"/>')
text(x(8), Y['g'] + 3, 'ESP32 DevKit (test_one.ino)', 11, color='#fff', weight='bold')
text(x(8), Y['e'] + 3, 'USB ← hàng 1 · ăng-ten → hàng 15', 9, color='#cfe3f5')
used = {'VIN','GND','D13','D12','D14','D27','D26','D25','D33','D32','D35'}
for i, (l, r) in enumerate(zip(left, right)):
    dot(x(i + 1), Y['b'], '#f2c94c' if l in used else '#8a99a8'); dot(x(i + 1), Y['j'], '#5b6b7b')
    text(x(i + 1), Y['c'] + 4, l, 7, color='#fff' if l in used else '#9fb3c6', weight='bold' if l in used else 'normal')
    text(x(i + 1), Y['i'] + 4, r, 6.5, color='#7f93a6')

# Nút nhấn vắt qua rãnh giữa: chân e(N) nối GPIO, chân chéo f(N+2) nối GND
for n, name in ((22, 'SOS'), (25, 'PRIVACY'), (28, 'DROP'), (31, 'STOP')):
    x1, x2 = x(n) - 4, x(n + 2) + 4
    out.append(f'<rect x="{x1}" y="{Y["f"]-7}" width="{x2-x1}" height="{Y["e"]-Y["f"]+14}" rx="3" fill="#6b6b6b" opacity=".85"/>')
    out.append(f'<circle cx="{(x1+x2)/2}" cy="{(Y["e"]+Y["f"])/2}" r="6" fill="#222"/>')
    dot(x(n), Y['e']); dot(x(n + 2), Y['f'])
    text((x1 + x2) / 2, Y['g'] - 2, name, 8, color='#333', weight='bold')

# LED thay mô-tơ rung
resistor('b35', 'b37', '220Ω')
out.append(f'<line x1="{x(37)}" y1="{Y["d"]}" x2="{x(38)}" y2="{Y["d"]}" stroke="#a32020" stroke-width="2"/>')
out.append(f'<circle cx="{x(37.5)}" cy="{Y["d"]-9}" r="7" fill="#ff5b5b" stroke="#a32020"/>')
dot(x(37), Y['d']); dot(x(38), Y['d'])
text(x(37), Y['c'] + 4, '+', 10, color='#a32020', weight='bold'); text(x(38), Y['c'] + 4, '−', 10, color='#a32020', weight='bold')
text(x(37.5), Y['e'] - 2, 'LED', 8, color='#a32020', weight='bold')
# Còi 2 chân qua S8050: điện trở 1k → B; E → GND; C → chân − còi; chân + còi → A+; diode song song còi
for (gpio_row, r_from, e, name, by_x) in (() if SINGLE else ((40, 40, 43, 'CÒI 1 (active)', 44), (47, 47, 50, 'CÒI 2 (passive)', 51))):
    resistor(f'c{r_from}', f'c{r_from+4}', '1k')
    out.append(f'<rect x="{x(e)-7}" y="{Y["e"]-8}" width="{2*P+14}" height="16" rx="7" fill="#333" opacity=".85"/>')
    for r, lab in zip((e, e + 1, e + 2), ('E', 'B', 'C')):
        dot(x(r), Y['e']); text(x(r), Y['e'] + 3, lab, 7, color='#fff', weight='bold')
    text(x(e + 1), Y['f'] + 4, 'S8050', 8, color='#333', weight='bold')
    # diode d(C) → A+
    (dx1, dy1), (dx2, dy2) = pt(f'd{e+2}'), pt(f'A+:{e+2}')
    out.append(f'<line x1="{dx1}" y1="{dy1}" x2="{dx2}" y2="{dy2}" stroke="#555" stroke-width="2"/>')
    out.append(f'<rect x="{dx1-4}" y="{(dy1+dy2)/2-9}" width="8" height="18" fill="#222"/><rect x="{dx1-4}" y="{(dy1+dy2)/2+5}" width="8" height="3" fill="#ddd"/>')
    text(dx1 + 7, (dy1 + dy2) / 2 + 3, 'diode', 7, 'start', '#555')
    # còi nằm ngoài bảng, dưới ray A+
    bx, byy = x(by_x), Y['A+'] + 48
    out.append(f'<circle cx="{bx}" cy="{byy}" r="13" fill="#222"/><circle cx="{bx}" cy="{byy}" r="4" fill="#666"/>')
    text(bx, byy + 26, name, 9, color='#222', weight='bold')
    for px, lab in ((bx - 8, '−'), (bx + 8, '+')): text(px, byy - 15, lab, 9, color='#a32020', weight='bold')
    out.append(f'<path d="M{bx-8},{byy-10} Q{bx-8},{Y["A+"]+10} {x(e+2)},{Y["b"]}" fill="none" stroke="#444" stroke-width="3"/>')
    dot(x(e + 2), Y['b'], '#444', 3.5)
    out.append(f'<path d="M{bx+8},{byy-10} L{x(e+3)},{Y["A+"]}" fill="none" stroke="{RED}" stroke-width="3"/>')
    dot(x(e + 3), Y['A+'], RED, 3.5)

if SINGLE:  # 1 còi active nối thẳng: + → a3 (D13), − → ray A−
    bx, byy = x(44), Y['A+'] + 48
    out.append(f'<circle cx="{bx}" cy="{byy}" r="13" fill="#222"/><circle cx="{bx}" cy="{byy}" r="4" fill="#666"/>')
    text(bx, byy + 26, 'CÒI ACTIVE (duy nhất)', 9, color='#222', weight='bold')
    for px, lab in ((bx - 8, '−'), (bx + 8, '+')): text(px, byy - 15, lab, 9, color='#a32020', weight='bold')
    out.append(f'<path d="M{bx+8},{byy-10} C{bx+8},{Y["A+"]+70} {x(3)},{Y["A+"]+70} {x(3)},{Y["a"]}" fill="none" stroke="#d4a017" stroke-width="3"/>')
    dot(x(3), Y['a'], '#d4a017', 3.5)
    out.append(f'<path d="M{bx-8},{byy-10} L{x(42)},{Y["A-"]}" fill="none" stroke="{BLACK}" stroke-width="3"/>')
    dot(x(42), Y['A-'], BLACK, 3.5)
    text(x(52), Y['b'] + 4, 'Hàng 40–52: để trống (không transistor, không còi 2)', 9, color='#8a8678')

# HC-SR04 nằm ngoài bảng (phía trên), 4 dây rời; mạch chia áp vẫn trên bảng
hx, hy = x(36.5), 66
out.append(f'<rect x="{hx-60}" y="{hy-14}" width="120" height="44" rx="5" fill="#3d7ab8"/>')
for cx in (hx - 28, hx + 28): out.append(f'<circle cx="{cx}" cy="{hy+8}" r="15" fill="#cfd8e3" stroke="#22456b" stroke-width="2"/>')
text(hx, hy - 20, 'HC-SR04 (ngoài bảng, nối rời)', 10, color='#22456b', weight='bold')
hpins = [(hx - 30, 'VCC', RED), (hx - 10, 'Trig', '#6a1b9a'), (hx + 10, 'Echo', '#1565c0'), (hx + 30, 'GND', BLACK)]
for px, lab, color in hpins:
    line(px, hy + 30, px, hy + 40, '#aaa', 3); text(px, hy + 50, lab, 7.5, color=color, weight='bold')
def loose(px, target, color, bend):
    tx, ty = pt(target)
    out.append(f'<path d="M{px},{hy+54} C{px},{hy+54+bend} {tx},{ty-bend} {tx},{ty}" fill="none" stroke="{color}" stroke-width="3" opacity=".9"/>')
    dot(tx, ty, color, 3.5)
loose(hpins[3][0], 'J-:39', BLACK, 20)
loose(hpins[2][0], 'f37', '#1565c0', 40)
loose(hpins[1][0], 'a10', '#6a1b9a', 120)
loose(hpins[0][0], 'A+:34', RED, 160)
resistor('h37', 'h39', 'R1 1k'); resistor('g39', 'g41', 'R2 1k'); resistor('h41', 'J-:41', 'R3 1k')

for a, b, c in [
    ('a1', 'A+:1', RED), ('a2', 'A-:2', BLACK), ('A-:20', 'J-:20', BLACK),
    ('a6', 'a22', '#c2185b'), ('j24', 'J-:24', BLACK),
    ('a5', 'a25', '#7b1fa2'), ('j27', 'J-:27', BLACK),
    ('a9', 'a28', '#00838f'), ('j30', 'J-:30', BLACK),
    ('a4', 'a31', '#5d4037'), ('j33', 'J-:33', BLACK),
    ('a8', 'a35', '#2f9e44'), ('a38', 'A-:38', BLACK),
    *(() if SINGLE else (('a3', 'a40', '#d4a017'), ('a43', 'A-:43', BLACK), ('a7', 'a47', '#b8860b'), ('a50', 'A-:50', BLACK))),
    ('i39', 'a11', '#1565c0'),
]: wire(a, b, c)

# Chú thích
ly = Y['A+'] + 110
notes = [
    (RED, 'VIN (a1) → ray A+ = 5V · GND (a2) → ray A− · nối A− ↔ J− ở hàng 20 · ray J+ để trống'),
    ('#c2185b', 'Nút (vắt qua rãnh): GPIO → a(N), chân chéo f(N+2) → j(N+2) → J−. SOS a6→a22 · PRIVACY a5→a25 · DROP a9→a28 · STOP a4→a31'),
    ('#2f9e44', 'LED thay rung: D25 (a8) → a35 → 220Ω (b35–b37) → LED chân dài d37, chân ngắn d38 → a38 → A−'),
    *((('#d4a017', 'CÒI ACTIVE nối thẳng: + (chân dài) → a3 (D13) · − (chân ngắn) → ray A− · KHÔNG lắp còi passive'),
       ('#d4a017', 'config.h: #define SINGLE_BUZZER 1  → còi kêu cả báo động lẫn bíp theo vật cản; LED vẫn báo khoảng cách')) if SINGLE else
      (('#d4a017', 'CÒI 1: D13 (a3) → a40 → 1k (c40–c44) → B; S8050 E·B·C = e43·e44·e45; E: a43 → A−; C: còi − (b45); còi + → A+; diode d45 → A+'),
       ('#b8860b', 'CÒI 2: D26 (a7) → a47 → 1k (c47–c51) → B; S8050 E·B·C = e50·e51·e52; E: a50 → A−; C: còi − (b52); còi + → A+; diode d52 → A+'))),
    ('#6a1b9a', 'HC-SR04 nối rời: VCC → ray A+ · Trig → a10 (D32) · Echo → f37 · GND → ray J−'),
    ('#1565c0', 'Chia áp trên bảng: R1 1k (h37–h39) → điểm giữa hàng 39 → i39 → D35 (a11); R2 (g39–g41) → R3 (h41–J−)  ⇒ ≈3,3V'),
    ('#888', 'ESP32-CAM ở trên đế ESP32-CAM-MB, KHÔNG cắm breadboard (cấp nguồn + nạp qua micro-USB của đế)'),
]
for i, (color, s) in enumerate(notes):
    out.append(f'<line x1="40" y1="{ly+i*22-4}" x2="68" y2="{ly+i*22-4}" stroke="{color}" stroke-width="4"/>')
    text(78, ly + i * 22, s, 11, 'start')

# Hình phóng to: HC-SR04 + mạch chia áp (sơ đồ nguyên lý)
by = ly + len(notes) * 22 + 30
text(40, by, 'Phóng to HC-SR04 (nhìn mặt có 2 “mắt”, chân ở dưới, từ trái sang phải: VCC · Trig · Echo · GND)', 12, 'start', '#22456b', 'bold')
sx, sy = 60, by + 20
out.append(f'<rect x="{sx}" y="{sy}" width="200" height="70" rx="6" fill="#3d7ab8"/>')
for cx in (sx + 55, sx + 145): out.append(f'<circle cx="{cx}" cy="{sy+32}" r="24" fill="#cfd8e3" stroke="#22456b" stroke-width="2"/>')
for i, (lab, color) in enumerate((('VCC', RED), ('Trig', '#6a1b9a'), ('Echo', '#1565c0'), ('GND', BLACK))):
    px = sx + 40 + i * 40
    line(px, sy + 70, px, sy + 95, '#aaa', 4)
    text(px, sy + 110, lab, 11, color=color, weight='bold')
line(sx + 40, sy + 118, sx + 40, sy + 150, RED); line(sx + 40, sy + 150, sx + 330, sy + 150, RED)
label(sx + 336, sy + 154, '5V = ray A+ (từ chân VIN của ESP32)', RED)
line(sx + 80, sy + 118, sx + 80, sy + 175, '#6a1b9a'); line(sx + 80, sy + 175, sx + 330, sy + 175, '#6a1b9a')
label(sx + 336, sy + 179, 'GPIO32 (D32) — nối thẳng, không cần điện trở', '#6a1b9a')
ex = sx + 120
line(ex, sy + 118, ex, sy + 200, '#1565c0')
out.append(f'<rect x="{ex-5}" y="{sy+200}" width="10" height="26" fill="#e8d3a8" stroke="#8a7a5a"/>'); label(ex + 10, sy + 217, 'R1 = 1 kΩ')
line(ex, sy + 226, ex, sy + 250, '#1565c0'); dot(ex, sy + 250, '#1565c0', 5)
line(ex, sy + 250, sx + 330, sy + 250, '#1565c0')
label(sx + 336, sy + 254, 'GPIO35 (D35) ← điểm giữa ≈ 3,3V (KHÔNG nối Echo thẳng vào ESP32)', '#1565c0')
line(ex, sy + 250, ex, sy + 266, '#8a7a5a', 2)
out.append(f'<rect x="{ex-5}" y="{sy+266}" width="10" height="26" fill="#e8d3a8" stroke="#8a7a5a"/>'); label(ex + 10, sy + 283, 'R2 = 1 kΩ')
line(ex, sy + 292, ex, sy + 302, '#8a7a5a', 2)
out.append(f'<rect x="{ex-5}" y="{sy+302}" width="10" height="26" fill="#e8d3a8" stroke="#8a7a5a"/>'); label(ex + 10, sy + 319, 'R3 = 1 kΩ   (R2 + R3 = 2 kΩ)')
line(ex, sy + 328, ex, sy + 340, BLACK)
def ground(gx, gy):  # ký hiệu đất: các điểm có ký hiệu này đều nối ray J−
    line(gx - 10, gy, gx + 10, gy, BLACK); line(gx - 6, gy + 4, gx + 6, gy + 4, BLACK, 2); line(gx - 2, gy + 8, gx + 2, gy + 8, BLACK, 2)
line(sx + 160, sy + 118, sx + 160, sy + 128, BLACK); ground(sx + 160, sy + 128)
ground(ex, sy + 340)
text(sx + 175, sy + 133, '⏚ = GND (ray J−)', 10, 'start', BLACK)
label(sx + 336, sy + 344, '⏚ GND = ray J− (đã nối với GND của ESP32 qua ray A−)')
label(sx + 336, sy + 290, 'Điện áp vào GPIO35 = 5V × 2k / (1k + 2k) ≈ 3,3V', '#6b5a35')
H = sy + 380
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui,Arial,sans-serif" role="img" '
       f'aria-label="Sơ đồ lắp ESP32, HC-SR04, LED, còi và nút trên breadboard 830 lỗ">'
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>' + ''.join(out) + '</svg>')
target = Path(__file__).resolve().parents[1] / 'docs' / ('breadboard-duo-1coi.svg' if SINGLE else 'breadboard-duo.svg')
target.write_text(svg, encoding='utf-8')
print('Built', target.name)
if not SINGLE:  # vẽ luôn biến thể 1 còi
    subprocess.run([sys.executable, __file__, '--single'], check=True)
