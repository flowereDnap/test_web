
from datetime import datetime, date

class DailyStatsManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.today = date.today()
        self.stats = {
            "new_users": 0,
            "active_users": 0,
            "videos_watched": 0,
            "clicks": 0,
            "total_balance": 0.0,
            "quests_done": 0,
            "cash_outs": 0,
        }

    async def collect(self):
        # новые пользователи сегодня
        query = "SELECT COUNT(*) FROM tg_users WHERE created_at::date = $1;"
        async with self.db.pool.acquire() as conn:
            self.stats["new_users"] = await conn.fetchval(query, self.today)

        # активные пользователи сегодня (example: users who watched videos today)
        query_active = """
            SELECT COUNT(DISTINCT telegram_id) 
            FROM user_daily_activity 
            WHERE activity_date = $1;
        """
        try:
            self.stats["active_users"] = await self.db.pool.fetchval(query_active, self.today)
        except Exception:
            self.stats["active_users"] = 0

        # видео просмотрено
        query_videos = "SELECT SUM(watched) FROM videos;"
        async with self.db.pool.acquire() as conn:
            self.stats["videos_watched"] = await conn.fetchval(query_videos) or 0

        # клики (видео или кнопки)
        query_clicks = "SELECT SUM(clicked) FROM videos;"
        async with self.db.pool.acquire() as conn:
            self.stats["clicks"] = await conn.fetchval(query_clicks) or 0

        # общий баланс
        query_balance = "SELECT SUM(balance) FROM tg_users;"
        async with self.db.pool.acquire() as conn:
            self.stats["total_balance"] = float(await conn.fetchval(query_balance) or 0.0)

        # квесты выполненные
        query_quests = "SELECT SUM(array_length(quests_done,1)) FROM tg_users;"
        async with self.db.pool.acquire() as conn:
            self.stats["quests_done"] = await conn.fetchval(query_quests) or 0

        # выводы средств
        query_cash = "SELECT SUM(array_length(cash_out_used,1)) FROM tg_users;"
        async with self.db.pool.acquire() as conn:
            self.stats["cash_outs"] = await conn.fetchval(query_cash) or 0

    async def save(self):
        query = """
        INSERT INTO daily_statistics (
            stat_date, new_users, active_users, videos_watched, clicks,
            total_balance, quests_done, cash_outs
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        ON CONFLICT (stat_date) DO UPDATE
        SET new_users = EXCLUDED.new_users,
            active_users = EXCLUDED.active_users,
            videos_watched = EXCLUDED.videos_watched,
            clicks = EXCLUDED.clicks,
            total_balance = EXCLUDED.total_balance,
            quests_done = EXCLUDED.quests_done,
            cash_outs = EXCLUDED.cash_outs;
        """
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                query,
                self.today,
                self.stats["new_users"],
                self.stats["active_users"],
                self.stats["videos_watched"],
                self.stats["clicks"],
                self.stats["total_balance"],
                self.stats["quests_done"],
                self.stats["cash_outs"]
            )

    async def diff(self, other_date: date):
        query = "SELECT * FROM daily_statistics WHERE stat_date = $1;"
        async with self.db.pool.acquire() as conn:
            today_row = await conn.fetchrow(query, self.today)
            other_row = await conn.fetchrow(query, other_date)

        if not today_row or not other_row:
            return None

        return {k: today_row[k] - other_row.get(k, 0) for k in self.stats.keys()}
