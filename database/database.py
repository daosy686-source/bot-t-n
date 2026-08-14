"""
Lớp Database bọc quanh aiosqlite, cung cấp toàn bộ thao tác đọc/ghi cho
guild_config, products và orders. Database tự tạo file/thư mục nếu chưa có
và không bao giờ lưu token hoặc thông tin đăng nhập nhạy cảm của khách.
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import List, Optional

import aiosqlite

from database.models import SCHEMA_SQL, GuildConfig, Order, Product


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def init_db(self, seed_products: Optional[List[dict]] = None):
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode = WAL;")
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.execute(
            "INSERT OR IGNORE INTO order_counter (id, counter) VALUES (1, 0);"
        )
        await self._conn.commit()

        if seed_products:
            cur = await self._conn.execute("SELECT COUNT(*) AS c FROM products;")
            row = await cur.fetchone()
            if row["c"] == 0:
                await self._seed_products(seed_products)

    async def close(self):
        if self._conn is not None:
            await self._conn.close()

    async def _seed_products(self, products: List[dict]):
        now = _now()
        rows = [
            (
                p["product_id"],
                p["category"],
                p["name"],
                p.get("original_price"),
                p["sale_price"],
                p.get("note"),
                now,
            )
            for p in products
        ]
        await self._conn.executemany(
            """
            INSERT OR IGNORE INTO products
                (product_id, category, name, original_price, sale_price, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        await self._conn.commit()

    # ------------------------------------------------------------------
    # Guild config
    # ------------------------------------------------------------------
    async def get_guild_config(self, guild_id: int) -> Optional[GuildConfig]:
        cur = await self._conn.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?;", (guild_id,)
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return GuildConfig(**dict(row))

    async def set_guild_config(
        self,
        guild_id: int,
        order_channel_id: int,
        log_channel_id: int,
        price_channel_id: int,
        staff_role_id: int,
        admin_role_id: int,
        ticket_channel_id: int,
    ):
        async with self._lock:
            await self._conn.execute(
                """
                INSERT INTO guild_config
                    (guild_id, order_channel_id, log_channel_id, price_channel_id,
                     staff_role_id, admin_role_id, ticket_channel_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    order_channel_id=excluded.order_channel_id,
                    log_channel_id=excluded.log_channel_id,
                    price_channel_id=excluded.price_channel_id,
                    staff_role_id=excluded.staff_role_id,
                    admin_role_id=excluded.admin_role_id,
                    ticket_channel_id=excluded.ticket_channel_id;
                """,
                (
                    guild_id,
                    order_channel_id,
                    log_channel_id,
                    price_channel_id,
                    staff_role_id,
                    admin_role_id,
                    ticket_channel_id,
                ),
            )
            await self._conn.commit()

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    async def list_products(
        self, category: Optional[str] = None, active_only: bool = True
    ) -> List[Product]:
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY sale_price ASC;"
        cur = await self._conn.execute(query, params)
        rows = await cur.fetchall()
        return [self._row_to_product(r) for r in rows]

    async def get_product(self, product_id: str) -> Optional[Product]:
        cur = await self._conn.execute(
            "SELECT * FROM products WHERE product_id = ?;", (product_id,)
        )
        row = await cur.fetchone()
        return self._row_to_product(row) if row else None

    async def add_product(self, product: Product):
        async with self._lock:
            await self._conn.execute(
                """
                INSERT INTO products
                    (product_id, category, name, original_price, sale_price, note, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    product.product_id,
                    product.category,
                    product.name,
                    product.original_price,
                    product.sale_price,
                    product.note,
                    _now(),
                ),
            )
            await self._conn.commit()

    async def edit_product(self, product_id: str, **fields) -> bool:
        if not fields:
            return False
        allowed = {"category", "name", "original_price", "sale_price", "note", "is_active"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return False
        async with self._lock:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [product_id]
            cur = await self._conn.execute(
                f"UPDATE products SET {set_clause} WHERE product_id = ?;", values
            )
            await self._conn.commit()
            return cur.rowcount > 0

    async def remove_product(self, product_id: str) -> bool:
        async with self._lock:
            cur = await self._conn.execute(
                "DELETE FROM products WHERE product_id = ?;", (product_id,)
            )
            await self._conn.commit()
            return cur.rowcount > 0

    @staticmethod
    def _row_to_product(row) -> Product:
        d = dict(row)
        d["is_active"] = bool(d["is_active"])
        return Product(**d)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    async def next_order_id(self) -> str:
        async with self._lock:
            cur = await self._conn.execute(
                "UPDATE order_counter SET counter = counter + 1 WHERE id = 1 RETURNING counter;"
            )
            row = await cur.fetchone()
            await self._conn.commit()
            return f"ORDER-{row['counter']:04d}"

    async def create_order(self, order: Order):
        async with self._lock:
            now = _now()
            order.created_at = now
            await self._conn.execute(
                """
                INSERT INTO orders (
                    order_id, guild_id, user_id, product_id, product_name, category,
                    original_price, sale_price, addon_no_sw, customer_note, link_data,
                    status, staff_id, created_at, processing_at, completed_at,
                    cancelled_at, cancel_reason, dm_notified, channel_id, message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.order_id,
                    order.guild_id,
                    order.user_id,
                    order.product_id,
                    order.product_name,
                    order.category,
                    order.original_price,
                    order.sale_price,
                    int(order.addon_no_sw),
                    order.customer_note,
                    order.link_data,
                    order.status,
                    order.staff_id,
                    now,
                    order.processing_at,
                    order.completed_at,
                    order.cancelled_at,
                    order.cancel_reason,
                    int(order.dm_notified),
                    order.channel_id,
                    order.message_id,
                ),
            )
            await self._conn.commit()

    async def get_order(self, order_id: str) -> Optional[Order]:
        cur = await self._conn.execute(
            "SELECT * FROM orders WHERE order_id = ?;", (order_id,)
        )
        row = await cur.fetchone()
        return self._row_to_order(row) if row else None

    async def set_order_message(self, order_id: str, channel_id: int, message_id: int):
        async with self._lock:
            await self._conn.execute(
                "UPDATE orders SET channel_id = ?, message_id = ? WHERE order_id = ?;",
                (channel_id, message_id, order_id),
            )
            await self._conn.commit()

    async def update_order_status(
        self,
        order_id: str,
        status: str,
        staff_id: Optional[int] = None,
        link_data: Optional[str] = None,
        cancel_reason: Optional[str] = None,
    ):
        from database.models import (
            STATUS_CANCELLED,
            STATUS_COMPLETED,
            STATUS_PROCESSING,
        )

        now = _now()
        fields = ["status = ?"]
        values = [status]

        if staff_id is not None:
            fields.append("staff_id = ?")
            values.append(staff_id)
        if status == STATUS_PROCESSING:
            fields.append("processing_at = ?")
            values.append(now)
        if status == STATUS_COMPLETED:
            fields.append("completed_at = ?")
            values.append(now)
            if link_data is not None:
                fields.append("link_data = ?")
                values.append(link_data)
        if status == STATUS_CANCELLED:
            fields.append("cancelled_at = ?")
            values.append(now)
            if cancel_reason is not None:
                fields.append("cancel_reason = ?")
                values.append(cancel_reason)

        values.append(order_id)
        async with self._lock:
            await self._conn.execute(
                f"UPDATE orders SET {', '.join(fields)} WHERE order_id = ?;", values
            )
            await self._conn.commit()

    async def set_dm_notified(self, order_id: str, value: bool = True):
        async with self._lock:
            await self._conn.execute(
                "UPDATE orders SET dm_notified = ? WHERE order_id = ?;",
                (int(value), order_id),
            )
            await self._conn.commit()

    @staticmethod
    def _row_to_order(row) -> Order:
        d = dict(row)
        d["addon_no_sw"] = bool(d["addon_no_sw"])
        d["dm_notified"] = bool(d["dm_notified"])
        return Order(**d)
