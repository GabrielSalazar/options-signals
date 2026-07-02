-- ============================================================
-- Fase 4 — Monitoramento em Shadow dos vetos de executabilidade
-- (OI, spread, VXBR, evento) e da classe v2, sem ativar bloqueios.
--
-- Rodar diariamente (Supabase SQL Editor) durante a janela de
-- validação (~2026-07-05 a 2026-07-19). Objetivo: reunir 50-60
-- sinais com desfecho conhecido por veto antes de ativar por etapas.
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
--    (join por signal_id; requer outcome já resolvido, i.e. trade encerrado)
SELECT
  s.filtro_liquidez_decisao,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE o.resultado_final = 'win') AS wins,
  COUNT(*) FILTER (WHERE o.resultado_final = 'loss') AS losses,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE o.resultado_final = 'win') / NULLIF(COUNT(*), 0),
    1
  ) AS win_rate_pct
FROM signals s
JOIN trigger_outcomes o ON o.signal_id = s.id
WHERE s.created_at >= NOW() - INTERVAL '14 days'
  AND o.resultado_final IS NOT NULL
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
