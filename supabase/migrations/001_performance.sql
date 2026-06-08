-- ============================================================
-- Migration 001: Performance indexes + full signals schema
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

-- 1. Add ALL columns used by the app (idempotent)
ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS ticker        TEXT,
  ADD COLUMN IF NOT EXISTS nome          TEXT,
  ADD COLUMN IF NOT EXISTS tipo_sinal    TEXT,
  ADD COLUMN IF NOT EXISTS direcao       TEXT,
  ADD COLUMN IF NOT EXISTS score         NUMERIC,
  ADD COLUMN IF NOT EXISTS preco_acao    NUMERIC,
  ADD COLUMN IF NOT EXISTS ticker_opcao  TEXT,
  ADD COLUMN IF NOT EXISTS strike_ref    NUMERIC,
  ADD COLUMN IF NOT EXISTS dist_otm_pct  NUMERIC,
  ADD COLUMN IF NOT EXISTS iv_hist       NUMERIC,
  ADD COLUMN IF NOT EXISTS dte           INTEGER,
  ADD COLUMN IF NOT EXISTS mes_venc      INTEGER,
  ADD COLUMN IF NOT EXISTS ano_venc      INTEGER,
  ADD COLUMN IF NOT EXISTS premio_est    NUMERIC,
  ADD COLUMN IF NOT EXISTS preco_tela    NUMERIC,
  ADD COLUMN IF NOT EXISTS entrada_min   NUMERIC,
  ADD COLUMN IF NOT EXISTS entrada_max   NUMERIC,
  ADD COLUMN IF NOT EXISTS alvo1         NUMERIC,
  ADD COLUMN IF NOT EXISTS alvo2         NUMERIC,
  ADD COLUMN IF NOT EXISTS alvo_final    NUMERIC,
  ADD COLUMN IF NOT EXISTS stop          NUMERIC,
  ADD COLUMN IF NOT EXISTS rr_alvo1      NUMERIC,
  ADD COLUMN IF NOT EXISTS rr_alvo2      NUMERIC,
  ADD COLUMN IF NOT EXISTS rr_final      NUMERIC,
  ADD COLUMN IF NOT EXISTS stoch_k       NUMERIC,
  ADD COLUMN IF NOT EXISTS rsi           NUMERIC,
  ADD COLUMN IF NOT EXISTS vol_ratio     NUMERIC,
  ADD COLUMN IF NOT EXISTS gatilhos      JSONB,
  ADD COLUMN IF NOT EXISTS timestamp     TIMESTAMPTZ DEFAULT now();

-- 2. Performance indexes
CREATE INDEX IF NOT EXISTS idx_signals_timestamp_desc
  ON signals (timestamp DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_signals_ticker_ts
  ON signals (ticker, timestamp DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_signals_tipo_score
  ON signals (tipo_sinal, score DESC);

-- 3. Partial index for the common query (score >= 5)
CREATE INDEX IF NOT EXISTS idx_signals_recent_active
  ON signals (timestamp DESC)
  WHERE score >= 5;

-- 5. Enable Realtime for the signals table (idempotente)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_publication_tables
    WHERE pubname    = 'supabase_realtime'
      AND schemaname = 'public'
      AND tablename  = 'signals'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE signals;
  END IF;
END
$$;
