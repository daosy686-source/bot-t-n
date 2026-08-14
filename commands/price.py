"""
Lệnh /price (xem bảng giá công khai) và nhóm lệnh /price-admin
(add / edit / remove / list — chỉ Admin) để quản lý bảng giá mà không cần
sửa source code.

Lưu ý kỹ thuật: Discord không cho phép một slash command vừa có thể gọi trực
tiếp (/price) vừa là group chứa subcommand (/price add...) cùng lúc. Vì vậy
việc xem bảng giá dùng lệnh gốc "/price" (đúng như yêu cầu), còn việc quản lý
được tách sang group riêng "/price-admin add|edit|remove|list".
"""
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from database.models import (
    CATEGORY_BUC_SIVI,
    CATEGORY_DECA0_LOGIN,
    CATEGORY_DECA0R_LINK,
    CATEGORY_LABELS,
    ADDON_NO_SW_NAICHOBS,
    CUSTOM_QUOTE_VALUE,
    Product,
)
from utils.embeds import (
    build_category_embed,
    build_note_embed,
    build_payment_embed,
    build_price_main_embed,
    format_price,
)
from utils.logger import log_event
from commands.order import BucSiviLinkModal, create_order, is_admin

CATEGORY_CHOICES = [
    app_commands.Choice(name=CATEGORY_LABELS[CATEGORY_DECA0_LOGIN], value=CATEGORY_DECA0_LOGIN),
    app_commands.Choice(name=CATEGORY_LABELS[CATEGORY_DECA0R_LINK], value=CATEGORY_DECA0R_LINK),
    app_commands.Choice(name=CATEGORY_LABELS[CATEGORY_BUC_SIVI], value=CATEGORY_BUC_SIVI),
]


# ---------------------------------------------------------------------------
# View: bảng giá chính (5 nút)
# ---------------------------------------------------------------------------
def build_price_main_view() -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(
        discord.ui.Button(label="Deca0 Login", emoji="🔐", style=discord.ButtonStyle.primary, custom_id="pb:cat:deca0_login")
    )
    view.add_item(
        discord.ui.Button(label="Deca0R/NPL/Frames", emoji="🎁", style=discord.ButtonStyle.primary, custom_id="pb:cat:deca0r_link")
    )
    view.add_item(
        discord.ui.Button(label="Búc Sivi", emoji="⚡", style=discord.ButtonStyle.primary, custom_id="pb:cat:buc_sivi")
    )
    view.add_item(
        discord.ui.Button(label="Lưu ý", emoji="📌", style=discord.ButtonStyle.secondary, custom_id="pb:note")
    )
    view.add_item(
        discord.ui.Button(label="Thanh toán", emoji="💳", style=discord.ButtonStyle.secondary, custom_id="pb:payment")
    )
    return view


def build_product_select_view(category: str, products: list) -> discord.ui.View:
    view = discord.ui.View(timeout=180)
    select = discord.ui.Select(
        custom_id=f"pb:select:{category}",
        placeholder="Chọn sản phẩm để đặt hàng...",
        min_values=1,
        max_values=1,
    )

    if category == CATEGORY_DECA0_LOGIN:
        for p in products:
            select.add_option(
                label=p.name[:100],
                description=f"{format_price(p.original_price)} ➜ {format_price(p.sale_price)}"[:100],
                value=f"{p.product_id}|0",
            )
            select.add_option(
                label=f"{p.name} (không sw_naichobs)"[:100],
                description=(
                    f"{format_price(p.original_price)} ➜ "
                    f"{format_price(p.sale_price + ADDON_NO_SW_NAICHOBS)}"
                )[:100],
                value=f"{p.product_id}|1",
            )
    elif category == CATEGORY_BUC_SIVI:
        for p in products:
            select.add_option(
                label=p.name[:100],
                description=format_price(p.sale_price)[:100],
                value=p.product_id,
            )
        select.add_option(
            label="Búc lẻ (tạo ticket để báo giá)",
            description="Không mua gói cố định — tạo ticket riêng",
            value=CUSTOM_QUOTE_VALUE,
        )
    else:  # CATEGORY_DECA0R_LINK
        for p in products:
            select.add_option(
                label=p.name[:100],
                description=f"{format_price(p.original_price)} ➜ {format_price(p.sale_price)}"[:100],
                value=p.product_id,
            )

    view.add_item(select)
    return view


# ---------------------------------------------------------------------------
# Handlers gọi từ events/on_interaction.py
# ---------------------------------------------------------------------------
async def handle_category_button(interaction: discord.Interaction, category: str):
    db = interaction.client.db
    products = await db.list_products(category=category, active_only=True)
    embed = build_category_embed(category, products)
    if not products:
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    view = build_product_select_view(category, products)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def handle_note_button(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_note_embed(), ephemeral=True)


async def handle_payment_button(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_payment_embed(), ephemeral=True)


async def handle_product_select(interaction: discord.Interaction, category: str):
    bot = interaction.client
    db = bot.db
    value = interaction.data["values"][0]

    if category == CATEGORY_BUC_SIVI and value == CUSTOM_QUOTE_VALUE:
        config = await db.get_guild_config(interaction.guild_id)
        if config and config.ticket_channel_id:
            await interaction.response.send_message(
                f"📩 Vui lòng tạo ticket tại <#{config.ticket_channel_id}> để được báo giá búc lẻ.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "📩 Vui lòng liên hệ Staff để được báo giá búc lẻ (kênh Ticket chưa được cấu hình).",
                ephemeral=True,
            )
        return

    if category == CATEGORY_DECA0_LOGIN:
        product_id, addon_flag = value.split("|", 1)
        product = await db.get_product(product_id)
        if not product or not product.is_active:
            await interaction.response.send_message("⚠️ Sản phẩm không còn khả dụng.", ephemeral=True)
            return
        await create_order(bot, interaction, product, addon_no_sw=(addon_flag == "1"))
        return

    if category == CATEGORY_BUC_SIVI:
        product = await db.get_product(value)
        if not product or not product.is_active:
            await interaction.response.send_message("⚠️ Sản phẩm không còn khả dụng.", ephemeral=True)
            return
        await interaction.response.send_modal(BucSiviLinkModal(product))
        return

    # CATEGORY_DECA0R_LINK
    product = await db.get_product(value)
    if not product or not product.is_active:
        await interaction.response.send_message("⚠️ Sản phẩm không còn khả dụng.", ephemeral=True)
        return
    await create_order(bot, interaction, product, addon_no_sw=False)


# ---------------------------------------------------------------------------
# Cog: /price + /price-admin
# ---------------------------------------------------------------------------
class PriceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- /price : xem bảng giá -------------------------------------------
    @app_commands.command(name="price", description="Xem bảng giá sản phẩm")
    async def price(self, interaction: discord.Interaction):
        embed = build_price_main_embed()
        view = build_price_main_view()
        await interaction.response.send_message(embed=embed, view=view)

    # --- /price-admin : quản lý bảng giá (group con) ----------------------
    price_admin = app_commands.Group(name="price-admin", description="Quản lý bảng giá (chỉ Admin)")

    async def _check_admin(self, interaction: discord.Interaction) -> bool:
        config = await self.bot.db.get_guild_config(interaction.guild_id)
        if not is_admin(interaction.user, config):
            await interaction.response.send_message("⛔ Chỉ Admin mới có thể dùng lệnh này.", ephemeral=True)
            return False
        return True

    @price_admin.command(name="add", description="Thêm sản phẩm mới")
    @app_commands.describe(
        product_id="Mã sản phẩm duy nhất (vd: d0-11)",
        category="Danh mục sản phẩm",
        name="Tên sản phẩm hiển thị",
        sale_price="Giá bán (VNĐ)",
        original_price="Giá gốc (VNĐ) — để trống nếu không có",
        note="Ghi chú thêm (tùy chọn)",
    )
    @app_commands.choices(category=CATEGORY_CHOICES)
    async def price_add(
        self,
        interaction: discord.Interaction,
        product_id: str,
        category: app_commands.Choice[str],
        name: str,
        sale_price: int,
        original_price: Optional[int] = None,
        note: Optional[str] = None,
    ):
        if not await self._check_admin(interaction):
            return
        existing = await self.bot.db.get_product(product_id)
        if existing:
            await interaction.response.send_message(f"⚠️ Mã sản phẩm `{product_id}` đã tồn tại.", ephemeral=True)
            return
        product = Product(
            product_id=product_id,
            category=category.value,
            name=name,
            sale_price=sale_price,
            original_price=original_price,
            note=note,
        )
        await self.bot.db.add_product(product)
        await interaction.response.send_message(
            f"✅ Đã thêm sản phẩm **{name}** (`{product_id}`) — {format_price(sale_price)}.", ephemeral=True
        )
        await log_event(self.bot, interaction.guild_id, "💰", f"{interaction.user.mention} đã thêm sản phẩm `{product_id}` — {name}")

    @price_admin.command(name="edit", description="Sửa thông tin sản phẩm")
    @app_commands.describe(
        product_id="Mã sản phẩm cần sửa",
        name="Tên mới (tùy chọn)",
        sale_price="Giá bán mới (tùy chọn)",
        original_price="Giá gốc mới (tùy chọn)",
        note="Ghi chú mới (tùy chọn)",
        active="Bật/tắt hiển thị sản phẩm (tùy chọn)",
    )
    async def price_edit(
        self,
        interaction: discord.Interaction,
        product_id: str,
        name: Optional[str] = None,
        sale_price: Optional[int] = None,
        original_price: Optional[int] = None,
        note: Optional[str] = None,
        active: Optional[bool] = None,
    ):
        if not await self._check_admin(interaction):
            return
        existing = await self.bot.db.get_product(product_id)
        if not existing:
            await interaction.response.send_message(f"⚠️ Không tìm thấy sản phẩm `{product_id}`.", ephemeral=True)
            return

        updates = {}
        if name is not None:
            updates["name"] = name
        if sale_price is not None:
            updates["sale_price"] = sale_price
        if original_price is not None:
            updates["original_price"] = original_price
        if note is not None:
            updates["note"] = note
        if active is not None:
            updates["is_active"] = int(active)

        if not updates:
            await interaction.response.send_message("⚠️ Bạn chưa cung cấp thông tin nào để sửa.", ephemeral=True)
            return

        await self.bot.db.edit_product(product_id, **updates)
        await interaction.response.send_message(f"✅ Đã cập nhật sản phẩm `{product_id}`.", ephemeral=True)
        await log_event(self.bot, interaction.guild_id, "💰", f"{interaction.user.mention} đã sửa sản phẩm `{product_id}`")

    @price_admin.command(name="remove", description="Xóa sản phẩm")
    @app_commands.describe(product_id="Mã sản phẩm cần xóa")
    async def price_remove(self, interaction: discord.Interaction, product_id: str):
        if not await self._check_admin(interaction):
            return
        removed = await self.bot.db.remove_product(product_id)
        if removed:
            await interaction.response.send_message(f"🗑️ Đã xóa sản phẩm `{product_id}`.", ephemeral=True)
            await log_event(self.bot, interaction.guild_id, "💰", f"{interaction.user.mention} đã xóa sản phẩm `{product_id}`")
        else:
            await interaction.response.send_message(f"⚠️ Không tìm thấy sản phẩm `{product_id}`.", ephemeral=True)

    @price_admin.command(name="list", description="Liệt kê toàn bộ sản phẩm (kể cả đã ẩn)")
    async def price_list(self, interaction: discord.Interaction):
        if not await self._check_admin(interaction):
            return
        products = await self.bot.db.list_products(active_only=False)
        if not products:
            await interaction.response.send_message("Chưa có sản phẩm nào.", ephemeral=True)
            return

        embed = discord.Embed(title="📋 Danh sách sản phẩm (Admin)", color=0x3498DB)
        by_category = {}
        for p in products:
            by_category.setdefault(p.category, []).append(p)

        for category, items in by_category.items():
            lines = []
            for p in items:
                status = "🟢" if p.is_active else "🔴"
                price_str = f"{format_price(p.original_price)} ➜ {format_price(p.sale_price)}" if p.original_price else format_price(p.sale_price)
                lines.append(f"{status} `{p.product_id}` — {p.name} — {price_str}")
            embed.add_field(
                name=CATEGORY_LABELS.get(category, category),
                value="\n".join(lines)[:1024],
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PriceCog(bot))
