import asyncio
import aiosqlite
from pathlib import Path
from storj_monitor.config import load_settings, get_settings

SCHEMA_PATH = Path("db/schema.sql")


async def init_db():
    settings = load_settings()
    db_path = Path(settings.database.path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        # Enable WAL mode if configured
        if settings.database.wal_mode:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")

        # Apply schema
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        await db.executescript(schema_sql)

        # Seed nodes table from config
        for node in settings.nodes:
            await db.execute(
                """
                INSERT OR IGNORE INTO nodes (name, dashboard_url, description)
                VALUES (?, ?, ?)
                """,
                (node.name, node.dashboard_url, node.description),
            )
        await db.commit()

    print(f"Database initialized at {db_path.resolve()}")


if __name__ == "__main__":
    asyncio.run(init_db())
