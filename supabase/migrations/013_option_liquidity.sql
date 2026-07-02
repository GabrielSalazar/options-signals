-- ============================================================
-- Migration 013: Tabela option_liquidity para dados externos
--                (OI, bid/ask, VXBR, eventos) — Fase 3 Matriz v2
-- Run via: Supabase Dashboard → SQL Editor
-- ============================================================

-- Tabela de liquidez diária (criada por job de coleta pós-fechamento)
-- Armazena dados de executabilidade e estado de liquidez para tomar decisões
-- de veto em shadow (Fase 3, §4) antes de ativar em Fase 4.
CREATE TABLE IF NOT EXISTS option_liquidity (
  id BIGSERIAL PRIMARY KEY,
  ticker VARCHAR(20) NOT NULL,           -- ticker base (ex: PETR4) — permite queries rápidas
  data DATE NOT NULL,                    -- data de coleta (pós-fechamento do dia)
  oi BIGINT,                             -- Open Interest total da série (somado sobre strikes); pode ser NULL se PR falhar
  bid FLOAT,                             -- bid de fechamento da série ATM; NULL se COTAHIST falhar
  ask FLOAT,                             -- ask de fechamento da série ATM; NULL se COTAHIST falhar
  spread_pct FLOAT,                      -- (ask - bid) / ((ask + bid) / 2) * 100; NULL se bid/ask indisponíveis
  vxbr FLOAT,                            -- índice de volatilidade da B3 (nível do dia); NULL se brapi indisponível
  evento_label VARCHAR(100),             -- label de evento (ex: "COPOM", "EARNINGS_PETR4"); NULL se sem evento
  created_at TIMESTAMP DEFAULT NOW()     -- timestamp de criação (log de quando foi coletado)
);

-- Índice para buscas frequentes (ticker, data)
-- Usado em core_engine.py::obter_option_liquidity() para consultas rápidas
-- na emissão de sinais (ticket não pode esperar N segundos por query len.)
-- UNIQUE garante que há no máximo uma entrada por ticker/data (idempotência de upsert).
CREATE UNIQUE INDEX IF NOT EXISTS idx_option_liquidity_ticker_data
  ON option_liquidity(ticker, data);

-- Índice para limpeza de dados antigos (mantém tabela enxuta)
-- Job futuro de limpeza: DELETE FROM option_liquidity WHERE data < NOW() - INTERVAL '1 year'
CREATE INDEX IF NOT EXISTS idx_option_liquidity_data
  ON option_liquidity(data);

-- RLS desativado: dados de liquidez são públicos e baseados em feeds públicos B3.
-- Sem FK para signals: é um dado de estado (snapshot do dia), não relacionado 1:1 a um sinal.
-- Sinais de diferentes dias/tickers podem consultar a mesma linha.
