-- ============================================================
-- Migration 016: Colunas da camada PUCK em signals (shadow)
--   Níveis ATR no ativo subjacente (gestão pelo ativo, não pela opção)
--   + telemetria de absorção/persistência de fluxo
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ativo_entrada FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ativo_stop FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ativo_tp1 FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS ativo_tp2 FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS absorcao BOOLEAN;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS fluxo_persistencia_dias INTEGER;
