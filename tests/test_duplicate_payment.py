
import unittest

from tillpoint import db
from tillpoint.api import App


class DuplicatePaymentTest(unittest.TestCase):

    def setUp(self):
        self.conn = db.connect()
        self.app = App(self.conn)
        self.app.catalog.add_product(
            "MUG", "Mug", 1200, stock=10
        )

    def tearDown(self):
        self.conn.close()

    def test_second_distinct_payment_is_flagged_for_review(self):
        order = self.app.orders.create(
            "ana", [("MUG", 1)]
        )

        first_payment = {
            "id": "evt_payment_1",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1200
        }

        second_payment = {
            "id": "evt_payment_2",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1200
        }

        self.app.payments.handle_event(first_payment)
        self.app.payments.handle_event(second_payment)

        # Retrying the second event must not create another review.
        self.app.payments.handle_event(second_payment)

        # Only the first payment counts as normal order revenue.
        self.assertEqual(
            self.app.payments.paid_cents(order["id"]),
            1200
        )

        review = self.conn.execute(
            """
            SELECT * FROM payment_reviews
            WHERE event_id = ?
            """,
            ("evt_payment_2",)
        ).fetchone()

        self.assertIsNotNone(review)
        self.assertEqual(review["amount_cents"], 1200)
        self.assertEqual(review["status"], "needs_review")

        review_count = self.conn.execute(
            """
            SELECT COUNT(*) FROM payment_reviews
            WHERE order_id = ?
            """,
            (order["id"],)
        ).fetchone()[0]

        self.assertEqual(review_count, 1)


if __name__ == "__main__":
    unittest.main()
