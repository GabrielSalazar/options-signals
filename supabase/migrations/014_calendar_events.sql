-- ============================================================
-- Migration 014: Tabela calendar_events para eventos de mercado
--                (Copom, earnings, vencimentos de opções) — Fase 3 Matriz v2
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

-- Calendário de eventos de mercado usado pelo veto shadow de liquidez.
-- Populado no boot do backend por event_service.registrar_copom_datas()
-- (idempotente via upsert on_conflict="data,label").
CREATE TABLE IF NOT EXISTS calendar_events (
  id BIGSERIAL PRIMARY KEY,
  data DATE NOT NULL,                    -- data do evento
  label VARCHAR(100) NOT NULL,           -- ex: "COPOM", "EARNINGS_PETR4", "VENCIMENTO_MARCO"
  descricao VARCHAR(255),                -- texto livre (ex: "Decisão de taxa Selic — Banco Central")
  criado_em TIMESTAMP DEFAULT NOW()      -- timestamp de criação
);

-- UNIQUE (data, label) garante idempotência do upsert do boot.
CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_events_data_label
  ON calendar_events(data, label);
