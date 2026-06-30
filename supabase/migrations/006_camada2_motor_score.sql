-- ============================================================
-- Migration 006: Camada 2 (Motor de Score) — familias/consenso/
-- setup em `signals` + telemetria por gatilho (`trigger_outcomes`)
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS gatilhos_ids          TEXT[],
  ADD COLUMN IF NOT EXISTS familias_ativas        INTEGER,
  ADD COLUMN IF NOT EXISTS score_familias_capped  INTEGER,
  ADD COLUMN IF NOT EXISTS consenso_decisao       TEXT,
  ADD COLUMN IF NOT EXISTS setup                  TEXT,
  ADD COLUMN IF NOT EXISTS setup_params_shadow     JSONB;

CREATE TABLE IF NOT EXISTS trigger_outcomes (
    id                  BIGSERIAL PRIMARY KEY,
    signal_id           BIGINT NOT NULL,
    gatilho_id          TEXT NOT NULL,
    familia             TEXT,
    pontos              INTEGER,
    setup               TEXT,
    resultado_final     TEXT,
    retorno_pct         NUMERIC,
    dias_ate_resolucao  INTEGER,
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (signal_id, gatilho_id)
);

CREATE INDEX IF NOT EXISTS idx_trigger_outcomes_gatilho
  ON trigger_outcomes (gatilho_id, resultado_final);
