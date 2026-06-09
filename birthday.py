import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
import datetime
import os

class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "database/bot_data.db"
        self.birthday_role_id = int(os.getenv("BIRTHDAY_ROLE_ID", 0))
        self.check_birthday.start()

    def cog_unload(self):
        self.check_birthday.cancel()

    # 在 Bot 準備就緒後，立即執行一次檢查，避免重啟後遺漏當日壽星
    @commands.Cog.listener()
    async def on_ready(self):
        # 確保在 Bot 啟動時執行一次
        await self.check_birthday()

    @tasks.loop(minutes=1)
    async def check_birthday(self):
        """每天定時檢查：清除舊壽星、加入新壽星、發送精美祝賀面板"""
        now = datetime.datetime.now()
        month, day = now.month, now.day
        
        channel_id = int(os.getenv("BIRTHDAY_CHANNEL_ID", 0))
        if not channel_id:
            return
            
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        guild = channel.guild
        birthday_role = guild.get_role(self.birthday_role_id)

        # --------------------------------------------------
        # 步驟 1：清除目前擁有該身分組的所有舊壽星
        # --------------------------------------------------
        if birthday_role:
            for member in birthday_role.members:
                try:
                    await member.remove_roles(birthday_role, reason="生日已過，自動移除壽星身分組")
                except discord.Forbidden:
                    continue
                except Exception as e:
                    print(f"❌ 移除身分組時出錯: {e}")

        # --------------------------------------------------
        # 步驟 2：從資料庫撈出今天的壽星，給予身分組並發送 Embed
        # --------------------------------------------------
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM birthdays WHERE month = ? AND day = ?", (month, day)) as cursor:
                async for row in cursor:
                    user_id = row[0]
                    # 優先從快取取得，若無則 fetch，減少 API 壓力
                    member = guild.get_member(user_id)
                    if not member:
                        try:
                            member = await guild.fetch_member(user_id)
                        except discord.NotFound:
                            continue
                    
                    # A. 給予當日壽星身分組
                    if birthday_role:
                        try:
                            await member.add_roles(birthday_role, reason="今日生日，自動給予壽星身分組")
                        except discord.Forbidden:
                            continue

                    # B. 發送精美生日 Embed
                    embed = discord.Embed(
                        title="<:white_18:1437755704151769109>叮～今天是一個很特別的日子<:white_18:1437755704151769109>",
                        color=0xe91e63
                    )
                    
                    embed.description = (
                        f"<:Dc_:1450757693697560616> {member.mention} 的生日！\n"
                        f"<:Sanrio_03:1465958873608487046> **Happy birthday to you ～** \n\n"
                        f"<a:pink_12:1450477502697836656> 恭喜你解鎖新的一歲！新的生活劇本要打開囉\n"
                        f"<a:pink_12:1450477502697836656> 這是你最特別的一天，祝你**生日快樂！** <a:Sanrio_16:1495359379933761666>\n\n"
                        f"願所有事情都會順順利利～ <a:pink_2:1437747971012690031>"
                    )
                    
                    embed.add_field(
                        name="⠀",
                        value=(
                            f"-# <a:DC__6:1495360551780618328> 距離下次生日還有365 天！開始倒計時\n"
                            f"-# 生日可得1000 <a:bar_:1450827269667815518> 與 <@&{self.birthday_role_id}> \n\n"
                            f"-# 🎂 {month}/{day}"
                        ),
                        inline=False
                    )
                    
                    embed.set_thumbnail(url=member.display_avatar.url)
                    await channel.send(embed=embed)

    @check_birthday.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ==================================================
    # 管理員設定生日
    # ==================================================
    @app_commands.command(name="管理員設定生日", description="[管理員專用] 強制幫指定成員設定或修改生日資料")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_set_birthday(self, interaction: discord.Interaction, 用戶: discord.User, 月: int, 日: int):
        if not (1 <= 月 <= 12) or not (1 <= 日 <= 31):
            return await interaction.response.send_message("❌ 請輸入正確的月份與日期！", ephemeral=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO birthdays (user_id, month, day) VALUES (?, ?, ?)", (用戶.id, 月, 日))
            await db.commit()
        await interaction.response.send_message(f"⚙️ [管理員操作] 已成功將 {用戶.mention} 的生日設定為 **{月}月{日}日**！", ephemeral=True)

    # ==================================================
    # 設定生日
    # ==================================================
    @app_commands.command(name="設定生日", description="設定你的生日（月/日）")
    async def set_birthday(self, interaction: discord.Interaction, 月: int, 日: int):
        if not (1 <= 月 <= 12) or not (1 <= 日 <= 31):
            return await interaction.response.send_message("❌ 請輸入正確的月份與日期！", ephemeral=True)
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO birthdays (user_id, month, day) VALUES (?, ?, ?)", (interaction.user.id, 月, 日))
            await db.commit()
        await interaction.response.send_message(f"✅ 已將你的生日設定為 {月}月{日}日，到時候見囉！", ephemeral=True)

    # ==================================================
    # 刪除生日
    # ==================================================
    @app_commands.command(name="刪除生日", description="[管理員專用] 刪除指定成員在資料庫中的生日紀錄")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_birthday(self, interaction: discord.Interaction, 用戶: discord.User):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT month, day FROM birthdays WHERE user_id = ?", (用戶.id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await interaction.response.send_message(f"❌ 找不到 {用戶.mention} 的生日紀錄！", ephemeral=True)
                old_month, old_day = row[0], row[1]
            await db.execute("DELETE FROM birthdays WHERE user_id = ?", (用戶.id,))
            await db.commit()
        await interaction.response.send_message(f"🗑️ 已成功刪除 {用戶.mention} 的生日紀錄（原設定為：{old_month}月{old_day}日）。", ephemeral=True)

    # ==================================================
    # 查詢生日
    # ==================================================
    @app_commands.command(name="查詢生日", description="[管理員專用] 按月份查詢該月所有生日的成員名單")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(月份=[
        app_commands.Choice(name="1 月 ❄️", value=1), app_commands.Choice(name="2 月 🍫", value=2),
        app_commands.Choice(name="3 月 🌸", value=3), app_commands.Choice(name="4 月 🎈", value=4),
        app_commands.Choice(name="5 月 🌿", value=5), app_commands.Choice(name="6 月 ☀️", value=6),
        app_commands.Choice(name="7 月 🍦", value=7), app_commands.Choice(name="8 月 🌊", value=8),
        app_commands.Choice(name="9 月 🍂", value=9), app_commands.Choice(name="10 月 🎃", value=10),
        app_commands.Choice(name="11 月 🍁", value=11), app_commands.Choice(name="12 月 🎄", value=12)
    ])
    async def query_birthday_by_month(self, interaction: discord.Interaction, 月份: app_commands.Choice[int]):
        selected_month = 月份.value
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id, day FROM birthdays WHERE month = ? ORDER BY day ASC", (selected_month,)) as cursor:
                rows = await cursor.fetchall()
                
        if not rows:
            return await interaction.response.send_message(f"📅 目前沒有任何成員在 **{selected_month} 月** 生日喔！", ephemeral=True)

        embed = discord.Embed(title=f"📅 {selected_month} 月份壽星名單總覽", color=0x5865F2, timestamp=datetime.datetime.now())
        birthday_list_text = ""
        for user_id, day in rows:
            member = interaction.guild.get_member(user_id)
            user_display = member.mention if member else f"已退群成員 (ID: `{user_id}`)"
            birthday_list_text += f"├ **{selected_month}/{day:02d}** ── {user_display}\n"
        
        embed.description = birthday_list_text
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="測試生日面板", description="[管理員專用] 立即手動觸發今日壽星檢測與發送")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_birthday(self, interaction: discord.Interaction):
        # 1. 立即回應 defer，爭取後續處理的時間
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # 2. 執行任務
        await self.check_birthday()
        
        # 3. 使用 follow-up 回應結果，不要用 response.send_message
        await interaction.followup.send("✅ 今日壽星檢測已執行完畢！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Birthday(bot))