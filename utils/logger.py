"""
Thiết lập logging ra console + file, và hàm log_event() để vừa ghi log nội bộ
vừa gửi thông báo vào kênh Log đã cấu hình qua /setup.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

import discord

from config.settings import LOG_DIR


def _setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    log = logging.getLogger("order_bot")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    log.addHandler(console)

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "bot.log"), maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    log.addHandler(file_handler)

    return log


logger = _setup_logger()


async def log_event(bot, guild_id: int, emoji: str, message: str):
    """Ghi log ra console/file, đồng thời gửi vào kênh Log của guild (nếu đã /setup)."""
    logger.info("[Guild %s] %s %s", guild_id, emoji, message)
    try:
        db = getattr(bot, "db", None)
        if db is None:
            return
        config = await db.get_guild_config(guild_id)
        if not config or not config.log_channel_id:
            return
        channel = bot.get_channel(config.log_channel_id)
        if channel is None:
            channel = await bot.fetch_channel(config.log_channel_id)
        embed = discord.Embed(description=f"{emoji} {message}", color=0x95A5A6)
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)
    except Exception:
        logger.exception("Không thể gửi log vào kênh Log của guild %s", guild_id)
