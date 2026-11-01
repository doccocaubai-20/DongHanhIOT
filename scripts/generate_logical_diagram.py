import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

def create_logical_diagram(data, output_png, output_svg, title_text, caption_text, subtitle=None, is_dong_hanh=True):
    fig_w, fig_h = 16, 10
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=300)
    ax.set_xlim(0, 1600)
    ax.set_ylim(0, 1000)
    ax.axis('off')

    # Background
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')

    # Academic Slide Top Header Bars
    ax.add_patch(patches.Rectangle((0, 990), 1600, 10, facecolor='#B91C1C', edgecolor='none'))
    ax.add_patch(patches.Rectangle((0, 984), 1600, 4, facecolor='#1F2937', edgecolor='none'))

    # Title & Subtitle
    ax.text(80, 930, title_text, fontsize=28, weight='bold', color='#0F172A', fontname='Segoe UI')
    if subtitle:
        ax.text(80, 895, subtitle, fontsize=14, color='#475569', fontname='Segoe UI', style='italic')

    # Coordinates
    layer_bottom = 160
    total_h = 680
    left_x = 80
    side_w = 140
    mid_x = left_x + side_w + 20 # 240
    mid_w = 1120
    right_x = mid_x + mid_w + 20 # 1380

    blue_outer = '#3B82F6'
    blue_border = '#1D4ED8'
    blue_text = '#FFFFFF'

    # Left Vertical Bar: Management
    left_box = patches.FancyBboxPatch(
        (left_x, layer_bottom), side_w, total_h,
        boxstyle="round,pad=0,rounding_size=16",
        facecolor=blue_outer,
        edgecolor=blue_border,
        linewidth=2.0
    )
    ax.add_patch(left_box)

    # Management Title & items
    ax.text(left_x + side_w / 2, layer_bottom + total_h - 45, data['management']['title'],
            fontsize=15, weight='bold', color=blue_text, ha='center', va='center', fontname='Segoe UI')
    
    # Inner pills for Management if Dong Hanh
    m_items = data['management']['items']
    m_usable_h = total_h - 90
    m_step = m_usable_h / (len(m_items) + 1)
    for i, it in enumerate(m_items):
        cy = layer_bottom + total_h - 60 - (i + 1) * m_step
        pill = patches.FancyBboxPatch(
            (left_x + 10, cy - 36), side_w - 20, 72,
            boxstyle="round,pad=0,rounding_size=8",
            facecolor='#FFFFFF',
            edgecolor='#93C5FD',
            linewidth=1.2
        )
        ax.add_patch(pill)
        if isinstance(it, tuple):
            ax.text(left_x + side_w / 2, cy + 10, it[0], fontsize=10, weight='bold', color='#0F172A', ha='center', va='center', fontname='Segoe UI')
            ax.text(left_x + side_w / 2, cy - 10, it[1], fontsize=8.5, color='#475569', ha='center', va='center', fontname='Segoe UI')
        else:
            ax.text(left_x + side_w / 2, cy, it, fontsize=11, weight='semibold', color='#1E293B', ha='center', va='center', fontname='Segoe UI')

    # Right Vertical Bar: Security
    right_box = patches.FancyBboxPatch(
        (right_x, layer_bottom), side_w, total_h,
        boxstyle="round,pad=0,rounding_size=16",
        facecolor=blue_outer,
        edgecolor=blue_border,
        linewidth=2.0
    )
    ax.add_patch(right_box)

    ax.text(right_x + side_w / 2, layer_bottom + total_h - 45, data['security']['title'],
            fontsize=15, weight='bold', color=blue_text, ha='center', va='center', fontname='Segoe UI')

    s_items = data['security']['items']
    s_usable_h = total_h - 90
    s_step = s_usable_h / (len(s_items) + 1)
    for i, it in enumerate(s_items):
        cy = layer_bottom + total_h - 60 - (i + 1) * s_step
        pill = patches.FancyBboxPatch(
            (right_x + 10, cy - 36), side_w - 20, 72,
            boxstyle="round,pad=0,rounding_size=8",
            facecolor='#FFFFFF',
            edgecolor='#93C5FD',
            linewidth=1.2
        )
        ax.add_patch(pill)
        if isinstance(it, tuple):
            ax.text(right_x + side_w / 2, cy + 10, it[0], fontsize=10, weight='bold', color='#0F172A', ha='center', va='center', fontname='Segoe UI')
            ax.text(right_x + side_w / 2, cy - 10, it[1], fontsize=8.5, color='#475569', ha='center', va='center', fontname='Segoe UI')
        else:
            ax.text(right_x + side_w / 2, cy, it, fontsize=11, weight='semibold', color='#1E293B', ha='center', va='center', fontname='Segoe UI')

    # 4 Middle Layers (Application, Service, Network, Device)
    layer_h = 152
    gap_layer = 24
    layers_data = [
        ('device', 0),
        ('network', 1),
        ('service', 2),
        ('application', 3)
    ]

    for key, idx in layers_data:
        ly = layer_bottom + idx * (layer_h + gap_layer)
        info = data[key]

        # Layer Outer Blue Box
        lbox = patches.FancyBboxPatch(
            (mid_x, ly), mid_w, layer_h,
            boxstyle="round,pad=0,rounding_size=14",
            facecolor=blue_outer,
            edgecolor=blue_border,
            linewidth=2.0
        )
        ax.add_patch(lbox)

        # Left label inside outer box
        label_w = 210
        ax.text(mid_x + label_w / 2, ly + layer_h / 2 + 10, info['layer_name'][0],
                fontsize=15, weight='bold', color=blue_text, ha='center', va='center', fontname='Segoe UI')
        ax.text(mid_x + label_w / 2, ly + layer_h / 2 - 14, info['layer_name'][1],
                fontsize=12, color='#DBEAFE', ha='center', va='center', fontname='Segoe UI')

        # Right White Content Box
        white_x = mid_x + label_w + 10
        white_w = mid_w - label_w - 24
        white_h = layer_h - 24
        white_y = ly + 12

        wbox = patches.FancyBboxPatch(
            (white_x, white_y), white_w, white_h,
            boxstyle="round,pad=0,rounding_size=10",
            facecolor='#FFFFFF',
            edgecolor='#BFDBFE',
            linewidth=1.2
        )
        ax.add_patch(wbox)

        # Header of white box
        ax.text(white_x + white_w / 2, white_y + white_h - 20, info['header'],
                fontsize=13, weight='bold', color='#1E3A8A', ha='center', va='center', fontname='Segoe UI')

        # Items inside white box
        items = info['items']
        n_items = len(items)
        inner_w = (white_w - 30 - (n_items - 1) * 16) / n_items
        inner_h = 70
        inner_y = white_y + 14

        for j, it in enumerate(items):
            ix = white_x + 15 + j * (inner_w + 16)
            ipill = patches.FancyBboxPatch(
                (ix, inner_y), inner_w, inner_h,
                boxstyle="round,pad=0,rounding_size=8",
                facecolor='#F8FAFC',
                edgecolor='#E2E8F0',
                linewidth=1.0
            )
            ax.add_patch(ipill)

            if isinstance(it, tuple):
                ax.text(ix + inner_w / 2, inner_y + inner_h - 22, it[0],
                        fontsize=11, weight='bold', color='#0F172A', ha='center', va='center', fontname='Segoe UI')
                ax.text(ix + inner_w / 2, inner_y + 20, it[1],
                        fontsize=8.8, color='#64748B', ha='center', va='center', fontname='Segoe UI')
            else:
                ax.text(ix + inner_w / 2, inner_y + inner_h / 2, it,
                        fontsize=12, weight='semibold', color='#1E293B', ha='center', va='center', fontname='Segoe UI')

    # Bottom caption
    ax.text(800, 75, caption_text, fontsize=16, weight='bold', color='#1E293B',
            ha='center', va='center', fontname='Segoe UI')

    # Save
    plt.savefig(output_png, format='png', dpi=300, bbox_inches='tight', pad_inches=0.15)
    plt.savefig(output_svg, format='svg', bbox_inches='tight', pad_inches=0.15)
    plt.close()
    print(f"Generated logical diagram: {output_png}")

# Data for Dong Hanh Logical Design
data_dong_hanh_logic = {
    'management': {
        'title': 'Management\n(Quản trị)',
        'items': [
            ('Cấu hình bo', 'Lưu Token/SSID\n(NVS Flash)'),
            ('Năng lượng', 'Đo dung lượng Pin\nCảnh báo sụt áp'),
            ('Trạng thái kết nối', 'Giám sát Heartbeat\nOnline / Offline'),
            ('Phân quyền RBAC', 'Caregiver, Chest,\nCane, Phone')
        ]
    },
    'security': {
        'title': 'Security\n(An ninh)',
        'items': [
            ('Xác thực Token', 'Bearer Token\n(RFC 6750)'),
            ('Mã hóa dữ liệu', 'TLS 1.3 / HTTPS\nCloudflare Proxy'),
            ('Chế độ riêng tư', 'Nút Privacy Mode\n(Ngắt gửi ảnh/GPS)'),
            ('An toàn sinh mạng', 'ESP-NOW độc lập\n100% không cần Net')
        ]
    },
    'application': {
        'layer_name': ('Application Layer', 'Tầng Ứng dụng'),
        'header': 'Ứng dụng & Dịch vụ người dùng (Applications Provided)',
        'items': [
            ('Web Dashboard PWA', 'Giám sát vị trí GPS, lịch sử SOS\n& trạng thái thiết bị theo thời gian thực'),
            ('Hỗ trợ di chuyển an toàn', 'Cảnh báo đa giác quan phân cấp:\nRung xúc giác + Âm thanh còi chíp'),
            ('Cứu trợ khẩn cấp', 'Kích hoạt còi báo động SOS,\ngửi tọa độ cứu nạn cho người thân')
        ]
    },
    'service': {
        'layer_name': ('Service Layer', 'Tầng Dịch vụ'),
        'header': 'Dịch vụ xử lý dữ liệu & Trí tuệ nhân tạo (Database and Processing)',
        'items': [
            ('FastAPI Cloud Server', 'Xử lý bất đồng bộ, định tuyến API\nvà phân phối lệnh tìm gậy / tắt còi'),
            ('SQLite WAL Database', 'Lưu trữ dữ liệu đo (Telemetry),\nnhật ký rung/còi và sự kiện khẩn cấp'),
            ('Dual-Engine AI Vision', 'Mô hình SegFormer / Gemini nhận diện\nvật cản trên cao, vũng nước & lòng đường')
        ]
    },
    'network': {
        'layer_name': ('Network Layer', 'Tầng Mạng'),
        'header': 'Môi trường truyền thông & Giao thức (Medium and Technology)',
        'items': [
            ('Mạng nội bộ ESP-NOW', 'Sóng MAC 2.4GHz kết nối trực tiếp\ngiữa Áo ↔ Gậy với độ trễ < 5ms'),
            ('Wi-Fi / 4G Hotspot', 'Kết nối Internet di động chuẩn 802.11\nqua điểm phát sóng của điện thoại'),
            ('RESTful HTTPS API', 'Giao thức truyền dữ liệu tiêu chuẩn Web,\ndễ dàng vượt tường lửa nhà mạng 4G')
        ]
    },
    'device': {
        'layer_name': ('Device Layer', 'Tầng Thiết bị'),
        'header': 'Phần cứng & Thiết bị ngoại vi (Devices - Sensors, Actuators, Controllers)',
        'items': [
            ('Cảm biến (Sensors)', 'HC-SR04 (quét cự ly 2-400cm),\nCamera OV2640 2MP, MPU-6050 (rơi gậy)'),
            ('Bộ điều khiển (Controllers)', 'ESP32 DevKit V1 (Khối Áo trung tâm)\n& ESP32-C3 Super Mini (Khối Gậy)'),
            ('Cơ cấu chấp hành (Actuators)', 'Motor rung xúc giác PWM, Active Buzzer\n(còi báo động) & 4 Nút bấm khẩn cấp')
        ]
    }
}

# Data for Generic IoT Logical Diagram (Textbook PTIT)
data_generic_logic = {
    'management': {
        'title': 'Management',
        'items': [
            'Device\nManagement',
            'Resource\nManagement',
            'Fault\nManagement',
            'Performance\nMonitoring'
        ]
    },
    'security': {
        'title': 'Security',
        'items': [
            'Data\nConfidentiality',
            'Data\nIntegrity',
            'Authentication\n& Authorization',
            'Availability\nProtection'
        ]
    },
    'application': {
        'layer_name': ('Application Layer', ''),
        'header': 'Applications Provided',
        'items': [
            'Smart Health',
            'Smart Farming',
            'Smart City'
        ]
    },
    'service': {
        'layer_name': ('Service Layer', ''),
        'header': 'Database and Processing',
        'items': [
            ('Database', 'Data Storage & Management'),
            ('Ubiquitous Computing', 'Context-aware processing'),
            ('Information Processing', 'Analytics & Decision Making')
        ]
    },
    'network': {
        'layer_name': ('Network Layer', ''),
        'header': 'Medium and Technology',
        'items': [
            ('Wi-Fi', '802.11 b/g/n / ac'),
            ('Gateway / Router', 'Mesh / Coordinator'),
            ('Cellular 3G / 4G / 5G', 'Wide Area Network')
        ]
    },
    'device': {
        'layer_name': ('Device Layer', ''),
        'header': 'Devices',
        'items': [
            ('Sensors', 'Temperature, Proximity, Light...'),
            ('Controllers', 'Microcontrollers & SoCs'),
            ('Actuators', 'Relays, Motors, Buzzers...')
        ]
    }
}

output_dir = Path(r"c:\Users\admin\Downloads\dong-hanh-hop-nhat\dong-hanh-hop-nhat\docs")

create_logical_diagram(
    data_dong_hanh_logic,
    output_dir / "thiet-ke-logic-iot-dong-hanh.png",
    output_dir / "thiet-ke-logic-iot-dong-hanh.svg",
    title_text="Thiết kế logic của hệ thống IoT",
    subtitle='Đề tài: Hệ thống hỗ trợ người khiếm thị di chuyển an toàn "Đồng Hành"',
    caption_text="Hình 2.2: Sơ đồ khối chức năng và thiết kế logic của hệ thống IoT Đồng Hành"
)

create_logical_diagram(
    data_generic_logic,
    output_dir / "thiet-ke-logic-iot-chung.png",
    output_dir / "thiet-ke-logic-iot-chung.svg",
    title_text="Thiết kế logic của IoT",
    subtitle="Học viện Công nghệ Bưu chính Viễn thông",
    caption_text="Sơ đồ khối chức năng của hệ thống IoT (IoT Functional Blocks & Layers)",
    is_dong_hanh=False
)
