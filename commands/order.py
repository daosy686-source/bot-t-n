"""
Toàn bộ logic nghiệp vụ liên quan tới Đơn hàng: tạo đơn, nhận đơn, hoàn thành,
hủy đơn — cùng các View (nút bấm) và Modal (form nhập liệu) liên quan.

Các hàm handle_* được gọi từ events/on_interaction.py khi người dùng bấm nút.
"""
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from database.models import (
    CATEGORY_BUC_SIVI,
    CATEGORY_DECA0_LOGIN,
    LINK_DELIVERY_CATEGORIES,
    LOGIN_REQUIRED_CATEGORIES,
    ADDON_NO_SW_NAICHOBS,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    Order,
    Product,
)
from utils.dm import send_cancelled_dm, send_completed_dm
from utils.embeds import build_cancel_confirm_embed, build_order_embed, format_price
from utils.logger import log_event, logger


# ---------------------------------------------------------------------------
# Quyền hạn
# ---------------------------------------------------------------------------
def is_staff_or_admin(member: discord.Member, config) -> bool:
    if member.guild_permissions.administrator:
        return True
    if config is None:
        return False
    role_ids = {r.id for r in member.roles}
    if config.admin_role_id and config.admin_role_id in role_ids:
        return True
    if config.staff_role_id and config.staff_role_id in role_ids:
        return True
    return False


def is_admin(member: discord.Member, config) -> bool:
    if member.guild_permissions.administrator:
        return True
    if config and config.admin_role_id:
        return config.admin_role_id in {r.id for r in member.roles}
    return False


# ---------------------------------------------------------------------------
# View: nút hành động cho Staff (Nhận đơn / Hoàn thành / Hủy đơn)
# ---------------------------------------------------------------------------
def build_staff_action_view(order_id: str, status: str = STATUS_PENDING) -> discord.ui.View:
    view = discord.ui.View(timeout=None)

    accept_btn = discord.ui.Button(
        label="Nhận đơn",
        emoji="🔄",
        style=discord.ButtonStyle.primary,
        custom_id=f"ord:accept:{order_id}",
        disabled=status != STATUS_PENDING,
    )
    complete_btn = discord.ui.Button(
        label="Hoàn thành",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id=f"ord:complete:{order_id}",
        disabled=status not in (STATUS_PENDING, STATUS_PROCESSING),
    )
    cancel_btn = discord.ui.Button(
        label="Hủy đơn",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id=f"ord:cancel:{order_id}",
        disabled=status in (STATUS_COMPLETED, STATUS_CANCELLED),
    )
    view.add_item(accept_btn)
    view.add_item(complete_btn)
    view.add_item(cancel_btn)
    return view


def build_cancel_confirm_view(order_id: str) -> discord.ui.View:
    view = discord.ui.View(timeout=120)
    view.add_item(
        discord.ui.Button(
            label="Xác nhận hủy",
            emoji="✅",
            style=discord.ButtonStyle.danger,
            custom_id=f"ord:cancel_confirm:{order_id}",
        )
    )
    view.add_item(
        discord.ui.Button(
            label="Không hủy",
            emoji="↩️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"ord:cancel_abort:{order_id}",
        )
    )
    return view


# ---------------------------------------------------------------------------
# Helper nội bộ
# ---------------------------------------------------------------------------
async def _refresh_order_message(bot, order: Order, customer=None, staff=None):
    """Cập nhật lại Embed + nút bấm trên message gốc của đơn hàng."""
    if not order.channel_id or not order.message_id:
        return
    try:
        channel = bot.get_channel(order.channel_id) or await bot.fetch_channel(order.channel_id)
        message = await channel.fetch_message(order.message_id)
        embed = build_order_embed(order, customer=customer, staff=staff)
        view = build_staff_action_view(order.order_id, status=order.status)
        await message.edit(embed=embed, view=view)
    except discord.NotFound:
        logger.warning("Không tìm thấy message gốc của đơn %s để cập nhật.", order.order_id)
    except discord.HTTPException:
        logger.exception("Lỗi khi cập nhật message của đơn %s", order.order_id)


async def _resolve_user(bot, guild: Optional[discord.Guild], user_id: int):
    member = guild.get_member(user_id) if guild else None
    if member:
        return member
    try:
        return await bot.fetch_user(user_id)
    except discord.HTTPException:
        return None


async def _ack(interaction: discord.Interaction, content: str):
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=True)
    else:
        await interaction.response.send_message(content, ephemeral=True)


# ---------------------------------------------------------------------------
# Tạo đơn hàng
# ---------------------------------------------------------------------------
async def create_order(
    bot,
    interaction: discord.Interaction,
    product: Product,
    addon_no_sw: bool = False,
    customer_note: Optional[str] = None,
):
    db = bot.db
    config = await db.get_guild_config(interaction.guild_id)
    if not config or not config.order_channel_id:
        await _ack(
            interaction,
            "⚠️ Bot chưa được cấu hình. Vui lòng nhờ Admin chạy lệnh `/setup` trước.",
        )
        return

    order_channel = interaction.guild.get_channel(config.order_channel_id)
    if order_channel is None:
        await _ack(
            interaction,
            "⚠️ Không tìm thấy kênh đơn hàng đã cấu hình. Vui lòng chạy lại `/setup`.",
        )
        return

    order_id = await db.next_order_id()
    sale_price = product.sale_price + (ADDON_NO_SW_NAICHOBS if addon_no_sw else 0)
    product_name = product.name + (" (không có sw_naichobs)" if addon_no_sw else "")

    order = Order(
        order_id=order_id,
        guild_id=interaction.guild_id,
        user_id=interaction.user.id,
        product_id=product.product_id,
        product_name=product_name,
        category=product.category,
        original_price=product.original_price,
        sale_price=sale_price,
        addon_no_sw=addon_no_sw,
        customer_note=customer_note,
        status=STATUS_PENDING,
    )
    await db.create_order(order)

    embed = build_order_embed(order, customer=interaction.user)
    view = build_staff_action_view(order_id, status=STATUS_PENDING)
    msg = await order_channel.send(embed=embed, view=view)
    await db.set_order_message(order_id, msg.channel.id, msg.id)

    extra = ""
    if product.category in LOGIN_REQUIRED_CATEGORIES:
        extra = (
            "\n\n⚠️ Sau khi đơn được Staff nhận, vui lòng gửi **tài khoản, mật khẩu, "
            "mã 2FA hoặc backup code** trực tiếp cho Staff qua tin nhắn riêng (DM). "
            "Bot **không** thu thập hay lưu các thông tin này."
        )

    await _ack(interaction, f"✅ Đơn hàng `{order_id}` của bạn đã được tạo!{extra}")

    await log_event(
        bot,
        interaction.guild_id,
        "📦",
        f"Đơn hàng mới `{order_id}` được tạo bởi {interaction.user.mention} — "
        f"{product_name} ({format_price(sale_price)})",
    )


# ---------------------------------------------------------------------------
# Modals
# ---------------------------------------------------------------------------
class BucSiviLinkModal(discord.ui.Modal):
    def __init__(self, product: Product):
        super().__init__(
            title=f"Đặt hàng: {product.name}"[:45],
            custom_id=f"ord:modal:create_buc:{product.product_id}",
        )
        self.product = product
        self.link_input = discord.ui.TextInput(
            label="Link server để búc",
            placeholder="https://discord.gg/...",
            style=discord.TextStyle.short,
            required=True,
            max_length=200,
        )
        self.add_item(self.link_input)

    async def on_submit(self, interaction: discord.Interaction):
        await create_order(
            interaction.client,
            interaction,
            self.product,
            addon_no_sw=False,
            customer_note=f"Link server: {self.link_input.value}",
        )


class CompleteLinkModal(discord.ui.Modal):
    def __init__(self, order_id: str):
        super().__init__(
            title="Hoàn thành đơn — Nhập Link",
            custom_id=f"ord:modal:complete_link:{order_id}",
        )
        self.order_id = order_id
        self.link_input = discord.ui.TextInput(
            label="Link gửi cho khách hàng",
            placeholder="https://...",
            style=discord.TextStyle.short,
            required=True,
            max_length=300,
        )
        self.add_item(self.link_input)

    async def on_submit(self, interaction: discord.Interaction):
        await complete_order(interaction.client, interaction, self.order_id, link=self.link_input.value)


class CancelReasonModal(discord.ui.Modal):
    def __init__(self, order_id: str):
        super().__init__(
            title="Lý do hủy đơn",
            custom_id=f"ord:modal:cancel_reason:{order_id}",
        )
        self.order_id = order_id
        self.reason_input = discord.ui.TextInput(
            label="Lý do hủy",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=300,
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        await cancel_order(interaction.client, interaction, self.order_id, reason=self.reason_input.value)


# ---------------------------------------------------------------------------
# Nhận đơn / Hoàn thành / Hủy đơn — logic nghiệp vụ
# ---------------------------------------------------------------------------
async def accept_order(bot, interaction: discord.Interaction, order_id: str):
    db = bot.db
    order = await db.get_order(order_id)
    if not order:
        await _ack(interaction, "Không tìm thấy đơn hàng.")
        return
    if order.status != STATUS_PENDING:
        await _ack(interaction, "⚠️ Đơn hàng này đã được xử lý trước đó.")
        return

    await db.update_order_status(order_id, STATUS_PROCESSING, staff_id=interaction.user.id)
    order = await db.get_order(order_id)

    customer = await _resolve_user(bot, interaction.guild, order.user_id)
    await _refresh_order_message(bot, order, customer=customer, staff=interaction.user)
    await _ack(interaction, f"🔄 Bạn đã nhận đơn `{order_id}`.")

    await log_event(bot, order.guild_id, "🔄", f"{interaction.user.mention} đã nhận đơn `{order_id}`")


async def complete_order(bot, interaction: discord.Interaction, order_id: str, link: Optional[str] = None):
    db = bot.db
    order = await db.get_order(order_id)
    if not order:
        await _ack(interaction, "Không tìm thấy đơn hàng.")
        return
    if order.status == STATUS_COMPLETED:
        await _ack(interaction, "⚠️ Đơn hàng này đã hoàn thành trước đó.")
        return
    if order.status == STATUS_CANCELLED:
        await _ack(interaction, "⚠️ Đơn hàng này đã bị hủy, không thể hoàn thành.")
        return

    await db.update_order_status(
        order_id, STATUS_COMPLETED, staff_id=interaction.user.id, link_data=link
    )
    order = await db.get_order(order_id)

    guild = interaction.guild or bot.get_guild(order.guild_id)
    customer = await _resolve_user(bot, guild, order.user_id)

    await _refresh_order_message(bot, order, customer=customer, staff=interaction.user)
    await _ack(interaction, "✅ Đơn hàng đã được đánh dấu hoàn thành.")

    await log_event(bot, order.guild_id, "✅", f"{interaction.user.mention} đã hoàn thành đơn `{order_id}`")

    # Chống DM trùng: chỉ gửi nếu dm_notified chưa được đánh dấu
    if not order.dm_notified and customer is not None:
        dm_ok = await send_completed_dm(bot, customer, order)
        if dm_ok:
            await db.set_dm_notified(order_id, True)
            await log_event(
                bot, order.guild_id, "📩", f"Đã gửi DM thông báo hoàn thành cho <@{order.user_id}> (`{order_id}`)"
            )
        else:
            await log_event(
                bot,
                order.guild_id,
                "⚠️",
                f"Không thể gửi DM cho <@{order.user_id}> (`{order_id}`) — có thể do khách tắt DM.",
            )


async def cancel_order(bot, interaction: discord.Interaction, order_id: str, reason: str):
    db = bot.db
    order = await db.get_order(order_id)
    if not order:
        await _ack(interaction, "Không tìm thấy đơn hàng.")
        return
    if order.status in (STATUS_COMPLETED, STATUS_CANCELLED):
        await _ack(interaction, "⚠️ Đơn hàng này đã được xử lý xong, không thể hủy.")
        return

    await db.update_order_status(order_id, STATUS_CANCELLED, cancel_reason=reason)
    order = await db.get_order(order_id)

    guild = interaction.guild or bot.get_guild(order.guild_id)
    customer = await _resolve_user(bot, guild, order.user_id)

    await _refresh_order_message(bot, order, customer=customer)
    await _ack(interaction, f"❌ Đã hủy đơn `{order_id}`.")

    await log_event(
        bot, order.guild_id, "❌", f"{interaction.user.mention} đã hủy đơn `{order_id}` — Lý do: {reason}"
    )

    if customer is not None:
        dm_ok = await send_cancelled_dm(bot, customer, order)
        if dm_ok:
            await log_event(bot, order.guild_id, "📩", f"Đã gửi DM thông báo hủy đơn cho <@{order.user_id}> (`{order_id}`)")
        else:
            await log_event(bot, order.guild_id, "⚠️", f"Không thể gửi DM hủy đơn cho <@{order.user_id}> (`{order_id}`)")


# ---------------------------------------------------------------------------
# Handlers gọi từ events/on_interaction.py (interaction dạng component)
# ---------------------------------------------------------------------------
async def handle_accept(interaction: discord.Interaction, order_id: str):
    bot = interaction.client
    config = await bot.db.get_guild_config(interaction.guild_id)
    if not is_staff_or_admin(interaction.user, config):
        await interaction.response.send_message("⛔ Bạn không có quyền thực hiện thao tác này.", ephemeral=True)
        return
    await accept_order(bot, interaction, order_id)


async def handle_complete_button(interaction: discord.Interaction, order_id: str):
    bot = interaction.client
    config = await bot.db.get_guild_config(interaction.guild_id)
    if not is_staff_or_admin(interaction.user, config):
        await interaction.response.send_message("⛔ Bạn không có quyền thực hiện thao tác này.", ephemeral=True)
        return

    order = await bot.db.get_order(order_id)
    if not order:
        await interaction.response.send_message("Không tìm thấy đơn hàng.", ephemeral=True)
        return
    if order.status not in (STATUS_PENDING, STATUS_PROCESSING):
        await interaction.response.send_message("⚠️ Đơn hàng này đã được xử lý xong hoặc đã hủy.", ephemeral=True)
        return

    if order.category in LINK_DELIVERY_CATEGORIES:
        await interaction.response.send_modal(CompleteLinkModal(order_id))
    else:
        await complete_order(bot, interaction, order_id, link=None)


async def handle_cancel_button(interaction: discord.Interaction, order_id: str):
    bot = interaction.client
    config = await bot.db.get_guild_config(interaction.guild_id)
    if not is_staff_or_admin(interaction.user, config):
        await interaction.response.send_message("⛔ Bạn không có quyền thực hiện thao tác này.", ephemeral=True)
        return

    order = await bot.db.get_order(order_id)
    if not order:
        await interaction.response.send_message("Không tìm thấy đơn hàng.", ephemeral=True)
        return
    if order.status in (STATUS_COMPLETED, STATUS_CANCELLED):
        await interaction.response.send_message("⚠️ Đơn hàng này đã được xử lý xong, không thể hủy.", ephemeral=True)
        return

    embed = build_cancel_confirm_embed(order)
    view = build_cancel_confirm_view(order_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def handle_cancel_confirm(interaction: discord.Interaction, order_id: str):
    bot = interaction.client
    config = await bot.db.get_guild_config(interaction.guild_id)
    if not is_staff_or_admin(interaction.user, config):
        await interaction.response.send_message("⛔ Bạn không có quyền thực hiện thao tác này.", ephemeral=True)
        return
    await interaction.response.send_modal(CancelReasonModal(order_id))


async def handle_cancel_abort(interaction: discord.Interaction, order_id: str):
    await interaction.response.edit_message(content="↩️ Đã hủy thao tác.", embed=None, view=None)


# ---------------------------------------------------------------------------
# Slash command bổ sung: /order lookup — Staff tra cứu nhanh 1 đơn hàng
# ---------------------------------------------------------------------------
class OrderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="order-lookup", description="Tra cứu thông tin một đơn hàng theo mã (chỉ Staff/Admin)")
    @app_commands.describe(order_id="Mã đơn hàng, ví dụ: ORDER-0001")
    async def order_lookup(self, interaction: discord.Interaction, order_id: str):
        config = await self.bot.db.get_guild_config(interaction.guild_id)
        if not is_staff_or_admin(interaction.user, config):
            await interaction.response.send_message("⛔ Bạn không có quyền dùng lệnh này.", ephemeral=True)
            return

        order = await self.bot.db.get_order(order_id.strip().upper())
        if not order or order.guild_id != interaction.guild_id:
            await interaction.response.send_message(f"Không tìm thấy đơn hàng `{order_id}`.", ephemeral=True)
            return

        customer = await _resolve_user(self.bot, interaction.guild, order.user_id)
        staff = None
        if order.staff_id:
            staff = await _resolve_user(self.bot, interaction.guild, order.staff_id)
        embed = build_order_embed(order, customer=customer, staff=staff)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(OrderCog(bot))
