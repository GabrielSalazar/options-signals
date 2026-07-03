-- ============================================================
-- Migration 017: Telemetria matriz v2 / Camada PUCK em signals (shadow)
--   Campos que o payload já produzia mas nunca eram persistidos:
--   classe v2, gatilhos v2/PUCK (IDs + texto), sizing, divergência de
--   prêmio e indicadores de fluxo PUCK (cmf_z, cmf_norm).
--   Necessário para o SignalCard exibir a telemetria em sinais lidos do
--   banco (GET /signals) e para as consultas de monitoramento da Fase 4.
-- Run via: Supabase Dashboard -> SQL Editor
-- ============================================================
ALTER TABLE signals ADD COLUMN IF NOT EXISTS classe_v2 VARCHAR(1);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS razoes_downgrade_classe JSONB;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS gatilhos_v2_ids JSONB;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS gatilhos_v2 JSONB;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS sizing_sugerido_pct FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS divergencia_premio_pct FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS cmf_z FLOAT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS cmf_norm FLOAT;
