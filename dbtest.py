import os
import asyncpg
from dotenv import load_dotenv



load_dotenv()
DB_URL = os.getenv("DATABASE_DSN")
if not DB_URL:
    raise ValueError("Ссылка на базу данных (PG_LINK) не указана в .env")


class DatabaseManager:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None
        self.users_db = None

    async def connect(self):
        """Создаёт пул подключений и передаёт его во все менеджеры баз данных."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=10, timeout=60)

        # Создаём экземпляры всех менеджеров БД, передавая общий пул подключений
        self.users_db = UsersDBManager(db_url=self.db_url, pool=self.pool)
        

    async def setup(self):
        """Создаёт таблицы, если их нет, и инициализирует БД."""
        await self.connect()
        print("2")
        await self.users_db.create_users_table()
    
    async def close(self):
        """Закрывает пул подключений."""
        if self.pool:
            await self.pool.close()
            self.pool = None






import asyncpg
import os
from dotenv import load_dotenv

class UsersDBManager:
    def __init__(self, db_url, pool):
        """
        Initialize the database manager with the database URL.
        :param db_url: Connection string for PostgreSQL database.
        """
        self.db_url = db_url
        self.pool = pool

    async def connect(self):
        """
        Establish a connection pool to the database.
        """
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,  # Минимальное количество подключений
                max_size=10,  # Максимальное количество подключений
                timeout=60  # Таймаут на установку подключения
            )

    async def close(self):
        """
        Close the connection pool.
        """
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def create_users_table(self):
        """
        Create the users table if it doesn't already exist.
        """
        print("1")
        query = """
        CREATE TABLE IF NOT EXISTS tg_users (
        telegram_id BIGINT PRIMARY KEY,            -- Telegram user id
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        language_code TEXT,
        is_premium BOOLEAN DEFAULT FALSE,
        referrals BIGINT[] DEFAULT '{}',           -- айди рефералов
        is_alive BOOLEAN DEFAULT TRUE,
        logs JSONB DEFAULT '[]',                   -- массив {дата, значение}
        balance NUMERIC(18,2) DEFAULT 0,
        quests_done BIGINT[] DEFAULT '{}',         -- айди выполненных квестов
        cash_out_used BIGINT[] DEFAULT '{}',       -- айди заявок/транзакций вывода
        created_at TIMESTAMPTZ DEFAULT now()
    );

        """
        async with self.pool.acquire() as conn:
            await conn.execute(query)

    async def add_user(self, telegram_id, username=None, full_name=None, promo_code=None, referrer_id=None, language=None, timezone=None):
        """
        Add a new user to the database.
        :param telegram_id: User's Telegram ID (unique).
        :param username: User's Telegram username.
        :param full_name: User's full name.
        :param promo_code: Promo code applied by the user.
        :param referrer_id: Telegram ID of the user who referred this user.
        :param language: Preferred language of the user.
        :param timezone: User's timezone.
        """
        query = """
        INSERT INTO users (telegram_id, username, full_name, promo_code, referrer_id, language, timezone)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (telegram_id) DO NOTHING;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, telegram_id, username, full_name, promo_code, referrer_id, language, timezone)

    async def get_user_by_telegram_id(self, telegram_id):
        """
        Retrieve a user from the database by Telegram ID.
        :param telegram_id: User's Telegram ID.
        :return: User record or None if not found.
        """
        query = "SELECT * FROM users WHERE telegram_id = $1;"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, telegram_id)

    async def update_last_active(self, telegram_id):
        """
        Update the last_active field for a user.
        :param telegram_id: User's Telegram ID.
        """
        query = """
        UPDATE users SET last_active = NOW()
        WHERE telegram_id = $1;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, telegram_id)

    async def add_referral(self, referrer_id, referral_id):
        """
        Add a referral to the referrer's record.
        :param referrer_id: Telegram ID of the referrer user.
        :param referral_id: Telegram ID of the referred user.
        """
        query = """
        UPDATE users
        SET referrals = referrals || to_jsonb($1::BIGINT), referrals_count = referrals_count + 1
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, referral_id, referrer_id)

    async def update_bot_availability(self, telegram_id, is_available):
        """
        Update the bot availability status for a user.
        :param telegram_id: User's Telegram ID.
        :param is_available: Boolean indicating if the bot is available for the user.
        """
        query = """
        UPDATE users
        SET bot_available = $1
        WHERE telegram_id = $2;
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, is_available, telegram_id)

    async def setup(self):
        """
        Set up the database (connect and create tables).
        """
        await self.connect()
        await self.create_users_table()


# Глобальный объект базы данных
db_manager = DatabaseManager(DB_URL)


async def init_db():
    print("3") 
    await db_manager.setup()


import asyncio

if __name__ == "__main__":
    asyncio.run(init_db())

