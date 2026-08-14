"""
Sự kiện on_interaction — bộ định tuyến (router) trung tâm cho toàn bộ tương
tác dạng nút bấm / menu chọn (component). Slash command và Modal submit được
discord.py tự xử lý riêng nên KHÔNG đi qua đây (tránh xử lý trùng lặp).

Toàn bộ custom_id trong dự án theo quy tắc:
    pb:cat:<category>        -> nút chọn danh mục trên bảng giá
    pb:note                  -> nút "Lưu ý"
    pb:payment                -> nút "Thanh toán"
    pb:select:<category>     -> menu chọn sản phẩm
    ord:accept:<order_id>    -> Staff bấm "Nhận đơn"
    ord:complete:<order_id>  -> Staff bấm "Hoàn thành"
    ord:cancel:<order_id>    -> Staff bấm "Hủy đơn"
    ord:cancel_confirm:<id>  -> xác nhận hủy
    ord:cancel_abort:<id>    -> hủy thao tác hủy đơn
"""
import discord

from commands import order as order_cmds
from commands import price as price_cmds
from utils.logger import logger


def register(bot):
    @bot.listen("on_interaction")
    async def handle_interaction(interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return  # slash command & modal submit được xử lý ở nơi khác

        data = interaction.data or {}
        custom_id = data.get("custom_id", "")
        if not custom_id:
            return

        try:
            if custom_id.startswith("pb:cat:"):
                await price_cmds.handle_category_button(interaction, custom_id.split(":", 2)[2])

            elif custom_id == "pb:note":
                await price_cmds.handle_note_button(interaction)

            elif custom_id == "pb:payment":
                await price_cmds.handle_payment_button(interaction)

            elif custom_id.startswith("pb:select:"):
                await price_cmds.handle_product_select(interaction, custom_id.split(":", 2)[2])

            elif custom_id.startswith("ord:accept:"):
                await order_cmds.handle_accept(interaction, custom_id.split(":", 2)[2])

            elif custom_id.startswith("ord:complete:"):
                await order_cmds.handle_complete_button(interaction, custom_id.split(":", 2)[2])

            elif custom_id.startswith("ord:cancel_confirm:"):
                await order_cmds.handle_cancel_confirm(interaction, custom_id.split(":", 2)[2])

            elif custom_id.startswith("ord:cancel_abort:"):
                await order_cmds.handle_cancel_abort(interaction, custom_id.split(":", 2)[2])

            elif custom_id.startswith("ord:cancel:"):
                await order_cmds.handle_cancel_button(interaction, custom_id.split(":", 2)[2])

        except Exception:
            logger.exception("Lỗi khi xử lý interaction custom_id=%s", custom_id)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Đã xảy ra lỗi khi xử lý thao tác này. Vui lòng thử lại.", ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "❌ Đã xảy ra lỗi khi xử lý thao tác này. Vui lòng thử lại.", ephemeral=True
                    )
            except Exception:
                logger.exception("Không thể gửi thông báo lỗi cho interaction custom_id=%s", custom_id)
