
import os
import tempfile
import unittest

from tillpoint import db
from tillpoint.catalog import Catalog, OutOfStock


class CatalogConcurrencyTest(unittest.TestCase):

    def test_stale_cache_cannot_oversell_stock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "shop.sqlite")

            # Simulate two separate server workers.
            conn1 = db.connect(database_path)
            conn2 = db.connect(database_path)

            try:
                catalog1 = Catalog(conn1)
                catalog2 = Catalog(conn2)

                catalog1.add_product(
                    "MUG", "Mug", 1200, stock=3
                )

                # Both workers cache the original stock of 3.
                catalog1.get_product("MUG")
                catalog2.get_product("MUG")

                # Worker 1 reserves 2 units.
                catalog1.reserve("MUG", 2)

                # Worker 2 tries to reserve 2 using its stale cache.
                with self.assertRaises(OutOfStock):
                    catalog2.reserve("MUG", 2)

                # Only 1 unit should remain. Stock must never be negative.
                row = conn1.execute(
                    "SELECT stock FROM products WHERE sku = ?",
                    ("MUG",)
                ).fetchone()

                self.assertEqual(row["stock"], 1)

            finally:
                conn1.close()
                conn2.close()


if __name__ == "__main__":
    unittest.main()
