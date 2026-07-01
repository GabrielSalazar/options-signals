-- ============================================================
-- Migration 011: Schema completo de `signals` (reconstrução retroativa)
-- Run via: Supabase Dashboard → SQL Editor (auto-aplicada pela integração)
--
-- Por que existe: a tabela `signals` NUNCA teve um CREATE TABLE versionado —
-- foi criada no dashboard do Supabase e só recebeu ALTER TABLE incrementais
-- (001, 002, 004, 006). Esta migração documenta o schema REAL como fonte de
-- verdade, coletado de information_schema.columns em produção (30/jun/2026).
--
-- Por que numerada 011 (e não 007): as migrações 008 e 010 JÁ foram aplicadas
--   em produção. Inserir uma migração com número menor que as já aplicadas
--   quebraria o histórico linear do Supabase (erro de "out-of-order" no
--   db push). Por isso ela vai como a próxima migração livre.
--
-- IF NOT EXISTS: em qualquer banco que já tem a tabela (produção, previews
-- clonados de produção) esta migração é NO-OP e não altera nada. Ela serve de
-- documentação/reconstrução de referência.
--
-- ⚠️ Não habilita reconstrução do zero: os ALTER TABLE de 001–006 rodam antes
--   desta CREATE e falhariam num banco vazio. Corrigir isso exigiria reordenar
--   o histórico já aplicado — fora de escopo.
--
-- ⚠️ Drift de schema documentado: `signals` tem DOIS conjuntos de colunas com
--   propósito sobreposto — um "inglês" original do dashboard (signal_type,
--   spot_price, option_symbol, strategy, entry_price, risk_level…) e um
--   "português" adicionado pelas Camadas via ALTER (tipo_sinal, preco_acao,
--   ticker_opcao, direcao, premio_est…). O backend usa o conjunto português.
--   Consolidar os dois é uma decisão de modelo à parte (não feita aqui).
--
-- Nota de tipos: `gatilhos_ids` aparece como ARRAY em information_schema
--   (o element type não é exposto ali); o backend grava lista de strings, então
--   está reconstruído como text[]. `character varying` sem length capturado foi
--   reconstruído como varchar (sem limite).
-- ============================================================

CREATE TABLE IF NOT EXISTS signals (
    id                      uuid        NOT NULL DEFAULT gen_random_uuid(),
    user_id                 uuid,
    -- ── Conjunto original (dashboard, "inglês") ──────────────────────────────
    ticker                  varchar     NOT NULL,
    option_symbol           varchar     NOT NULL,
    strategy                varchar     NOT NULL,
    signal_type             varchar     NOT NULL,
    spot_price              numeric     NOT NULL,
    strike                  numeric,
    price                   numeric,
    entry_price             numeric,
    confidence_score        numeric,
    risk_level              varchar     NOT NULL DEFAULT 'MEDIUM',
    reason                  text,
    recommendation          text,
    created_at              timestamptz DEFAULT now(),
    updated_at              timestamptz DEFAULT now(),
    "timestamp"             timestamptz,
    -- ── Conjunto das Camadas (ALTER TABLE 002/004/006, "português") ───────────
    nome                    text,
    tipo_sinal              text,
    direcao                 text,
    score                   numeric,
    preco_acao              numeric,
    ticker_opcao            text,
    strike_ref              numeric,
    dist_otm_pct            numeric,
    hv_20d                  numeric,
    dte                     integer,
    mes_venc                integer,
    ano_venc                integer,
    premio_est              numeric,
    preco_tela              numeric,
    entrada_min             numeric,
    entrada_max             numeric,
    alvo1                   numeric,
    alvo2                   numeric,
    alvo_final              numeric,
    stop                    numeric,
    rr_alvo1                numeric,
    rr_alvo2                numeric,
    rr_final                numeric,
    stoch_k                 numeric,
    rsi                     numeric,
    vol_ratio               numeric,
    gatilhos                jsonb,
    greeks                  jsonb,
    book_until              text,
    score_ponderado         integer,
    ponderado_passou        boolean,
    iv_mercado              numeric,
    score_tecnico           integer,
    bonus_sessao            integer,
    -- Camada 1 (IV)
    iv_impl                 numeric,
    iv_source               text,
    iv_rank                 numeric,
    iv_premium              numeric,
    iv_filter_decisao       text,
    -- Camada 2 (motor de score / consenso / setup)
    gatilhos_ids            text[],
    familias_ativas         integer,
    score_familias_capped   integer,
    consenso_decisao        text,
    setup                   text,
    setup_params_shadow     jsonb,
    CONSTRAINT signals_pkey PRIMARY KEY (id)
);
