-- ============================================================
-- Migration 004: Camada 1 (IV) — rename + novas colunas em `signals`
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'signals' AND column_name = 'iv_hist'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'signals' AND column_name = 'hv_20d'
  ) THEN
    ALTER TABLE signals RENAME COLUMN iv_hist TO hv_20d;
  END IF;
END $$;

ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS iv_impl          NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_source        TEXT,
  ADD COLUMN IF NOT EXISTS iv_rank          NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_premium       NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_filter_decisao TEXT;
