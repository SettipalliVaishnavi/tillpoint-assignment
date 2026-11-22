
"""Creating, cancelling and listing orders."""
from datetime import timedelta

from . import db, pricing
from .catalog import Catalog


class OrderError(Exception):
    pass


class Orders:
    RESERVATION_MINUTES = 30

    def __init__(self, conn, catalog=None):
        self.conn = conn
        self.catalog = catalog or Catalog(conn)

    def create(self, customer, items, region="NONE", coupon_code=None, now=None):
        """Create an order and reserve its stock."""
        if not items:
            raise OrderError("an order needs at least one item")
        if any(qty <= 0 for _, qty in items):
            raise OrderError("quantities must be positive")

        self.expire_pending_orders(now=now)

        self.conn.execute("BEGIN IMMEDIATE")
        try:
            coupon = self._coupon(coupon_code)
            priced = [
                (sku, qty, self.catalog.get_product(sku).price_cents)
                for sku, qty in items
            ]
            totals = pricing.price_order(
                [(price, qty) for _, qty, price in priced],
                region,
                coupon
            )

            for sku, qty, _ in priced:
                self.catalog.reserve(sku, qty)

            if coupon is not None:
                self.conn.execute(
                    "UPDATE coupons SET uses = uses + 1 WHERE code = ?",
                    (coupon_code,)
                )

            cur = self.conn.execute(
                "INSERT INTO orders (customer, region, coupon, subtotal_cents, "
                "discount_cents, tax_cents, total_cents, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    customer,
                    region,
                    coupon_code,
                    totals["subtotal_cents"],
                    totals["discount_cents"],
                    totals["tax_cents"],
                    totals["total_cents"],
                    db.to_iso(now or db.utcnow())
                )
            )

            order_id = cur.lastrowid

            self.conn.executemany(
                "INSERT INTO order_items "
                "(order_id, sku, qty, unit_price_cents) VALUES (?, ?, ?, ?)",
                [
                    (order_id, sku, qty, price)
                    for sku, qty, price in priced
                ]
            )

            self.conn.execute("COMMIT")

        except Exception:
            self.conn.execute("ROLLBACK")
            raise

        return self.get(order_id)

    def cancel(self, order_id):
        """Cancel an order and release its reserved stock."""
        order = self.get(order_id)

        if order["status"] == "cancelled":
            return order

        if order["status"] == "shipped":
            raise OrderError("a shipped order cannot be cancelled")

        self.conn.execute("BEGIN IMMEDIATE")
        try:
            for item in order["items"]:
                self.catalog.release(item["sku"], item["qty"])

            if order["coupon"]:
                self.conn.execute(
                    "UPDATE coupons SET uses = uses - 1 "
                    "WHERE code = ? AND uses > 0",
                    (order["coupon"],)
                )

            self.conn.execute(
                "UPDATE orders SET status = 'cancelled' WHERE id = ?",
                (order_id,)
            )

            self.conn.execute("COMMIT")

        except Exception:
            self.conn.execute("ROLLBACK")
            raise

        return self.get(order_id)

    def expire_pending_orders(self, now=None):
        """Cancel unpaid orders older than the reservation time limit."""
        now = now or db.utcnow()
        cutoff = now - timedelta(minutes=self.RESERVATION_MINUTES)

        expired_orders = self.conn.execute(
            "SELECT id FROM orders "
            "WHERE status = 'pending' AND created_at <= ?",
            (db.to_iso(cutoff),)
        ).fetchall()

        expired_count = 0

        for row in expired_orders:
            self.cancel(row["id"])
            expired_count += 1

        return expired_count

    def ship(self, order_id):
        order = self.get(order_id)

        if order["status"] != "paid":
            raise OrderError("only a paid order can ship")

        self.conn.execute(
            "UPDATE orders SET status = 'shipped' WHERE id = ?",
            (order_id,)
        )

        return self.get(order_id)

    def get(self, order_id):
        row = self.conn.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        ).fetchone()

        if row is None:
            raise OrderError(f"no order {order_id}")

        order = dict(row)

        order["items"] = [
            dict(r)
            for r in self.conn.execute(
                "SELECT sku, qty, unit_price_cents "
                "FROM order_items WHERE order_id = ? ORDER BY rowid",
                (order_id,)
            )
        ]

        return order

    def list_for(self, customer, page=1, per_page=20):
        rows = self.conn.execute(
            "SELECT id FROM orders WHERE customer = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (customer, per_page, (page - 1) * per_page)
        ).fetchall()

        return [self.get(r["id"]) for r in rows]

    def _coupon(self, code):
        if code is None:
            return None

        row = self.conn.execute(
            "SELECT * FROM coupons WHERE code = ?",
            (code,)
        ).fetchone()

        if row is None:
            raise pricing.CouponRejected(f"unknown coupon {code}")

        return row
