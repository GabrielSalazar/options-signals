-- Migration 003: persistência da config do Telegram (Camada 0.4)
CREATE TABLE IF NOT EXISTS telegram_config (
  id        INTEGER PRIMARY KEY DEFAULT 1,
  token     TEXT,
  chat_id   TEXT,
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT single_row CHECK (id = 1)
);
