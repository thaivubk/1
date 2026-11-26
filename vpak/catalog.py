"""Danh sách phòng và agent: nguồn duy nhất cho giao diện và trạng thái."""

ROOMS = [
    {"id": "tt", "name": "Phòng Thanh toán", "short": "Thanh toán", "color": "#0F766E"},
    {"id": "qt", "name": "Phòng Quyết toán", "short": "Quyết toán", "color": "#6D28D9"},
    {"id": "sx", "name": "Phòng Soát xét", "short": "Soát xét", "color": "#BE185D"},
    {"id": "dp", "name": "Điều phối & Tổng hợp", "short": "Điều phối", "color": "#1F3A5F"},
    {"id": "qd", "name": "Phòng Quy trình – Quy định", "short": "Quy trình – Quy định", "color": "#92400E"},
    {"id": "cd", "name": "Phòng Công đoàn", "short": "Công đoàn", "color": "#4D7C0F"},
]


def _a(name, tag, room, role, acc=""):
    return {"name": name, "tag": tag, "room": room, "role": role, "acc": acc}


AGENTS = {
    "giao-viec": _a("Giao việc", "Giao việc", "dp", "Điều phối: nhận lệnh, xem nhanh thư mục, chia việc", "headset"),
    "tong-hop": _a("Tổng hợp", "Tổng hợp", "dp", "Tạo file theo mẫu, lập phiếu, báo Telegram ngắn gọn", "tie"),
    "liet-ke-ho-so": _a("Liệt kê hồ sơ", "Liệt kê HS", "tt", "Liệt kê file cả thư mục con, cộng dồn list hồ sơ dự án"),
    "doi-chieu-hop-dong": _a("Đối chiếu HĐ", "Đối chiếu HĐ", "tt", "Đối chiếu giá trị với điều khoản thanh toán"),
    "tong-hop-gia-tri": _a("Tổng hợp giá trị", "Tổng hợp GT", "qt", "Tổng hợp giá trị đề nghị quyết toán"),
    "doi-chieu-so-lieu": _a("Đối chiếu số liệu", "Đối chiếu SL", "qt", "Khớp số đã thanh toán với số liệu kế toán"),
    "soat-cap-1": _a("Cấp 1 · Đủ hồ sơ", "Cấp 1", "sx", "Đủ chứng từ, đúng mẫu, đủ chữ ký", "glasses"),
    "soat-cap-2": _a("Cấp 2 · Logic", "Cấp 2", "sx", "Số tiền, ngày, tên, số hiệu khớp nhau giữa các văn bản", "glasses"),
    "soat-cap-3": _a("Cấp 3 · Lỗi hay gặp", "Cấp 3", "sx", "Soát theo trí nhớ: lỗi hay gặp, điểm sếp hay xem", "glasses"),
    "van-ban-moi": _a("Văn bản mới", "Văn bản mới", "qd", "Đọc văn bản mới, tóm tắt điểm thay đổi"),
    "tra-cuu-van-ban": _a("Tra cứu văn bản", "Tra cứu VB", "qd", "Tra app tra cứu của đại ca, không có thì tra Internet"),
    "doc-so-cai": _a("Đọc sổ cái", "Đọc sổ cái", "cd", "Đọc Excel sổ cái, lấy phần thu và chi"),
    "bao-cao-thu-chi": _a("Báo cáo thu chi", "Báo cáo TC", "cd", "Nhặt thu chi vào báo cáo thu chi"),
}

ROOM_COLOR = {r["id"]: r["color"] for r in ROOMS}


def agent_color(agent_id: str) -> str:
    a = AGENTS.get(agent_id)
    return ROOM_COLOR[a["room"]] if a else "#1F3A5F"
