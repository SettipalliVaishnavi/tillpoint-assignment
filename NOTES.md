# NOTES

## 1. Report

> Finance says that on some days the revenue in the daily report is higher than what the payment provider paid out, and a few orders show more money received than their total.

**Status:** Partly fixed

**What I saw:** The same successful payment webhook could be processed more than once. Repeated deliveries with the same event ID created multiple payment records and increased the amount counted for an order.

**Root cause:** The payments table did not enforce uniqueness on the provider event ID, and the webhook handler inserted every delivery without checking whether that event had already been processed.

**Fix and why:** Added a unique index on `payments.event_id` and used `ON CONFLICT(event_id) DO NOTHING` when inserting payments. This prevents the same provider event from being counted more than once. Separate successful payments with different event IDs are handled by the additional-payment review mechanism described in Report 6. Full provider payout reconciliation is not implemented.

**How I verified it:** Added `test_duplicate_payment_webhook_is_not_counted_twice`. The test failed before the fix because two records were created for the same event, and passed after the fix. The complete test suite also passed.

**Commits:** `4386348`, `c47a762`

## 2. Report

> Products show as sold out, or nearly, while the shelf is full. Staff say it gets worse on days when many customers abandon checkout.

**Status:** Fixed

**What I saw:** Stock was reserved when an order was created. Cancelling a pending order did not restore its reserved stock. Abandoned pending orders could also keep stock reserved.

**Root cause:** The cancellation logic restored stock only for paid orders. Pending orders were not handled correctly, and there was no expiry process for abandoned unpaid orders.

**Fix and why:** Updated cancellation to release stock for pending and paid orders. Added a 30-minute expiry for pending orders. Expired orders are cancelled and their reserved stock is released. Expiry cleanup runs when a new order is created or an API request is handled; it is not a separate background scheduler.

**How I verified it:** Added tests for cancelling pending orders, expiring pending orders after 30 minutes, and confirming that orders do not expire before 30 minutes. All tests passed.

**Commits:** `8f202f5`

## 3. Report

> Customers in taxed regions who used a coupon say the tax on their receipt is too high. Receipts without a coupon are right.

**Status:** Fixed

**What I saw:** The tax was calculated using the original subtotal before applying the coupon discount.

**Root cause:** The pricing function calculated tax before subtracting the coupon discount from the subtotal.

**Fix and why:** Changed the calculation order so the coupon discount is applied first. Tax is now calculated on the discounted taxable amount. This keeps the calculation consistent with the expected receipt total.

**How I verified it:** Added `test_coupon_discount_is_applied_before_tax`. For a 1,200-cent item with a 10% coupon in the CA tax region, the test checks a 120-cent discount, 78-cent tax, and 1,158-cent total. The test passed after the fix.

**Commits:** `3b1df4a`

## 4. Report

> Our shop in India (UTC+5:30) says sales taken in the morning do not appear in that day's report and turn up under the day before.

**Status:** Fixed

**What I saw:** The UTC boundaries for a shop-local calendar day were calculated in the wrong direction when a positive UTC offset was supplied.

**Root cause:** The `day_bounds_utc()` function added the shop's UTC offset instead of subtracting it to convert local midnight into UTC.

**Fix and why:** Changed the function to subtract the UTC offset when calculating the UTC start of the local day. The end boundary is calculated as 24 hours after the start.

**How I verified it:** Added `test_daily_sales_uses_india_timezone`. It checks that a payment received at 20:00 UTC on March 10 appears in the March 11 report for UTC+5:30. The test failed before the fix and passed afterwards.

**Commits:** `b8c29af`

## 5. Report

> Ever since we started running two server workers, we have sold more units of an item than we had, and its stock went negative.

**Status:** Fixed

**What I saw:** Two catalog instances could cache the same stock quantity. One worker could update the database while another worker still used its old cached stock value.

**Root cause:** The original reserve function checked stock using a cached product value and then performed a separate database update. The check and deduction were not one atomic database operation.

**Fix and why:** Changed the reservation query to update stock only when the database's current stock is greater than or equal to the requested quantity. The database checks and deducts stock in one conditional SQL update. The local cache is cleared after a successful reservation.

**How I verified it:** Added `test_stale_cache_cannot_oversell_stock` using two separate SQLite connections to simulate two server workers. Both workers initially read the same stock. After the first worker reserves two of three units, the second worker's attempt to reserve two units raises `OutOfStock`. The remaining stock stays at one. The test failed before the fix and passed afterwards.

**Commits:** `6866899`

## 6. Open Question

> Sometimes a customer really does pay twice for one order (two separate payments, not a retry of the same one).

**My decision:** Accept the first successful payment for the order. Do not count a second distinct successful payment as normal order revenue. Record the additional payment for manual review and possible refund.

**Why:** An order should not be counted as receiving more money than its total just because two separate payment events succeeded. At the same time, the second payment may represent real money captured from the customer, so it must not be silently discarded.

**What it costs:** The additional payment needs manual review and refund handling. This implementation flags the payment but does not automatically issue a refund or communicate with the payment provider's refund API.

**What I built:** Added a `payment_reviews` table to store additional successful payments. Updated the payment handler to check whether the order is already paid or shipped. If it is, the new payment is stored with status `needs_review` instead of being added to normal order payments. The event ID is unique in the review table so webhook retries do not create duplicate review records.

**How I verified it:** Added `test_second_distinct_payment_is_flagged_for_review`. It verifies that only the first payment contributes to normal order revenue, the second payment is stored for review, and retrying the second event does not create another review record. The test passed. The full test suite passed with 15 tests.

**Commits:** `c47a762`

## Other Things I Noticed

Pending-order expiry is triggered by API activity or new order creation rather than a background scheduler. This means an abandoned order may remain pending beyond 30 minutes until another request triggers cleanup. This limitation is documented above.

Automatic refunds for additional successful payments are not implemented. Such payments are retained for manual review.

## Session Logs

AI tool used: ChatGPT.

- ChatGPT assessment and debugging conversation: `chatgpt_tillpoint_assessment.md`
