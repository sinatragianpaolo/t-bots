import os
import aiosqlite

DB_PATH = os.getenv("DATABASE_PATH", "data/casa.db")


async def init_db() -> None:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS filters (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.executemany(
            "INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)",
            [("total_checked",), ("total_sent",)],
        )
        await db.commit()


async def is_seen(listing_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM seen_listings WHERE id = ?", (listing_id,)
        )
        return await cursor.fetchone() is not None


async def mark_seen(listing_id: str, source: str, url: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO seen_listings (id, source, url) VALUES (?, ?, ?)",
            (listing_id, source, url),
        )
        await db.commit()


async def set_filter(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO filters (key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()


async def increment_stats(checked: int, sent: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE stats SET value = value + ? WHERE key = 'total_checked'", (checked,)
        )
        await db.execute(
            "UPDATE stats SET value = value + ? WHERE key = 'total_sent'", (sent,)
        )
        await db.commit()


async def get_stats() -> dict[str, int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key, value FROM stats")
        rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}


async def clear_seen_listings() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM seen_listings")
        row = await cursor.fetchone()
        count = row[0] if row else 0
        await db.execute("DELETE FROM seen_listings")
        await db.commit()
    return count


async def get_effective_filters() -> dict:
    from config import DEFAULT_FILTERS

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key, value FROM filters")
        rows = await cursor.fetchall()
    db_filters = {row[0]: row[1] for row in rows}
    return {**DEFAULT_FILTERS, **db_filters}
