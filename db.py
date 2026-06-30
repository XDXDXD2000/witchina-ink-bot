import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import aiosqlite
from dataclasses import dataclass

from config import DB_PATH

@dataclass
class Service:
    id: int
    name: str
    duration_minutes: int
    price: int
    description: str = ""

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    description TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    phone TEXT NOT NULL,
                    service_id INTEGER NOT NULL,
                    slot_start TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'booked',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    reminder_sent INTEGER DEFAULT 0,
                    secret_used TEXT,
                    discount_percent INTEGER DEFAULT 0,
                    FOREIGN KEY (service_id) REFERENCES services(id)
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    rating INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT (datetime('now', 'localtime'))
                );

                CREATE INDEX IF NOT EXISTS idx_appointments_slot_start ON appointments(slot_start);
                CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);

                INSERT OR IGNORE INTO services (id, name, duration_minutes, price, description) VALUES
                    (1, 'Консультация', 30, 0, 'Бесплатно'),
                    (2, 'Минимализм', 60, 2000, 'От 2000 руб.'),
                    (3, 'До 20 см', 120, 6000, 'От 6000 руб.'),
                    (4, 'Цветная', 90, 4000, 'От 4000 руб.'),
                    (5, '20 см и более', 180, 9000, 'От 9000 руб.');
            """)
            print("✅ База данных создана!")

    async def get_services(self) -> List[Service]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, name, duration_minutes, price, description FROM services") as cursor:
                rows = await cursor.fetchall()
                return [Service(**dict(row)) for row in rows]

    async def get_free_slots(self, date_str: str) -> List[str]:
        from config import WORK_START_HOUR, WORK_END_HOUR, SLOT_DURATION_MINUTES
        
        start_dt = datetime.strptime(date_str, "%Y-%m-%d")
        end_dt = start_dt.replace(hour=WORK_END_HOUR, minute=0)
        
        all_slots = []
        current = start_dt.replace(hour=WORK_START_HOUR, minute=0)
        while current < end_dt:
            if current > datetime.now() + timedelta(hours=0):
                all_slots.append(current.strftime("%H:%M"))
            current += timedelta(minutes=SLOT_DURATION_MINUTES)
        
        if not all_slots:
            return []
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT slot_start FROM appointments
                WHERE date(slot_start) = ? AND status IN ('booked', 'reminded')
            """
            async with db.execute(query, (date_str,)) as cursor:
                rows = await cursor.fetchall()
                booked_slots = [row["slot_start"].split("T")[1][:5] for row in rows]
        
        return [slot for slot in all_slots if slot not in booked_slots]

    async def book_appointment(self, user_id: int, username: str, phone: str, 
                               service_id: int, slot_start: str, description: str = "",
                               secret_used: str = None, discount_percent: int = 0) -> Optional[int]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            await db.execute("BEGIN")
            try:
                cursor = await db.execute(
                    "SELECT id FROM appointments WHERE slot_start = ? AND status IN ('booked', 'reminded')",
                    (slot_start,)
                )
                existing = await cursor.fetchone()
                if existing:
                    await db.rollback()
                    return None
                
                cursor = await db.execute(
                    """
                    INSERT INTO appointments 
                    (user_id, username, phone, service_id, slot_start, description, secret_used, discount_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, username, phone, service_id, slot_start, description, secret_used, discount_percent)
                )
                appointment_id = cursor.lastrowid
                await db.commit()
                return appointment_id
            except Exception as e:
                await db.rollback()
                raise e

    async def get_user_appointments(self, user_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT a.*, s.name as service_name, s.price
                FROM appointments a
                JOIN services s ON a.service_id = s.id
                WHERE a.user_id = ? AND a.status IN ('booked', 'reminded')
                AND datetime(a.slot_start) > datetime('now')
                ORDER BY a.slot_start ASC
            """
            async with db.execute(query, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_appointments(self) -> List[Dict[str, Any]]:
        """Для админа: все записи"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT a.*, s.name as service_name
                FROM appointments a
                JOIN services s ON a.service_id = s.id
                WHERE a.status IN ('booked', 'reminded')
                ORDER BY a.slot_start ASC
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_appointment_by_id(self, appointment_id: int) -> Optional[Dict[str, Any]]:
        """Получить запись по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT a.*, s.name as service_name
                FROM appointments a
                JOIN services s ON a.service_id = s.id
                WHERE a.id = ?
            """
            async with db.execute(query, (appointment_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Для рассылки: все пользователи"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT DISTINCT user_id, username 
                FROM appointments 
                WHERE user_id IS NOT NULL
                ORDER BY user_id
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def cancel_appointment(self, appointment_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            result = await db.execute(
                "UPDATE appointments SET status = 'cancelled' WHERE id = ? AND user_id = ?",
                (appointment_id, user_id)
            )
            await db.commit()
            return result.rowcount > 0

    async def get_appointments_for_reminder(self, hours_before: int) -> List[Dict[str, Any]]:
        now = datetime.now()
        target_time = now + timedelta(hours=hours_before)
        target_time_str = target_time.strftime("%Y-%m-%dT%H:00:00")
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT a.*, s.name as service_name
                FROM appointments a
                JOIN services s ON a.service_id = s.id
                WHERE datetime(a.slot_start) = datetime(?)
                AND a.status = 'booked' AND a.reminder_sent = 0
            """
            async with db.execute(query, (target_time_str,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def mark_reminder_sent(self, appointment_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE appointments SET reminder_sent = 1 WHERE id = ?",
                (appointment_id,)
            )
            await db.commit()

    async def add_review(self, user_id: int, username: str, rating: int, text: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO reviews (user_id, username, rating, text, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (user_id, username, rating, text)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_approved_reviews(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT * FROM reviews
                WHERE status = 'approved'
                ORDER BY created_at DESC
                LIMIT ?
            """
            async with db.execute(query, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_pending_reviews(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT * FROM reviews
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def moderate_review(self, review_id: int, action: str) -> bool:
        if action not in ['approved', 'rejected']:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            result = await db.execute(
                "UPDATE reviews SET status = ? WHERE id = ? AND status = 'pending'",
                (action, review_id)
            )
            await db.commit()
            return result.rowcount > 0

    async def check_user_reviewed(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM reviews WHERE user_id = ? AND status != 'rejected'",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row is not None

    async def cleanup_old_appointments(self, days: int = 30) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM appointments WHERE status IN ('completed', 'cancelled') AND datetime(created_at) < datetime('now', ?)",
                (f"-{days} days",)
            )
            await db.commit()
            return cursor.rowcount

db = Database()