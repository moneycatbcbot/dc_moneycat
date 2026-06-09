import discord
from discord.ext import commands
import os
import datetime

class AutoBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 讀取頻道 ID
        self.log_channel_id = int(os.getenv("BAN_LOG_CHANNEL_ID", 0))
        self.protected_channel_id = int(os.getenv("PROTECTED_CHANNEL_ID", 0))

    @commands.Cog.listener()
    async def on_message(self, message):
        # 排除 Bot、私訊、管理員
        if message.author.bot or message.guild is None or message.author.guild_permissions.administrator:
            return

        # 判斷受保護頻道
        if message.channel.id == self.protected_channel_id:
            await self.execute_auto_ban(message)

    async def execute_auto_ban(self, message):
        user = message.author
        guild = message.guild
        content = message.content if message.content else "(無文字內容，可能是表情或圖片)"
        reason = "在自動停權頻道發送訊息"

        try:
            # 1. 執行停權 (Ban) 並清除 24 小時訊息
            await user.ban(reason=reason, delete_message_seconds=86400)
            
            # 2. 獲取紀錄頻道
            if self.log_channel_id:
                log_channel = self.bot.get_channel(self.log_channel_id)
                if log_channel:
                    # 參考最新照片風格設計 Embed
                    embed = discord.Embed(
                        title="🚫 自動停權執行",
                        color=0xe74c3c # 鮮紅色側邊條
                    )
                    
                    # 組合描述文字
                    embed.description = f"用戶 **{user.name}** 已被自動停權"
                    
                    # 用戶欄位
                    embed.add_field(
                        name="用戶", 
                        value=f"{user.mention}\n`{user.id}`", 
                        inline=False
                    )
                    
                    # 頻道欄位
                    embed.add_field(
                        name="頻道", 
                        value=f"✨ {guild.name} › {message.channel.mention}", 
                        inline=False
                    )
                    
                    # 訊息內容欄位
                    embed.add_field(
                        name="訊息內容", 
                        value=content, 
                        inline=False
                    )
                    
                    # 設定右側大頭貼縮圖
                    embed.set_thumbnail(url=user.display_avatar.url)
                    
                    # 底部訊息 ID 與 時間 (格式：訊息 ID: XXX | YYYY/MM/DD, HH:MM)
                    timestamp = datetime.datetime.now().strftime("%Y/%m/%d, %H:%M")
                    embed.set_footer(text=f"訊息 ID: {message.id} | {timestamp}")

                    await log_channel.send(embed=embed)
            
            # 3. 刪除原始違規訊息
            await message.delete()

        except discord.Forbidden:
            print(f"❌ 權限不足，無法停權 {user.name}")
        except Exception as e:
            print(f"❌ 停權通知出錯: {e}")

async def setup(bot):
    await bot.add_cog(AutoBan(bot))