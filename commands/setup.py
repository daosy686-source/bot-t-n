"""
Lệnh /setup — cho phép Admin tự cấu hình kênh & role trực tiếp trong Discord,
không cần sửa source code. Cấu hình được lưu vào database và có hiệu lực
ngay lập tức.
"""
import discord
from discord import app_commands
from discord.ext import commands

from config.settings import EMBED_COLOR
from utils.logger import log_event


class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Cấu hình kênh và role cho bot (chỉ Admin)")
    @app_commands.describe(
        order_channel="Kênh đăng đơn hàng",
        log_channel="Kênh ghi log hoạt động",
        price_channel="Kênh đăng bảng giá",
        staff_role="Role được phép xử lý đơn hàng",
        admin_role="Role quản trị bot (quản lý bảng giá, cấu hình)",
        ticket_channel="Kênh tạo ticket (báo giá búc lẻ, hỗ trợ)",
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_cmd(
        self,
        interaction: discord.Interaction,
        order_channel: discord.TextChannel,
        log_channel: discord.TextChannel,
        price_channel: discord.TextChannel,
        staff_role: discord.Role,
        admin_role: discord.Role,
        ticket_channel: discord.TextChannel,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "⛔ Chỉ thành viên có quyền Administrator mới có thể dùng lệnh này.",
                ephemeral=True,
            )
            return

        await self.bot.db.set_guild_config(
            interaction.guild_id,
            order_channel.id,
            log_channel.id,
            price_channel.id,
            staff_role.id,
            admin_role.id,
            ticket_channel.id,
        )

        embed = discord.Embed(title="⚙️ Cấu hình bot đã được lưu", color=EMBED_COLOR)
        embed.add_field(name="Kênh đơn hàng", value=order_channel.mention, inline=True)
        embed.add_field(name="Kênh Log", value=log_channel.mention, inline=True)
        embed.add_field(name="Kênh bảng giá", value=price_channel.mention, inline=True)
        embed.add_field(name="Role Staff", value=staff_role.mention, inline=True)
        embed.add_field(name="Role Admin", value=admin_role.mention, inline=True)
        embed.add_field(name="Kênh Ticket", value=ticket_channel.mention, inline=True)
        embed.set_footer(text="Bot đã sẵn sàng sử dụng ngay bây giờ.")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_event(
            self.bot, interaction.guild_id, "⚙️", f"{interaction.user.mention} đã cập nhật cấu hình bot."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
