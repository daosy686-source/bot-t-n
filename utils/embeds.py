"""
Toàn bộ các hàm dựng Embed dùng trong bot: bảng giá, đơn hàng, DM khách hàng.
"""
from typing import List, Optional

import discord

from config.settings import EMBED_COLOR, EMBED_COLOR_INFO
from database.models import (
    CATEGORY_LABELS,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_EMOJI,
    STATUS_LABEL_VI,
    STATUS_PENDING,
    STATUS_PROCESSING,
    Order,
    Product,
)
from products.prices import EMOJI_DECA0, EMOJI_SVBUC, NOTES, PAYMENT_NOTE

STATUS_COLOR = {
    STATUS_PENDING: 0xF1C40F,
    STATUS_PROCESSING: 0x3498DB,
    STATUS_COMPLETED: 0x2ECC71,
    STATUS_CANCELLED: 0xE74C3C,
}


def format_price(value: Optional[int]) -> str:
    if value is None:
        return "Liên hệ"
    return f"{value:,.0f}".replace(",", ".") + " VNĐ"


# ---------------------------------------------------------------------------
# Bảng giá
# ---------------------------------------------------------------------------
def build_price_main_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📋 BẢNG GIÁ SẢN PHẨM",
        description=(
            "Chọn một mục bên dưới để xem chi tiết sản phẩm và đặt hàng.\n"
            "Nhấn **📌 Lưu ý** và **💳 Thanh toán** để biết thêm điều khoản."
        ),
        color=EMBED_COLOR,
    )
    embed.add_field(
        name=f"{EMOJI_DECA0} Deca0 — Dạng Login",
        value="Tài khoản đăng nhập trực tiếp.",
        inline=False,
    )
    embed.add_field(
        name="🎁 Deca0R / NPL / Frames — Dạng Link",
        value="Giao qua Link, không cần đăng nhập.",
        inline=False,
    )
    embed.add_field(
        name=f"{EMOJI_SVBUC} Búc Sivi",
        value="Búc theo gói hoặc báo giá lẻ qua ticket.",
        inline=False,
    )
    embed.set_footer(text="Nhấn nút bên dưới để tiếp tục")
    return embed


def build_category_embed(category: str, products: List[Product]) -> discord.Embed:
    label = CATEGORY_LABELS.get(category, category)
    embed = discord.Embed(title=f"📦 {label}", color=EMBED_COLOR)
    lines = []
    for p in products:
        if p.original_price:
            price_str = f"~~{format_price(p.original_price)}~~ ➜ **{format_price(p.sale_price)}**"
        else:
            price_str = f"**{format_price(p.sale_price)}**"
        note = f" _{p.note}_" if p.note else ""
        lines.append(f"• **{p.name}** — {price_str}{note}")
    embed.description = "\n".join(lines) if lines else "Hiện chưa có sản phẩm."
    embed.add_field(name="📌 Lưu ý", value=NOTES.get(category, "Không có."), inline=False)
    embed.set_footer(text="Chọn sản phẩm ở menu bên dưới để đặt hàng")
    return embed


def build_note_embed() -> discord.Embed:
    embed = discord.Embed(title="📌 LƯU Ý CHUNG", color=EMBED_COLOR_INFO)
    for category, text in NOTES.items():
        embed.add_field(name=CATEGORY_LABELS.get(category, category), value=text, inline=False)
    return embed


def build_payment_embed() -> discord.Embed:
    embed = discord.Embed(title="💳 THANH TOÁN", description=PAYMENT_NOTE, color=EMBED_COLOR_INFO)
    return embed


# ---------------------------------------------------------------------------
# Đơn hàng
# ---------------------------------------------------------------------------
def build_order_embed(
    order: Order,
    customer: Optional[discord.abc.User] = None,
    staff: Optional[discord.abc.User] = None,
) -> discord.Embed:
    emoji = STATUS_EMOJI.get(order.status, "⚪")
    label = STATUS_LABEL_VI.get(order.status, order.status)
    color = STATUS_COLOR.get(order.status, EMBED_COLOR)

    title = {
        STATUS_PENDING: "📦 ĐƠN HÀNG ĐÃ TIẾP NHẬN",
        STATUS_PROCESSING: "🔄 ĐƠN HÀNG ĐANG XỬ LÝ",
        STATUS_COMPLETED: "✅ ĐƠN HÀNG HOÀN THÀNH",
        STATUS_CANCELLED: "❌ ĐƠN HÀNG ĐÃ HỦY",
    }.get(order.status, "📦 ĐƠN HÀNG")

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="Mã đơn", value=f"`{order.order_id}`", inline=True)
    customer_mention = customer.mention if customer else f"<@{order.user_id}>"
    embed.add_field(name="Khách hàng", value=customer_mention, inline=True)
    embed.add_field(name="Sản phẩm", value=order.product_name, inline=False)
    embed.add_field(name="Giá", value=format_price(order.sale_price), inline=True)

    if order.staff_id:
        staff_mention = staff.mention if staff else f"<@{order.staff_id}>"
        embed.add_field(name="Người xử lý", value=staff_mention, inline=True)

    if order.customer_note:
        embed.add_field(name="Ghi chú", value=order.customer_note, inline=False)

    if order.status == STATUS_CANCELLED and order.cancel_reason:
        embed.add_field(name="Lý do hủy", value=order.cancel_reason, inline=False)

    embed.add_field(name="Trạng thái", value=f"{emoji} {label}", inline=False)
    embed.timestamp = discord.utils.utcnow()
    embed.set_footer(text="Order Management Bot")
    return embed


def build_cancel_confirm_embed(order: Order) -> discord.Embed:
    embed = discord.Embed(
        title="⚠️ Xác nhận hủy đơn hàng",
        description=(
            f"Bạn có chắc muốn hủy đơn `{order.order_id}` "
            f"({order.product_name} — {format_price(order.sale_price)}) không?"
        ),
        color=0xE67E22,
    )
    return embed


# ---------------------------------------------------------------------------
# DM khách hàng
# ---------------------------------------------------------------------------
def build_completed_dm_embed(order: Order) -> discord.Embed:
    embed = discord.Embed(
        title="📦 ĐƠN HÀNG CỦA BẠN ĐÃ HOÀN TẤT",
        description=(
            f"Xin chào <@{order.user_id}>!\n\n"
            f"Đơn hàng `{order.order_id}` của bạn đã hoàn tất."
        ),
        color=STATUS_COLOR[STATUS_COMPLETED],
    )
    embed.add_field(name="🛒 Sản phẩm", value=order.product_name, inline=False)
    embed.add_field(name="💰 Giá", value=format_price(order.sale_price), inline=True)
    embed.add_field(name="👤 Người xử lý", value=f"<@{order.staff_id}>", inline=True)
    embed.add_field(name="✅ Trạng thái", value="Hoàn tất", inline=True)
    if order.link_data:
        embed.add_field(name="🔗 Link", value=order.link_data, inline=False)
    embed.add_field(
        name="\u200b",
        value="Cảm ơn bạn đã sử dụng dịch vụ ❤️\nNếu có vấn đề, vui lòng liên hệ Staff/Support.",
        inline=False,
    )
    return embed


def build_cancelled_dm_embed(order: Order) -> discord.Embed:
    embed = discord.Embed(
        title="❌ ĐƠN HÀNG CỦA BẠN ĐÃ BỊ HỦY",
        description=(
            f"Xin chào <@{order.user_id}>, đơn hàng `{order.order_id}` "
            f"({order.product_name}) đã bị hủy."
        ),
        color=STATUS_COLOR[STATUS_CANCELLED],
    )
    if order.cancel_reason:
        embed.add_field(name="Lý do", value=order.cancel_reason, inline=False)
    embed.add_field(
        name="\u200b",
        value="Nếu có thắc mắc, vui lòng liên hệ Staff/Support.",
        inline=False,
    )
    return embed
