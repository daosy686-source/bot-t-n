"""
main.py — Điểm khởi động của Discord Order Bot.

Chạy: python main.py
"""
import asyncio

import discord
from discord.ext import commands

from config.settings import DB_PATH, DEV_GUILD_ID, DISCORD_TOKEN
from database.database import Database
from events import on_interaction, on_ready
from products.prices import DEFAULT_PRODUCTS
from utils.logger import logger


class OrderBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = False  # bot chỉ dùng Slash Command, không cần đọc nội dung tin nhắn
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.db = Database(DB_PATH)

    async def setup_hook(self):
        # 1) Khởi tạo database (tự tạo file/thư mục + seed bảng giá lần đầu)
        await self.db.init_db(seed_products=DEFAULT_PRODUCTS)
        logger.info("Database đã sẵn sàng tại: %s", DB_PATH)

        # 2) Nạp các Cog (Slash Command)
        await self.load_extension("commands.setup")
        await self.load_extension("commands.price")
        await self.load_extension("commands.order")

        # 3) Đăng ký các Event handler
        on_ready.register(self)
        on_interaction.register(self)

        # 4) Đồng bộ Slash Command lên Discord
        if DEV_GUILD_ID:
            guild = discord.Object(id=DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Đã đồng bộ %d slash command tới guild dev (%s).", len(synced), DEV_GUILD_ID)
        else:
            synced = await self.tree.sync()
            logger.info("Đã đồng bộ %d slash command (global — có thể mất tới 1 giờ để cập nhật).", len(synced))

    async def close(self):
        await self.db.close()
        await super().close()


bot = OrderBot()


def main():
    if not DISCORD_TOKEN:
        raise SystemExit(
            "❌ Chưa cấu hình DISCORD_TOKEN. Hãy tạo file .env (dựa theo .env.example) "
            "và điền token bot Discord của bạn vào biến DISCORD_TOKEN."
        )
    try:
        bot.run(DISCORD_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("Đăng nhập thất bại: DISCORD_TOKEN không hợp lệ.")


if __name__ == "__main__":
    main()
