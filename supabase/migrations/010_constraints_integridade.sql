-- ============================================================
-- Migration 010: Constraints de integridade
-- Run via: Supabase Dashboard → SQL Editor
--
-- Contexto: adiciona uma FK ausente (trigger_outcomes.signal_id →
-- signals.id, com ON DELETE CASCADE) e CHECK constraints nos campos
-- categóricos de signals/trigger_outcomes, para evitar que typos
-- silenciosos (ex: 'Call' em vez de 'CALL') entrem no banco sem
-- erro visível.
--
-- ── Pré-requisito manual (rodar ANTES de aplicar esta migração) ────────────
-- SELECT DISTINCT tipo_sinal FROM signals WHERE tipo_sinal NOT IN ('CALL', 'PUT');
-- SELECT DISTINCT consenso_decisao FROM signals WHERE consenso_decisao IS NOT NULL AND consenso_decisao NOT IN ('passaria', 'bloquearia');
-- SELECT DISTINCT setup FROM signals WHERE setup IS NOT NULL AND setup NOT IN ('REVERSAO', 'CONTINUACAO', 'HIBRIDO');
-- SELECT DISTINCT resultado_final FROM trigger_outcomes WHERE resultado_final NOT IN ('alvo1', 'alvo2', 'alvo_final', 'stop', 'expirou', 'aberto', 'indeterminado');
-- SELECT tro.signal_id FROM trigger_outcomes tro LEFT JOIN signals s ON s.id = tro.signal_id WHERE s.id IS NULL;
-- Se qualquer uma retornar linhas, NÃO aplicar esta migração sem antes
-- corrigir/limpar os dados divergentes.
-- ============================================================

-- FK: trigger_outcomes não deve sobreviver à exclusão do signal pai.
ALTER TABLE trigger_outcomes
  ADD CONSTRAINT fk_trigger_outcomes_signal
  FOREIGN KEY (signal_id) REFERENCES signals(id) ON DELETE CASCADE;

-- CHECK constraints em campos categóricos (evita typos silenciosos).
ALTER TABLE signals
  ADD CONSTRAINT chk_tipo_sinal CHECK (tipo_sinal IN ('CALL', 'PUT')),
  ADD CONSTRAINT chk_consenso_decisao CHECK (consenso_decisao IS NULL OR consenso_decisao IN ('passaria', 'bloquearia')),
  ADD CONSTRAINT chk_setup CHECK (setup IS NULL OR setup IN ('REVERSAO', 'CONTINUACAO', 'HIBRIDO'));

ALTER TABLE trigger_outcomes
  ADD CONSTRAINT chk_resultado_final CHECK (
    resultado_final IN ('alvo1', 'alvo2', 'alvo_final', 'stop', 'expirou', 'aberto', 'indeterminado')
  );
