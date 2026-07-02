-- ============================================================
-- Migration 015: Colunas de liquidez/VXBR/evento em signals
--                (telemetria shadow — Fase 3 Matriz v2)
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

-- Campos preenchidos por core_engine.analisar_ativo() a partir de
-- option_liquidity/calendar_events; todos nullable (fail-safe: NULL
-- quando os dados externos estão indisponíveis). Shadow até Fase 4.
ALTER TABLE signals ADD COLUMN IF NOT EXISTS oi BIGINT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS bid FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ask FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS spread_pct FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS vxbr FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS evento_label VARCHAR(100);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS filtro_liquidez_decisao VARCHAR(50);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS filtro_liquidez_motivo VARCHAR(255);
