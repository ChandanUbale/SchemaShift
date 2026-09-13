-- Seed data for MySQL source demo
-- Includes ~5 rows for testing. Expand to 10k via a Python script later if needed.
-- Contains dirty data (e.g. invalid dates or orphan FKs) to test profiling.

INSERT INTO customers (id, name, email, created_at) VALUES
(1, 'Alice Smith', 'alice@example.com', '2023-01-01 10:00:00'),
(2, 'Bob Jones', 'bob@example.com', '2023-01-02 11:00:00'),
(3, 'Charlie Brown', 'charlie@example.com', '2023-01-03 12:00:00'),
(4, 'Duplicate Dan', 'alice@example.com', '2023-01-04 13:00:00'); -- duplicate email

-- Note: invalid date simulation will require a VARCHAR date field, but using standard DATE here for simplicity
INSERT INTO orders (id, customer_id, order_date, total) VALUES
(1, 1, '2023-02-01', 100.50),
(2, 2, '2023-02-02', 200.00),
(3, 999, '2023-02-03', 50.00); -- orphan FK (if FK checks are temporarily disabled during seed)

INSERT INTO order_items (id, order_id, product_name, quantity, price) VALUES
(1, 1, 'Widget A', 2, 25.00),
(2, 1, 'Widget B', 1, 50.50),
(3, 2, 'Widget C', 4, 50.00);
