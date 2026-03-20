CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    total_amount INTEGER NOT NULL CHECK (total_amount > 0),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    amount INTEGER NOT NULL CHECK (amount > 0),
    type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    bank_payment_id VARCHAR(100) UNIQUE,
    bank_status_snapshot VARCHAR(50),
    bank_paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_payments_order_id ON payments(order_id);
