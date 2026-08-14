"""
Toàn bộ bảng giá sản phẩm (dữ liệu khởi tạo ban đầu) và các nội dung Lưu ý /
Thanh toán. Dữ liệu này chỉ được dùng để "seed" (khởi tạo) database ở lần
chạy đầu tiên — sau đó Admin quản lý giá hoàn toàn qua lệnh /price-admin
(add / edit / remove / list), KHÔNG cần sửa file này nữa.
"""
from database.models import CATEGORY_BUC_SIVI, CATEGORY_DECA0_LOGIN, CATEGORY_DECA0R_LINK

# ---------------------------------------------------------------------------
# Emoji tùy chỉnh (theo server gốc) — dùng trong các embed
# ---------------------------------------------------------------------------
EMOJI_DECA0 = "<:decaor:1480867163832193044>"
EMOJI_SW_NAICHOBS = "<:sw_naichobs:1519032286371123401>"
EMOJI_SVBUC = "<:sw_svbuc:1480867163832193044>"

# ---------------------------------------------------------------------------
# Danh sách sản phẩm khởi tạo
# ---------------------------------------------------------------------------
DEFAULT_PRODUCTS = [
    # --- Deca0 — Dạng Login -------------------------------------------------
    {"product_id": "d0-01", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 66k",  "original_price": 66000,  "sale_price": 32000},
    {"product_id": "d0-02", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 79k",  "original_price": 79000,  "sale_price": 38000},
    {"product_id": "d0-03", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 92k",  "original_price": 92000,  "sale_price": 57000},
    {"product_id": "d0-04", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 105k", "original_price": 105000, "sale_price": 67000},
    {"product_id": "d0-05", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 111k", "original_price": 111000, "sale_price": 71000},
    {"product_id": "d0-06", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 118k", "original_price": 118000, "sale_price": 81000},
    {"product_id": "d0-07", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 131k", "original_price": 131000, "sale_price": 91000},
    {"product_id": "d0-08", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 141k", "original_price": 141000, "sale_price": 101000},
    {"product_id": "d0-09", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 146k", "original_price": 146000, "sale_price": 104000},
    {"product_id": "d0-10", "category": CATEGORY_DECA0_LOGIN, "name": "Deca0 Login — Gói 189k", "original_price": 189000, "sale_price": 120000},

    # --- Deca0R / NPL / Frames — Dạng Link (giao qua link, không cần login) --
    {"product_id": "d0r-01", "category": CATEGORY_DECA0R_LINK, "name": "Deca0R/NPL/Frames — Gói 66k",  "original_price": 66000,  "sale_price": 50000},
    {"product_id": "d0r-02", "category": CATEGORY_DECA0R_LINK, "name": "Deca0R/NPL/Frames — Gói 79k",  "original_price": 79000,  "sale_price": 70000},
    {"product_id": "d0r-03", "category": CATEGORY_DECA0R_LINK, "name": "Deca0R/NPL/Frames — Gói 92k",  "original_price": 92000,  "sale_price": 70000},
    {"product_id": "d0r-04", "category": CATEGORY_DECA0R_LINK, "name": "Deca0R/NPL/Frames — Gói 105k", "original_price": 105000, "sale_price": 75000},
    {"product_id": "d0r-05", "category": CATEGORY_DECA0R_LINK, "name": "Deca0R/NPL/Frames — Gói 111k", "original_price": 111000, "sale_price": 80000},
    {"product_id": "d0r-06", "category": CATEGORY_DECA0R_LINK, "name": "Deca0R/NPL/Frames — Gói 131k", "original_price": 131000, "sale_price": 105000},
    {"product_id": "d0r-07", "category": CATEGORY_DECA0R_LINK, "name": "Deca0R/NPL/Frames — Gói 141k", "original_price": 141000, "sale_price": 115000},

    # --- Búc Sivi -------------------------------------------------------------
    {"product_id": "bs-x14-1m", "category": CATEGORY_BUC_SIVI, "name": "Búc Sivi x14 — 1 tháng", "original_price": None, "sale_price": 130000, "note": "Bảo hành 2 tuần"},
    {"product_id": "bs-x14-3m", "category": CATEGORY_BUC_SIVI, "name": "Búc Sivi x14 — 3 tháng", "original_price": None, "sale_price": 335000, "note": "Bảo hành full time"},
    {"product_id": "bs-x2-1m",  "category": CATEGORY_BUC_SIVI, "name": "Búc Sivi x2 — 1 tháng (chỉ nhận chẵn)", "original_price": None, "sale_price": 35000, "note": "Chỉ nhận chẵn — Bảo hành 2 tuần"},
    {"product_id": "bs-x2-3m",  "category": CATEGORY_BUC_SIVI, "name": "Búc Sivi x2 — 3 tháng (chỉ nhận chẵn)", "original_price": None, "sale_price": 40000, "note": "Chỉ nhận chẵn — Bảo hành full time"},
]

# ---------------------------------------------------------------------------
# Nội dung "Lưu ý" theo từng danh mục
# ---------------------------------------------------------------------------
NOTES = {
    CATEGORY_DECA0_LOGIN: (
        f"• Tài khoản không có {EMOJI_SW_NAICHOBS}: **+9.000 VNĐ**\n"
        "• Yêu cầu khách cung cấp tài khoản, mật khẩu, mã 2FA hoặc backup code "
        "**trực tiếp cho Staff qua tin nhắn riêng** sau khi đơn được nhận "
        "(Bot không thu thập hay lưu các thông tin này).\n"
        "• Sau khi hoàn thành đơn, khách có **12 giờ** để đổi mật khẩu.\n"
        "• Shop chỉ đăng nhập để hoàn thành đơn và đăng xuất ngay sau khi xong.\n"
        "• Nếu lỗi do shop: hoàn **70%** giá trị đơn hoặc sản phẩm tương ứng.\n"
        "• Nếu lỗi do khách: **không** được bảo hành/đền bù."
    ),
    CATEGORY_DECA0R_LINK: (
        "• Hình thức nhận qua **Link**, không cần đăng nhập tài khoản.\n"
        "• Bot gửi Link trực tiếp cho khách sau khi đơn hoàn thành.\n"
        "• Khách chỉ cần **Claim** vào tài khoản của mình.\n"
        "• Không cần cung cấp mật khẩu."
    ),
    CATEGORY_BUC_SIVI: (
        "• Yêu cầu Link server để búc (nhập khi đặt hàng).\n"
        "• Có hỗ trợ **búc lẻ** — chọn mục tương ứng để tạo ticket báo giá.\n"
        "• Giá có thể thay đổi.\n"
        "• Thời gian hoàn thành: **24–48 giờ**.\n"
        "• Gói 1 tháng: bảo hành 2 tuần. Gói 3 tháng: bảo hành full time."
    ),
}

PAYMENT_NOTE = (
    "💳 **Búc Sivi**: thanh toán bằng thẻ cào — chiết khấu **20%**.\n\n"
    "💳 **Các sản phẩm khác**: phương thức thanh toán sẽ được Staff trao đổi "
    "trực tiếp cùng bạn sau khi đơn được nhận."
)
