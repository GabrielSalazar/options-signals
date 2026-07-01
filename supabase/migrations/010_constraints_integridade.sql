-- ============================================================
-- Migration 010: Constraints de integridade
-- Run via: Supabase Dashboard → SQL Editor
--
-- Contexto: adiciona CHECK constraints nos campos categóricos de
-- signals/trigger_outcomes, para evitar que typos silenciosos
-- (ex: 'Call' em vez de 'CALL') entrem no banco sem erro visível.
--
-- ⚠️ FK REMOVIDA (adiada) — bug de modelo de dados pré-existente:
--   A FK trigger_outcomes.signal_id → signals.id NÃO pode ser criada
--   porque os tipos são incompatíveis: `signals.id` é UUID (criado fora
--   de migração, no dashboard) mas `trigger_outcomes.signal_id` é BIGINT
--   (migration 006). O Supabase Preview provou isso:
--     "foreign key constraint cannot be implemented ... incompatible
--      types: bigint and uuid" (SQLSTATE 42804).
--   Pior: backend/services/outcome_service.py grava `sinal["id"]` (UUID)
--   nessa coluna BIGINT, então todo insert em trigger_outcomes sempre
--   falhou silenciosamente (try/except que só loga warning). A telemetria
--   da Camada 2.4 provavelmente nunca persistiu.
--   Correção correta = migração que converte signal_id para UUID + backfill,
--   uma decisão de modelo com impacto em produção — feita à parte, não aqui.
--
-- ── Pré-requisito manual (rodar ANTES de aplicar esta migração) ────────────
-- SELECT DISTINCT tipo_sinal FROM signals WHERE tipo_sinal NOT IN ('CALL', 'PUT');
-- SELECT DISTINCT consenso_decisao FROM signals WHERE consenso_decisao IS NOT NULL AND consenso_decisao NOT IN ('passaria', 'bloquearia');
-- SELECT DISTINCT setup FROM signals WHERE setup IS NOT NULL AND setup NOT IN ('REVERSAO', 'CONTINUACAO', 'HIBRIDO');
-- SELECT DISTINCT resultado_final FROM trigger_outcomes WHERE resultado_final NOT IN ('alvo1', 'alvo2', 'alvo_final', 'stop', 'expirou', 'aberto', 'indeterminado');
-- Se qualquer uma retornar linhas, NÃO aplicar esta migração sem antes
-- corrigir/limpar os dados divergentes.
-- ============================================================

-- CHECK constraints em campos categóricos (evita typos silenciosos).
ALTER TABLE signals
  ADD CONSTRAINT chk_tipo_sinal CHECK (tipo_sinal IN ('CALL', 'PUT')),
  ADD CONSTRAINT chk_consenso_decisao CHECK (consenso_decisao IS NULL OR consenso_decisao IN ('passaria', 'bloquearia')),
  ADD CONSTRAINT chk_setup CHECK (setup IS NULL OR setup IN ('REVERSAO', 'CONTINUACAO', 'HIBRIDO'));

ALTER TABLE trigger_outcomes
  ADD CONSTRAINT chk_resultado_final CHECK (
    resultado_final IN ('alvo1', 'alvo2', 'alvo_final', 'stop', 'expirou', 'aberto', 'indeterminado')
  );
