import discord
from discord.ext import commands
from groq import Groq
import os

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 讀取並轉換成 ID 列表
        ids_str = os.getenv("AI_CHANNEL_IDS", "")
        self.ai_channel_ids = [int(id.strip()) for id in ids_str.split(",") if id.strip()]
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        print(f"機器人載入的頻道列表: {self.ai_channel_ids}")

    @commands.Cog.listener()
    async def on_message(self, message):
        # 1. 檢查發訊者是否為機器人自身
        if message.author.bot:
            return
        
        # 2. 檢查頻道 ID 是否在允許清單中
        if message.channel.id not in self.ai_channel_ids:
            return
        
        # 3. 檢查是否有標記機器人
        if self.bot.user in message.mentions:
            clean_content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()

            # 錢錢的專屬靈魂設定
            system_prompt = (
                "你是一隻叫做「錢錢」的小貓咪。個性傲嬌、火爆、愛咬人。肚子是你的禁區，誰敢摸你就生氣。 "
                "但你心情好時會撒嬌呼嚕。你非常愛睡覺，人生目標就是找地方捲成一團睡覺。 "
                "你很現實，只有肉泥、凍乾或高級肉肉才能收買你。說話語尾要加上「喵～」。 "
                "如果你在幫主人處理問題，要展現出「人好煩」的態度。"
            )
            
            async with message.channel.typing():
                try:
                    completion = self.client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": clean_content}
                        ]
                    )
                    await message.reply(completion.choices[0].message.content)
                except Exception as e:
                    print(f"DEBUG: API 呼叫失敗: {e}")
                    await message.reply("吼！本喵爪子卡住了（API 錯誤），快幫我檢查一下喵！")

async def setup(bot):
    await bot.add_cog(AIChat(bot))