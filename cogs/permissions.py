import discord
from discord import app_commands
from discord.ext import commands
import datetime
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ==================================================
# 建立按鈕元件：歷史大盤人數成長圖
# ==================================================
class ExportChartButton(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=180)
        self.guild = guild

    @discord.ui.button(label="📊 匯出人員數量變化圖", style=discord.ButtonStyle.blurple, custom_id="export_chart")
    async def export_chart_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ 你不是管理員，無法匯出圖表！", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)

        members = [m for m in self.guild.members if m.joined_at is not None]
        members_sorted = sorted(members, key=lambda m: m.joined_at)

        if not members_sorted:
            return await interaction.followup.send("❌ 無法取得成員加入歷史資料！", ephemeral=True)

        dates = []
        counts = []
        current_count = 0

        for member in members_sorted:
            current_count += 1
            dates.append(member.joined_at)
            counts.append(current_count)

        dates.append(datetime.datetime.now(datetime.timezone.utc))
        counts.append(current_count)

        plt.figure(figsize=(10, 5))
        plt.plot(dates, counts, marker='', color='#5865F2', linewidth=2.5, label="Member Count")
        
        plt.title(f"{self.guild.name} - Historical Member Growth", fontsize=14, pad=15)
        plt.xlabel("Date", fontsize=11, labelpad=10)
        plt.ylabel("Total Members", fontsize=11, labelpad=10)
        plt.grid(True, linestyle='--', alpha=0.5)
        
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gcf().autofmt_xdate()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        plt.close()

        discord_file = discord.File(buf, filename="server_growth.png")
        await interaction.followup.send(
            content=f"📈 這是 `{self.guild.name}` 的歷史人員數量變化趨勢圖：", 
            file=discord_file, 
            ephemeral=True
        )


class PermissionsManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================================================
    # 核心亮點功能一：/監視器 (即時狀態 + 文字與語音雙重方案A監控)
    # ==================================================
    @app_commands.command(name="監視器", description="[管理員專用] 天眼即時監控：成員娛樂狀態、語音在線、以及近期最活躍文字頻道")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def monitor_activities(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        # 1. 強制確保會員快取完整
        if not guild.chunked:
            await guild.chunk()

        gaming_text = []
        voice_text = []
        
        # 2. 處理成員狀態 (優化：一次迴圈處理兩種狀態)
        for member in guild.members:
            if member.bot: continue

            # 語音狀態
            if member.voice and member.voice.channel:
                state = "🎙️"
                if member.voice.self_deaf or member.voice.deaf: state = "🎧❌"
                elif member.voice.self_mute or member.voice.mute: state = "🔇"
                voice_text.append(f"└ {member.mention} 正在 {member.voice.channel.mention} {state}")

            # 遊戲狀態 (簡化邏輯，避免過度判斷)
            for activity in member.activities:
                if isinstance(activity, discord.Game):
                    gaming_text.append(f"├ {member.mention} 正在玩 🎮 **{activity.name}**")
                elif isinstance(activity, discord.Streaming):
                    gaming_text.append(f"├ {member.mention} 正在直播 📺 **{activity.name}**")

        # 3. 處理文字頻道 (已修正錯誤處理邏輯)
        text_channel_dynamic = []
        for channel in guild.text_channels[:10]:
            if not channel.permissions_for(guild.me).read_message_history: 
                continue
            
            # 使用 try-except 區塊處理已不存在的訊息 ID
            try:
                # 優先抓取快取，若無則 fetch
                last_msg = channel.last_message
                if not last_msg and channel.last_message_id:
                    last_msg = await channel.fetch_message(channel.last_message_id)
                
                if last_msg and not last_msg.author.bot:
                    time_diff = datetime.datetime.now(datetime.timezone.utc) - last_msg.created_at
                    mins = int(time_diff.total_seconds() / 60)
                    if mins < 1440: # 只顯示 24 小時內
                        text_channel_dynamic.append(f"├ {channel.mention}: {last_msg.author.display_name} ({mins} 分鐘前)")
            
            except discord.NotFound:
                # 若發生 10008 錯誤，直接跳過該頻道，不中斷程式
                continue
            except Exception as e:
                print(f"頻道 {channel.name} 數據獲取失敗: {e}")
                continue

        # 4. 構建 Embed (使用 join 優化字串處理)
        embed = discord.Embed(title="🛰️ 伺服器天眼系統", color=0x2ecc71)
        embed.add_field(name="🎮 遊戲狀態", value="\n".join(gaming_text[:15]) or "無數據", inline=False)
        embed.add_field(name="🔊 語音狀態", value="\n".join(voice_text[:15]) or "無數據", inline=False)
        embed.add_field(name="💬 近期發言", value="\n".join(text_channel_dynamic) or "無數據", inline=False)

        await interaction.followup.send(embed=embed)
        
    # ==================================================
    # 功能二：/踢除 (將指定成員停權/封鎖)
    # ==================================================
    @app_commands.command(name="踢除", description="[管理員專用] 將伺服器指定的惡意成員無限期停權（封鎖 Ban）")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def ban_member(self, interaction: discord.Interaction, 用戶: discord.Member, 原因: str = "未提供具體原因"):
        guild = interaction.guild
        if not guild: return

        if 用戶.id == interaction.user.id:
            return await interaction.response.send_message("❌ 你不能把自己停權喔！", ephemeral=True)
        if 用戶.id == guild.owner_id:
            return await interaction.response.send_message("❌ 權限錯誤：無法對伺服器創始人執行停權！", ephemeral=True)
        if interaction.user.id != guild.owner_id and 用戶.top_role.position >= interaction.user.top_role.position:
            return await interaction.response.send_message("❌ 權限不足：你無法停權身分組順位比你高（或平級）的成員！", ephemeral=True)

        bot_member = guild.get_member(self.bot.user.id)
        if 用戶.top_role.position >= bot_member.top_role.position:
            return await interaction.response.send_message("❌ 機器人權限不足：該成員的身分組階層高於機器人，請將機器人角色順位拉高！", ephemeral=True)

        try:
            await guild.ban(用戶, reason=f"管理員 [{interaction.user.name}] 執行停權。原因：{原因}", delete_message_days=1)
            
            embed = discord.Embed(title="🔨 伺服器成員停權處分公報", description="已成功將惡意用戶永久隔離並列入伺服器黑名單。", color=0xff0000, timestamp=datetime.datetime.now())
            embed.add_field(name="👤 被停權用戶", value=f"{用戶.mention} (`{用戶.name}` / ID: `{用戶.id}`)", inline=False)
            embed.add_field(name="👮 執行管理員", value=f"{interaction.user.mention}", inline=True)
            embed.add_field(name="📝 停權原因", value=f"`{原因}`", inline=True)
            embed.set_thumbnail(url=用戶.display_avatar.url)

            await interaction.response.send_message(embed=embed, ephemeral=False)
        except Exception as e:
            await interaction.response.send_message(f"❌ 執行停權時發生錯誤: {e}", ephemeral=True)


    # ==================================================
    # 功能三：/伺服器歷史資料
    # ==================================================
    @app_commands.command(name="伺服器歷史資料", description="[管理員專用] 查詢伺服器核心大盤數據與歷史創立資料")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def server_history(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild: return

        total_members = guild.member_count
        bot_count = len([m for m in guild.members if m.bot])
        human_count = total_members - bot_count
        boost_count = guild.premium_subscription_count
        boost_tier = guild.premium_tier
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        category_channels = len(guild.categories)
        total_roles = len(guild.roles)

        create_time = guild.created_at.strftime("%Y/%m/%d %H:%M:%S")
        server_age = (datetime.datetime.now(datetime.timezone.utc) - guild.created_at).days

        embed = discord.Embed(title=f"🏰 {guild.name} 伺服器核心歷史總覽", color=0xe91e63, timestamp=datetime.datetime.now())
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="📅 伺服器創立時間", value=f"`{create_time}`\n(已穩定營運了 **{server_age}** 天)", inline=False)
        embed.add_field(name="👑 伺服器擁有者", value=f"<@{guild.owner_id}> (`ID: {guild.owner_id}`)", inline=False)
        embed.add_field(name="👥 人員數據統計", value=f"├ 總人數：`{total_members}` 人\n├ 真實成員：`{human_count}` 人\n└ 機器人：`{bot_count}` 尊", inline=True)
        embed.add_field(name="💎 伺服器加成狀態", value=f"├ 加成等級：`Level {boost_tier}`\n└ 總加成次數：`{boost_count}` 次", inline=True)
        embed.add_field(name="📂 頻道與架構", value=f"├ 類別總數：`{category_channels}` 個\n├ 文字頻道：`{text_channels}` 條\n├ 語音頻道：`{voice_channels}` 條\n└ 身份組總數：`{total_roles}` 個", inline=False)

        view = ExportChartButton(guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    # ==================================================
    # 功能四：/權限
    # ==================================================
    @app_commands.command(name="權限", description="[管理員專用] 列出所有伺服器成員並依權限大小排序分類")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def list_permissions(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild: return
        
        members = [member async for member in guild.fetch_members()]
        sorted_members = sorted(members, key=lambda m: (m.top_role.position, m.joined_at or datetime.datetime.min), reverse=True)

        embed = discord.Embed(title=f"👑 {guild.name} 伺服器權限階層排序", color=0x5865F2)
        current_role = None
        role_group_text = ""

        for member in sorted_members:
            if member.bot: continue
            if member.top_role != current_role:
                if current_role and role_group_text:
                    embed.description = (embed.description or "") + f"\n⚜️ **{current_role.name}** (順位: {current_role.position})\n{role_group_text}"
                current_role = member.top_role
                role_group_text = ""
            role_group_text += f"└ {member.mention} (ID: `{member.id}`)\n"

        if current_role and role_group_text:
            embed.description = (embed.description or "") + f"\n⚜️ **{current_role.name}** (順位: {current_role.position})\n{role_group_text}"

        await interaction.followup.send(embed=embed, ephemeral=True)


    # ==================================================
    # 功能五：/權限查詢
    # ==================================================
    @app_commands.command(name="權限查詢", description="[管理員專用] 查詢指定用戶的進入時間、身份組與權限大小")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def check_user_permission(self, interaction: discord.Interaction, 用戶: discord.Member):
        guild = interaction.guild
        if not guild: return
        
        roles = [role.mention for role in 用戶.roles if role != guild.default_role]
        roles_str = "、".join(roles) if roles else "無任何身分組"
        join_time = 用戶.joined_at.strftime("%Y/%m/%d %H:%M:%S") if 用戶.joined_at else "未知"
        create_time = 用戶.created_at.strftime("%Y/%m/%d %H:%M:%S")
        is_owner = "👑 伺服器創始人" if guild.owner_id == 用戶.id else "否"
        is_admin = "✅ 是 (擁有管理員權限)" if 用戶.guild_permissions.administrator else "❌ 否"

        embed = discord.Embed(title=f"🔍 權限與成員資料查詢", color=用戶.top_role.color if 用戶.top_role.color.value != 0 else 0x979c9f)
        embed.set_thumbnail(url=用戶.display_avatar.url)
        embed.add_field(name="👤 帳號名稱", value=f"{用戶.mention} (`{用戶.name}`)", inline=True)
        embed.add_field(name="🆔 用戶 ID", value=f"`{用戶.id}`", inline=True)
        embed.add_field(name="👑 核心權限", value=f"**創始人：** {is_owner}\n**管理員：** {is_admin}", inline=False)
        embed.add_field(name="📊 權限權重大小", value=f"最高身分組：{用戶.top_role.mention}\n階層順位權重：`#{用戶.top_role.position}`", inline=False)
        embed.add_field(name="🔮 擁有的身份組", value=roles_str, inline=False)
        embed.add_field(name="📅 帳號創立時間", value=f"`{create_time}`", inline=True)
        embed.add_field(name="📥 進入伺服器時間", value=f"`{join_time}`", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)


    # 全域權限報錯攔截
    @monitor_activities.error
    @ban_member.error
    @server_history.error
    @list_permissions.error
    @check_user_permission.error
    async def permission_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ 權限不足！這個指令只有伺服器管理員可以使用。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PermissionsManager(bot))