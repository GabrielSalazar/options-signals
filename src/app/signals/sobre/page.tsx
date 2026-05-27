"use client"

import Link from "next/link"
import {
    ArrowLeft, TrendingUp, TrendingDown, Shield, Target,
    BarChart2, Zap, Clock, GitMerge, BookOpen, Activity
} from "lucide-react"

// ── Dados ────────────────────────────────────────────────────────────────────

const PIPELINE = [
    {
        n: "01",
        label: "Validação de Reentrada",
        desc: "Antes de qualquer cálculo, o motor consulta o histórico interno: existe sinal para este ativo nos últimos 3 dias úteis? Se sim, descarta. O ciclo médio de uma operação de opção OTM dura 1–5 dias úteis — emitir sinais consecutivos no mesmo papel multiplicaria o risco sem multiplicar a expectativa estatística. É a primeira camada anti-overtrading do sistema.",
    },
    {
        n: "02",
        label: "Download OHLCV (6 meses)",
        desc: "Baixa preço de abertura, máxima, mínima, fechamento e volume (OHLCV) dos últimos 6 meses (~126 candles diários). É a janela mínima para alimentar a EMA200 e validar comportamento estatístico do RSI e da volatilidade. yfinance é gratuito mas instável — o motor aplica 3 tentativas com backoff de 2s, resolvendo ~99% das falhas transitórias da API.",
    },
    {
        n: "03",
        label: "Filtro de Volume Mínimo",
        desc: "Volume médio diário do ativo subjacente abaixo de 1.000.000 → descartado imediatamente. A razão é mecânica: opções de papéis ilíquidos possuem spread bid-ask de 30–50% no book, o que destrói qualquer R/R teórico. Sem volume no underlying, a opção também não tem gamma operável — você compra, mas não consegue sair pelo preço justo.",
    },
    {
        n: "04",
        label: "Cálculo de 19 Indicadores Técnicos",
        desc: "Em uma única passagem vetorial, o motor calcula: Estocástico (%K e %D para momentum de curto prazo), RSI (força relativa em 14 períodos), MACD (convergência/divergência de EMAs), ATR (range médio para tolerância de níveis), EMAs 9/21/200 (tendência em múltiplos timeframes), Bandas de Bollinger (compressão de volatilidade), suporte/resistência rolante de 20 dias e detecção de máximos/mínimos locais.",
    },
    {
        n: "05",
        label: "Motor de Score (19 Gatilhos)",
        desc: "O coração do algoritmo. Em vez de uma regra binária (\"se A cruza B então compre\"), o motor avalia o ativo sob duas óticas simultâneas — compra de CALL e compra de PUT — somando evidências independentes (+1 a +3 pts cada). 11 gatilhos altistas e 8 baixistas são checados em paralelo. A direção vencedora emite o sinal apenas se o score atingir o limiar mínimo de 5.",
    },
    {
        n: "06",
        label: "Seleção de Strike OTM",
        desc: "Strike é o preço de exercício da opção. \"Fora do dinheiro\" (OTM) significa que o strike está acima do preço atual (CALL) ou abaixo (PUT). Quanto mais OTM, mais barata a opção e maior o gamma — mas menor a probabilidade. O motor calibra essa distância por ativo: 12% para MGLU3 (alta volatilidade), 5% para ITUB4 (defensivo). Depois valida contra a grade real da B3 via scraping no opcoes.net.br.",
    },
    {
        n: "07",
        label: "Cálculo de DTE & IV Histórica",
        desc: "DTE (Days To Expiration) = dias úteis até o vencimento, sempre a 3ª sexta-feira do mês (padrão B3). A janela aceita é 10–45 du: abaixo de 10 o theta-decay devora o prêmio antes do movimento; acima de 45 o gamma fica fraco demais, exigindo movimento desproporcional. IV histórica = volatilidade anualizada calculada com log-returns dos últimos 20 dias.",
    },
    {
        n: "08",
        label: "Black-Scholes (Prêmio Estimado)",
        desc: "Modelo matemático clássico que precifica opções a partir de 5 inputs: preço da ação, strike, tempo até vencimento, volatilidade e taxa livre de risco (Selic 10,75%). Para opções americanas da B3 é uma aproximação muito sólida em strikes OTM. Quando o scraping de opcoes.net.br retorna prêmio real de tela, o sistema substitui a estimativa — usando o preço efetivo do book.",
    },
    {
        n: "09",
        label: "Estrutura de Entrada e Saída",
        desc: "Sobre o prêmio estimado, o motor monta automaticamente: zona de entrada (±10% para absorver spread do book), Alvo 1 em +25% (realização parcial de 50% da posição), Alvo 2 em +150% (alvo técnico principal onde a maioria dos wins fecha), Alvo Final em +400% (especulação remanescente). Stop em −42%, calibrado pela perda média histórica de −39,5% observada em 4 stops da base.",
    },
    {
        n: "10",
        label: "Filtro Obrigatório R/R ≥ 0.8×",
        desc: "Risk/Reward = (Alvo 1 − prêmio) ÷ (prêmio − stop). Sinais com R/R do Alvo 1 abaixo de 0,8× são descartados, mesmo com score 10. A matemática: com 82% de acerto histórico e R/R 0,8, a expectância líquida é (0,82 × 0,8) − (0,18 × 1,0) = +0,476 por operação. Sem esse filtro, sinais com score alto mas assimetria ruim derrubariam a performance.",
    },
    {
        n: "11",
        label: "Registro & Notificação",
        desc: "Sinal aprovado é persistido no Supabase com 29 campos (gatilhos ativados, score, R/R, IV, DTE, etc.), enviado via Telegram com formatação Markdown (token + chat_id em env vars), e seu timestamp é registrado no histórico interno — bloqueando o mesmo ticker pelos próximos 3 dias úteis (de volta à Etapa 1).",
    },
]

const GATILHOS_ALTA = [
    {
        id: "G1", pts: 3, cat: "Oscilador",
        label: "Cruzamento Estocástico em Sobrevenda",
        interp: "O Estocástico mede onde o fechamento atual está dentro do range das últimas 14 barras (0 = mínima absoluta, 100 = máxima absoluta). %K é o valor rápido; %D é a média móvel de 3 períodos do %K. Quando %K cruza acima de %D dentro da zona < 35, significa duas coisas simultâneas: (1) o preço estava no fundo do range recente e (2) a velocidade da queda acabou de se reverter. É o gatilho mais antecipatório do sistema — capta o ponto exato em que vendedores começam a soltar a pressão.",
    },
    {
        id: "G2", pts: 2, cat: "Oscilador",
        label: "RSI(14) < 35 — Sobrevenda Extrema",
        interp: "O Relative Strength Index compara a magnitude dos ganhos contra as perdas nos últimos 14 períodos, normalizado em escala 0–100. Abaixo de 35: a pressão vendedora acumulada está estatisticamente esgotada. Sozinho não dispara sinal — funciona como confirmação adicional ao G1, indicando que a exaustão não é só de momentum (Stoch) mas também de magnitude (RSI). O threshold 35 (em vez do clássico 30) capta reversões um pouco mais cedo, comportamento observado no mercado brasileiro.",
    },
    {
        id: "G6", pts: 2, cat: "Oscilador",
        label: "MACD Histogram cruza zero para cima",
        interp: "MACD = EMA(12) − EMA(26). O Histogram (Diff) = MACD − Signal(9). Quando o Diff cruza zero subindo, significa que a média rápida ultrapassou a sinal — o impulso de curto prazo se tornou maior que o de médio prazo. É uma confirmação totalmente independente do Estocástico: enquanto Stoch mede posição relativa, MACD mede aceleração. Geralmente dispara 1–2 candles após o G1, fechando o ciclo de confirmação.",
    },
    {
        id: "G9", pts: 3, cat: "Divergência",
        label: "Divergência Altista — preço ↓, RSI ↑",
        interp: "Janela de 5 barras: o preço fez um fundo mais baixo enquanto o RSI fez um fundo mais alto. Esse descasamento revela que cada nova queda do preço está sendo feita com menos pressão vendedora — \"hidden buying\". Compradores institucionais estão absorvendo a oferta nos fundos sem ainda mover o preço. É o sinal mais qualitativo do sistema: captura a intenção do mercado antes do movimento visível, frequentemente antecipando reversões violentas.",
    },
    {
        id: "G4", pts: 2, cat: "Tendência",
        label: "EMA9 cruza acima da EMA21",
        interp: "EMA (Exponential Moving Average) dá peso maior aos preços recentes. EMA9 reage a ~9 candles; EMA21 a ~21. O cruzamento de uma média rápida sobre uma mais lenta é o clássico \"golden cross de curto prazo\". Não é antecipação — é confirmação estrutural. Enquanto G1/G9 capturam intenção, o G4 confirma que o movimento já materializou e está sendo seguido. Sinaliza que a reversão deixou de ser hipótese e virou tendência observável.",
    },
    {
        id: "G11", pts: 2, cat: "Tendência",
        label: "Canal Linear Altista (slope > 0)",
        interp: "Aplica regressão linear nas máximas E nas mínimas dos últimos 20 candles. Se ambos os slopes (coeficientes angulares) forem positivos, existe um canal geometricamente altista — tanto topos quanto fundos crescentes. Diferente do G7 (estrutura discreta de fundos), G11 mede a inclinação contínua. Confirma que a pressão compradora não é pontual, mas sustentada geometricamente ao longo do período.",
    },
    {
        id: "G7", pts: 2, cat: "Tendência",
        label: "Três Fundos Locais Ascendentes",
        interp: "Identifica os mínimos locais (pontos em que o low é menor que os 5 candles à esquerda e à direita) e checa se os 3 mais recentes estão em ordem crescente. É a definição clássica de Charles Dow para tendência de alta: \"cada fundo mais alto que o anterior\". Significa que vendedores estão recuando — não conseguem mais empurrar o preço abaixo do mínimo anterior. Sinal estrutural puro, sem dependência de osciladores.",
    },
    {
        id: "G3", pts: 2, cat: "Estrutura",
        label: "Preço próximo do Suporte 20D (+1×ATR)",
        interp: "Suporte_20D = menor mínima dos últimos 20 candles. ATR (Average True Range) = volatilidade absoluta média do período. Se o preço atual está abaixo de suporte_20D + 1×ATR, ele tocou ou penetrou levemente a zona de absorção institucional histórica. Nesses níveis, ordens de compra acumuladas tendem a ser executadas (\"magnetismo de suporte\"). A tolerância de 1×ATR evita falsos positivos em ativos voláteis.",
    },
    {
        id: "G8", pts: 1, cat: "Estrutura",
        label: "Preço encostando na Banda Inferior de Bollinger",
        interp: "Bollinger Bands = média móvel ± 2 desvios-padrão. Estatisticamente, 95% dos preços ficam dentro das bandas. Tocar a banda inferior significa que o preço está em um extremo de volatilidade. Quando isso coincide com compressão das bandas (volatilidade baixa), há setup pré-expansão: o mercado está \"acumulando energia\" para um movimento direcional. Vale +1pt apenas porque sozinho é fraco, mas combinado com osciladores ganha força.",
    },
    {
        id: "G10", pts: 3, cat: "Liquidez",
        label: "Zona de Demanda Histórica (swing low 60D)",
        interp: "Mapeia todos os mínimos locais dos últimos 60 candles e verifica se o preço atual está dentro de ±1 ATR de algum deles. Esses swing lows são onde grandes players historicamente acumularam posição — o \"mapa institucional\" do ativo. Quando o preço retorna a essas zonas, a tendência é encontrar absorção pela mesma demanda que segurou anteriormente. Junto com G5 (volume), forma o gatilho mais correlacionado com os maiores ganhos da base histórica.",
    },
    {
        id: "G5", pts: 1, cat: "Liquidez",
        label: "Volume ≥ 1.5× Média 20D",
        interp: "Volume é a única variável fundamental verdadeiramente independente — não é derivado do preço. Volume 50% acima da média recente sinaliza presença institucional ativa: alguém grande está negociando deliberadamente. Em combinação com G10 (zona de demanda), confirma que essa institucional é compradora. Vale apenas +1pt isoladamente porque pode ocorrer em qualquer direção, mas tem efeito multiplicador junto com outros gatilhos.",
    },
]

const GATILHOS_BAIXA = [
    {
        id: "B1", pts: 3, cat: "Oscilador",
        label: "Cruzamento Estocástico em Sobrecompra",
        interp: "Espelho exato do G1. Quando %K cruza abaixo de %D dentro da zona > 75, significa que (1) o preço estava no topo do range recente e (2) a velocidade da subida acabou de se reverter. Mais importante: capta o ponto em que compradores começam a vender suas posições. Em ativos brasileiros, esse cruzamento frequentemente precede correções de 5–15% em poucos dias úteis, especialmente após rallies prolongados.",
    },
    {
        id: "B2", pts: 2, cat: "Oscilador",
        label: "RSI(14) > 65 — Sobrecompra Extrema",
        interp: "Quando o RSI ultrapassa 65, a pressão compradora dos últimos 14 períodos foi excessiva — o preço subiu mais rápido do que conseguiria sustentar fundamentalmente. Sem demanda nova entrando, a oferta latente se materializa e o preço cai com violência (a queda é tipicamente mais rápida que a subida que a precedeu). Threshold 65 em vez de 70 antecipa o sinal — ativos brasileiros raramente esticam até RSI 70+ sem reverter.",
    },
    {
        id: "B6", pts: 2, cat: "Oscilador",
        label: "MACD Histogram cruza zero para baixo",
        interp: "Espelho do G6: quando o Diff do MACD cai abaixo de zero, a média rápida desceu abaixo da linha sinal — o impulso de curto prazo se tornou negativo. Confirma desaceleração de momentum independente do Estocástico. É o sinal de que vendedores já estão dominando o flow, mesmo que o preço ainda não tenha caído visivelmente. Tipicamente coincide com B1 dentro de 1–2 candles, formando consenso de reversão.",
    },
    {
        id: "B7", pts: 3, cat: "Divergência",
        label: "Divergência Baixista — preço ↑, RSI ↓",
        interp: "Janela de 5 barras: preço fez topo mais alto, RSI fez topo mais baixo. Cada nova alta do preço está sendo feita com menos força — \"hidden selling\". Players institucionais estão distribuindo posição nos topos sem mover o preço para baixo ainda, mas a magnitude da compra está diminuindo. Como o G9 para o lado contrário, é o sinal mais qualitativo da família baixa: capta intenção de distribuição antes do rompimento visível.",
    },
    {
        id: "B4", pts: 2, cat: "Tendência",
        label: "EMA9 cruza abaixo da EMA21",
        interp: "O \"death cross de curto prazo\". A média rápida (9 candles) cruza para baixo da média de médio prazo (21 candles), confirmando que a queda recente é estrutural, não ruído. Como o G4 inverso: não antecipa, mas confirma. Quando dispara, transforma uma hipótese de reversão em fato observável. Combinado com B1/B7, eleva o sinal de \"possível pull-back\" para \"reversão de tendência\".",
    },
    {
        id: "B9", pts: 2, cat: "Tendência",
        label: "Canal Linear Baixista (slope < 0)",
        interp: "Regressão linear nos topos E nos fundos das últimas 20 barras com ambos os slopes negativos. Espelho do G11: a pressão vendedora não é pontual, está geometricamente sustentada — topos e fundos sequencialmente menores. Distingue uma queda real (estrutural) de um simples spike vendedor (pontual). Tendências bem definidas, mesmo de curtíssimo prazo, geram opções com gamma muito alto em strikes próximos.",
    },
    {
        id: "B5", pts: 2, cat: "Tendência",
        label: "Três Topos Locais Descendentes",
        interp: "Identifica os máximos locais (highs maiores que os 5 candles à esquerda e à direita) e verifica se os 3 mais recentes estão em ordem decrescente. É a definição clássica de Dow para tendência de baixa: \"cada topo mais baixo que o anterior\". Significa que compradores estão recuando — não conseguem mais empurrar o preço acima do máximo anterior. Sinal puramente estrutural, sem dependência de osciladores.",
    },
    {
        id: "B3", pts: 2, cat: "Estrutura",
        label: "Preço próximo da Resistência 20D (−1×ATR)",
        interp: "Resistência_20D = maior máxima dos últimos 20 candles. Quando o preço sobe até resistência_20D − 1×ATR (perto mas não acima), ele tocou a zona onde ordens de venda institucionais historicamente foram executadas. Esses níveis funcionam como \"teto técnico\": vendedores que aguardavam preços melhores ativam suas ordens, criando oferta súbita. A tolerância de ATR é simétrica ao G3, calibrada para a volatilidade do ativo.",
    },
    {
        id: "B8", pts: 3, cat: "Liquidez",
        label: "Zona de Oferta Histórica (swing high 60D)",
        interp: "Mapeia todos os máximos locais dos últimos 60 candles. Quando o preço atual está dentro de ±1 ATR de algum desses swing highs, ele atingiu uma zona de oferta institucional histórica — local onde grandes players já realizaram lucros ou abriram shorts no passado. Espelho exato do G10: o \"mapa institucional inverso\" do ativo. Vale +3pts porque é um dos gatilhos mais correlacionados com PUTs de maior performance na base histórica.",
    },
]

const CAT_COLORS: Record<string, { bg: string; text: string }> = {
    "Oscilador":  { bg: "var(--dw-blue-soft)",  text: "var(--dw-blue)"  },
    "Divergência":{ bg: "#EDE9FE",               text: "#7C3AED"         },
    "Tendência":  { bg: "#FEF3C7",               text: "#92400E"         },
    "Estrutura":  { bg: "var(--dw-bg-soft)",     text: "var(--dw-ink)"   },
    "Liquidez":   { bg: "var(--dw-green-soft)",  text: "var(--dw-green)" },
}

const OTM_TABLE = [
    { grupo: "Alta volatilidade",       pct: "12%",  ativos: "MGLU3, BEEF3", razao: "Ativos com IV histórica > 40% suportam strikes muito distantes — opções baratas e com gamma explosivo." },
    { grupo: "Volatilidade média-alta", pct: "10%",  ativos: "BRKM5, USIM5, ASAI3, MRVE3, BRAV3", razao: "Setores cíclicos (siderurgia, varejo, petróleo) com IV entre 35–40% — equilibram alavancagem e probabilidade." },
    { grupo: "Volatilidade média",      pct: "7–8%", ativos: "VALE3, SUZB3, LREN3, RADL3, GGBR4, GOAU4, KLBN11", razao: "Blue chips com IV de 25–32% — strikes muito distantes ficam improváveis no DTE 10–45." },
    { grupo: "Baixa volatilidade",      pct: "5–6%", ativos: "ITUB4, BBDC4, ABEV3, BBSE3, BBAS3, SANB11, BPAC11, WEGE3, EGIE3, PETR4", razao: "Bancos e utilities com IV < 25% — strikes mais próximos do ATM para ter prêmio operável." },
    { grupo: "ETF (ultra-baixa)",       pct: "4%",   ativos: "BOVA11", razao: "Diversificação intrínseca do ETF reduz IV a 15–20% — strikes muito próximos do preço atual." },
]

const EXEMPLOS = [
    {
        ticker: "MGLU3", opcao: "MGLUQ833", resultado: "+455%", alvo: "Alvo 2",
        tipo: "CALL" as const, data: "01/Mai/2026 — 14:15",
        gatilhos: [
            { id: "G1", pts: 3, label: "Stoch em sobrevenda" },
            { id: "G2", pts: 2, label: "RSI < 35" },
            { id: "G10",pts: 3, label: "Zona de demanda" },
            { id: "G5", pts: 1, label: "Volume 2.1×" },
            { id: "⏰", pts: 3, label: "Bônus horário (14:15)" },
        ],
        scoreAlta: 12, scoreBaixa: 3,
        entrada: "R$ 0,32", alvo1: "R$ 0,42 (+31%)", alvo2: "R$ 1,60 (+400%)", stop: "R$ 0,19",
    },
    {
        ticker: "BBSE3", opcao: "BBSER376", resultado: "+26%", alvo: "Alvo 1",
        tipo: "PUT" as const, data: "Jun/2026 — 14:00",
        gatilhos: [
            { id: "B1", pts: 3, label: "Stoch em sobrecompra" },
            { id: "B2", pts: 2, label: "RSI > 65" },
            { id: "B3", pts: 2, label: "Resistência 20D" },
            { id: "B8", pts: 3, label: "Zona de oferta" },
            { id: "⏰", pts: 3, label: "Bônus horário (14:00)" },
        ],
        scoreAlta: 0, scoreBaixa: 13,
        entrada: "R$ 1,20", alvo1: "R$ 1,50 (+25%)", alvo2: "R$ 3,00 (+150%)", stop: "R$ 0,70",
    },
]

// ── Componente ────────────────────────────────────────────────────────────────

export default function SobrePage() {
    return (
        <main className="main-content">

            {/* Header */}
            <div className="page-header">
                <div>
                    <Link href="/signals" className="flex items-center gap-1.5 text-sm text-dw-ink-muted hover:text-dw-blue mb-3 transition-colors">
                        <ArrowLeft className="w-4 h-4" />
                        Voltar para Sinais
                    </Link>
                    <h1 className="font-serif">Como os Sinais são Gerados</h1>
                    <p className="mt-3 text-dw-ink-light text-lg max-w-3xl leading-relaxed">
                        Pipeline completo de 11 etapas — do dado bruto ao sinal operacional — com
                        Black-Scholes, 19 gatilhos técnicos e filtro obrigatório de R/R ≥ 0.8×.
                        Cada etapa abaixo explica não só <em>o que</em> o motor faz, mas <em>por quê</em>.
                    </p>
                </div>
            </div>

            {/* ── 1. Pipeline ── */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <GitMerge className="w-4 h-4" />
                    <span className="text-xs font-extrabold uppercase tracking-widest">Pipeline de Execução — 11 Etapas</span>
                </div>
                <div className="space-y-3">
                    {PIPELINE.map(({ n, label, desc }) => (
                        <div key={n} className="card flex items-start gap-5">
                            <span
                                className="font-mono text-sm font-bold flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
                                style={{ background: "var(--dw-blue-soft)", color: "var(--dw-blue)" }}
                            >
                                {n}
                            </span>
                            <div className="flex-1">
                                <p className="font-semibold text-dw-ink text-base mb-2">{label}</p>
                                <p className="text-sm text-dw-ink-mid leading-relaxed">{desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── 2. Sistema de Score ── */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <Target className="w-4 h-4" />
                    <span className="text-xs font-extrabold uppercase tracking-widest">Sistema de Score — Lógica Aditiva</span>
                </div>
                <div className="card mb-4">
                    <p className="text-base text-dw-ink-mid leading-relaxed mb-5">
                        Sistemas de trading tradicionais usam regras binárias: <em>"se média rápida cruza a lenta, compre"</em>.
                        O problema é que toda regra binária falha quando o mercado muda de regime — gera muitos falsos positivos.
                        O motor deste sistema usa <strong className="text-dw-ink">lógica aditiva de consenso</strong>: avalia o ativo
                        simultaneamente sob as óticas CALL e PUT, somando evidências independentes de fontes técnicas diferentes
                        (osciladores, tendência, estrutura, liquidez). O sinal é emitido apenas quando múltiplos gatilhos
                        convergem na mesma direção — reduzindo drasticamente a taxa de falsos sinais.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="p-4 rounded-lg" style={{ background: "var(--dw-bg-soft)" }}>
                            <p className="font-semibold text-dw-ink text-base mb-2">Score de ALTA</p>
                            <p className="text-sm text-dw-ink-mid leading-relaxed">11 gatilhos altistas (+1 a +3 pts cada). Se o total ≥ 5 e maior que o de baixa → emite CALL.</p>
                        </div>
                        <div className="p-4 rounded-lg" style={{ background: "var(--dw-bg-soft)" }}>
                            <p className="font-semibold text-dw-ink text-base mb-2">Score de BAIXA</p>
                            <p className="text-sm text-dw-ink-mid leading-relaxed">8 gatilhos baixistas (+1 a +3 pts cada). Se o total ≥ 5 e maior que o de alta → emite PUT.</p>
                        </div>
                        <div className="p-4 rounded-lg" style={{ background: "var(--dw-bg-soft)" }}>
                            <p className="font-semibold text-dw-ink text-base mb-2">Bônus de Horário</p>
                            <p className="text-sm text-dw-ink-mid leading-relaxed">Aplicado em ambos os lados — captura janelas de maior liquidez: 10h–11h30 (+2), 13h–15h (+3), 15h–16h30 (+1).</p>
                        </div>
                    </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                        { range: "Score 5–6", label: "~30% dos sinais", sub: "Confiança média",       color: "var(--dw-ink-muted)" },
                        { range: "Score 7–9", label: "~50% dos sinais", sub: "Confiança alta",        color: "var(--dw-blue)" },
                        { range: "Score 10+", label: "~20% dos sinais", sub: "Altíssima confiança",   color: "var(--dw-green)" },
                        { range: "< 5 pts",   label: "SEM SINAL",       sub: "Descartado",            color: "var(--dw-red)" },
                    ].map(({ range, label, sub, color }) => (
                        <div key={range} className="card text-center">
                            <span className="font-mono font-bold text-lg" style={{ color }}>{range}</span>
                            <span className="label mt-1">{label}</span>
                            <span className="text-xs text-dw-ink-muted">{sub}</span>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── 3. Gatilhos ALTA ── */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <TrendingUp className="w-4 h-4 text-dw-green" />
                    <span className="text-xs font-extrabold uppercase tracking-widest text-dw-green">11 Gatilhos de ALTA → Sinal CALL</span>
                </div>
                <div className="space-y-3">
                    {GATILHOS_ALTA.map(({ id, pts, cat, label, interp }) => {
                        const c = CAT_COLORS[cat]
                        return (
                            <div key={id} className="card flex items-start gap-5">
                                <div className="flex-shrink-0 flex flex-col items-center gap-1.5 w-14">
                                    <span className="font-mono text-sm font-bold text-dw-green bg-emerald-50 px-2 py-1 rounded w-full text-center">{id}</span>
                                    <span className="text-[11px] font-bold px-1.5 py-0.5 rounded-full w-full text-center"
                                        style={{ background: "var(--dw-green-soft)", color: "var(--dw-green)" }}>
                                        +{pts}pts
                                    </span>
                                    <span className="text-[10px] font-semibold px-1 py-0.5 rounded text-center w-full"
                                        style={{ background: c.bg, color: c.text }}>
                                        {cat}
                                    </span>
                                </div>
                                <div className="flex-1">
                                    <p className="font-semibold text-dw-ink text-base mb-2">{label}</p>
                                    <p className="text-sm text-dw-ink-mid leading-relaxed">{interp}</p>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </section>

            {/* ── 4. Gatilhos BAIXA ── */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <TrendingDown className="w-4 h-4 text-dw-red" />
                    <span className="text-xs font-extrabold uppercase tracking-widest text-dw-red">8 Gatilhos de BAIXA → Sinal PUT</span>
                </div>
                <div className="space-y-3">
                    {GATILHOS_BAIXA.map(({ id, pts, cat, label, interp }) => {
                        const c = CAT_COLORS[cat]
                        return (
                            <div key={id} className="card flex items-start gap-5">
                                <div className="flex-shrink-0 flex flex-col items-center gap-1.5 w-14">
                                    <span className="font-mono text-sm font-bold text-dw-red bg-red-50 px-2 py-1 rounded w-full text-center">{id}</span>
                                    <span className="text-[11px] font-bold px-1.5 py-0.5 rounded-full w-full text-center"
                                        style={{ background: "var(--dw-red-soft)", color: "var(--dw-red)" }}>
                                        +{pts}pts
                                    </span>
                                    <span className="text-[10px] font-semibold px-1 py-0.5 rounded text-center w-full"
                                        style={{ background: c.bg, color: c.text }}>
                                        {cat}
                                    </span>
                                </div>
                                <div className="flex-1">
                                    <p className="font-semibold text-dw-ink text-base mb-2">{label}</p>
                                    <p className="text-sm text-dw-ink-mid leading-relaxed">{interp}</p>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </section>

            {/* ── 5. OTM dinâmico ── */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <Zap className="w-4 h-4 text-dw-blue" />
                    <span className="text-xs font-extrabold uppercase tracking-widest">Seleção de Strike — OTM Dinâmico por Volatilidade</span>
                </div>
                <div className="card mb-4 text-center">
                    <p className="text-base text-dw-ink-mid leading-relaxed max-w-3xl mx-auto">
                        O motor não usa a mesma distância OTM para todos os papéis. Ativos mais voláteis suportam
                        strikes distantes (opções baratas, maior gamma, mais alavancagem); ativos defensivos precisam
                        de strikes próximos para que a opção tenha prêmio operável. Após calcular o strike teórico, o
                        sistema valida contra a grade real da B3 via scraping em <strong className="text-dw-ink">opcoes.net.br</strong> —
                        substituindo o prêmio estimado pelo prêmio de tela efetivamente negociado.
                    </p>
                </div>
                <div className="space-y-3">
                    {OTM_TABLE.map(({ grupo, pct, ativos, razao }) => (
                        <div key={grupo} className="card flex flex-col items-center text-center gap-3 py-6">
                            <span
                                className="font-mono font-bold text-xl px-4 py-2 rounded-lg"
                                style={{ background: "var(--dw-blue-soft)", color: "var(--dw-blue)" }}
                            >
                                {pct}
                            </span>
                            <p className="font-semibold text-dw-ink text-lg">{grupo}</p>
                            <p className="text-base text-dw-ink-mid leading-relaxed max-w-2xl">{razao}</p>
                            <p className="text-sm text-dw-ink-muted font-mono">{ativos}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── 6. DTE + Black-Scholes ── */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <Clock className="w-4 h-4" />
                    <span className="text-xs font-extrabold uppercase tracking-widest">DTE, IV Histórica & Black-Scholes</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div className="card flex flex-col items-center text-center gap-3 py-6">
                        <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: "var(--dw-blue-soft)" }}>
                            <Clock className="w-6 h-6" style={{ color: "var(--dw-blue)" }} />
                        </div>
                        <p className="font-semibold text-dw-ink text-lg">Vencimento (DTE)</p>
                        <p className="text-base text-dw-ink-mid leading-relaxed max-w-xs">
                            DTE = dias úteis até o vencimento. A B3 padroniza opções com vencimento na <strong className="text-dw-ink">3ª sexta-feira</strong> de cada mês.
                            A janela aceita é <strong className="text-dw-ink">10–45 dias úteis</strong>:
                            abaixo de 10, o theta-decay (perda por tempo) devora o prêmio antes do movimento direcional;
                            acima de 45, o gamma fica fraco demais, exigindo movimento desproporcional.
                        </p>
                    </div>
                    <div className="card flex flex-col items-center text-center gap-3 py-6">
                        <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: "var(--dw-blue-soft)" }}>
                            <Activity className="w-6 h-6" style={{ color: "var(--dw-blue)" }} />
                        </div>
                        <p className="font-semibold text-dw-ink text-lg">IV Histórica</p>
                        <p className="text-base text-dw-ink-mid leading-relaxed max-w-xs">
                            Calculada via desvio padrão dos log-returns dos <strong className="text-dw-ink">últimos 20 dias</strong>,
                            anualizada por √252 (dias úteis no ano). Ex.: IV 32% = o ativo oscila ±32% ao ano (1 desvio-padrão).
                            Quanto maior a IV, mais caras as opções e maior o gamma esperado. Fallback de 40% se dados insuficientes.
                        </p>
                    </div>
                    <div className="card flex flex-col items-center text-center gap-3 py-6">
                        <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: "var(--dw-blue-soft)" }}>
                            <BarChart2 className="w-6 h-6" style={{ color: "var(--dw-blue)" }} />
                        </div>
                        <p className="font-semibold text-dw-ink text-lg">Black-Scholes</p>
                        <p className="text-base text-dw-ink-mid leading-relaxed max-w-xs">
                            Modelo matemático clássico que precifica opções europeias a partir de 5 inputs:
                            preço, strike, tempo, volatilidade e taxa Selic (10,75%). Para opções americanas
                            da B3 em strikes OTM, a aproximação é muito sólida.
                            Quando há prêmio real de tela disponível, ele substitui a estimativa.
                        </p>
                    </div>
                </div>
            </section>

            {/* ── 7. Estrutura de saída ── */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <Shield className="w-4 h-4 text-dw-blue" />
                    <span className="text-xs font-extrabold uppercase tracking-widest">Estrutura de Entrada, Alvos & Filtro R/R</span>
                </div>
                <div className="card mb-4">
                    <p className="text-base text-dw-ink-mid leading-relaxed mb-5">
                        Com prêmio definido, a estrutura é montada automaticamente. Os múltiplos (+25%, +150%, +400%, −42%)
                        foram calibrados a partir da base histórica de 22 operações: representam os pontos onde o R/R x
                        probabilidade maximiza a expectância. O filtro final de R/R garante que mesmo sinais de score alto
                        sejam descartados se a assimetria não for favorável.
                    </p>
                    <div className="overflow-x-auto">
                        <table className="w-full text-base">
                            <thead>
                                <tr style={{ borderBottom: "2px solid var(--dw-rule)" }}>
                                    <th className="text-left py-4 px-2 label font-semibold text-sm">Nível</th>
                                    <th className="text-right py-4 px-2 label font-semibold text-sm">Cálculo</th>
                                    <th className="text-right py-4 px-2 label font-semibold text-sm">Exemplo (prêmio R$0,35)</th>
                                    <th className="text-right py-4 px-2 label font-semibold text-sm">Lógica</th>
                                </tr>
                            </thead>
                            <tbody className="text-base">
                                {[
                                    { nivel: "Entrada Mín", calc: "prêmio × 0.90", ex: "R$ 0,32",          log: "Spread do book" },
                                    { nivel: "Entrada Máx", calc: "prêmio × 1.10", ex: "R$ 0,38",          log: "Spread do book" },
                                    { nivel: "Alvo 1",      calc: "prêmio × 1.25", ex: "R$ 0,44 (+25%)",   log: "Realização parcial (50%)" },
                                    { nivel: "Alvo 2",      calc: "prêmio × 2.50", ex: "R$ 0,88 (+150%)",  log: "Alvo técnico principal" },
                                    { nivel: "Alvo Final",  calc: "prêmio × 5.00", ex: "R$ 1,75 (+400%)",  log: "Especulação remanescente" },
                                    { nivel: "Stop Loss",   calc: "prêmio × 0.58", ex: "R$ 0,20 (−42%)",   log: "Proteção absoluta" },
                                ].map(({ nivel, calc, ex, log }) => (
                                    <tr key={nivel} style={{ borderBottom: "1px solid var(--dw-rule-soft)" }}>
                                        <td className="py-4 px-2 font-semibold text-dw-ink">{nivel}</td>
                                        <td className="py-4 px-2 text-right font-mono text-dw-ink-muted">{calc}</td>
                                        <td className="py-4 px-2 text-right font-mono text-dw-blue font-semibold">{ex}</td>
                                        <td className="py-4 px-2 text-right text-dw-ink-mid">{log}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <div className="mt-6 p-5 rounded-lg text-base leading-relaxed" style={{ background: "var(--dw-bg-soft)", color: "var(--dw-ink-mid)" }}>
                        <strong className="text-dw-ink">Filtro R/R obrigatório:</strong> Se R/R do Alvo 1 {"<"} 0.8× → sinal descartado automaticamente.{" "}
                        A matemática da expectância com R/R=0.8 e 82% acerto: <strong className="text-dw-ink">(0.82 × 0.8) − (0.18 × 1.0) = +0.476 por operação</strong> —
                        ou seja, +47,6% de retorno esperado por trade, em média, no longo prazo.
                    </div>
                </div>
            </section>

            {/* ── 8. Exemplos reais ── */}
            <section className="mb-12">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <BarChart2 className="w-4 h-4" />
                    <span className="text-xs font-extrabold uppercase tracking-widest">Exemplos Reais Validados na Planilha</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {EXEMPLOS.map((ex) => (
                        <div key={ex.opcao} className="card" style={{
                            borderColor: ex.tipo === "CALL" ? "var(--dw-green)" : "var(--dw-red)",
                            borderWidth: "1.5px"
                        }}>
                            <div className="flex items-start justify-between mb-4">
                                <div>
                                    <span className="font-mono font-bold text-dw-ink text-base">{ex.ticker}</span>
                                    <span className="mx-1.5 text-dw-ink-muted">·</span>
                                    <span className="font-mono text-sm text-dw-ink-muted">{ex.opcao}</span>
                                    <p className="text-xs text-dw-ink-muted mt-1">{ex.data}</p>
                                </div>
                                <div className="text-right">
                                    <span
                                        className="font-bold text-2xl"
                                        style={{ color: ex.tipo === "CALL" ? "var(--dw-green)" : "var(--dw-red)" }}
                                    >
                                        {ex.resultado}
                                    </span>
                                    <p className="text-xs text-dw-ink-muted">{ex.alvo}</p>
                                </div>
                            </div>

                            <div className="space-y-1.5 mb-4">
                                {ex.gatilhos.map(({ id, pts, label }) => (
                                    <div key={id} className="flex items-center gap-2 text-sm">
                                        <span className="font-mono font-bold w-8 text-center flex-shrink-0"
                                            style={{ color: ex.tipo === "CALL" ? "var(--dw-green)" : "var(--dw-red)" }}>
                                            {id}
                                        </span>
                                        <span className="text-dw-ink-mid flex-1">{label}</span>
                                        <span className="font-bold flex-shrink-0"
                                            style={{ color: ex.tipo === "CALL" ? "var(--dw-green)" : "var(--dw-red)" }}>
                                            +{pts}
                                        </span>
                                    </div>
                                ))}
                            </div>

                            <div className="flex items-center gap-3 pt-3 border-t text-sm"
                                style={{ borderColor: "var(--dw-rule-soft)" }}>
                                <span className="font-semibold text-dw-ink">
                                    Score {ex.tipo}: {ex.tipo === "CALL" ? ex.scoreAlta : ex.scoreBaixa}pts
                                </span>
                                <span className="text-dw-ink-muted">vs {ex.tipo === "CALL" ? ex.scoreBaixa : ex.scoreAlta}pts oposto</span>
                                <span className="ml-auto font-mono text-dw-blue">{ex.entrada}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* ── 9. Performance ── */}
            <section className="mb-10">
                <div className="flex items-center gap-2 mb-5 pb-2" style={{ borderBottom: "2.5px solid var(--dw-ink)" }}>
                    <Activity className="w-4 h-4" />
                    <span className="text-xs font-extrabold uppercase tracking-widest">Performance Histórica — Base Validada</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
                    {[
                        { label: "Operações",       value: "22",      sub: "Mar–Mai/2026",        color: "text-dw-ink" },
                        { label: "Taxa de Acerto",  value: "82%",     sub: "18 wins / 4 stops",   color: "text-dw-green" },
                        { label: "Ganho médio",     value: "+82,7%",  sub: "por operação (wins)",  color: "text-dw-green" },
                        { label: "Perda média",     value: "−39,5%",  sub: "por operação (stops)", color: "text-dw-red" },
                        { label: "Expectância",     value: "+60,4%",  sub: "por operação",         color: "text-dw-blue" },
                        { label: "Maior resultado", value: "+455%",   sub: "MGLUQ833 — Alvo 2",   color: "text-dw-yellow" },
                    ].map(({ label, value, sub, color }) => (
                        <div key={label} className="card flex flex-col items-center text-center gap-1 py-5">
                            <span className="label text-sm">{label}</span>
                            <span className={`text-3xl font-bold font-mono ${color}`}>{value}</span>
                            <span className="text-sm text-dw-ink-muted">{sub}</span>
                        </div>
                    ))}
                </div>
                <p className="text-base text-dw-ink-mid leading-relaxed text-center max-w-3xl mx-auto">
                    Base: planilha TP Capital (22 operações confirmadas, período março a maio de 2026).
                    Dados históricos não garantem resultados futuros — performance passada deve ser interpretada
                    como evidência estatística de que o modelo capta padrões reais, não como promessa de retorno.
                </p>
            </section>

            {/* Aviso legal */}
            <div className="card border-l-4" style={{ borderLeftColor: "var(--dw-yellow)" }}>
                <div className="flex items-start gap-3">
                    <BookOpen className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "#D97706" }} />
                    <p className="text-sm text-dw-ink-mid leading-relaxed">
                        <strong className="text-dw-ink">Aviso legal:</strong> Sistema exclusivamente educacional e analítico.
                        Prêmios são estimativas baseadas em Black-Scholes com dados históricos —
                        dados reais de opções requerem acesso à chain da B3 (OpLab, Nelogica, Profit).
                        Opções podem perder 100% do capital investido. Consulte assessor habilitado CVM/CNPI antes de operar.
                    </p>
                </div>
            </div>

        </main>
    )
}
