import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

def create_iot_diagram(data, output_png, output_svg, title_text, caption_text, subtitle=None):
    fig_w, fig_h = 16, 9.5
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=300)
    ax.set_xlim(0, 1600)
    ax.set_ylim(0, 950)
    ax.axis('off')

    # Background
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    # Slide Header Decoration (Academic / Professional Style)
    # Primary red band
    ax.add_patch(patches.Rectangle((0, 940), 1600, 10, facecolor='#B91C1C', edgecolor='none'))
    # Dark slate separator
    ax.add_patch(patches.Rectangle((0, 934), 1600, 4, facecolor='#1F2937', edgecolor='none'))

    # Title & Subtitle
    ax.text(80, 878, title_text, fontsize=28, weight='bold', color='#0F172A', fontname='Segoe UI')
    if subtitle:
        ax.text(80, 842, subtitle, fontsize=14, color='#475569', fontname='Segoe UI', style='italic')

    # Layout coordinates
    start_x = 80
    col_w = 270
    gap_x = 24
    row_h = 245
    row1_y = 480
    row2_y = 200
    tall_h = (row1_y + row_h) - row2_y # Exactly 525, top & bottom aligned!
    col3_w = 345

    def draw_block(x, y, w, h, bg_color, border_color, title, items, is_tall=False):
        # Outer block rounded box
        outer_box = patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0,rounding_size=12",
            facecolor=bg_color,
            edgecolor=border_color,
            linewidth=2.0
        )
        ax.add_patch(outer_box)

        # Title
        if is_tall:
            ax.text(x + w / 2, y + h - 34, title[0], fontsize=15, weight='bold', color='#0F172A',
                    ha='center', va='center', fontname='Segoe UI')
            ax.text(x + w / 2, y + h - 58, title[1], fontsize=12, color='#334155',
                    ha='center', va='center', fontname='Segoe UI', style='italic')
            usable_top = y + h - 85
            usable_bottom = y + 15
        else:
            ax.text(x + w / 2, y + h - 30, title, fontsize=15, weight='bold', color='#0F172A',
                    ha='center', va='center', fontname='Segoe UI')
            usable_top = y + h - 60
            usable_bottom = y + 15

        n = len(items)
        pill_w = w - 40
        pill_h = 42 if not is_tall else 46
        usable_h = usable_top - usable_bottom

        # Evenly distribute items vertically inside available space
        if n == 1:
            ys = [usable_bottom + usable_h / 2]
        else:
            step = usable_h / (n + 1)
            ys = [usable_top - (i + 1) * step for i in range(n)]

        for i, item in enumerate(items):
            cur_y = ys[i]
            pill = patches.FancyBboxPatch(
                (x + 20, cur_y - pill_h / 2), pill_w, pill_h,
                boxstyle="round,pad=0,rounding_size=7",
                facecolor='#FFFFFF',
                edgecolor='#CBD5E1',
                linewidth=1.2
            )
            ax.add_patch(pill)

            if isinstance(item, tuple):
                ax.text(x + w / 2, cur_y + 7.5, item[0], fontsize=11.5, weight='bold', color='#0F172A',
                        ha='center', va='center', fontname='Segoe UI')
                ax.text(x + w / 2, cur_y - 9.5, item[1], fontsize=9.2, color='#64748B',
                        ha='center', va='center', fontname='Segoe UI')
            else:
                ax.text(x + w / 2, cur_y, item, fontsize=13, weight='semibold', color='#1E293B',
                        ha='center', va='center', fontname='Segoe UI')

    # Color Palette inspired by original diagram & modernized
    # Col 0:
    x0 = start_x
    draw_block(x0, row1_y, col_w, row_h, '#D5E8D4', '#82B366', data['connectivity']['title'], data['connectivity']['items'])
    draw_block(x0, row2_y, col_w, row_h, '#E1D5E7', '#9673A6', data['memory']['title'], data['memory']['items'])

    # Col 1:
    x1 = x0 + col_w + gap_x
    draw_block(x1, row1_y, col_w, row_h, '#FFE6CC', '#D79B00', data['processor']['title'], data['processor']['items'])
    draw_block(x1, row2_y, col_w, row_h, '#D5E8D4', '#60A5FA', data['graphics']['title'], data['graphics']['items'])

    # Col 2:
    x2 = x1 + col_w + gap_x
    draw_block(x2, row1_y, col_w, row_h, '#DAE8FC', '#6C8EBF', data['audio_video']['title'], data['audio_video']['items'])
    draw_block(x2, row2_y, col_w, row_h, '#F8CECC', '#B85450', data['storage']['title'], data['storage']['items'])

    # Col 3 (Tall):
    x3 = x2 + col_w + gap_x
    draw_block(x3, row2_y, col3_w, tall_h, '#D0F0FD', '#38BDF8',
               data['io']['title'], data['io']['items'], is_tall=True)

    # Caption at bottom
    ax.text(800, 105, caption_text, fontsize=16, weight='bold', color='#1E293B',
            ha='center', va='center', fontname='Segoe UI')

    # Save outputs
    plt.savefig(output_png, format='png', dpi=300, bbox_inches='tight', pad_inches=0.15)
    plt.savefig(output_svg, format='svg', bbox_inches='tight', pad_inches=0.15)
    plt.close()
    print(f"Generated successfully: {output_png}")

# Data for Dong Hanh IoT Project
data_dong_hanh = {
    'connectivity': {
        'title': 'Connectivity (Kết nối)',
        'items': [
            ('Wi-Fi 802.11 b/g/n', 'HTTPS RESTful tới Cloud Server'),
            ('ESP-NOW (2.4 GHz)', 'Truyền nội bộ < 5ms (Áo ↔ Gậy)'),
            ('Bluetooth v4.2 / BLE', 'Cấu hình và ghép nối thiết bị')
        ]
    },
    'processor': {
        'title': 'Processor (Bộ xử lý)',
        'items': [
            ('ESP32 Xtensa Dual-Core', '32-bit LX6 @ 240MHz (Khối Áo)'),
            ('ESP32-C3 RISC-V', '32-bit Single-Core @ 160MHz (Gậy)')
        ]
    },
    'audio_video': {
        'title': 'Audio/Video (Âm thanh & Hình ảnh)',
        'items': [
            ('Camera OV2640 2MP', 'DVP 8-bit Bus (Chụp ảnh AI)'),
            ('Active Buzzer (Còi chíp)', 'Báo động SOS & Tìm gậy (D13/D5)'),
            ('Passive Buzzer (Âm thanh)', 'Báo nhịp khoảng cách vật cản')
        ]
    },
    'memory': {
        'title': 'Memory (Giao tiếp bộ nhớ)',
        'items': [
            ('520 KB SRAM nội', 'Bộ nhớ thực thi thời gian thực'),
            ('4MB / 8MB SPI Flash', 'Lưu Firmware & Web App'),
            ('4MB PSRAM (ESP32-CAM)', 'Bộ đệm khung hình chụp ảnh AI')
        ]
    },
    'graphics': {
        'title': 'Graphics / Display (Hiển thị)',
        'items': [
            ('Status LEDs (Đèn báo)', 'Báo nguồn, sóng Wi-Fi & ESP-NOW'),
            ('Dashboard Web PWA', 'Giao diện giám sát cho người thân')
        ]
    },
    'storage': {
        'title': 'Storage (Giao tiếp lưu trữ)',
        'items': [
            ('MicroSD Card Slot', 'Giao tiếp SPI/SDIO (Lưu ảnh AI)'),
            ('NVS (Flash nội bộ)', 'Lưu Token, Wi-Fi SSID/Pass')
        ]
    },
    'io': {
        'title': ('I/O Interfaces (Ngoại vi)', '(Cảm biến & Cơ cấu chấp hành)'),
        'items': [
            ('HC-SR04 (Siêu âm)', 'GPIO 32 (Trig) & 35 (Echo)'),
            ('Motor Rung xúc giác', 'PWM GPIO 25 (Transistor NPN)'),
            ('Nút khẩn cấp SOS', 'GPIO 27 (Nhấn 1.5s gửi cứu trợ)'),
            ('Nút chức năng Find / Stop', 'GPIO 33 (Tìm gậy) & 12 (Tắt còi)'),
            ('Cảm biến rơi MPU-6050', 'Giao thức I2C (SCL / SDA)'),
            ('Cổng UART (Nạp / Debug)', 'GPIO 1 (TX0) & GPIO 3 (RX0)')
        ]
    }
}

# Data for Generic IoT Textbook Diagram
data_generic = {
    'connectivity': {
        'title': 'Connectivity',
        'items': ['USB Host', 'RJ45/Ethernet']
    },
    'processor': {
        'title': 'Processor',
        'items': ['CPU']
    },
    'audio_video': {
        'title': 'Audio/Video Interfaces',
        'items': ['HDMI', '3.5mm audio', 'RCA video']
    },
    'memory': {
        'title': 'Memory Interfaces',
        'items': ['NAND/NOR', 'DDR1/DDR2/DDR3']
    },
    'graphics': {
        'title': 'Graphics',
        'items': ['GPU']
    },
    'storage': {
        'title': 'Storage Interfaces',
        'items': ['SD', 'MMC', 'SDIO']
    },
    'io': {
        'title': ('I/O Interfaces', '(for sensors, actuators, etc.)'),
        'items': ['UART', 'SPI', 'I2C', 'CAN']
    }
}

output_dir = Path(r"c:\Users\admin\Downloads\dong-hanh-hop-nhat\dong-hanh-hop-nhat\docs")

create_iot_diagram(
    data_dong_hanh,
    output_dir / "thiet-ke-vat-ly-iot-dong-hanh.png",
    output_dir / "thiet-ke-vat-ly-iot-dong-hanh.svg",
    title_text="Thiết kế vật lý của thiết bị IoT",
    subtitle='Đề tài: Hệ thống hỗ trợ người khiếm thị di chuyển an toàn "Đồng Hành"',
    caption_text="Hình 3.1: Sơ đồ khối thiết kế vật lý thiết bị IoT — Hệ thống Đồng Hành"
)

create_iot_diagram(
    data_generic,
    output_dir / "thiet-ke-vat-ly-iot-chung.png",
    output_dir / "thiet-ke-vat-ly-iot-chung.svg",
    title_text="Thiết kế vật lý của IoT",
    subtitle=None,
    caption_text="Sơ đồ khối chung của một thiết bị IoT"
)
