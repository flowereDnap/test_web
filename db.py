import os
import asyncio
import asyncpg
import random
import logging
from dotenv import load_dotenv
from datetime import datetime, date

load_dotenv()
DB_URL = os.getenv("DATABASE_DSN")
if not DB_URL:
    raise ValueError("Ссылка на базу данных (PG_LINK) не указана в .env")

logger = logging.getLogger(__name__)

# ------------------ USERS ------------------
class UsersDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.db_url = db_url
        self.pool = pool

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

    async def add_user(self, telegram_id, username=None, first_name=None, last_name=None, language_code=None, timezone=None, is_premium=False):
        query = """
        INSERT INTO tg_users (telegram_id, username, first_name, last_name, language_code, timezone, is_premium)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (telegram_id) DO NOTHING;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, telegram_id, username, first_name, last_name, language_code, timezone, is_premium)

    async def get_user_by_telegram_id(self, telegram_id: int):
        query = "SELECT * FROM tg_users WHERE telegram_id = $1;"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, telegram_id)

    async def update_balance(self, telegram_id: int, amount: float):
        query = "UPDATE tg_users SET balance = balance + $1 WHERE telegram_id = $2;"
        async with self.pool.acquire() as conn:
            await conn.execute(query, amount, telegram_id)

    async def add_referral(self, referrer_id: int, referral_id: int):
        query = """
        UPDATE tg_users
        SET referrals = COALESCE(referrals, ARRAY[]::BIGINT[]) || ARRAY[$1]::BIGINT[]
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, referral_id, referrer_id)

    async def update_is_alive(self, telegram_id: int, is_alive: bool):
        query = "UPDATE tg_users SET is_alive = $1 WHERE telegram_id = $2;"
        async with self.pool.acquire() as conn:
            await conn.execute(query, is_alive, telegram_id)

    async def add_quest_done(self, telegram_id: int, quest_id: int):
        query = "UPDATE tg_users SET quests_done = COALESCE(quests_done, ARRAY[]::BIGINT[]) || ARRAY[$1]::BIGINT[] WHERE telegram_id = $2;"
        async with self.pool.acquire() as conn:
            await conn.execute(query, quest_id, telegram_id)

# ------------------ VIDEOS ------------------
class VideosDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None, videos_path: str = "vids"):
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

    async def add_video_if_not_exists(self, title: str, video_url: str):
        query = "INSERT INTO videos (title, video_url) VALUES ($1, $2) ON CONFLICT (video_url) DO NOTHING;"
        async with self.pool.acquire() as conn:
            await conn.execute(query, title, video_url)

    async def sync_videos_from_folder(self):
        if not os.path.exists(self.videos_path):
            print(f"Папка {self.videos_path} не найдена")
            return
        for filename in os.listdir(self.videos_path):
            if filename.lower().endswith((".mp4", ".mov", ".webm")):
                video_path = os.path.join(self.videos_path, filename)
                title = os.path.splitext(filename)[0]
                await self.add_video_if_not_exists(title=title, video_url=video_path)

    async def get_random_video(self):
        query = "SELECT * FROM videos WHERE is_active = TRUE;"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return random.choice(rows) if rows else None

    async def increment_watched(self, video_id: int):
        query = "UPDATE videos SET watched = watched + 1 WHERE id = $1;"
        async with self.pool.acquire() as conn:
            await conn.execute(query, int(video_id))

# ------------------ MAILING ------------------
class MailingDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.pool = pool

    async def create_mailing_table(self):
        async with self.pool.acquire() as conn:
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
            CREATE TABLE IF NOT EXISTS mailing_runs (
                id BIGSERIAL PRIMARY KEY,
                mailing_id BIGINT REFERENCES mailings(id) ON DELETE CASCADE,
                users_count INTEGER DEFAULT 0,
                start_time TIMESTAMPTZ DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS mailing_stats (
                id BIGSERIAL PRIMARY KEY,
                run_id BIGINT REFERENCES mailing_runs(id) ON DELETE CASCADE,
                telegram_id BIGINT NOT NULL,
                status TEXT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT now()
            );
            """)

    async def start_new_run(self, mailing_id: int) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("INSERT INTO mailing_runs (mailing_id) VALUES ($1) RETURNING id;", mailing_id)

    async def log_stat(self, run_id: int, telegram_id: int, status: str):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO mailing_stats (run_id, telegram_id, status) VALUES ($1, $2, $3);", run_id, telegram_id, status)

    async def add_broadcast(self, name, title, text, **kwargs):
        query = """INSERT INTO mailings (name, title, text, media_url, media_type, button_text, button_link) 
                   VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, name, title, text, kwargs.get('media_url'), kwargs.get('media_type'), kwargs.get('button_text'), kwargs.get('button_link'))

    async def get_all_broadcast_names(self):
        query = "SELECT DISTINCT ON (name) id, name FROM mailings ORDER BY name, created_at DESC;"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]

    async def get_mailing_by_run_id(self, run_id: int):
        query = "SELECT m.* FROM mailings m JOIN mailing_runs mr ON m.id = mr.mailing_id WHERE mr.id = $1;"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, run_id)

    async def get_stats(self, run_id: int):
        query = "SELECT status, COUNT(*) FROM mailing_stats WHERE run_id = $1 GROUP BY status;"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, run_id)
            return {r['status']: r['count'] for r in rows}

# ------------------ QUESTS & COUNTERS ------------------
class QuestStatusDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.pool = pool

    async def create_quest_statuses_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS user_quest_statuses (
            id BIGSERIAL PRIMARY KEY,
            telegram_id BIGINT REFERENCES tg_users(telegram_id) ON DELETE CASCADE,
            quest_id TEXT NOT NULL,
            status TEXT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (telegram_id, quest_id)
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def set_quest_status(self, telegram_id: int, quest_id: str, status: str):
        """
        Устанавливает статус квеста: 'initial', 'visited', 'ready_to_claim', 'completed'
        """
        query = """
        INSERT INTO user_quests (telegram_id, quest_id, status)
        VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id, quest_id) 
        DO UPDATE SET status = EXCLUDED.status, updated_at = now();
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, telegram_id, quest_id, status)

    async def get_user_quest_statuses(self, telegram_id: int):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT quest_id, status FROM user_quest_statuses WHERE telegram_id = $1", telegram_id)
            return [dict(r) for r in rows]

class CountersDBManager:
    def __init__(self, db_url: str, pool: asyncpg.pool.Pool | None = None):
        self.pool = pool

    async def create_user_counters_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS user_counters (
            id BIGSERIAL PRIMARY KEY,
            telegram_id BIGINT REFERENCES tg_users(telegram_id) ON DELETE CASCADE,
            counter_key TEXT NOT NULL,
            value INTEGER DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (telegram_id, counter_key)
        );
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def increment_counter(self, telegram_id: int, counter_key: str, increment: int = 1):
        query = """
        INSERT INTO user_counters (telegram_id, counter_key, value) VALUES ($1, $2, $3)
        ON CONFLICT (telegram_id, counter_key) DO UPDATE SET value = user_counters.value + $3 RETURNING value;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, telegram_id, counter_key, increment)

    async def get_counter(self, telegram_id: int, counter_key: str):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT value FROM user_counters WHERE telegram_id = $1 AND counter_key = $2", telegram_id, counter_key) or 0

# ------------------ DAILY STATISTICS ------------------
class DailyStatsManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.today = date.today()
        self.stats = {"new_users": 0, "active_users": 0, "videos_watched": 0, "clicks": 0, "total_balance": 0.0, "quests_done": 0, "cash_outs": 0}

    async def collect_and_save(self):
        today = date.today()
        async with self.db.pool.acquire() as conn:
            new_users = await conn.fetchval("SELECT COUNT(*) FROM tg_users WHERE created_at::date = $1", today)
            watched = await conn.fetchval("SELECT SUM(watched) FROM videos") or 0
            balance = await conn.fetchval("SELECT SUM(balance) FROM tg_users") or 0
            
            query = """
            INSERT INTO daily_statistics (stat_date, new_users, videos_watched, total_balance)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (stat_date) DO UPDATE SET 
            new_users = EXCLUDED.new_users, videos_watched = EXCLUDED.videos_watched, total_balance = EXCLUDED.total_balance
            """
            await conn.execute(query, today, new_users, watched, balance)

# ------------------ DATABASE MANAGER ------------------
class DatabaseManager:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None
        self.users_db = None
        self.videos_db = None
        self.mailing_db = None
        self.quests_db = None
        self.counters_db = None
        self.daily_stats = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=10)
        self.users_db = UsersDBManager(self.db_url, self.pool)
        self.videos_db = VideosDBManager(self.db_url, self.pool)
        self.mailing_db = MailingDBManager(self.db_url, self.pool)
        self.quests_db = QuestStatusDBManager(self.db_url, self.pool)
        self.counters_db = CountersDBManager(self.db_url, self.pool)
        self.daily_stats = DailyStatsManager(self)

    async def setup(self):
        await self.connect()
        await self.users_db.create_users_table()
        await self.videos_db.create_videos_table()
        await self.mailing_db.create_mailing_table()
        await self.quests_db.create_quest_statuses_table()
        await self.counters_db.create_user_counters_table()
        # Таблица статистики
        async with self.pool.acquire() as conn:
            await conn.execute("""CREATE TABLE IF NOT EXISTS daily_statistics (
                stat_date DATE PRIMARY KEY, new_users BIGINT DEFAULT 0, videos_watched BIGINT DEFAULT 0,
                total_balance NUMERIC(18,2) DEFAULT 0, quests_done BIGINT DEFAULT 0, cash_outs BIGINT DEFAULT 0
            );""")

    async def get_all_user_ids(self) -> list[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT telegram_id FROM tg_users WHERE is_alive = TRUE;")
            return [row['telegram_id'] for row in rows]

    async def close(self):
        if self.pool: await self.pool.close()

db_manager = DatabaseManager(DB_URL)