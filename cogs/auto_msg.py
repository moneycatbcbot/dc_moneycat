import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import aiosqlite

class AutoSendModal(discord.ui.Modal):
    def __init__(self, code):
        super().__init__(title=f"設定自動發送 - {code}")
        self.code = code
        self.msg_title = discord.ui.TextInput(label="標題", placeholder="請輸入標題...")
        self.channel_id = discord.ui.TextInput(label="頻道 ID", placeholder="請貼上頻道 ID...")
        self.send_time = discord.ui.TextInput(label="發送時間 (HH:mm)", placeholder="例如 08:30")
        self.content = discord.ui.TextInput(label="內文", style=discord.TextStyle.paragraph)
        
        self.add_item(self.msg_title)
        self.add_item(self.channel_id)
        self.add_item(self.send_time)
        self.add_item(self.content)

    async def on_submit(self, interaction: discord.Interaction):
        async with aiosqlite.connect("database/bot_data.db") as db:
            db.row_factory = aiosqlite.Row # 在這裡設定
            async with db.execute("SELECT title, channel_id, content FROM auto_msgs") as cursor:
                async for row in cursor:
                    # 直接使用欄位名稱存取，大幅降低維護成本
                    print(f"標題: {row['title']}, 內文: {row['content']}")
            await db.commit()
        await interaction.response.send_message(f"✅ 代號 `{self.code}` 設定完成！", ephemeral=True)

class AutoMsg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_schedule.start()

    @tasks.loop(minutes=1)
    async def check_schedule(self):
        now = datetime.datetime.now().strftime("%H:%M")
        async with aiosqlite.connect("database/bot_data.db") as db:
            async with db.execute("SELECT title, channel_id, content FROM auto_msgs WHERE send_time = ?", (now,)) as cursor:
                async for row in cursor:
                    channel = self.bot.get_channel(row[1])
                    if channel:
                        embed = discord.Embed(title=row[0], description=row[2], color=discord.Color.blue())
                        await channel.send(embed=embed)

    @app_commands.command(name="自動發送", description="設定每日自動發送訊息")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def auto_send(self, interaction: discord.Interaction, 代號: str):
        await interaction.response.send_modal(AutoSendModal(代號))

    @app_commands.command(name="刪除發送", description="刪除已設定的自動發送")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def delete_send(self, interaction: discord.Interaction, 代號: str):
        async with aiosqlite.connect("database/bot_data.db") as db:
            await db.execute("DELETE FROM auto_msgs WHERE code = ?", (代號,))
            await db.commit()
        await interaction.response.send_message(f"🗑️ 已刪除代號 `{代號}` 的設定。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoMsg(bot))