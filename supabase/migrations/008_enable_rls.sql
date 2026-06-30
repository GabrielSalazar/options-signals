-- ============================================================
-- Migration 008: Habilita Row Level Security em todas as tabelas
-- Run via: Supabase Dashboard → SQL Editor
--
-- Contexto: o backend FastAPI usa a service_role key (ignora RLS).
-- Confirmado via `grep -rn "NEXT_PUBLIC_SUPABASE" src/` que o frontend
-- Next.js usa a anon key para:
--   1) autenticação (auth.getUser) — não afetado por RLS de tabela;
--   2) leitura direta da tabela `signals` (src/hooks/useSignals.ts e
--      src/components/TickerSelector.tsx fazem SELECT client-side
--      com a anon key, incl. realtime subscription).
-- Não há uso confirmado da anon key para leitura/escrita das demais
-- tabelas (trigger_outcomes, iv_history, telegram_config) — apenas a
-- service_role policy é aplicada a elas, em defesa em profundidade.
-- ============================================================

ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trigger_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE iv_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_config ENABLE ROW LEVEL SECURITY;

-- service_role ignora RLS por padrão, mas a policy abaixo documenta a intenção
-- e cobre o caso de alguém futuramente usar a chave anon contra essas tabelas.
CREATE POLICY service_role_full_access ON signals
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_full_access ON trigger_outcomes
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_full_access ON iv_history
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY service_role_full_access ON telegram_config
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- A anon key é usada client-side (useSignals.ts, TickerSelector.tsx) para
-- leitura pública legítima da tabela `signals` (feed ao vivo + realtime +
-- autocomplete de ticker). Sem esta policy, ENABLE ROW LEVEL SECURITY
-- bloquearia essas leituras (nenhuma policy = nega tudo por padrão).
CREATE POLICY anon_read_signals ON signals
  FOR SELECT TO anon USING (true);
