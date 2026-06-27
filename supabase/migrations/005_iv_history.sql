-- ============================================================
-- Migration 005: Camada 1.2 — histórico diário de IV / IV Rank
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS iv_history (
    id          BIGSERIAL PRIMARY KEY,
    ticker      TEXT NOT NULL,
    data        DATE NOT NULL,
    iv_atm      NUMERIC,
    hv_20d      NUMERIC,
    iv_premium  NUMERIC,
    fonte       TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (ticker, data)
);

CREATE INDEX IF NOT EXISTS idx_iv_history_ticker_data
  ON iv_history (ticker, data DESC);
