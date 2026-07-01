-- ============================================================
-- Migration 012: Corrige o tipo de trigger_outcomes.signal_id (BIGINT → UUID)
--                e (re)cria a FK para signals(id)
-- Run via: Supabase Dashboard → SQL Editor (auto-aplicada pela integração)
--
-- Contexto (bug de modelo pré-existente): a migration 006 criou
--   trigger_outcomes.signal_id como BIGINT, assumindo que signals.id fosse
--   bigint — mas signals.id é UUID (ver 011). O backend
--   (outcome_service.py::_persistir_trigger_outcomes) sempre gravou
--   sinal["id"] (um UUID) nessa coluna BIGINT, então TODO insert falhava e
--   era engolido por um try/except que só loga warning. A telemetria por
--   gatilho da Camada 2.4 nunca persistiu.
--
-- Verificado em produção (30/jun/2026): SELECT count(*) FROM trigger_outcomes
--   = 0 linhas. A tabela está vazia, então a conversão de tipo é segura (não
--   há valores bigint legados para converter/descartar).
--
-- Efeito: depois desta migração, signal_id passa a ser UUID e casa com
--   signals.id — os inserts do outcome_service (UUID → UUID) passam a
--   funcionar sozinhos, SEM mudança de código. A FK removida da 010 (que era
--   impossível com tipos incompatíveis) é recriada aqui.
--
-- Idempotente (mesmo padrão da 004): só converte se ainda for bigint e só
--   cria a FK se ela ainda não existir.
-- ============================================================

-- 1) Converte signal_id de BIGINT para UUID (tabela vazia → USING não toca linhas).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'trigger_outcomes'
      AND column_name = 'signal_id'
      AND data_type = 'bigint'
  ) THEN
    ALTER TABLE trigger_outcomes
      ALTER COLUMN signal_id TYPE uuid USING signal_id::text::uuid;
  END IF;
END $$;

-- 2) Recria a FK (agora possível: uuid → uuid), com ON DELETE CASCADE.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_trigger_outcomes_signal'
  ) THEN
    ALTER TABLE trigger_outcomes
      ADD CONSTRAINT fk_trigger_outcomes_signal
      FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE CASCADE;
  END IF;
END $$;
