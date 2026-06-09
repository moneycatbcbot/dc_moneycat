import aiosqlite
import os

class BotDatabase:
    def __init__(self, db_path="database/bot_data.db"):
        self.db_path = db_path
        self._connection = None

    async def setup(self):
        """初始化資料庫與資料表"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        async with aiosqlite.connect(self.db_path) as db:
            # 建立資料表
            await db.execute('''CREATE TABLE IF NOT EXISTS auto_msgs 
                (code TEXT PRIMARY KEY, title TEXT, channel_id INTEGER, send_time TEXT, content TEXT)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS birthdays 
                (user_id INTEGER PRIMARY KEY, month INTEGER, day INTEGER)''')
            await db.execute('''CREATE TABLE IF NOT EXISTS protected_channels 
                (channel_id INTEGER PRIMARY KEY)''')
            await db.commit()

    async def get_connection(self):
        """獲取常駐連接，並設定 Row Factory 以方便存取資料"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def close(self):
        """關閉資料庫連接"""
        if self._connection:
            await self._connection.close()
            self._connection = None