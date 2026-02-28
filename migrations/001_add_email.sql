-- Migration 001: add email subscription support
-- Run once on existing databases: sqlite3 subscriptions.db < migrations/001_add_email.sql
-- Requires SQLite 3.25+ (available on AL2023)

ALTER TABLE subscriptions RENAME COLUMN webhook_url TO destination;
ALTER TABLE subscriptions ADD COLUMN subscription_type TEXT NOT NULL DEFAULT 'discord';
