import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional # 記得匯入這個
import os

class Donation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="贊助", description="紀錄玩家贊助")
    @app_commands.checks.has_permissions(administrator=True)
    async def donate(self, interaction: discord.Interaction, 用戶: discord.Member, 金額: int, 備註: Optional[str] = None):
        channel_id_str = os.getenv("DONATION_CHANNEL_ID")
        
        if not channel_id_str:
            await interaction.response.send_message("❌ 系統錯誤：未設定贊助公告頻道 ID。", ephemeral=True)
            return

        channel = self.bot.get_channel(int(channel_id_str))
        
        if not channel:
            await interaction.response.send_message("❌ 找不到指定的贊助公告頻道。", ephemeral=True)
            return
        
        # 處理備註顯示
        note_text = 備註 if 備註 else "無"
        
        embed = discord.Embed(title="贊助感謝", color=0x3498db)
        embed.add_field(name="贊助玩家", value=用戶.mention, inline=True)
        embed.add_field(name="金額", value=f"{金額}", inline=True)
        embed.add_field(name="備註", value=note_text, inline=False)
        
        icon_url = interaction.guild.icon.url if interaction.guild.icon else None
        embed.set_footer(text="夢幻酒吧 εïз", icon_url=icon_url)
        
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ 已成功紀錄 {用戶.display_name} 的贊助！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Donation(bot))