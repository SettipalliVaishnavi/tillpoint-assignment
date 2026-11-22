
"""Payment provider webhooks. The provider may retry webhook deliveries."""

from . import db


class PaymentError(Exception):
    pass


class Payments:
    def __init__(self, conn):
        self.conn = conn

    def handle_event(self, event, now=None):
        """Process successful payments once and flag extra captures for review."""

        if event.get("type") != "payment.succeeded":
            return None

        order = self.conn.execute(
            "SELECT * FROM orders WHERE id = ?",
            (event["order_id"],)
        ).fetchone()

        if order is None:
            raise PaymentError(
                f"payment for unknown order {event['order_id']}"
            )

        if order["status"] == "cancelled":
            raise PaymentError(f"order {order['id']} is cancelled")

        received_at = db.to_iso(now or db.utcnow())

        # Ignore a retry of an event already accepted or flagged for review.
        existing = self.conn.execute(
            """
            SELECT event_id FROM payments WHERE event_id = ?
            UNION ALL
            SELECT event_id FROM payment_reviews WHERE event_id = ?
            """,
            (event["id"], event["id"])
        ).fetchone()

        if existing is not None:
            return order["status"]

        # A second distinct successful payment must not increase order revenue.
        if order["status"] == "paid" or order["status"] == "shipped":
            self.conn.execute(
                """
                INSERT INTO payment_reviews
                (order_id, event_id, amount_cents, received_at, reason)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order["id"],
                    event["id"],
                    event["amount_cents"],
                    received_at,
                    "Additional successful payment for an already-paid order"
                )
            )
            return order["status"]

        # Accept the first successful payment.
        self.conn.execute(
            """
            INSERT INTO payments
            (order_id, event_id, amount_cents, received_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(event_id) DO NOTHING
            """,
            (
                order["id"],
                event["id"],
                event["amount_cents"],
                received_at
            )
        )

        if self.paid_cents(order["id"]) >= order["total_cents"]:
            self.conn.execute(
                "UPDATE orders SET status = 'paid' WHERE id = ?",
                (order["id"],)
            )
            return "paid"

        return order["status"]

    def paid_cents(self, order_id):
        row = self.conn.execute(
            """
            SELECT COALESCE(SUM(amount_cents), 0) AS paid
            FROM payments
            WHERE order_id = ?
            """,
            (order_id,)
        ).fetchone()

        return row["paid"]
