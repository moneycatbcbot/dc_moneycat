import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# 建立一個簡單的 Flask 伺服器
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_server():
    # Render 透過環境變數 PORT 分配連接埠，預設為 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --------------------------------------------------
# 在 main() 中修改
# --------------------------------------------------
async def main():
    # 1. 啟動 HTTP 伺服器執行緒 (讓 Render 的 Web Service 抓到 Port)
    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 2. 接著啟動您的 Bot
    # ... 原有的 bot 啟動邏輯 ...

# 載入環境變數
load_dotenv()

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True          # 必須開啟，用於監視器與生日功能
        intents.message_content = True  # 必須開啟，用於讀取訊息
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 1. 綁定全域斜線指令錯誤處理
        self.tree.on_error = self.on_tree_error
        
        # 2. 自動載入 cogs 資料夾下的所有模組
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f"✅ 已載入模組: {filename}")
        
        # 3. 同步指令到 Discord
        await self.tree.sync()
        print("🚀 指令同步完成")

    # 全域錯誤處理器
    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        # 判斷是否已經回應過，避免產生 400 Bad Request
        if interaction.response.is_done():
            # 如果已經回應過，就改用 follow-up
            await interaction.followup.send("❌ 系統發生錯誤。", ephemeral=True)
        else:
            # 如果還沒回應，才用 response.send_message
            await interaction.response.send_message("❌ 系統發生錯誤。", ephemeral=True)
        
        print(f"❌ 發生錯誤: {error}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

async def main():
    # 若有 Opus 需求 (音樂功能)
    if discord.opus.is_loaded():
        print("✅ Opus 函式庫已載入")
    else:
        # 請根據您的系統調整路徑，或由環境變數讀取
        opus_path = os.getenv("OPUS_PATH", "/opt/homebrew/lib/libopus.dylib")
        try:
            discord.opus.load_opus(opus_path)
            print(f"✅ 成功載入 Opus 函式庫: {opus_path}")
        except Exception as e:
            print(f"⚠️ 無法載入 Opus: {e}")

    bot = MyBot()
    async with bot:
        await bot.start(os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())