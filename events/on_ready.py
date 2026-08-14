"""
Sự kiện on_ready — chạy khi bot kết nối thành công tới Discord.
"""
import discord

from utils.logger import logger


def register(bot):
    @bot.event
    async def on_ready():
        logger.info("Đã đăng nhập thành công: %s (ID: %s)", bot.user, bot.user.id)
        logger.info("Bot đang hoạt động trong %d server.", len(bot.guilds))
        try:
            await bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(type=discord.ActivityType.watching, name="/price | /setup"),
            )
        except Exception:
            logger.exception("Không thể cập nhật trạng thái hoạt động (presence).")
