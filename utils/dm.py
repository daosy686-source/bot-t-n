"""
Gửi DM cho khách hàng khi đơn hoàn thành / bị hủy.

Việc chống DM trùng (dm_notified) được kiểm tra ở tầng gọi (commands/order.py)
trước khi gọi các hàm này — ở đây chỉ chịu trách nhiệm gửi và báo cáo kết quả.
"""
import discord

from database.models import Order
from utils.embeds import build_cancelled_dm_embed, build_completed_dm_embed
from utils.logger import logger


async def send_completed_dm(bot, user: discord.abc.User, order: Order) -> bool:
    try:
        embed = build_completed_dm_embed(order)
        await user.send(embed=embed)
        return True
    except discord.Forbidden:
        logger.warning(
            "Không thể DM user %s (khách chặn DM) cho đơn %s",
            getattr(user, "id", "?"),
            order.order_id,
        )
        return False
    except discord.HTTPException:
        logger.exception("Lỗi khi gửi DM hoàn thành cho đơn %s", order.order_id)
        return False


async def send_cancelled_dm(bot, user: discord.abc.User, order: Order) -> bool:
    try:
        embed = build_cancelled_dm_embed(order)
        await user.send(embed=embed)
        return True
    except discord.Forbidden:
        logger.warning(
            "Không thể DM user %s (khách chặn DM) cho đơn %s",
            getattr(user, "id", "?"),
            order.order_id,
        )
        return False
    except discord.HTTPException:
        logger.exception("Lỗi khi gửi DM hủy đơn cho đơn %s", order.order_id)
        return False
