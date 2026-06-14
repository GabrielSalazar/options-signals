-- ============================================================
-- Migration 002: Separa score técnico do bônus de sessão (Camada 0.2)
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

-- 1. Novas colunas (idempotente)
ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS score_tecnico INTEGER,
  ADD COLUMN IF NOT EXISTS bonus_sessao  INTEGER;

-- 2. Backfill do bônus a partir da hora BRT do timestamp (aproximado por faixa).
--    Janelas: 10:00–11:30 → 2 · 13:00–15:00 → 3 · 15:00–16:30 → 1 · resto → 0.
UPDATE signals
SET bonus_sessao = CASE
    WHEN (EXTRACT(HOUR   FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')) * 60
        + EXTRACT(MINUTE FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')))
        BETWEEN 600 AND 690 THEN 2
    WHEN (EXTRACT(HOUR   FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')) * 60
        + EXTRACT(MINUTE FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')))
        BETWEEN 780 AND 900 THEN 3
    WHEN (EXTRACT(HOUR   FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')) * 60
        + EXTRACT(MINUTE FROM (timestamp AT TIME ZONE 'America/Sao_Paulo')))
        BETWEEN 900 AND 990 THEN 1
    ELSE 0
END
WHERE bonus_sessao IS NULL;

-- 3. score_tecnico histórico = score − bônus inferido (nunca negativo).
UPDATE signals
SET score_tecnico = GREATEST(COALESCE(score, 0) - COALESCE(bonus_sessao, 0), 0)
WHERE score_tecnico IS NULL;

-- 4. Índice para priorização por score técnico
CREATE INDEX IF NOT EXISTS idx_signals_score_tecnico
  ON signals (tipo_sinal, score_tecnico DESC);
