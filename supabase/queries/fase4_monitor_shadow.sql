-- ============================================================
-- Fase 4 — Monitoramento em Shadow: vetos de executabilidade
-- (OI, spread, VXBR, evento), classe v2 e Camada PUCK, sem ativar
-- nenhum bloqueio.
--
-- Rodar diariamente (Supabase SQL Editor) durante a janela de
-- validação. Objetivo: reunir sinais com desfecho conhecido antes
-- de ativar qualquer flag por etapas.
--
-- Convenção de desfecho (trigger_outcomes.resultado_final):
--   ganho  = 'alvo1' | 'alvo2' | 'alvo_final'
--   perda  = 'stop'
--   neutro = 'expirou'
-- (NÃO existem 'win'/'loss' — são os literais acima, de outcome.py.)
-- ============================================================

-- 1) Visão geral diária: volume de sinais, classes v2 e vetos shadow
SELECT
  DATE(created_at) AS data,
  COUNT(*) AS total_sinais,
  COUNT(*) FILTER (WHERE classe_v2 = 'A') AS classe_a,
  COUNT(*) FILTER (WHERE classe_v2 = 'B') AS classe_b,
  COUNT(*) FILTER (WHERE classe_v2 = 'C') AS classe_c,
  COUNT(*) FILTER (WHERE filtro_liquidez_decisao = 'bloquear') AS vetados_spread,
  COUNT(*) FILTER (WHERE filtro_liquidez_decisao = 'atencao') AS em_atencao,
  COUNT(*) FILTER (WHERE filtro_liquidez_decisao = 'normal') AS normal,
  COUNT(*) FILTER (WHERE filtro_liquidez_decisao IS NULL) AS sem_dado_liquidez
FROM signals
WHERE created_at >= NOW() - INTERVAL '14 days'
GROUP BY 1
ORDER BY 1 DESC;

-- 2) Hit-rate dos vetados (spread>15%) vs. aprovados — usa trigger_outcomes
--    (join por signal_id; requer outcome já resolvido, i.e. trade encerrado).
--    Uma linha de trigger_outcomes por gatilho, mas o desfecho é do SINAL
--    (mesmo resultado_final em todas as linhas do signal_id), então tomamos
--    um desfecho por sinal com DISTINCT ON para não contar em duplicidade.
WITH desfecho_por_sinal AS (
  SELECT DISTINCT ON (signal_id) signal_id, resultado_final
  FROM trigger_outcomes
  WHERE resultado_final IS NOT NULL
)
SELECT
  s.filtro_liquidez_decisao,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE d.resultado_final IN ('alvo1','alvo2','alvo_final')) AS ganhos,
  COUNT(*) FILTER (WHERE d.resultado_final = 'stop') AS perdas,
  COUNT(*) FILTER (WHERE d.resultado_final = 'expirou') AS expirou,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE d.resultado_final IN ('alvo1','alvo2','alvo_final'))
    / NULLIF(COUNT(*), 0), 1
  ) AS win_rate_pct
FROM signals s
JOIN desfecho_por_sinal d ON d.signal_id = s.id
WHERE s.created_at >= NOW() - INTERVAL '14 days'
GROUP BY 1
ORDER BY 1;

-- 3) Motivo de veto mais frequente (para priorizar qual ativar primeiro)
SELECT
  filtro_liquidez_motivo,
  COUNT(*) AS ocorrencias
FROM signals
WHERE created_at >= NOW() - INTERVAL '14 days'
  AND filtro_liquidez_decisao IN ('atencao', 'bloquear')
GROUP BY 1
ORDER BY 2 DESC;

-- 4) Impacto por classe v2 (checar se os vetos afetam A/B/C de forma equilibrada
--    ou concentram-se numa classe específica, o que sinalizaria viés)
SELECT
  classe_v2,
  filtro_liquidez_decisao,
  COUNT(*) AS total
FROM signals
WHERE created_at >= NOW() - INTERVAL '14 days'
GROUP BY 1, 2
ORDER BY 1, 2;

-- 5) Cobertura de dados externos (fração de sinais com oi/vxbr/evento preenchidos
--    vs. null — mede se a coleta diária está funcionando de forma consistente)
SELECT
  DATE(created_at) AS data,
  COUNT(*) AS total_sinais,
  COUNT(oi) AS com_oi,
  COUNT(spread_pct) AS com_spread,
  COUNT(vxbr) AS com_vxbr,
  COUNT(evento_label) AS com_evento
FROM signals
WHERE created_at >= NOW() - INTERVAL '14 days'
GROUP BY 1
ORDER BY 1 DESC;

-- ============================================================
-- Camada PUCK (shadow) — telemetria dos campos e gatilhos G20-G22/B20-B22
-- ============================================================

-- 6) Cobertura diária dos campos PUCK (migração 016): quantos sinais têm
--    níveis ATR no ativo, absorção detectada e fluxo persistente. Se
--    "com_niveis_ativo" ficar muito abaixo de total_sinais, revisar o cálculo
--    de ATR; absorção/persistência = 0 constante pode indicar zona HC ausente.
SELECT
  DATE(created_at) AS data,
  COUNT(*) AS total_sinais,
  COUNT(ativo_stop) AS com_niveis_ativo,
  COUNT(*) FILTER (WHERE absorcao IS TRUE) AS com_absorcao,
  COUNT(*) FILTER (WHERE fluxo_persistencia_dias >= 3) AS fluxo_persist_3d_mais,
  ROUND(AVG(fluxo_persistencia_dias), 1) AS media_persist_dias
FROM signals
WHERE created_at >= NOW() - INTERVAL '14 days'
GROUP BY 1
ORDER BY 1 DESC;

-- 7) Hit-rate dos gatilhos PUCK (G20-G22 alta / B20-B22 baixa).
--    IMPORTANTE: em shadow os IDs PUCK ficam em signals.gatilhos_v2_ids (array),
--    NÃO em trigger_outcomes (que só recebe os gatilhos principais). Então
--    cruzamos o array com o desfecho do próprio sinal (um por signal_id).
--    Pré-requisito: o sinal também disparou >=1 gatilho clássico (todo sinal
--    emitido dispara, pois exige score mínimo), garantindo linha em outcomes.
--    OBS: gatilhos_v2_ids é assumido JSONB. Se a coluna for text[] nativo,
--    troque a linha do CROSS JOIN por:  unnest(s.gatilhos_v2_ids) AS gid
WITH desfecho_por_sinal AS (
  SELECT DISTINCT ON (signal_id) signal_id, resultado_final
  FROM trigger_outcomes
  WHERE resultado_final IS NOT NULL
)
SELECT
  gid AS gatilho_puck,
  COUNT(*) AS resolvidos,
  COUNT(*) FILTER (WHERE d.resultado_final IN ('alvo1','alvo2','alvo_final')) AS ganhos,
  COUNT(*) FILTER (WHERE d.resultado_final = 'stop') AS perdas,
  COUNT(*) FILTER (WHERE d.resultado_final = 'expirou') AS expirou,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE d.resultado_final IN ('alvo1','alvo2','alvo_final'))
    / NULLIF(COUNT(*), 0), 1
  ) AS win_rate_pct
FROM signals s
CROSS JOIN LATERAL jsonb_array_elements_text(s.gatilhos_v2_ids::jsonb) AS gid
JOIN desfecho_por_sinal d ON d.signal_id = s.id
WHERE s.created_at >= NOW() - INTERVAL '14 days'
  AND gid IN ('G20','G21','G22','B20','B21','B22')
GROUP BY gid
ORDER BY gid;

-- 8) Frequência dos gatilhos PUCK por dia (mesmo sem desfecho ainda), para
--    saber se estão disparando o suficiente para gerar amostra estatística.
SELECT
  DATE(s.created_at) AS data,
  gid AS gatilho_puck,
  COUNT(*) AS disparos
FROM signals s
CROSS JOIN LATERAL jsonb_array_elements_text(s.gatilhos_v2_ids::jsonb) AS gid
WHERE s.created_at >= NOW() - INTERVAL '14 days'
  AND gid IN ('G20','G21','G22','B20','B21','B22')
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- 9) Absorção e persistência de fluxo por classe v2 (os modificadores de classe
--    PUCK só registram razão em shadow; aqui medimos com que frequência
--    disparariam um downgrade/upgrade se ativados, e em qual classe se concentram).
SELECT
  classe_v2,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE absorcao IS TRUE) AS com_absorcao,
  COUNT(*) FILTER (WHERE fluxo_persistencia_dias >= 3) AS fluxo_persist_3d_mais
FROM signals
WHERE created_at >= NOW() - INTERVAL '14 days'
GROUP BY 1
ORDER BY 1;
