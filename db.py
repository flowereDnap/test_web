import os
import asyncio
import asyncpg
from dotenv import load_dotenv
import random
from datetime import datetime, date

load_dotenv()
DB_URL = os.getenv("DATABASE_DSN")
if not DB_URL:
    raise ValueError("Ссылка на базу данных (PG_LINK) не указана в .env")


class UsersDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.db_url = db_url
        self.pool = pool

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=10,
                timeout=60
            )

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def create_users_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS tg_users (
            telegram_id BIGINT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            timezone TEXT,
            is_premium BOOLEAN DEFAULT FALSE,
            referrals BIGINT[] DEFAULT '{}',
            is_alive BOOLEAN DEFAULT TRUE,
            logs JSONB DEFAULT '[]',
            balance NUMERIC(18,2) DEFAULT 0,
            quests_done BIGINT[] DEFAULT '{}',
            cash_out_used BIGINT[] DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT now()
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def add_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
        timezone: str | None = None,
        is_premium: bool = False
    ):
        query = """
        INSERT INTO tg_users (
            telegram_id,
            username,
            first_name,
            last_name,
            language_code,
            timezone,
            is_premium
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (telegram_id) DO NOTHING;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                telegram_id,
                username,
                first_name,
                last_name,
                language_code,
                timezone,
                is_premium
            )

    async def get_user_by_telegram_id(self, telegram_id: int):
        query = "SELECT * FROM tg_users WHERE telegram_id = $1;"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, telegram_id)


    async def add_referral(self, referrer_id: int, referral_id: int):
        query = """
        UPDATE tg_users
        SET referrals = COALESCE(referrals, ARRAY[]::BIGINT[]) || ARRAY[$1]::BIGINT[]
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, referral_id, referrer_id)

    async def update_is_alive(self, telegram_id: int, is_alive: bool):
        query = """
        UPDATE tg_users
        SET is_alive = $1
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, is_alive, telegram_id)

    async def add_cash_out_used(self, telegram_id: int, cash_out_id: int):
        query = """
        UPDATE tg_users
        SET cash_out_used = COALESCE(cash_out_used, ARRAY[]::BIGINT[]) || ARRAY[$1]::BIGINT[]
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, cash_out_id, telegram_id)

    async def add_quest_done(self, telegram_id: int, quest_id: int):
        query = """
        UPDATE tg_users
        SET quests_done = COALESCE(quests_done, ARRAY[]::BIGINT[]) || ARRAY[$1]::BIGINT[]
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, quest_id, telegram_id)

    async def update_balance(self, telegram_id: int, new_balance: float):
        query = """
        UPDATE tg_users
        SET balance = $1
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, new_balance, telegram_id)

    async def set_timezone(self, telegram_id: int, timezone: str):
        query = """
        UPDATE tg_users
        SET timezone = $1
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, timezone, telegram_id)


# ------------------ VIDEOS ------------------
class VideosDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None,  videos_path: str = "vids"):
        self.db_url = db_url
        self.pool = pool
        self.videos_path = videos_path

    async def create_videos_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS videos (
            id BIGSERIAL PRIMARY KEY,
            title TEXT,
            video_url TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            watched INTEGER DEFAULT 0,
            clicked INTEGER DEFAULT 0
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def add_video(self, title: str, video_url: str, is_active: bool = True):
        query = """
        INSERT INTO videos (title, video_url, is_active)
        VALUES ($1, $2, $3)
        RETURNING id;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, title, video_url, is_active)

    async def get_video_by_id(self, video_id: int):
        query = "SELECT * FROM videos WHERE id = $1;"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, video_id)
        
    async def add_video_if_not_exists(self, title: str, video_url: str):
        query = """
        INSERT INTO videos (title, video_url)
        VALUES ($1, $2)
        ON CONFLICT (video_url) DO NOTHING;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, title, video_url)

    async def sync_videos_from_folder(self):
        """
        Пробегаемся по папке videos_path, если файла нет в базе — добавляем.
        """
        if not os.path.exists(self.videos_path):
            print(f"Папка {self.videos_path} не найдена")
            return

        for filename in os.listdir(self.videos_path):
            if filename.lower().endswith((".mp4", ".mov", ".webm")):
                video_path = os.path.join(self.videos_path, filename)
                title = os.path.splitext(filename)[0]  # название без расширения
                await self.add_video_if_not_exists(title=title, video_url=video_path)

    async def get_random_video(self):
        query = "SELECT * FROM videos WHERE is_active = TRUE;"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            if not rows:
                return None
            return random.choice(rows)
        
    async def increment_watched(self, video_id: int):
        query = "UPDATE videos SET watched = watched + 1 WHERE id = $1;"
        async with self.pool.acquire() as conn:
            await conn.execute(query, video_id)


# ------------------ SETTINGS (заготовка) ------------------
class SettingsDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.db_url = db_url
        self.pool = pool

    async def create_settings_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS settings (
            id BIGSERIAL PRIMARY KEY
            -- сюда позже добавим поля
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)



# ------------------ MAILING STATISTICS ------------------
class MailingDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.db_url = db_url
        self.pool = pool

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=10,
                timeout=60
            )

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def create_mailing_table(self):
        """
        Создаёт таблицы для рассылок, их запусков и статистики.
        """
        async with self.pool.acquire() as conn:
            # 1. Основная таблица рассылок (Mailing Templates)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS mailings (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                media_url TEXT,
                media_type TEXT,    
                button_text TEXT,
                button_link TEXT,                          
                created_at TIMESTAMPTZ DEFAULT now()
            );
            """)

            # 2. Таблица запусков рассылок (Mailing Runs)
            # Эта таблица будет хранить запись о КАЖДОМ фактическом запуске.
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS mailing_runs (
                id BIGSERIAL PRIMARY KEY,
                mailing_id BIGINT REFERENCES mailings(id) ON DELETE CASCADE,
                users_count INTEGER DEFAULT 0,
                start_time TIMESTAMPTZ DEFAULT now()
            );
            """)

            # 3. Таблица статистики (Mailing Stats)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS mailing_stats (
                id BIGSERIAL PRIMARY KEY,
                run_id BIGINT REFERENCES mailing_runs(id) ON DELETE CASCADE,
                telegram_id BIGINT NOT NULL,
                status TEXT NOT NULL, -- sent, failed, clicked и т.д.
                timestamp TIMESTAMPTZ DEFAULT now()
            );
            """)
    
    # db.py (в классе MailingDBManager)

    async def start_new_run(self, mailing_id: int) -> int:
        """
        Регистрирует новый запуск существующего шаблона рассылки и возвращает run_id.
        """
        async with self.pool.acquire() as conn:
            run_id = await conn.fetchval(
                "INSERT INTO mailing_runs (mailing_id) VALUES ($1) RETURNING id;",
                mailing_id
            )
            return run_id # <-- Это уникальный ID для текущего сеанса

    async def get_all_broadcast_names(self) -> list[dict]:
        """
        Возвращает список всех уникальных названий рассылок с их ID.
        Используем DISTINCT ON (title) для получения последней версии каждой уникальной рассылки.
        """
        query = """
        SELECT DISTINCT ON (name) id, name
        FROM mailings
        ORDER BY name, created_at DESC;
        """
        async with self.pool.acquire() as conn:
            # fetch возвращает список записей (Record), которые можно преобразовать в словари
            rows = await conn.fetch(query)
            return [dict(row) for row in rows]
    
    async def add_broadcast(self, name: str, title: str, text: str, media_url: str | None = None, media_type: str | None = None, button_text: str | None = None, button_link: str | None = None) -> int:
        """
        Создаёт новую рассылку и возвращает её ID.
        """
        async with self.pool.acquire() as conn:
            mailing_id = await conn.fetchval(
                "INSERT INTO mailings (name, title, text, media_url, media_type, button_text, button_link) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id;",
                name, title, text, media_url, media_type, button_text, button_link
            )
            return mailing_id

    async def log_stat(self, run_id: int, telegram_id: int, status: str): # <-- Принимает run_id
        """
        Логирует событие по пользователю для конкретного ЗАПУСКА.
        """

        print("222222222222222", run_id, telegram_id, status)

        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO mailing_stats (run_id, telegram_id, status) VALUES ($1, $2, $3);",
                run_id, telegram_id, status
            )

    async def get_mailing_by_run_id(self, run_id: int) -> dict | None:
        """
        Получает данные шаблона рассылки (из mailings) по ID запуска (из mailing_runs).
        """
        query = """
        SELECT m.*
        FROM mailings m
        JOIN mailing_runs mr ON m.id = mr.mailing_id
        WHERE mr.id = $1;
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, run_id)
            return dict(row) if row else None

    async def get_stats(self, run_id: int) -> dict: # <-- Принимает run_id
        """
        Возвращает статистику по конкретному ЗАПУСКУ рассылки.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT status, COUNT(*) AS count FROM mailing_stats WHERE run_id=$1 GROUP BY status;",
                run_id # <-- Фильтрация теперь идет только по run_id
            )
            return {row['status']: row['count'] for row in rows}

    async def get_mailing(self, mailing_id: int):
        """
        Получить данные рассылки по ID.
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM mailings WHERE id=$1;", mailing_id)
        
    async def get_mailing_by_name(self, name: str):
        """
        Получить данные рассылки по названию (name).

        """
        query = "SELECT * FROM mailings WHERE name = $1 ORDER BY created_at DESC LIMIT 1;"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, name)

    async def get_mailing_id_by_name(self, name: str) -> int | None:
        """
        Получить ID рассылки по названию (name).
        """
        query = "SELECT id FROM mailings WHERE name = $1 ORDER BY created_at DESC LIMIT 1;"
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, name)


# ------------------ STATISTICS DB MANAGER ------------------
class StatisticsDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.db_url = db_url
        self.pool = pool
        self.daily_stats: DailyStatsManager | None = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=10, timeout=60)
        if not self.daily_stats:
            self.daily_stats = DailyStatsManager(self)

    async def create_stats_table(self):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_statistics (
                stat_date DATE PRIMARY KEY,
                new_users BIGINT DEFAULT 0,
                active_users BIGINT DEFAULT 0,
                videos_watched BIGINT DEFAULT 0,
                clicks BIGINT DEFAULT 0,
                total_balance NUMERIC(18,2) DEFAULT 0,
                quests_done BIGINT DEFAULT 0,
                cash_outs BIGINT DEFAULT 0
            );
            """)


    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
        self.daily_stats = None

# ------------------ НОВЫЙ КЛАСС: QuestStatusDBManager ------------------
class QuestStatusDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.db_url = db_url
        self.pool = pool

    async def create_quest_statuses_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS user_quest_statuses (
            id BIGSERIAL PRIMARY KEY,
            telegram_id BIGINT REFERENCES tg_users(telegram_id) ON DELETE CASCADE,
            quest_id TEXT NOT NULL,
            status TEXT NOT NULL, -- 'visited', 'completed', 'unclaimed'
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (telegram_id, quest_id)
        );
        -- Индекс для быстрого поиска по пользователю
        CREATE INDEX IF NOT EXISTS idx_user_quest_status ON user_quest_statuses (telegram_id, status);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def set_quest_status(self, telegram_id: int, quest_id: str, status: str):
        """
        Устанавливает или обновляет статус квеста ('visited', 'completed', 'unclaimed').
        """
        query = """
        INSERT INTO user_quest_statuses (telegram_id, quest_id, status)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id, quest_id) DO UPDATE
        SET status = EXCLUDED.status, updated_at = now();
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, telegram_id, quest_id, status)

    async def get_user_quest_statuses(self, telegram_id: int) -> list[dict]:
        """
        Возвращает список словарей со статусами всех квестов пользователя.
        """
        query = "SELECT quest_id, status FROM user_quest_statuses WHERE telegram_id = $1;"
        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, telegram_id)
            return [dict(r) for r in records]
        
# db.py, после MailingDBManager или QuestStatusDBManager

# ------------------ НОВЫЙ КЛАСС: CountersDBManager ------------------
class CountersDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.db_url = db_url
        self.pool = pool

    async def create_user_counters_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS user_counters (
            id BIGSERIAL PRIMARY KEY,
            telegram_id BIGINT REFERENCES tg_users(telegram_id) ON DELETE CASCADE,
            counter_key TEXT NOT NULL, -- например, 'videos_watched', 'clicks_today'
            value INTEGER DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (telegram_id, counter_key)
        );
        CREATE INDEX IF NOT EXISTS idx_user_counter ON user_counters (telegram_id);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def increment_counter(self, telegram_id: int, counter_key: str, increment: int = 1) -> int:
        """
        Атомарно увеличивает счетчик и возвращает новое значение.
        """
        query = """
        INSERT INTO user_counters (telegram_id, counter_key, value)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id, counter_key) DO UPDATE
        SET value = user_counters.value + $3, updated_at = now()
        RETURNING value;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, telegram_id, counter_key, increment)

    async def get_counter(self, telegram_id: int, counter_key: str) -> int:
        """
        Возвращает текущее значение счетчика.
        """
        query = "SELECT value FROM user_counters WHERE telegram_id = $1 AND counter_key = $2;"
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, telegram_id, counter_key) or 0
# ------------------ CountersDBManager КОНЕЦ ------------------

# ------------------ DATABASE MANAGER ------------------
class DatabaseManager:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool: asyncpg.pool.Pool | None = None
        self.users_db: UsersDBManager | None = None
        self.videos_db: VideosDBManager | None = None
        self.mailing_db: MailingDBManager | None = None
        self.settings_db: SettingsDBManager | None = None
        self.stats_db_manager: StatisticsDBManager | None = None
        self.quests_db: QuestStatusDBManager | None = None
        self.counters_db: CountersDBManager | None = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=10, timeout=60)
        if not self.users_db:
            self.users_db = UsersDBManager(self.db_url, pool=self.pool)
        if not self.videos_db:
            self.videos_db = VideosDBManager(self.db_url, pool=self.pool)
        if not self.mailing_db:
            self.mailing_db = MailingDBManager(self.db_url, pool=self.pool)
        if not self.settings_db:
            self.settings_db = SettingsDBManager(self.db_url, pool=self.pool)
        if not self.stats_db_manager:
            self.stats_db_manager = StatisticsDBManager(self.db_url, pool=self.pool)
        if not self.quests_db:
            self.quests_db = QuestStatusDBManager(self.db_url, pool=self.pool)
        if not self.counters_db:
            self.counters_db = CountersDBManager(self.db_url, pool=self.pool)

    async def setup(self):
        await self.connect()
        await self.users_db.create_users_table()
        await self.videos_db.create_videos_table()
        await self.mailing_db.create_mailing_table()
        await self.settings_db.create_settings_table()
        await self.stats_db_manager.create_stats_table()
        await self.quests_db.create_quest_statuses_table()
        await self.counters_db.create_user_counters_table()

    async def create_quest_statuses_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS user_quest_statuses (
            id BIGSERIAL PRIMARY KEY,
            telegram_id BIGINT REFERENCES tg_users(telegram_id) ON DELETE CASCADE,
            quest_id TEXT NOT NULL,
            status TEXT NOT NULL, -- 'visited', 'completed', 'unclaimed'
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (telegram_id, quest_id)
        );
        -- Индекс для быстрого поиска по пользователю
        CREATE INDEX IF NOT EXISTS idx_user_quest_status ON user_quest_statuses (telegram_id, status);
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def get_all_users(self) -> list[int]:
        """
        Возвращает список всех telegram_id для рассылки.
        """
        query = "SELECT telegram_id FROM tg_users WHERE is_alive = TRUE;"
        async with self.pool.acquire() as conn:
            # fetchcol возвращает список значений из первого столбца
            rows = await conn.fetch(query)
            return [row['telegram_id'] for row in rows]
        


    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
        self.users_db = None
        self.videos_db = None
        self.mailing_db = None
        self.settings_db = None

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




# ------------------ GLOBAL ------------------
db_manager = DatabaseManager(DB_URL)


async def init_db():
    await db_manager.setup()


if __name__ == "__main__":
    asyncio.run(init_db())