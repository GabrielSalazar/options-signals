-- ============================================================
-- Migration 004: Camada 1 (IV) — rename + novas colunas em `signals`
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

ALTER TABLE signals RENAME COLUMN iv_hist TO hv_20d;

ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS iv_impl          NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_source        TEXT,
  ADD COLUMN IF NOT EXISTS iv_rank          NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_premium       NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_filter_decisao TEXT;
