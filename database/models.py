"""
Định nghĩa cấu trúc dữ liệu: hằng số trạng thái/loại sản phẩm, dataclass
đại diện cho các bảng, và schema SQL để khởi tạo database.
"""
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Trạng thái đơn hàng
# ---------------------------------------------------------------------------
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

STATUS_EMOJI = {
    STATUS_PENDING: "🟡",
    STATUS_PROCESSING: "🔵",
    STATUS_COMPLETED: "🟢",
    STATUS_CANCELLED: "🔴",
}

STATUS_LABEL_VI = {
    STATUS_PENDING: "Chờ xử lý",
    STATUS_PROCESSING: "Đang xử lý",
    STATUS_COMPLETED: "Hoàn thành",
    STATUS_CANCELLED: "Đã hủy",
}

# ---------------------------------------------------------------------------
# Loại / danh mục sản phẩm
# ---------------------------------------------------------------------------
CATEGORY_DECA0_LOGIN = "deca0_login"       # Dạng Login - cần tài khoản/mật khẩu
CATEGORY_DECA0R_LINK = "deca0r_link"       # Dạng Link - giao qua link, không cần login
CATEGORY_BUC_SIVI = "buc_sivi"             # Búc Sivi

CATEGORY_LABELS = {
    CATEGORY_DECA0_LOGIN: "Deca0 — Dạng Login",
    CATEGORY_DECA0R_LINK: "Deca0R / NPL / Frames — Dạng Link",
    CATEGORY_BUC_SIVI: "Búc Sivi",
}

# Các danh mục giao hàng bằng Link (staff phải nhập link khi bấm Hoàn thành)
LINK_DELIVERY_CATEGORIES = {CATEGORY_DECA0R_LINK}

# Các danh mục yêu cầu khách cung cấp thông tin đăng nhập (không lưu trong DB)
LOGIN_REQUIRED_CATEGORIES = {CATEGORY_DECA0_LOGIN}

# Phụ phí khi khách chọn tài khoản không có sw_naichobs (chỉ áp dụng Deca0 Login)
ADDON_NO_SW_NAICHOBS = 9000

# Giá trị đặc biệt cho lựa chọn "Búc lẻ" (không phải sản phẩm thật, chỉ điều
# hướng khách sang tạo ticket để được báo giá)
CUSTOM_QUOTE_VALUE = "CUSTOM_QUOTE"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class GuildConfig:
    guild_id: int
    order_channel_id: Optional[int] = None
    log_channel_id: Optional[int] = None
    price_channel_id: Optional[int] = None
    staff_role_id: Optional[int] = None
    admin_role_id: Optional[int] = None
    ticket_channel_id: Optional[int] = None


@dataclass
class Product:
    product_id: str
    category: str
    name: str
    sale_price: int
    original_price: Optional[int] = None
    note: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


@dataclass
class Order:
    order_id: str
    guild_id: int
    user_id: int
    product_id: str
    product_name: str
    category: str
    sale_price: int
    original_price: Optional[int] = None
    addon_no_sw: bool = False
    customer_note: Optional[str] = None
    link_data: Optional[str] = None
    status: str = STATUS_PENDING
    staff_id: Optional[int] = None
    created_at: Optional[str] = None
    processing_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    cancel_reason: Optional[str] = None
    dm_notified: bool = False
    channel_id: Optional[int] = None
    message_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Schema SQL
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id            INTEGER PRIMARY KEY,
    order_channel_id    INTEGER,
    log_channel_id      INTEGER,
    price_channel_id    INTEGER,
    staff_role_id       INTEGER,
    admin_role_id       INTEGER,
    ticket_channel_id   INTEGER
);

CREATE TABLE IF NOT EXISTS products (
    product_id      TEXT PRIMARY KEY,
    category        TEXT NOT NULL,
    name            TEXT NOT NULL,
    original_price  INTEGER,
    sale_price      INTEGER NOT NULL,
    note            TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        TEXT PRIMARY KEY,
    guild_id        INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    product_id      TEXT NOT NULL,
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    original_price  INTEGER,
    sale_price      INTEGER NOT NULL,
    addon_no_sw     INTEGER NOT NULL DEFAULT 0,
    customer_note   TEXT,
    link_data       TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    staff_id        INTEGER,
    created_at      TEXT NOT NULL,
    processing_at   TEXT,
    completed_at    TEXT,
    cancelled_at    TEXT,
    cancel_reason   TEXT,
    dm_notified     INTEGER NOT NULL DEFAULT 0,
    channel_id      INTEGER,
    message_id      INTEGER
);

CREATE TABLE IF NOT EXISTS order_counter (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    counter INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_orders_guild ON orders(guild_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
"""
