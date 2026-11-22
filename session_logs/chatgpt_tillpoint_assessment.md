# Tillpoint Assignment – ChatGPT Assessment and Debugging Record

## 1. Interview Preparation

**Question: What should I prepare to explain in the technical interview?**

The main preparation areas are:

- Tillpoint project architecture
- Python backend development
- Order creation and payment processing
- SQLite database operations
- REST APIs and HTTP methods
- Database transactions and concurrency
- Automated testing
- The six reported assignment issues

The most important point is to understand the actual implementation rather than memorise generic answers.

## 2. Tillpoint Project Overview

Tillpoint is a Python-based order-management backend application using SQLite.

Its functionality includes:

- Product and inventory management
- Order creation
- Coupon discounts and tax calculations
- Payment webhook processing
- Order cancellation
- Daily sales reporting

### Main Project Files

| File | Purpose |
|---|---|
| `server.py` | Starts the HTTP server |
| `tillpoint/api.py` | Handles API routes and requests |
| `tillpoint/orders.py` | Handles order operations |
| `tillpoint/payments.py` | Handles payment processing |
| `tillpoint/pricing.py` | Handles pricing, discounts and tax |
| `tillpoint/catalog.py` | Handles product and stock operations |
| `tillpoint/db.py` | Handles SQLite database connections and schema |

## 3. Completed Implementation Work

The local project contains six separate Git commits.

### Git Commits

1. `4386348` – Prevent duplicate payment webhook processing
2. `8f202f5` – Release stock from abandoned pending orders
3. `3b1df4a` – Calculate tax after coupon discount
4. `b8c29af` – Fix daily sales timezone boundaries
5. `6866899` – Prevent concurrent stock overselling
6. `c47a762` – Flag additional successful payments for review

### Automated Tests

The local project has 15 passing automated tests.

Test output:

```text
Ran 15 tests in 0.048s
OK
```

### Six Reported Issues

#### 1. Duplicate Payment Webhook Processing

Implemented duplicate-event protection so that retrying the same payment event does not create duplicate payment effects.

#### 2. Abandoned Pending Orders

Pending orders are expired after 30 minutes when API activity or new order creation triggers the expiry cleanup.

**Limitation:** There is no background scheduler. An abandoned order may remain pending beyond 30 minutes until another request triggers cleanup.

#### 3. Coupon Discount and Tax Calculation

Tax is calculated after applying the coupon discount.

#### 4. Daily Sales Timezone Boundaries

Daily sales reporting handles UTC and India timezone boundaries.

#### 5. Concurrent Stock Overselling

The catalog uses a conditional SQL update:

```sql
UPDATE products
SET stock = stock - ?
WHERE sku = ? AND stock >= ?
```

The update checks available stock before reducing it. The implementation also checks the affected row count and invalidates the product cache after a successful reservation.

#### 6. Additional Successful Payments

The first successful payment is accepted. An additional distinct successful payment is stored in `payment_reviews` with status `needs_review`, rather than being counted as another normal payment.

**Limitation:** Automatic refunds are not implemented. Additional successful payments require manual review.

## 4. Database and Testing

The application uses SQLite.

The database schema includes tables for:

- Products
- Coupons
- Orders
- Order items
- Payments
- Payment reviews

The automated tests cover payment retries, order expiry, tax calculations, timezone boundaries, stock reservation, and pricing behaviour.

## 5. Important Interview Topics

Prepare to explain:

- What is an HTTP API?
- What is a REST API?
- What is a webhook?
- What is idempotency?
- What is a database transaction?
- What is a race condition?
- What is a SQL conditional update?
- What is a database index?
- What is a rollback?
- Why are automated tests important?

Also prepare Python fundamentals, OOP, Django, SQL, and backend development.

## 6. Project Introduction – Interview Practice

"I worked on a Python-based order-management application called Tillpoint. It uses SQLite as its database and provides functionality for product management, order creation, coupon discounts, payment webhooks, and daily sales reports.

During the assignment, I investigated and implemented fixes for issues involving duplicate payment events, abandoned orders, tax calculations, timezone boundaries, stock overselling, and additional successful payments.

I created separate Git commits for the implementation work and added automated tests to verify the changes. My local project currently has 15 passing tests."

## 7. Preparation Rule

The interview explanations must be based on the actual completed source code.

For every technical question:

1. Inspect the relevant source code.
2. Explain what the implementation actually does.
3. Explain why the change was made.
4. Identify limitations and edge cases.
5. Prepare a simple interview-ready answer.
6. Practise follow-up questions.

**Important:** Do not claim that a feature is implemented unless the actual code confirms it.

## 8. Session Log Information

AI tool used: ChatGPT.

This document is an edited record of the assessment discussion. It is not a complete, unedited conversation export.

For assignment submission, include the original complete ChatGPT conversation export if the assignment requires a verbatim transcript.